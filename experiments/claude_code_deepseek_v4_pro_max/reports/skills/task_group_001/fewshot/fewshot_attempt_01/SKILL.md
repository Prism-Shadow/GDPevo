# HarborCRM Skill

## Environment

Base URL: `http://34.46.77.124:8001`. All API calls use this prefix. Never start local env/setup.sh or use localhost — environment_access.md overrides any task text that mentions local URLs.

## API Reference

### Events (post-event reconciliation tasks)
| Endpoint | Returns |
|---|---|
| `GET /api/events` | All events |
| `GET /api/events/{event_id}` | Single event with `end_date`, `followup_days_after_end`, `sponsor_followup_days_after_end`, `lead_opportunity_amount` |
| `GET /api/events/{event_id}/orders` | Sponsor orders (account_id, amount, order_status, ticket_contacts) |
| `GET /api/events/{event_id}/badges` | Badge scans (badge_id, badge_type, company_name, contact_name, email, phone, job_title, scan_score) |
| `GET /api/events/{event_id}/sponsor_packages` | Same shape as orders |

### Tradeshows (prospecting tasks)
| Endpoint | Returns |
|---|---|
| `GET /api/tradeshows` | All tradeshows |
| `GET /api/tradeshows/{show_id}/exhibitors` | Exhibitors with company_id, company_name, description, booth, country, website, crm_account_id |
| `GET /api/tradeshows/{show_id}/meeting_interest` | Per-company interest_score, requested_demo, notes |

### Finance
| Endpoint | Returns |
|---|---|
| `GET /api/finance/invoices?event_id={id}` | Invoices with status (paid_deferred/open), amount, paid_amount, deferred_amount |

### CRM
| Endpoint | Returns |
|---|---|
| `GET /api/crm/accounts` | All accounts (account_id, name, domain, status, disqualified_reason) |
| `GET /api/crm/contacts` | All contacts (contact_id, account_id, name, email, phone, opted_out) |
| `GET /api/crm/opportunities` | All opportunities |
| `GET /api/crm/campaign_members?event_id={id}` | Existing campaign members for an event |

### Import Batches
| Endpoint | Returns |
|---|---|
| `GET /api/import_batches` | All batches (batch_id, campaign_code) |
| `GET /api/import_batches/{batch_id}/raw_contacts` | Raw rows with row_id, company_name, contact_name, email, phone, source_name, captured_at |
| `GET /api/import_batches/{batch_id}/suppression` | Suppression list (email, phone, reason) |

### Policies
`GET /api/policies` — returns `contact_hygiene`, `prospecting.platform_enums` (always `["AUV","ROV","Underwater Camera"]`), `sponsor_handoff.status_enums`.

---

## Normalization Rules

- **Email**: lowercase, trim leading/trailing whitespace. If blank/whitespace-only after trim → treat as empty string.
- **Phone**: strip all non-digit characters (`+`, `-`, `.`, `(`, `)`, spaces). If result is empty → empty string.

---

## Sponsor Status Derivation

For event reconciliation tasks, classify each sponsor order:

1. **Order is canceled** (`order_status == "canceled"`) → **exclude entirely** (inactive sponsor record). Do NOT include in sponsor_statuses. Include in excluded_records with reason `inactive_sponsor_record`.

2. **Has invoice with `status == "paid_deferred"`** → `paid_deferred`. `paid_amount` = invoice.paid_amount, `open_balance` = 0 (deferred revenue recognized, fully paid).
   - Revenue total: sum `package_amount` (the order/invoice amount).

3. **Has invoice with `status == "open"`** → `open_invoice`. `paid_amount` = invoice.paid_amount, `open_balance` = invoice.amount - invoice.paid_amount.
   - Revenue total: sum invoice amount. `open_invoice_balance` = sum of all open_balance values.

4. **No invoice exists but order is active** (`order_status == "confirmed"` or `"proposal_sent"`) → `proposal_only`. `paid_amount` = 0, `open_balance` = 0, `invoice_id` = null.
   - Revenue total: sum order amount.

5. **Not a sponsor** (`not_sponsor`) — use only when a task template explicitly requires it.

### Sponsor Revenue Totals
```json
{
  "paid_deferred": <sum of amounts for paid_deferred sponsors>,
  "open_invoice": <sum of amounts for open_invoice sponsors>,
  "proposal_only": <sum of amounts for proposal_only sponsors>,
  "open_invoice_balance": <sum of (amount - paid_amount) for open_invoice sponsors>
}
```
All values are integers (USD).

### Sponsor Finance Follow-up
- **Accounts needing follow-up**: sponsors with status `open_invoice` or `proposal_only` (not `paid_deferred`).
- **Due date**: `event.end_date + event.sponsor_followup_days_after_end` days (format `YYYY-MM-DD`).
- **Task count**: number of accounts needing follow-up.

---

## Lead Qualification (Event Tasks)

From badge scans, identify qualified non-sponsor leads:

1. **Exclude sponsor attendees**: any badge whose `company_name` matches a sponsor order's `account_name` (case-sensitive exact match). Include in excluded_records with reason `sponsor_attendee`.
2. **Exclude non-business badges**: `badge_type` is `"student"`, `"press"`, or similar non-business types → reason `non_business_badge`.
3. **Exclude disqualified CRM accounts**: look up badge `company_name` in CRM accounts. If the account has `status == "disqualified"` or non-null `disqualified_reason` → reason `existing_disqualified`.
4. **Remaining badges** → qualified non-sponsor leads.

### CRM Actions for Qualified Leads
- **Account**: if the company has a matching CRM account (matched by name or by email domain — extract domain from the badge contact's normalized email, compare to CRM account `domain` field) → `update_existing`. Otherwise → `create_account`.
- **Contact**: if a CRM contact exists with the same normalized email → `update_existing`. Otherwise → `create_contact`. (Also check same account_id.)
- **Campaign member**: all qualified leads get `add_campaign_member`.

### Opportunity Amount
Use `event.lead_opportunity_amount` for each qualified lead. `lead_pipeline_total` = sum of all lead opportunity amounts.

### Lead Follow-up
- **Due date**: `event.end_date + event.followup_days_after_end` days (format `YYYY-MM-DD`).
- **Task count**: number of qualified leads.

---

## Trade Show Prospecting

### Qualification
Read each exhibitor's `description` field. An exhibitor is **qualified** if it manufactures/OEM-builds at least one of the target platforms: AUV, ROV, or Underwater Camera. Use the description text to determine platform coverage:
- "builds AUVs", "manufactures ROVs", "OEM underwater cameras" → qualified
- "distributor", "reseller", "does not manufacture" → not qualified
- "sensor-only", "analytics dashboard using partner hardware", "consulting/operates rented" → not qualified

### Exclusion Reasons (controlled vocabulary)
Use the exclusion_reason enum from the task's answer template. Common values:
- `distributor_only` — reseller/distributor, doesn't manufacture platforms
- `service_only` — consulting/services, operates but doesn't build
- `sensor_vendor_only` / `sensor_only` — sensor-only vendor, no platform manufacturing
- `research_only` — research institution
- `not_target_market` — doesn't fit campaign criteria

Match `relationship_type` to exclusion_reason when both are required: distributor→distributor_only, service_provider→service_only, sensor_vendor→sensor_only, research→research_only.

### Platform Enums
Always `["AUV", "ROV", "Underwater Camera"]` in that order. Sort platforms lists in this enum order, not alphabetically.

### Priority Tiers & Opportunity Sizing
Derived from meeting interest data (joined by company_name):

| Tier | Condition | Opportunity (USD) |
|---|---|---|
| A | `requested_demo == true` AND `interest_score >= 90` | 120000 |
| B | `requested_demo == true` AND `interest_score >= 80` | 90000 |
| C | All other qualified exhibitors | 50000 |

### Ranking (when task requires ranked output)
1. Demo requested first (`true` before `false`)
2. Interest score descending
3. Platform coverage count descending (more platforms ranks higher)
4. Company name ascending (alphabetical tiebreaker)

### CRM Actions (Trade Show)
- Exhibitor has `crm_account_id` not null → `update_existing`
- Exhibitor has `crm_account_id` null → `create_account`
- Excluded exhibitors → `no_import`

### CRM Account Matching
- Match exhibitor `crm_account_id` to CRM account `account_id` directly when the field is present.
- For event tasks without explicit exhibitor CRM links: extract domain from normalized email → match against CRM `domain` field. Fall back to company_name match if domain lookup fails.

### Aggregate/Summary Counts
- `qualified_total`: number of qualified exhibitors
- `platform_counts`: count of qualified exhibitors covering each platform (a company may cover multiple platforms)
- `priority_counts`: count of qualified exhibitors per tier
- `existing_crm_overlap_count`: number of qualified exhibitors with non-null crm_account_id
- `total_estimated_opportunity_usd`: sum of opportunity_estimate_usd across all qualified leads

---

## Batch Import Cleaning

### Deduplication
Group raw contacts by **normalized email** (lowercase, trimmed). When multiple rows share the same email:

**Winner selection** (source priority, highest first):
1. `partner_upload`
2. `webinar_form`
3. `badge_scan`
4. `sponsor_form`
5. `exhibitor_form`
6. `manual_upload`

If same source, pick the row with the **later `captured_at`** timestamp. The winner becomes the `clean_contact`. Its `row_id` is used as both `clean_contact_id` and `source_row_id`.

### Suppression
Check each surviving clean contact (after dedup) against:
1. **Suppression list** (`GET .../suppression`): match by normalized email OR digits-only phone.
2. **CRM contacts with `opted_out == true`**: match by normalized email.

A contact is suppressed if it matches EITHER source. Suppressed contacts get `crm_action: "suppress"`, removal reason `"suppressed"`.

### Missing Contact
A row is unusable if `contact_name` is blank/null OR normalized email is empty/whitespace-only. Removal reason: `"missing_contact"`.

### CRM Account/Contact Matching (Batch Import)
- Match company to CRM account: extract domain from normalized email → find CRM account with matching `domain`. If email is empty, try company_name match.
- Match contact to CRM contact: normalized email match against CRM contacts. Only set `existing_contact_id` if the matched contact belongs to the matched account.
- If account found → `update_existing`. If not → `create_account`.

### Duplicate Key Format
`"email:<normalized_email>"` — one entry per duplicate group.

### Removal Summary
- `unusable_removed_count`: rows removed for `missing_contact`
- `suppressed_removed_count`: rows removed for `suppressed`
- `duplicate_removed_count`: rows removed as losers in dedup (in duplicate_summary)
- `removed_rows`: ALL removed rows (duplicates + suppressed + missing_contact), sorted by `row_id` ascending

### Import Action Totals
Count actions across ALL raw contact rows (not just clean ones):
- `create_account`: clean contacts with no matching CRM account
- `update_existing`: clean contacts with matching CRM account
- `no_import`: removed duplicates + missing_contact rows
- `suppress`: suppressed rows

### Campaign Member Count
Number of clean contacts that survived dedup, suppression, and missing-contact removal — i.e., `clean_contacts.length`.

---

## Badge-Level Handling (Event Reconciliation with Badges)

When a task requires per-badge decisions:

### Classification
- `sponsor_attendee`: badge company_name matches a sponsor order's account_name
- `qualified_non_sponsor_lead`: not a sponsor attendee, not disqualified, business badge type
- `excluded`: non-business badge OR existing disqualified CRM account

### CRM Action per Badge
- New account + new contact needed → `create_account_contact_campaign_member`
- Existing account, new contact → `create_contact_campaign_member`
- Existing account and contact, just add to campaign → `add_campaign_member`
- Sponsor attendee with existing campaign member → `update_campaign_member` or `no_action`
- Excluded badges → `no_import`
- Sponsor attendee (contact needed but lead-excluded) → `create_contact_campaign_member` (adds the contact record but they remain classified as sponsor_attendee for lead purposes)

### Campaign Member Actions
For each unique (account, contact) pair relevant to the event:

| Existing campaign member? | Classification | Action | target_status |
|---|---|---|---|
| No | sponsor attendee | `create` | `attended_sponsor` |
| Yes, status=attended_sponsor | sponsor attendee | `no_action` | `attended_sponsor` |
| Yes, status=registered_sponsor | sponsor attendee | `no_action` | `registered_sponsor` |
| No | qualified lead | `create` | `attended` |
| Excluded badge | — | `no_import` | `excluded` |

Subject key format: `"acct_{id}:cont_{id}"` for CRM contacts, `"badge:{badge_id}"` for badge-only leads.

### Badge-Only Contacts
Contacts from badges that have no existing CRM contact record. Include normalized email (lowercase, trimmed; empty string if none) and normalized phone (digits only; empty string if none). Include sponsor attendee badge-only contacts too. Sort by company_name ascending.

### Exclusion Counts
Count excluded badges by reason: `sponsor_attendee`, `non_business_badge`, `existing_disqualified`, `missing_contact`. Integer values.

---

## Sorting Rules (by task type)

| Context | Sort field(s) | Direction |
|---|---|---|
| sponsor_statuses | account_name | ascending |
| qualified_lead_accounts | account_name | ascending |
| excluded_records | company_name, then contact_name | ascending, ascending |
| qualified_exhibitors | company_name (or rank when ranked) | ascending |
| excluded_near_misses / excluded_exhibitors | company_name | ascending |
| badge_decisions | badge_id | ascending |
| badge_only_contacts | company_name | ascending |
| campaign_member_actions | subject_key | ascending |
| clean_contacts | clean_contact_id | ascending |
| duplicate_keys | key | ascending |
| removed_rows | row_id | ascending |
| ranked_leads | rank | ascending |
| platforms (within an item) | enum order: AUV, ROV, Underwater Camera | — |
| qualified_non_sponsor_account_names | account_name | ascending |
| unpaid_sponsor_account_names | account_name | ascending |
| existing_crm_overlap_account_ids | account_id | ascending |

---

## General Rules

1. **Return JSON only** — no explanatory prose outside the JSON object.
2. **Match the answer template exactly** — do not add or omit top-level keys. Use the field names and enum values from the template.
3. **Integer amounts** — all monetary values are integers (USD). No decimals or floats.
4. **Date format** — always `YYYY-MM-DD`. Calculate follow-up dates as `end_date + offset_days`.
5. **Empty strings, not null** — for missing emails/phones in normalized output, use `""` not `null`, unless the template explicitly requires `null`.
6. **account_id / invoice_id nulls** — use JSON `null` for absent IDs per the template (e.g., no invoice → `invoice_id: null`; no CRM account → `account_id: null` or `crm_account_id: null`).
7. **Campaign member actions span both CRM contacts and badge-only contacts** — include all relevant (account, contact) pairs for the event, not just qualified leads.
8. **Canceled sponsor orders are inactive** — exclude from sponsor_statuses; include in excluded_records with reason `inactive_sponsor_record`.
9. **Don't double-count** — when a sponsor contact appears in both campaign_members and badges, don't create duplicate campaign member actions.
10. **Domain extraction** — from `user@example.com` extract `example.com`. Use this to match against CRM account `domain` field.
