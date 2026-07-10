# HarborCRM Skill — Transferable Rules

## Environment

Use `GDPEVO_ENV_BASE_URL` as the API base URL. Never use localhost or run setup scripts directly.

## API Overview

HarborCRM exposes these public endpoint families (replace `{id}` with the task-specific identifier):

| Category | Endpoints |
|---|---|
| Events | `/api/events/{event_id}`, `/api/events/{event_id}/orders`, `/api/events/{event_id}/badges`, `/api/events/{event_id}/sponsor_packages` |
| Finance | `/api/finance/invoices?event_id={event_id}` |
| CRM | `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities` |
| Campaigns | `/api/crm/campaign_members?event_id={event_id}` |
| Tradeshows | `/api/tradeshows`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest` |
| Import | `/api/import_batches`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression` |
| Config | `/api/policies` — returns policy metadata including opportunity amounts, follow-up windows, qualification rules |

Always start by fetching `/api/policies` — it encodes task-specific business rules (qualification criteria, opportunity amounts, follow-up windows).

## Data Normalization

### Email
- Trim whitespace, convert to **lowercase**.
- When no email is available, use an empty string `""`.
- Deduplication keys use format: `"email:<lowercase_email>"`.

### Phone
- Strip all non-digit characters. Keep only `[0-9]`.
- When no phone is available, use an empty string `""`.

## Sponsor Status Logic

Derive each sponsor's status from their invoice data:

| Condition | Status |
|---|---|
| Invoice exists AND `paid_amount >= total_amount` (fully paid) | `paid_deferred` |
| Invoice exists AND `0 < paid_amount < total_amount` (partial) | `open_invoice` |
| No invoice exists for the sponsor package | `proposal_only` |

For `open_invoice` status:
- `open_balance` = `total_amount - paid_amount`
- For `paid_deferred` and `proposal_only`, `open_balance` = `0`.

All monetary values are **integers in USD**.

## Sponsor Revenue Totals

Sum package amounts by status:
- `paid_deferred`: sum of all `paid_deferred` sponsor package amounts
- `open_invoice`: sum of all `open_invoice` sponsor package amounts
- `proposal_only`: sum of all `proposal_only` sponsor package amounts
- `open_invoice_balance`: sum of all open balances from `open_invoice` sponsors

## Qualified Lead / Account Logic

### Qualification (Event/Exhibitor Tasks)
- A contact is a **qualified non-sponsor lead** if ALL of:
  1. Their company is NOT a sponsor (sponsor attendees are excluded).
  2. Their CRM account is NOT already disqualified.
  3. Their badge is a business badge (not non-business like student/press).
  4. For trade-show tasks: the exhibitor meets the platform/product criteria in the policy (e.g., makes/OEM-builds the target product category).

### CRM Action Determination
- For each qualified lead, check `/api/crm/accounts` and `/api/crm/contacts`:
  - If a matching CRM account exists → `crm_account_action: "update_existing"`, set `account_id`.
  - If no matching CRM account → `crm_account_action: "create_account"`, `account_id: null`.
  - If a matching CRM contact exists for that account → `crm_contact_action: "update_existing"`, set contact ID.
  - If no matching CRM contact → `crm_contact_action: "create_contact"`.
- Campaign member action for qualified leads is always `"add_campaign_member"`.

### Opportunity Amount
- Use the event's `lead_opportunity_amount` (from `/api/events/{id}` or `/api/policies`) for each qualified non-sponsor account.
- `lead_pipeline_total` = sum of opportunity amounts across all qualified lead accounts.

## Exclusion Categories

| Reason | When to apply |
|---|---|
| `sponsor_attendee` | Contact's company is an active event sponsor |
| `existing_disqualified` | CRM account exists and is already disqualified |
| `non_business_badge` | Badge type is non-business (student, press, speaker, etc.) |
| `inactive_sponsor_record` | Sponsor record is canceled/inactive |
| `distributor_only` | Exhibitor is a distributor, not a manufacturer/OEM |
| `service_only` | Exhibitor provides services only |
| `sensor_vendor_only` / `sensor_only` | Exhibitor sells sensors but not the target platform |
| `research_only` | Exhibitor is a research institution |
| `not_target_market` | Exhibitor doesn't serve the target market |
| `missing_contact` | Row has no contact name |

Use the "relationship_type" field from the exhibitor data to determine the matching exclusion reason.

## Deduplication

When processing import batches:
- Duplicate key = `"email:<normalized_lowercase_email>"`.
- **Winner**: the row with the **lowest `row_id`** (lexicographic/numeric ascending) among duplicates.
- All other rows for that key are marked as `"duplicate"` with reason and go into `removed_rows`.
- `duplicate_removed_count` = total number of removed duplicate rows (not including the winner).

## Suppression

From `/api/import_batches/{batch_id}/suppression`:
- Any raw contact whose normalized email matches a suppression entry is marked `crm_action: "suppress"` (or `"no_import"`), reason `"suppressed"`, and added to `removed_rows`.
- Suppressed contacts do NOT appear in `clean_contacts`.

## Follow-Up Due Dates

Compute from the event date (from `/api/events/{id}`):
- **Lead follow-up due date**: event date + 90 days.
- **Sponsor finance due date**: event date + 87 days.
- Format: `"YYYY-MM-DD"`.

### Follow-Up Task Counts
- `lead_task_count` = number of `qualified_lead_accounts`.
- `sponsor_finance_task_count` = number of sponsor accounts with `open_invoice` or `proposal_only` status (unpaid sponsors).
- `sponsor_finance_accounts` = list of account names for those unpaid sponsors, sorted alphabetically ascending.

## CRM Action Counts

Count across all qualified lead accounts:
- `accounts_create`: count where `crm_account_action == "create_account"`.
- `accounts_update`: count where `crm_account_action == "update_existing"`.
- `contacts_create`: count where `crm_contact_action == "create_contact"`.
- `contacts_update`: count where `crm_contact_action == "update_existing"`.
- `campaign_members_create`: count of `"add_campaign_member"` actions (= number of qualified leads).
- `campaign_members_update`: count where existing campaign members are updated (typically 0 in fresh handoffs).

## Import Batch CRM Actions

For batch import tasks, `crm_action` per clean contact:
- `"create_account"` — company not in CRM, valid contact data.
- `"update_existing"` — company found in CRM (match by account name).
- `"no_import"` — removed (missing_contact, duplicate, or suppressed).
- `"suppress"` — separately counted; the row is suppressed.

`campaign_member_import_count` = number of clean contacts with `crm_action` of `create_account` or `update_existing`.

## Campaign Member Logic (Reconciliation Tasks)

For post-event reconciliation:
- **Sponsor contacts with CRM records**: `action: "no_action"`, `target_status: "attended_sponsor"` (if they attended) or `"registered_sponsor"` (if registered but didn't attend).
- **Qualified non-sponsor badge contacts**: `action: "create"`, `target_status: "attended"`.
- **Sponsor contacts without CRM records** (badge-only): `action: "create"`, `target_status: "attended_sponsor"`.
- **Excluded badges**: `action: "no_import"`.

Subject key format:
- CRM-resident contacts: `"acct_{account_id}:cont_{contact_id}"`
- Badge-only contacts: `"badge:{badge_id}"`

## Trade Show Prospecting — Ranking & Tiers

### Priority Tier Assignment
| Tier | Criteria | Opportunity (USD) |
|---|---|---|
| A | Requested demo AND interest score ≥ 90 | 120,000 |
| B | Requested demo AND interest score ≥ 80 | 90,000 |
| C | All other qualified leads | 50,000 |

### Ranking Order (most important first)
1. `requested_demo == true` before `false`
2. `interest_score` descending
3. Platform coverage count descending (more platforms = higher rank)
4. `company_name` ascending (alphabetical tiebreaker)

Ranks are 1-based contiguous integers.

### Platform Enum Order
Always use this order for platform lists: `"AUV"`, `"ROV"`, `"Underwater Camera"`.

## Sorting Rules (General)

| Section | Sort Key | Direction |
|---|---|---|
| `sponsor_statuses` | `account_name` | ascending |
| `qualified_lead_accounts` | `account_name` | ascending |
| `excluded_records` | `company_name`, then `contact_name` | ascending |
| `excluded_exhibitors` / `excluded_near_misses` | `company_name` | ascending |
| `clean_contacts` | `clean_contact_id` | ascending |
| `duplicate_summary.duplicate_keys` | `key` | ascending |
| `removal_summary.removed_rows` | `row_id` | ascending |
| `badge_decisions` | `badge_id` | ascending |
| `campaign_member_actions` | `subject_key` | ascending |
| `badge_only_contacts` | `company_name` | ascending |
| `ranked_leads` | `rank` | ascending |
| Lists of account names/IDs | lexicographic | ascending |

## General Pitfalls

1. **Always fetch `/api/policies` first** — it contains task-specific rules, opportunity amounts, and qualification criteria.
2. **Normalize emails before matching** — case differences should not cause missed matches.
3. **Don't double-count duplicates** — winner appears in clean list, removed duplicates in removal list only.
4. **Sponsor contacts with badges are excluded from qualified leads** even if their badge is business-type.
5. **Empty strings for missing email/phone**, never `null`.
6. **Monetary values are always integers** — no decimals, no float.
7. **Follow-up date computation** uses the event date from the event endpoint, not the current date.
8. **Platform arrays** always use the canonical enum order: AUV, ROV, Underwater Camera.
9. **Suppressed contacts** count toward `suppress` / `suppressed_removed_count` and are separate from `no_import` / `unusable_removed_count`.
10. **Output only valid JSON** — no explanatory prose, no markdown fences.
