# HarborCRM Task Group Skill

## Environment

Use the base URL supplied by the runner or `environment_access.md`. Never use `localhost`, `127.0.0.1`, or run `env/setup.sh` — `environment_access.md` overrides all local references.

The API returns JSON. All outputs must be a single JSON object with no explanatory prose outside it.

## Normalization Conventions

- **Email**: lowercase, trim leading/trailing whitespace. Empty string when no email supplied.
- **Phone**: strip all non-digit characters (spaces, parens, dots, hyphens, leading `+1`). Empty string when no phone supplied.
- **USD amounts**: always integers (whole dollars, no cents).
- **Dates**: `YYYY-MM-DD` format. Compute follow-up dates as `end_date + N days` (calendar addition).
- **Booleans**: JSON `true`/`false`, not strings.

## Sorting Rules (universal)

- Sort string lists ascending (lexicographic, case-sensitive as returned by API).
- Where a template specifies a sort key, use it. Common: `account_name` asc, `company_name` asc, `badge_id` asc, `clean_contact_id` asc, `row_id` asc, `rank` asc.
- For platform enums appearing in lists, sort in the enum definition order: `AUV`, `ROV`, `Underwater Camera`.
- For `excluded_records` with two sort keys: primary by `company_name` asc, secondary by `contact_name` asc.

## API Endpoint Reference

### Events
| Endpoint | Description |
|---|---|
| `GET /api/events` | List all events |
| `GET /api/events/{event_id}` | Event detail: `name`, `start_date`, `end_date`, `campaign_code`, `status`, `followup_days_after_end`, `sponsor_followup_days_after_end`, `lead_opportunity_amount` (integer USD) |
| `GET /api/events/{event_id}/orders` | Sponsor orders: `account_id`, `account_name`, `amount`, `order_status` (`confirmed`, `proposal_sent`, `canceled`), `package_level`, `ticket_contacts`, `voucher_code` |
| `GET /api/events/{event_id}/sponsor_packages` | Same shape as orders (identical data) |
| `GET /api/events/{event_id}/badges` | Badge scans: `badge_id`, `badge_type` (`sponsor`, `attendee`, `student`, `press`), `company_name`, `contact_name`, `email`, `phone`, `job_title`, `scan_score`, `session_interest`, `source` |

### Finance
| Endpoint | Description |
|---|---|
| `GET /api/finance/invoices?event_id={event_id}` | Invoices: `invoice_id`, `account_id`, `account_name`, `amount`, `paid_amount`, `deferred_amount`, `status` (`paid_deferred`, `open`), `due_date`, `invoice_date`, `payment_date` |

### CRM
| Endpoint | Description |
|---|---|
| `GET /api/crm/accounts` | All accounts: `account_id`, `name`, `domain`, `industry`, `status` (`customer`, `prospect`, `disqualified`), `disqualified_reason` (string or null), `owner_region` |
| `GET /api/crm/contacts` | All contacts: `contact_id`, `account_id`, `name`, `email` (normalized), `phone` (digits-only), `title`, `opted_out` (bool), `source_updated_at` |
| `GET /api/crm/opportunities` | All opportunities: `opportunity_id`, `account_id`, `event_id`, `name`, `amount`, `stage`, `close_date` |
| `GET /api/crm/campaign_members?event_id={event_id}` | Campaign members: `account_id`, `contact_id`, `event_id`, `status` (`attended_sponsor`, `registered_sponsor`, `attended`), `last_activity_date` |

### Trade Shows
| Endpoint | Description |
|---|---|
| `GET /api/tradeshows` | List all trade shows |
| `GET /api/tradeshows/{show_id}/exhibitors` | Exhibitors: `company_id`, `company_name`, `booth`, `country`, `website`, `description`, `crm_account_id` (string or null), `show_id` |
| `GET /api/tradeshows/{show_id}/meeting_interest` | Meeting interest: `company_name`, `interest_score` (int), `notes`, `requested_demo` (bool), `show_id` |

### Import Batches
| Endpoint | Description |
|---|---|
| `GET /api/import_batches` | List all batches |
| `GET /api/import_batches/{batch_id}/raw_contacts` | Raw rows: `row_id`, `company_name`, `contact_name`, `email`, `phone`, `source_name`, `captured_at` (ISO timestamp), `country`, `city`, `interest` |
| `GET /api/import_batches/{batch_id}/suppression` | Suppression list: `email`, `phone` (normalized), `reason` (`global_opt_out`, `privacy_request`, `role_account`) |

### Policies
| Endpoint | Description |
|---|---|
| `GET /api/policies` | Business rules: `contact_hygiene` (normalization), `prospecting.platform_enums` (`["AUV","ROV","Underwater Camera"]`), `sponsor_handoff.status_enums` (`["paid_deferred","open_invoice","proposal_only","not_sponsor"]`) |

---

## Task Pattern: Event Reconciliation

Applies when the task provides an `event_id` and asks to reconcile sponsors, badges, invoices, and CRM.

### Workflow
1. Fetch event detail, orders, badges, invoices, CRM accounts, CRM contacts, CRM opportunities, campaign members for the event, and policies.
2. Build a sponsor lookup: keyed by `account_id` from orders where `order_status != "canceled"`.
3. Build a CRM account lookup: keyed by `account_id`; note `disqualified_reason` (null = active).
4. Build a CRM contact lookup: keyed by `(account_id, contact_name)`.
5. Classify each sponsor, each badge, and each campaign member.

### Sponsor Status Classification

For each order where `order_status != "canceled"`:
1. Find the invoice matching `(account_id, event_id)`.
2. Derive `sponsor_status`:
   - Invoice exists with `status = "paid_deferred"` → `paid_deferred`
   - Invoice exists with `status = "open"` → `open_invoice`
   - No invoice exists and `order_status = "proposal_sent"` → `proposal_only`
   - No invoice exists and `order_status = "confirmed"` — the invoice is pending; treat as `open_invoice` with `paid_amount = 0` and `open_balance = order.amount`
3. Canceled orders (`order_status = "canceled"`) are **inactive** — exclude from sponsor_statuses; report as `inactive_sponsor_record` in exclusions.

### Sponsor Revenue Totals
- `paid_deferred`: sum of `amount` for all sponsors with sponsor_status `paid_deferred`.
- `open_invoice`: sum of `amount` for all sponsors with sponsor_status `open_invoice`.
- `proposal_only`: sum of `amount` for all sponsors with sponsor_status `proposal_only`.
- `open_invoice_balance`: sum of `(invoice.amount - invoice.paid_amount)` across all invoices with status `"open"`.

### Sponsor Status Record Fields
- `account_id`: from the order.
- `account_name`: from the order.
- `status`: one of `paid_deferred`, `open_invoice`, `proposal_only`.
- `package_amount`: order `amount` (integer).
- `invoice_id`: invoice `invoice_id` if invoice exists, else `null`.
- `paid_amount`: invoice `paid_amount` if invoice exists, else `0`.
- `open_balance`: `invoice.amount - invoice.paid_amount` if invoice exists and status is `"open"`, else `0`.

### Badge Classification

| badge_type | Company is active sponsor? | CRM account disqualified? | Classification |
|---|---|---|---|
| `sponsor` | yes | any | `sponsor_attendee` |
| `attendee` | no | no (or no CRM account) | `qualified_non_sponsor_lead` |
| `attendee` | yes | any | `sponsor_attendee` |
| `attendee` | no | yes | `excluded` / `existing_disqualified` |
| `student` | any | any | `excluded` / `non_business_badge` |
| `press` | any | any | `excluded` / `non_business_badge` |

A company is an "active sponsor" if it has an order with `order_status != "canceled"` for this event.

### Exclusion Reasons
- `sponsor_attendee`: badge belongs to a sponsor company (active order).
- `existing_disqualified`: CRM account exists and `disqualified_reason` is not null.
- `inactive_sponsor_record`: sponsor order with `order_status = "canceled"`.
- `non_business_badge`: `badge_type` is `student` or `press`.

### Qualified Lead Fields
- `account_name`: from badge `company_name`.
- `account_id`: CRM `account_id` if account exists, else `null`.
- `primary_contact`: badge `contact_name`.
- `normalized_email`: normalize badge `email`.
- `normalized_phone`: normalize badge `phone`.
- `crm_account_action`: `"update_existing"` if CRM account exists and is not disqualified, else `"create_account"`.
- `crm_contact_action`: `"update_existing"` if CRM contact exists matching `(account_id, contact_name)`, else `"create_contact"`.
- `campaign_member_action`: `"add_campaign_member"`.
- `opportunity_amount`: the event's `lead_opportunity_amount` (same for all qualified leads).

### Campaign Member Actions (when template includes `campaign_member_actions`)
- `subject_key`: a compound key identifying the member, e.g., `"{account_id}:{contact_id}"` or `"{badge_id}"`. Use a stable, sortable identifier. If the template sorts by `subject_key`, derive it so sorting is predictable.
- `action`: `"create"` (new member), `"update"` (existing member needs status change), `"no_action"` (existing member already correct), `"no_import"` (excluded).
- `target_status`:
  - For sponsor attendees: `"attended_sponsor"` (badge scanned) or `"registered_sponsor"` (no badge, from order ticket_contacts).
  - For qualified non-sponsor leads: `"attended"`.
  - For excluded: `"excluded"` or omit.

For existing campaign members, compare the desired target status with the current status. If they match → `no_action`. If they differ → `update`. If no campaign member record exists for a qualified lead → `create`.

### CRM Action Counts
Count unique accounts and contacts across all qualified leads:
- `accounts_create`: qualified leads with `crm_account_action = "create_account"`.
- `accounts_update`: qualified leads with `crm_account_action = "update_existing"`.
- `contacts_create`: qualified leads with `crm_contact_action = "create_contact"`.
- `contacts_update`: qualified leads with `crm_contact_action = "update_existing"`.
- `campaign_members_create`: qualified leads getting new campaign member records.
- `campaign_members_update`: existing campaign members being updated.

When the template includes `lead_pipeline_total`: sum of `opportunity_amount` across all qualified leads (equals `qualified_lead_count × lead_opportunity_amount` when all leads use the same event amount).

### Follow-Up Dates
- `lead_due_date`: `end_date + followup_days_after_end` (from event).
- `sponsor_finance_due_date`: `end_date + sponsor_followup_days_after_end` (from event).
- `lead_task_count`: number of qualified lead accounts.
- `sponsor_finance_task_count`: number of sponsor accounts with `open_invoice` or `proposal_only` status.
- `sponsor_finance_accounts`: account names with `open_invoice` or `proposal_only`, sorted ascending.

### Badge-Only Contacts (when template includes `badge_only_contacts`)
These are qualified leads whose contact info comes only from badge scans (not already in CRM contacts). Include normalized email and phone even when empty.

---

## Task Pattern: Trade-Show Prospecting

Applies when the task provides a `show_id` and asks to qualify exhibitors for a campaign.

### Workflow
1. Fetch trade show, exhibitors, meeting interest, CRM accounts, CRM contacts, and policies.
2. Read each exhibitor's `description` to determine what they build/manufacture.
3. Classify platform coverage from the policy `platform_enums`.
4. Classify priority tier from meeting interest data.
5. Separate qualified exhibitors from excluded near-misses.

### Platform Classification

Read the exhibitor `description` and decide if they **build or OEM-manufacture** platforms in the policy's `platform_enums`. Keywords that indicate platform building:
- **AUV**: "builds AUV", "autonomous underwater vehicle", "AUV scouts", "autonomous AUV"
- **ROV**: "builds ROV", "inspection-class ROV", "ROV with", "manufactures ROV", "pen-cleaning ROVs"
- **Underwater Camera**: "underwater camera", "camera modules", "camera arrays", "OEM underwater camera", "rugged underwater camera"

An exhibitor can qualify for multiple platforms. Sort platforms in the enum order from policies (AUV, ROV, Underwater Camera).

### Qualification Gate

**Qualified**: Exhibitor description indicates they **build or OEM-manufacture** at least one target platform. They integrate hardware, not just resell, service, or provide software-only analytics.

**Excluded** (near-misses) — use these controlled reasons:
- `distributor_only`: reseller, dealer, sales agent; "does not manufacture"
- `service_only`: consulting, rental/operation services, no manufacturing
- `sensor_only` / `sensor_vendor_only`: builds only sensors/probes, not the platforms that carry them
- `research_only`: academic/research institution, not a commercial platform builder
- `not_target_market`: analytics software, dashboard-only, no hardware

Match the exclusion reason to the `relationship_type` when the template requires both.

### Priority Tier Assignment

When meeting interest data exists for an exhibitor:

| Condition | Tier | Opportunity (if template requires) |
|---|---|---|
| `requested_demo = true` AND `interest_score >= 90` | A | Follow task-specific amounts |
| `requested_demo = true` AND `interest_score >= 80` | B | Follow task-specific amounts |
| All other qualified | C | Follow task-specific amounts |

The task prompt or template may specify different score thresholds or amounts per tier. Default tier assignment: C for any qualified exhibitor that doesn't meet A or B criteria.

### Ranking (when template requires `rank`)

Sort qualified exhibitors by:
1. `requested_demo = true` first (demo requesters before non-requesters)
2. `interest_score` descending (higher scores first; treat missing as 0)
3. Number of platforms descending (broader coverage ranks higher)
4. `company_name` ascending (tiebreaker)

Assign contiguous 1-based ranks.

### CRM Action for Exhibitors
- `create_account`: `crm_account_id` is `null` (no CRM match).
- `update_existing`: `crm_account_id` is not `null`.
- `no_import`: all excluded exhibitors.

### Existing CRM Overlap
- `existing_crm_overlap_count`: count of qualified exhibitors with non-null `crm_account_id`.
- `existing_crm_overlap_account_ids`: those CRM account IDs, sorted ascending.

### Aggregate / Summary Counts
- `qualified_total`: count of qualified exhibitors.
- `excluded_count` / `excluded_near_misses_total`: count of excluded exhibitors.
- `platform_coverage_counts`: for each platform enum, count how many qualified exhibitors cover that platform.
- `priority_counts`: for each tier (A, B, C), count how many qualified exhibitors have that tier.
- `total_estimated_opportunity_usd`: sum of all qualified leads' opportunity estimates.

---

## Task Pattern: Import Batch Cleaning

Applies when the task provides a `batch_id` and asks to clean raw contacts for CRM import.

### Workflow
1. Fetch batch detail, raw contacts, suppression list, CRM accounts, CRM contacts, policies.
2. Normalize all emails and phones in raw contacts.
3. Remove unusable rows (missing contact name).
4. Deduplicate by normalized email.
5. Check suppression list.
6. Match survivors against CRM.
7. Classify CRM actions and compute summary counts.

### Step-by-Step Rules

**1. Unusable Row Removal**
A raw contact row is unusable if:
- `contact_name` is blank/whitespace-only, OR
- Both `email` and `phone` are blank/whitespace-only after normalization.
- Reason: `"missing_contact"`.

**2. Deduplication**
- **Duplicate key**: normalized email (lowercase, trimmed). Two rows with the same normalized email are duplicates.
- **Winner selection**: the row with the most recent `captured_at` timestamp. If timestamps are equal, prefer the row appearing earlier in the raw contacts list (lower array index; alternatively, lower `row_id` string sort).
- The winning row becomes the `clean_contact_id` (use its `row_id`) and `source_row_id`.
- Removed duplicates get reason `"duplicate"`.
- Record each duplicate group in `duplicate_summary.duplicate_keys` with:
  - `key`: the normalized email.
  - `winner_row_id`: the surviving `row_id`.
  - `removed_row_ids`: list of removed `row_id`s.

**3. Suppression Check**
For each surviving row, check the suppression list:
- Match by normalized email (case-insensitive) OR normalized phone (digits-only).
- If either matches → `crm_action = "suppress"`, reason `"suppressed"`.
- A row that is both duplicate-removed AND suppressed only appears once in `removed_rows`. Deduplication takes precedence (the row is removed as a duplicate, not re-counted as suppressed).

**4. CRM Matching**
For each surviving, non-suppressed row:
- Match against CRM accounts: first try exact `company_name` == CRM `name`. If no exact match, try domain matching — extract the domain from the row's normalized email and match against CRM `domain`. Use the matched CRM account's `account_id` as `existing_account_id`. If neither matches, `existing_account_id = null`.
- Match `contact_name` against CRM contacts for that account. If a CRM contact with the same `name` exists for the matched account, set `existing_contact_id`. Otherwise `null`.
- For trade-show exhibitors: the `crm_account_id` field on the exhibitor record is already the CRM match — use it directly rather than name-matching.

**5. CRM Action Classification**
- `create_account`: no matching CRM account found, contact is not suppressed, contact is usable.
- `update_existing`: matching CRM account found, contact usable.
- `no_import`: row is unusable (missing contact), but not suppressed.
- `suppress`: contact matched the suppression list.

**6. Clean Contact Record Fields**
- `clean_contact_id`: the winning `row_id` (same as `source_row_id`).
- `source_row_id`: the winning `row_id`.
- `company_name`, `contact_name`: from the winning row.
- `email`: normalized email (lowercase, trimmed) or `""`.
- `phone`: digits-only or `""`.
- `source_name`: from the winning row (one of: `badge_scan`, `sponsor_form`, `partner_upload`, `webinar_form`, `exhibitor_form`, `manual_upload`).
- `captured_at`: ISO timestamp from the winning row.
- `crm_action`: as classified above.
- `existing_account_id`: CRM `account_id` or `null`.
- `existing_contact_id`: CRM `contact_id` or `null`.

**7. Counts**
- `import_action_totals.create_account`: rows with `crm_action = "create_account"`.
- `import_action_totals.update_existing`: rows with `crm_action = "update_existing"`.
- `import_action_totals.no_import`: rows with `crm_action = "no_import"`.
- `import_action_totals.suppress`: rows with `crm_action = "suppress"`.
- `campaign_member_import_count`: number of clean contacts with `crm_action` in `(create_account, update_existing)` — these become campaign members for the batch's `campaign_code`.

**8. Removal Summary**
- `unusable_removed_count`: rows removed for `missing_contact`.
- `suppressed_removed_count`: rows removed for `suppressed`.
- `removed_rows`: list of `{row_id, reason}` for all removed rows (both unusable and suppressed, but NOT duplicate-removed). Sort by `row_id` ascending.

---

## Common Pitfalls

1. **Canceled ≠ Proposal**: `order_status = "canceled"` means the sponsor is inactive — exclude entirely from sponsor_statuses. `order_status = "proposal_sent"` without an invoice is `proposal_only` — still an active sponsor record.

2. **Invoice amount vs paid_amount**: The open balance is `amount - paid_amount`, not `amount - deferred_amount`. `deferred_amount` is a revenue-recognition field, not the outstanding balance.

3. **Badge email/phone are raw**: Always normalize badge emails (lowercase, trim) and phones (digits only) before comparing with CRM contacts (which are already normalized).

4. **CRM account matching strategy varies by task type**: For event reconciliation, sponsor order `account_name` matches CRM `name` exactly. For import batch cleaning, try exact `company_name` match first, then fall back to domain matching (extract domain from normalized email, match against CRM `domain`). For trade-show prospecting, use the exhibitor's `crm_account_id` field directly — it is pre-linked.

5. **Duplicate-key precedence**: Dedup removal takes priority over suppression. A row that is a duplicate is removed as `duplicate`, not re-reported as suppressed — even if it would also match the suppression list.

6. **Same-timestamp tiebreaker in dedup**: When two duplicate rows share the same `captured_at`, the earlier row in the list (lower array index) wins. Verify by checking row order from the API response.

7. **Non-sponsor but CRM-disqualified**: A badge for a non-sponsor company that has a disqualified CRM account is excluded as `existing_disqualified`, NOT as a qualified lead. The disqualification blocks the lead regardless of badge type.

8. **Sponsor badge type vs sponsor company**: A badge with `badge_type = "attendee"` but a `company_name` matching an active sponsor order's `account_name` is still a `sponsor_attendee`. Classification depends on company sponsorship, not just the `badge_type` field.

9. **Proposal-only sponsors and badges**: A company with `order_status = "proposal_sent"` IS an active sponsor. Their badges are `sponsor_attendee`. Their contacts from `ticket_contacts` in the order should be considered for campaign member records even if they didn't scan a badge.

10. **Platform classification from descriptions**: Read the full description text. A company that "builds ROVs with camera arrays" qualifies for both `ROV` AND `Underwater Camera`. A company that "embeds third-party probes" into cameras qualifies for `Underwater Camera` (they build the camera platform) but not for AUV/ROV. A company that only makes the sensor/probe itself does NOT qualify.

11. **Empty email is allowed**: A badge with an empty email but a valid phone is still a qualified lead (not `missing_contact`). `missing_contact` means the contact **name** is missing or both email AND phone are blank.

12. **opted_out contacts**: CRM contacts with `opted_out = true` are still valid CRM records for matching purposes. Opt-out status affects whether to contact them but not whether they exist in the CRM. However, suppression list entries with `global_opt_out` or `privacy_request` DO cause removal from import batches.

13. **Sorting is case-sensitive**: API responses use exact casing. Sort lexicographically as-is; do not lowercase for sorting.

14. **Single JSON output**: Never include markdown fences, explanations, or prose outside the JSON object. The output must parse as a single JSON value.
