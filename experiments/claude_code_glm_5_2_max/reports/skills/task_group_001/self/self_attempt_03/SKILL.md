# HarborCRM CRM-Marketing Solver

Solve HarborCRM event/trade-show/import reconciliation tasks that return a single JSON object conforming to a provided `answer_template.json`. These tasks reconcile sponsor orders, finance invoices, badge scans, CRM accounts/contacts/opportunities, campaign members, trade-show exhibitors, meeting interest, and import batches into an import-ready CRM handoff.

## When to use

Use whenever a task asks you to: reconcile a HarborCRM event post-handoff, prepare a trade-show prospecting/campaign lead list, clean a CRM import batch, or produce sponsor-finance follow-up — and provides an output JSON schema (`answer_template.json`) plus a HarborCRM API. If a task instead asks for arbitrary free-text prose or operations unrelated to HarborCRM data, do not use this skill.

## Environment & API access

- HarborCRM is a **read-only** JSON API. Use `curl -s "<BASE><endpoint>" | python3 -m json.tool` (or pipe through `jq`).
- **Base URL:** use the remote base supplied in the environment access file (`<remote-env-url>`). Prompts may mention `127.0.0.1:8067` or a runner-supplied URL — prefer the remote base from the environment access file; never start or read a local `env/` service. If the runner explicitly hands you a different base URL at solve time, use that.
- Public GET endpoints (all return JSON; dataset is deterministic):
  - `GET /health`
  - `GET /api/events` · `GET /api/events/{event_id}` · `GET /api/events/{event_id}/orders` · `GET /api/events/{event_id}/badges` · `GET /api/events/{event_id}/sponsor_packages`
  - `GET /api/finance/invoices?event_id={event_id}`
  - `GET /api/crm/accounts` · `GET /api/crm/contacts` · `GET /api/crm/opportunities` · `GET /api/crm/campaign_members?event_id={event_id}`
  - `GET /api/tradeshows` · `GET /api/tradeshows/{show_id}/exhibitors` · `GET /api/tradeshows/{show_id}/meeting_interest`
  - `GET /api/import_batches` · `GET /api/import_batches/{batch_id}/raw_contacts` · `GET /api/import_batches/{batch_id}/suppression`
  - `GET /api/policies`
- **Never** call any POST/PUT/DELETE, judge, eval, or scoring endpoint. Read-only.
- `/api/events/{id}/orders` and `/api/events/{id}/sponsor_packages` return the same sponsor-order rows; either is fine.

## Universal solver workflow

Run these steps for every task. Do not skip.

1. **Read the task's `answer_template.json` first and treat it as law.** It defines the exact top-level keys, per-item required keys, field types, **allowed enum strings**, ordering rules, and numeric precision. Enum vocabularies and field shapes vary across tasks (e.g., one task uses `sensor_vendor_only`, another uses `sensor_only`; one splits sponsor money into `package_amount`/`paid_amount`/`open_balance`, another uses a single `amount_usd`). Always echo the template's exact strings — never substitute a synonym.
2. **Identify the task archetype** from the prompt (see table below) to pick endpoints.
3. **Fetch `/api/policies`** for the canonical enum lists (`sponsor_handoff.status_enums`, `prospecting.platform_enums`) and any sizing/qualification notes.
4. **Fetch the task's anchor record** (event detail, tradeshow, or import batch) and every endpoint the archetype table lists. Cache all responses.
5. **Join the data** using the decision tables below (sponsor status, badge exclusion, CRM create-vs-update, prospecting qualification, duplicate resolution, normalization, due dates).
6. **Compute aggregates** (revenue totals, pipeline/opportunity sums, action counts, platform/priority counts).
7. **Sort every list** exactly as the template specifies (ordering rules usually appear in the template; if absent, default to ascending by the first string key).
8. **Emit one JSON object only**, matching the template's required keys and nothing extra. No prose, no markdown fences, no trailing commas, no comments.

## Task archetypes → endpoints

| Archetype | Anchor | Endpoints to fetch |
|---|---|---|
| Event post-handoff reconciliation (sponsor statuses + lead handoff + finance follow-up) | `event_id` | `events/{id}`, `events/{id}/orders`, `events/{id}/badges`, `finance/invoices?event_id={id}`, `crm/accounts`, `crm/contacts`, `crm/opportunities`, `crm/campaign_members?event_id={id}`, `policies` |
| Trade-show prospecting / campaign lead list | `show_id` | `tradeshows`, `tradeshows/{id}/exhibitors`, `tradeshows/{id}/meeting_interest`, `crm/accounts`, `crm/contacts`, `policies` |
| Import-batch cleaning | `batch_id` | `import_batches`, `import_batches/{id}/raw_contacts`, `import_batches/{id}/suppression`, `crm/accounts`, `crm/contacts`, `policies` |

Some event tasks add badge-level decisions and campaign-member create/update/no-action decisions — same endpoints as the event archetype.

## Decision table A — Sponsor status classification

Inputs: sponsor order (`order_status`) + matching finance invoice (`status`, `paid_amount`, `amount`, `deferred_amount`). Match invoice to order by `account_id`+`event_id`.

Order of checks (first match wins):

| Condition | sponsor_status | Money fields |
|---|---|---|
| `order_status == "canceled"` (or missing/inactive) | **exclude** as `inactive_sponsor_record` (do not list in active sponsor_statuses) | — |
| invoice `status == "paid_deferred"` (paid in full, deferred revenue) | `paid_deferred` | package_amount = order.amount; paid_amount = invoice.paid_amount; open_balance = amount − paid_amount (0) |
| invoice `status == "open"` (or paid_amount < amount), order confirmed | `open_invoice` | package_amount = amount; paid_amount = paid_amount; open_balance = amount − paid_amount |
| `order_status == "proposal_sent"` and no invoice | `proposal_only` | package_amount = amount; invoice_id = null; paid_amount = 0; open_balance = 0 |
| account has no sponsor order for this event | `not_sponsor` (only when the template's allowed values include it) | amount = 0 |

- Use the template's money-field names: if it asks for `package_amount`/`paid_amount`/`open_balance` use those; if it asks for a single `amount_usd`, output `order.amount` (integer USD) for sponsors and `0` for `not_sponsor`.
- All money is **integer USD**. No decimals, no currency symbols.
- `invoice_id` is `null` when no invoice exists.

### Sponsor revenue rollup

- Group active sponsors by `sponsor_status` and sum `package_amount` (or `amount`) into per-status totals: `paid_deferred`, `open_invoice`, `proposal_only`.
- `open_invoice_balance` = sum of `open_balance` across `open_invoice` sponsors only.
- Unpaid / finance-follow-up set = sponsors with `open_balance > 0` (i.e., `open_invoice` with unpaid balance). `proposal_only` sponsors have no invoice and balance 0 → **not** finance-follow-up (they are sales/BD, not collections) unless the prompt explicitly says otherwise. `paid_deferred` → balance 0 → not follow-up.

## Decision table B — Badge exclusion classification & precedence

Evaluate every badge in this order; first match decides `classification` / `exclusion_reason`:

| # | Condition | classification | exclusion_reason | crm_action |
|---|---|---|---|---|
| 1 | `badge_type` is non-business (`student`, `press`, `staff`, `speaker`, …) | `excluded` | `non_business_badge` | `no_import` / `no_action` |
| 2 | Badge belongs to an **active** sponsor: `badge_type == "sponsor"`, OR `contact_name` ∈ an active (non-canceled) sponsor order's `ticket_contacts`, OR `company_name` matches an active sponsor account | `sponsor_attendee` | `sponsor_attendee` | `no_action` (sponsor already handled) |
| 3 | Badge belongs to a **canceled/inactive** sponsor order (contact in its `ticket_contacts` or company matches) | `excluded` | `inactive_sponsor_record` | `no_import` |
| 4 | Company's CRM account `status == "disqualified"` | `excluded` | `existing_disqualified` | `no_import` |
| 5 | Otherwise (business badge, not a sponsor, not disqualified, has contact info) | `qualified_non_sponsor_lead` | `null` | per table C |

- "Active sponsor" = any sponsor order whose `order_status` is **not** `canceled` (i.e., `confirmed` or `proposal_sent` are both active; `proposal_sent` sponsors are still sponsors, status `proposal_only`).
- Precedence rationale: non-business first (badge itself is invalid), then sponsor affiliation (active > inactive), then CRM disqualification, then qualified.
- A badge with `badge_type == "attendee"` whose company is a canceled sponsor is `inactive_sponsor_record` (table row 3), not `sponsor_attendee`.

## Decision table C — CRM create-vs-update (accounts / contacts / campaign members)

For each qualified lead / clean contact, resolve against existing CRM by **normalized email domain → account `domain`**, **exact normalized email → contact `email`**, and **exact normalized phone → contact `phone`**.

### Accounts
| Condition | `crm_account_action` | `existing_account_id` |
|---|---|---|
| An existing CRM account matches the company (domain match from email, or exact name match) | `update_existing` | that `account_id` |
| No existing account | `create_account` | `null` |

### Contacts
| Condition | `crm_contact_action` | `existing_contact_id` |
|---|---|---|
| Existing CRM contact matches normalized email **or** normalized phone **or** exact name within a matched account | `update_existing` | that `contact_id` |
| Account exists but no matching contact | `create_contact` | `null` |
| No account at all | `create_contact` | `null` |

### Campaign members (per event)
| Existing member for (account_id/event_id)? | `campaign_member_action` |
|---|---|
| No | `add_campaign_member` / `create` |
| Yes, status needs change | `update` / `update_campaign_member` |
| Yes, status already at target | `no_action` |
| Row suppressed/excluded | `no_import` |

- `target_status` for campaign members: sponsor who attended → `attended_sponsor`; sponsor registered only → `registered_sponsor`; non-sponsor qualified lead (badge scanned) → `attended`; excluded → `excluded`. Use only the template's allowed `target_status` values.
- Some tasks fold account+contact+member into one combined `crm_action` string (e.g., `create_account_contact_campaign_member`, `create_contact_campaign_member`, `add_campaign_member`, `update_campaign_member`). Use the template's exact combined enum.

## Decision table D — Trade-show prospecting qualification & exclusion

### Qualification
An exhibitor is a **qualified lead** iff it **makes or OEM-builds** target underwater platforms (AUV, ROV, Underwater Camera). Distributors, resellers, service/consulting operators, sensor-only vendors, and research bodies are **not** qualified even if they mention platforms, because they do not manufacture/OEM them.

Derive `platforms` from the exhibitor `description`, then **sort by the enum order** `AUV`, `ROV`, `Underwater Camera` (never by description word order):
- AUV: "AUV", "autonomous underwater vehicle", "AUV scout".
- ROV: "ROV", "remotely operated".
- Underwater Camera: "underwater camera", "camera array", "camera module", "camera manufacturer".

### CRM action for qualified exhibitors
- `crm_account_id` non-null on the exhibitor → `update_existing` (account already in CRM).
- `crm_account_id` null → `create_account`.
- Some exhibitors may carry their own `crm_account_id`; otherwise match by domain/name against `crm/accounts`.

### Priority tier & opportunity sizing (default policy)
Assign tier from meeting-interest data (`requested_demo`, `interest_score`):

| Tier | Rule | Opportunity USD |
|---|---|---|
| `A` | `requested_demo == true` **and** `interest_score >= 90` | 120000 |
| `B` | `requested_demo == true` **and** `interest_score >= 80` | 90000 |
| `C` | all other qualified leads | 50000 |

- **If the task prompt states explicit tier thresholds or amounts, override the defaults with the prompt's values.** Check `/api/policies` and the prompt for sizing constants before falling back to 120000/90000/50000.
- Exhibitors with no meeting-interest record: `requested_demo = false`, `interest_score = 0` → tier `C`.
- `total_estimated_opportunity_usd` = sum of opportunity estimates across qualified leads.

### Exclusion classification (relationship_type → exclusion_reason)
Infer the relationship from the description, then map to the template's allowed enum strings. **The enum strings differ between tasks** (e.g., `sensor_vendor_only` vs `sensor_only`) — always use the exact strings the template lists.

| Relationship (from description) | typical reason string |
|---|---|
| Distributor / reseller / dealer / sales agent ("does not manufacture", "reseller", "imported … brands") | `distributor_only` |
| Service / consulting / operates rented rigs / analytics-only SaaS (no hardware) | `service_only` |
| Sensor-only vendor / probes / water-quality instruments (no platform) | `sensor_vendor_only` **or** `sensor_only` (per template) |
| Research institute / university / lab | `research_only` |
| Other non-target (no platform build, none of the above) | `not_target_market` (only if the template allows it) |

### Ranking qualified leads (when the template requires a `rank`)
Sort by, in order: (1) `requested_demo == true` first; (2) `interest_score` descending; (3) broader platform coverage (count of platforms) descending; (4) `company_name` ascending. Assign 1-based contiguous `rank`.

## Decision table E — Normalization transforms

| Field | Transform |
|---|---|
| `normalized_email` | lowercase + strip surrounding whitespace. If empty/missing → `""` (empty string, not null). |
| `normalized_phone` | keep **digits only** (`[0-9]`), drop all punctuation/spaces/`+`/parens. Retain a leading `1` country code if present (e.g., `+1 (415) 555-0101` → `14155550101`; `415-555-0188` → `4155550188`). If empty/missing → `""`. |
| company/contact names | use as-is from the winning row; do not rename. |
| timestamps | pass through ISO string from the winning row unchanged. |

Normalization is applied **before** dedup, suppression matching, and CRM matching. Email match is case-insensitive after normalization; phone match is on the digit string.

## Decision table F — Duplicate resolution (import batches)

1. **Duplicate key = normalized email** (after table E). Rows with the same normalized email form one duplicate group. (Rows with no usable email are not grouped by phone; they stand alone.)
2. **Usability gate (run before dedup):** a row is *usable* if it has a non-empty normalized email **or** a non-empty normalized phone. A row with both empty → `missing_contact` → `crm_action = no_import`, removed.
3. **Suppression gate (run before dedup, after usability):** if the row's normalized email **or** normalized phone matches any entry in the batch's `suppression` list → `crm_action = suppress`, removed (reason `suppressed`). Suppression trumps CRM-existence.
4. **Winner selection** within a duplicate group (deterministic, in order):
   1. Highest **source priority**, where priority = the position of `source_name` in the template's `source_name` enum list (earlier = higher priority). Typical implied order: `badge_scan` > `sponsor_form` > `partner_upload` > `webinar_form` > `exhibitor_form` > `manual_upload`. If the template does not define an order, skip to (2).
   2. Earliest `captured_at` timestamp.
   3. Lowest `row_id` ascending (lexicographic).
   - Override with any explicit winner rule stated in the task prompt.
5. Losers are removed with reason `duplicate`. The winner's `clean_contact_id` and `source_row_id` both equal the winner's `row_id`.
6. `duplicate_summary.duplicate_keys`: one entry per group — `key` (normalized email), `winner_row_id`, `removed_row_ids` (losers). Sort by `key` ascending.
7. `removal_summary.removed_rows`: every removed row (`row_id`, `reason` ∈ {`duplicate`, `missing_contact`, `suppressed`}), sorted by `row_id` ascending. `unusable_removed_count` = missing_contact count; `suppressed_removed_count` = suppressed count.
8. `import_action_totals`: counts of `create_account`, `update_existing`, `no_import`, `suppress` across **all original rows** (winners counted by their action; removed rows counted by their removal reason). Verify: winners + removed = total raw rows.
9. `campaign_member_import_count` = number of surviving (non-removed) clean contacts — i.e. those with `crm_action` in {`create_account`, `update_existing`}.

## Decision table G — Due-date arithmetic

Due dates are computed from the **event record**, not from `/api/policies`:

- `lead_followup_due_date` / `lead_due_date` = `event.end_date` + `event.followup_days_after_end` days.
- `sponsor_followup_due_date` / `sponsor_finance_due_date` = `event.end_date` + `event.sponsor_followup_days_after_end` days.

Rules:
- Parse `end_date` as `YYYY-MM-DD`; add the integer number of days; format the result as `YYYY-MM-DD` (calendar addition, no time components).
- For import-batch / trade-show tasks with no event, due dates are typically omitted (follow the template).
- Task counts: `lead_task_count` = number of qualified lead accounts (one task per lead); `sponsor_finance_task_count` = number of unpaid-sponsor accounts with `open_balance > 0`.

## Decision table H — Pipeline & opportunity math

- **Event lead pipeline:** each qualified non-sponsor lead account gets `opportunity_amount` = `event.lead_opportunity_amount` (from the event record). `lead_pipeline_total` = Σ opportunity_amount over qualified leads.
- `open_opportunity_total_usd` / `open_opportunity_count` = sum and count of CRM `opportunities` for this event whose `stage` is **not** `closed_won` and **not** `closed_lost` (i.e., open: `proposal`, `qualification`, `negotiation`, etc.). Use the opportunity `amount`.
- `total_estimated_opportunity_usd` (trade-show) = Σ tier opportunity estimates (table D).
- `existing_crm_overlap_count` / `existing_crm_overlap_account_ids` (trade-show) = qualified exhibitors whose `crm_account_id` is non-null (or that match an existing CRM account). Sort account IDs ascending.
- All money integer USD; no rounding.

## Decision table I — Enums & allowed values

- Always pull canonical enums from `/api/policies`: `sponsor_handoff.status_enums` (`paid_deferred`, `open_invoice`, `proposal_only`, `not_sponsor`) and `prospecting.platform_enums` (`AUV`, `ROV`, `Underwater Camera`).
- **But the answer_template.json is the final authority for every enum string** in the output. Common per-task divergences to honor exactly:
  - sponsor money shape: `package_amount`/`paid_amount`/`open_balance` vs single `amount_usd`.
  - sensor exclusion: `sensor_vendor_only` (some tasks) vs `sensor_only` (others).
  - crm_action granularity: separate account/contact/member enums vs combined strings like `create_account_contact_campaign_member`.
  - sponsor_status presence of `not_sponsor`.
  - source_name enum ordering (used as dedup source priority).
- If a template allows a value, you may emit it; if it does not list a value, never invent it. When a real classification has no home in the template's enum, pick the closest allowed bucket (e.g., a software-only exhibitor with no `not_target_market` bucket → `service_only`).

## Decision table J — Sorting

Apply the template's stated ordering. If the template is silent, default to ascending by the first string key (then secondary string key). Recurring rules observed:

| List | Typical sort |
|---|---|
| `sponsor_statuses` | `account_name` ascending |
| `qualified_lead_accounts` / `qualified_exhibitors` | `account_name` / `company_name` ascending |
| `excluded_records` / `excluded_near_misses` / `excluded_exhibitors` | `company_name` ascending, then `contact_name` ascending |
| `badge_decisions` | `badge_id` ascending |
| `campaign_member_actions` | `subject_key` ascending |
| `badge_only_contacts` | `company_name` ascending |
| `clean_contacts` | `clean_contact_id` ascending |
| `duplicate_summary.duplicate_keys` | `key` ascending |
| `removal_summary.removed_rows` | `row_id` ascending |
| `ranked_leads` | `rank` ascending (1-based contiguous) |
| `platforms` (within an item) | enum order: AUV, ROV, Underwater Camera |
| ID lists (`existing_crm_overlap_account_ids`, etc.) | ascending |

## Cross-task consistency rules

- **One pass, one JSON.** Emit exactly one JSON object. No prose, no markdown fences, no keys beyond the template's required set.
- **Strings as-is.** Use account/contact/company names and IDs verbatim from the API — do not re-title-case, expand abbreviations, or translate.
- **Null vs empty string.** `invoice_id`, `existing_account_id`, `existing_contact_id`, `crm_account_id`, `exclusion_reason` (when allowed) are `null` when absent. `normalized_email` / `normalized_phone` are `""` (empty string) when absent — never null.
- **Integers only** for all counts and money. No floats, no `null` for numeric counts (use `0`).
- **Deterministic joins.** Match sponsors→invoices and badges→sponsors by `account_id`/`event_id`; match contacts/accounts by normalized email/phone/domain; match exhibitors→meeting_interest by `company_name`.
- **Exclusion precedence is global** (table B) across event tasks; apply it the same way for every badge.
- **Suppression always wins** over CRM-existence in import batches (a suppressed row is `suppress`, even if its email matches an existing CRM contact).
- **Read the prompt for overrides.** Tier sizing, winner tiebreaks, and "unpaid sponsor" definitions may be restated per task; prompt overrides the defaults in tables D/F/A.

## Common pitfalls

- Forgetting that `proposal_sent` orders are **active** sponsors (status `proposal_only`), not excluded — only `canceled` orders are excluded as `inactive_sponsor_record`.
- Listing `proposal_only` sponsors in finance follow-up — they have no invoice and balance 0, so they are not collections targets.
- Matching badges to sponsors by company name only and missing canceled-sponsor ticket contacts (must check `ticket_contacts` too).
- Emitting `sensor_only` when the template says `sensor_vendor_only` (or vice versa) — always copy the template's enum string.
- Computing due dates from `start_date` or from a hardcoded 7/3 — use the event's own `followup_days_after_end` / `sponsor_followup_days_after_end` added to `end_date`.
- Sorting `platforms` by description word order instead of the enum order AUV, ROV, Underwater Camera.
- Counting removed rows in `import_action_totals` incorrectly — removed rows are counted under their removal reason (`no_import`/`suppress`), and only surviving rows count toward `create_account`/`update_existing` and toward `campaign_member_import_count`.
- Rounding money or emitting decimals — all amounts are integer USD.
- Adding extra commentary fields "for clarity" — the template forbids undeclared fields.
