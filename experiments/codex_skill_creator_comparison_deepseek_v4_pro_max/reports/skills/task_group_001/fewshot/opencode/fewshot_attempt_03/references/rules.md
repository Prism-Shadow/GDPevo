# HarborCRM Business Rules Reference

This reference captures the detailed business rules derived from the HarborCRM policy endpoint and the recurring
patterns observed across event reconciliation, trade-show prospecting, and import-batch cleaning tasks.

---

## Contact hygiene

Contacts from any source (badge scans, raw imports, exhibitor lists) must be normalized before cross-referencing or
output. The normalization rules are:

### Email

1. Trim leading and trailing whitespace.
2. Convert to lowercase (ASCII lowercasing is sufficient).
3. If the result is empty or contains only whitespace, treat as missing (use `""` in output fields like
   `normalized_email`).

Examples:
- `" John.Doe@AcmeCorp.example "` → `"john.doe@acmecorp.example"`
- `"JANE.SMITH@bigco.example"` → `"jane.smith@bigco.example"`
- `" "` → `""` (treated as missing)

### Phone

1. Strip every character that is not an ASCII digit (`0-9`).
2. Do NOT strip a leading `1` — preserve the full digit sequence including country code.
3. If no digits remain, use `""`.

Examples:
- `"+1 (415) 555-0101"` → `"14155550101"`
- `"415-555-0188"` → `"4155550188"` (this still works for matching because CRM contacts also normalize to digits-only)
- `"1.206.555.0177"` → `"12065550177"`
- `"650 555 0144"` → `"6505550144"`
- `""` → `""`

### When to normalize

Normalize as soon as the record is loaded from the API. Use the normalized values for:
- Cross-reference matching (CRM contact lookup, dedup detection, suppression matching).
- Output fields named `normalized_email` and `normalized_phone`.

Never use raw/un-normalized values for matching — case or format mismatches cause false negatives.

---

## Sponsor classification

Sponsor status is determined by joining event orders with finance invoices on `account_id`.

### Active vs. inactive sponsors

A sponsor order is **active** when `order_status` is not `"canceled"`. Canceled orders are excluded from sponsor
statuses, sponsor revenue totals, and sponsor-attendee badge exclusions. Canceled orders are NOT `not_sponsor` in the
output — they are simply omitted from the sponsor section entirely.

### Status determination

For each active sponsor order, look up the invoice by `account_id`:

| Invoice status | Sponsor status | package_amount source | paid_amount | open_balance |
|---|---|---|---|---|
| `paid_deferred` | `paid_deferred` | invoice `amount` | invoice `paid_amount` | 0 |
| `open` | `open_invoice` | invoice `amount` | invoice `paid_amount` | `amount - paid_amount` |
| No invoice found | `proposal_only` | order `amount` | 0 | 0 |

The `invoice_id` field is `null` for proposal-only sponsors (no invoice exists).

### Sponsor revenue totals

Aggregate across all active sponsors:

- `paid_deferred` total → sum of `package_amount` for sponsors with status `paid_deferred`.
- `open_invoice` total → sum of `package_amount` for sponsors with status `open_invoice`.
- `proposal_only` total → sum of `package_amount` for sponsors with status `proposal_only`.
- `open_invoice_balance` → sum of `open_balance` for sponsors with status `open_invoice`.

All totals are integers in USD.

### Sponsor finance follow-up targets

Accounts requiring sponsor finance follow-up are those with status `open_invoice` or `proposal_only`.
The `sponsor_finance_accounts` list contains their account names, sorted ascending.

---

## Badge classification and lead qualification

The badge list from `/api/events/{event_id}/badges` needs classification into three categories:
`sponsor_attendee`, `qualified_non_sponsor_lead`, and `excluded`.

### Step 1: Match badges to sponsor accounts

Match each badge's `company_name` to the `account_name` of **active** sponsor orders (orders where `order_status` is not
`"canceled"`). Use case-insensitive comparison after trimming whitespace.

If the badge company matches an active sponsor → the badge is a `sponsor_attendee`. These are excluded from the qualified
lead list. Their `crm_action` and `target_status` in campaign-member actions depend on the task template — some templates
still need campaign-member records for sponsor attendees.

### Step 2: Match remaining badges to CRM accounts

For badges not matched to a sponsor, match `company_name` to CRM accounts (case-insensitive, trimmed). If matched:

- Is the CRM account disqualified? (`status == "disqualified"` or non-null `disqualified_reason`) → `excluded` with
  reason `existing_disqualified`.
- Otherwise → potentially `qualified_non_sponsor_lead`.

### Step 3: Identify non-business badges

Badges with `badge_type` values that are clearly non-business (`student`, `press`, etc.) → `excluded` with reason
`non_business_badge`.

### Step 4: Identify missing-contact badges

Badges where `contact_name` is empty or only whitespace after trimming → `excluded` with reason `missing_contact`.

### Step 5: Qualified leads

Any remaining badge that is not excluded and not a sponsor attendee is a `qualified_non_sponsor_lead`.

### Opportunity amounts for leads

Each qualified non-sponsor lead account gets the event's `lead_opportunity_amount` as its opportunity amount. The
`lead_pipeline_total` is `lead_opportunity_amount × number_of_qualified_lead_accounts`.

---

## Trade-show lead qualification

### Platform detection from exhibitor descriptions

Read each exhibitor's `description` field. Classify platforms by keyword presence:

| Description contains... | Platform |
|---|---|
| Builds/makes/manufactures AUVs, autonomous underwater vehicles | `AUV` |
| Builds/makes/manufactures ROVs, inspection-class ROVs, remotely operated vehicles | `ROV` |
| Builds/makes/manufactures/designs underwater cameras, camera modules, camera arrays | `Underwater Camera` |

An exhibitor can have zero, one, or multiple platforms. Sort platforms in the canonical order: `AUV`, `ROV`,
`Underwater Camera`.

### Qualification logic

An exhibitor **qualifies** when its description shows it **manufactures or OEM-builds** at least one target underwater
platform (AUV, ROV, or Underwater Camera).

An exhibitor is **excluded** when it does not manufacture platforms. Common exclusion patterns:

| Pattern | Exclusion reason |
|---|---|
| Distributor, reseller, sales agent, imports brands | `distributor_only` |
| Consulting, renting, operating equipment, services | `service_only` |
| Sensor/probe maker only, no platform manufacturing | `sensor_vendor_only` or `sensor_only` |
| Academic/research lab | `research_only` |
| Other non-qualifying | `not_target_market` |

Use the exclusion reason enum values declared in the answer template. Different templates use slightly different enum
sets (e.g., `sensor_vendor_only` vs `sensor_only`). Pick the one that matches the template's allowed values.

### CRM overlap

For each qualified exhibitor, check if `crm_account_id` is non-null (direct CRM linkage) or if `company_name`
matches a CRM account. If matched:

- The lead's `crm_action` is `update_existing`.
- The `crm_account_id` field in output gets the matched account ID.

If no CRM match:

- The lead's `crm_action` is `create_account`.
- The `crm_account_id` field is `null`.

### Priority tiers and opportunity sizing

Priority tiers and opportunity amounts are **task-specific** — defined in the prompt, not in the API. Common patterns:

- **Tier A**: demo requested AND interest_score >= 90. Opportunity: higher amount (e.g., $120,000).
- **Tier B**: demo requested AND interest_score >= 80 (but < 90). Opportunity: mid amount (e.g., $90,000).
- **Tier C**: all other qualified leads. Opportunity: lower amount (e.g., $50,000).

Always read the prompt's exact tier definitions and opportunity amounts. Do not assume values from one task apply to
another.

### Ranking

The prompt specifies the sort order for `ranked_leads`. Implement it as a compound sort key. Common order:

1. `requested_demo` descending (demo requesters first)
2. `interest_score` descending
3. Number of platforms descending (broader coverage first)
4. `company_name` ascending (alphabetical tiebreaker)

Assign `rank` as contiguous 1-based integers after sorting.

---

## Import-batch cleaning rules

### Processing order

Process raw contacts in this order to avoid misclassification:

1. **Normalize** all emails and phones.
2. **Deduplicate** — find and resolve duplicate normalized emails.
3. **Suppression check** — remove suppressed contacts entirely.
4. **Missing-contact check** — flag rows with unusable contact names.
5. **CRM matching** — match surviving rows to existing accounts and contacts.

### Deduplication

For rows sharing the same normalized email:

- **Winner**: the row with the **latest `captured_at` ISO timestamp**.
- **Tiebreaker**: if timestamps are identical, prefer `source_name == "partner_upload"` over `"webinar_form"`.
- **Winner row**: becomes the `clean_contact_id`, with `source_row_id` set to its `row_id`. The winner's `captured_at`
  and `source_name` are preserved in output.
- **Removed rows**: get reason `duplicate` in `removal_summary.removed_rows`.

The `duplicate_summary.duplicate_keys` array records each dedup group:

- `key`: `"email:<normalized_email>"` format.
- `winner_row_id`: the winning row's `row_id`.
- `removed_row_ids`: array of the other row IDs in the group.

### Suppression matching

For each row (after dedup), check its normalized email and normalized phone against the suppression list. A match on
**either** field is sufficient:

- If the row's normalized email equals a suppression entry's email (case-insensitive, already normalized) → suppressed.
- If the row's normalized phone equals a suppression entry's phone (digits-only) → suppressed.

Suppressed rows get `crm_action: "suppress"` (or `"no_import"` — use whatever the template's `crm_action` enum provides
for non-importable rows) and removal reason `suppressed`.

### Missing-contact rows

After suppression filtering, any row whose `contact_name` is empty or only whitespace after trimming is unusable.
These rows get `crm_action: "no_import"` and removal reason `missing_contact`. They do not appear in `clean_contacts`.

### CRM account matching

Match surviving rows to CRM accounts by `company_name`:

- Normalize: trim whitespace, convert to lowercase.
- Compare the normalized company_name against CRM account `name` (also trimmed and lowercased).
- Some raw import rows have abbreviated names (e.g., `"AcmeCorp Mfg."` vs CRM name `"AcmeCorp Manufacturing"`).
  When an exact match fails, check if one is a substring of the other or if they share a common prefix — but prefer
  exact matches. The data patterns observed show that company_name matching is generally straightforward
  (case-insensitive trim comparison is enough for most cases).

### CRM contact matching

Match by normalized email against CRM contacts. CRM contacts already have normalized (lowercase) emails, so matching
is direct after normalizing the raw row's email.

### CRM action classification

For each surviving, non-suppressed, non-missing-contact row:

| Condition | `crm_action` | `existing_account_id` | `existing_contact_id` |
|---|---|---|---|
| Matches CRM account AND CRM contact | `update_existing` | matched account_id | matched contact_id |
| Matches CRM account but NOT CRM contact | `update_existing` | matched account_id | null |
| No CRM account match | `create_account` | null | null |

**Important**: The `crm_action` enum values must match the answer template exactly. Different templates use different
values — e.g., one template uses `create_account`/`update_existing`/`no_import`/`suppress`, while another uses a
different set. Always use the template's declared values, not hardcoded strings.

### Counting

- `import_action_totals.create_account` — count of `clean_contacts` with `crm_action: "create_account"`.
- `import_action_totals.update_existing` — count with `crm_action: "update_existing"`.
- `import_action_totals.no_import` — count of removed rows with reason `missing_contact` plus rows that are otherwise
  not importable.
- `import_action_totals.suppress` — count of removed rows with reason `suppressed`.
- `duplicate_summary.duplicate_removed_count` — total number of rows removed due to deduplication (sum of all
  `removed_row_ids` lengths).
- `removal_summary.unusable_removed_count` — count of rows removed for `missing_contact`.
- `removal_summary.suppressed_removed_count` — count of rows removed for `suppressed`.
- `campaign_member_import_count` — number of `clean_contacts` whose `crm_action` is `create_account` or
  `update_existing` (i.e., rows that will actually flow into CRM).

---

## Follow-up date computation

Event follow-up dates are computed from the event's `end_date` by adding day offsets:

```
lead_followup_due_date = end_date + followup_days_after_end days
sponsor_followup_due_date = end_date + sponsor_followup_days_after_end days
```

Use calendar-day arithmetic (date + N days). Format output as `YYYY-MM-DD`.

For event reconciliation tasks, the follow-up object typically includes:

- `lead_due_date` — the computed lead follow-up date.
- `lead_task_count` — number of qualified lead accounts.
- `sponsor_finance_due_date` — the computed sponsor follow-up date.
- `sponsor_finance_task_count` — number of unpaid sponsor accounts (open_invoice + proposal_only).
- `sponsor_finance_accounts` — sorted list of unpaid sponsor account names.

---

## CRM action counting patterns

### For event reconciliation

- `accounts_create`: qualified leads whose badge company has no matching CRM account.
- `accounts_update`: qualified leads whose badge company matches a CRM account (add campaign member only).
- `contacts_create`: qualified lead badges whose normalized email does not match any CRM contact.
- `contacts_update`: qualified lead badges whose normalized email matches an existing CRM contact.
- `campaign_members_create`: count of records needing new campaign_member creation.
- `campaign_members_update`: count of existing campaign_member records that need a status update.

### For import-batch cleaning

CRM action counts come directly from the `crm_action` classification on each row. The field names in the output
must match the answer template (e.g., `import_action_totals` vs `crm_action_counts`).

---

## Enum reference

### Sponsor statuses (from policies `sponsor_handoff.status_enums`)

- `paid_deferred` — invoice fully paid with deferred recognition.
- `open_invoice` — invoice issued but not fully paid.
- `proposal_only` — order confirmed or proposed but no invoice yet.
- `not_sponsor` — not a sponsor (canceled orders, but these are typically excluded rather than listed).

### Platforms (from policies `prospecting.platform_enums`)

- `AUV` — Autonomous Underwater Vehicle.
- `ROV` — Remotely Operated Vehicle.
- `Underwater Camera` — Underwater camera modules/systems.

### Badge types (observed values)

- `sponsor` — sponsor personnel badge.
- `attendee` — business attendee badge.
- `student` — academic/student badge (non-business, excluded).
- Other values may appear; any clearly non-business badge_type triggers `non_business_badge` exclusion.

### Import source_name values (observed values)

- `badge_scan` — captured from event badge scan.
- `sponsor_form` — captured from sponsor registration form.
- `partner_upload` — uploaded by a partner (higher fidelity).
- `webinar_form` — self-registration from webinar.
- `exhibitor_form` — captured from exhibitor registration.
- `manual_upload` — manually entered.

### Exclusion reasons (event reconciliation)

- `sponsor_attendee` — contact belongs to an active sponsor.
- `existing_disqualified` — CRM account is disqualified.
- `non_business_badge` — badge type is non-business (student, press, etc.).
- `missing_contact` — no usable contact name.

### Exclusion reasons (trade-show prospecting)

- `distributor_only` — distributes but does not manufacture.
- `service_only` — provides services only.
- `sensor_vendor_only` or `sensor_only` — builds sensors but not platforms.
- `research_only` — research or academic institution.
- `not_target_market` — other non-qualifying reason.

### CRM actions (varies by template — check answer_template.json)

Common values: `create_account`, `update_existing`, `no_import`, `suppress`, `add_campaign_member`,
`no_action`, `create_contact_campaign_member`, `create_account_contact_campaign_member`.

### Campaign member statuses (observed values)

- `attended_sponsor` — sponsor contact who attended.
- `registered_sponsor` — sponsor contact who registered but did not attend.
- `attended` — non-sponsor attendee.
- Other values may appear based on the event.

---

## Null vs. empty string

| Situation | Output |
|---|---|
| Field declared as nullable in template (e.g., `existing_account_id`, `invoice_id`, `exclusion_reason`) and no value | `null` |
| Field declared as string with empty fallback (e.g., `normalized_email`, `normalized_phone`) and no data | `""` |
| CRM account ID not found for a lead | `null`, not `""` |
