# HarborCRM Skill

## Environment

All API calls target the base URL supplied by the runner (e.g. `http://34.46.77.124:8001`). Do not use localhost or run setup scripts unless the remote URL itself points there.

## API Reference

| Purpose | Endpoint |
|---|---|
| Event details | `GET /api/events/{event_id}` |
| Sponsor orders | `GET /api/events/{event_id}/orders` |
| Sponsor packages | `GET /api/events/{event_id}/sponsor_packages` |
| Badge scans | `GET /api/events/{event_id}/badges` |
| Finance invoices | `GET /api/finance/invoices?event_id={event_id}` |
| CRM accounts | `GET /api/crm/accounts` |
| CRM contacts | `GET /api/crm/contacts` |
| CRM opportunities | `GET /api/crm/opportunities` |
| Campaign members | `GET /api/crm/campaign_members?event_id={event_id}` |
| Policies | `GET /api/policies` |
| Tradeshow list | `GET /api/tradeshows` |
| Tradeshow exhibitors | `GET /api/tradeshows/{show_id}/exhibitors` |
| Meeting interest | `GET /api/tradeshows/{show_id}/meeting_interest` |
| Import batches | `GET /api/import_batches` |
| Raw import contacts | `GET /api/import_batches/{batch_id}/raw_contacts` |
| Suppression list | `GET /api/import_batches/{batch_id}/suppression` |

## Contact Normalization

- **Email**: lowercase, trimmed. Use empty string `""` when no email is supplied.
- **Phone**: digits only. Preserve country code when present in the source (e.g. `+1 415-555-0188` → `14155550188`). Use empty string when no phone is supplied.

## Sponsor Reconciliation (Event Tasks)

### Determining Sponsor Status

Cross-reference orders and invoices. Map to the controlled status values:

| Condition | Status |
|---|---|
| Invoice with status `paid_deferred` | `paid_deferred` |
| Invoice with status `open` | `open_invoice` |
| Order exists, no invoice | `proposal_only` |
| Order status `canceled` | Exclude from active sponsors |

Only **active** (non-canceled) sponsor orders appear in sponsor statuses. Include `invoice_id` as `null` for proposal-only sponsors.

### Sponsor Revenue

- `sponsor_revenue_totals`: sum `package_amount` (from order/invoice) by status.
- `open_invoice_balance`: sum of `amount - paid_amount` across open invoices.
- `open_balance` per sponsor: `amount - paid_amount`.

### Sponsor Follow-Up

- `sponsor_finance_due_date`: event `end_date` + `sponsor_followup_days_after_end`.
- Unpaid sponsors include both **open_invoice** AND **proposal_only** sponsors.
- `unpaid_sponsor_total_usd`: sum of their amounts.

## Lead Qualification (Event Tasks)

### Inclusion Rules
A badge qualifies as a lead when ALL of the following hold:
1. Badge type is **not** `sponsor`, `student`, `press`, or other non-business type.
2. The contact is **not** listed as a `ticket_contact` on any sponsor order.
3. The company's CRM account is **not** disqualified (status ≠ `disqualified`, `disqualified_reason` is null).

### Exclusion Categories

| Condition | Exclusion Reason |
|---|---|
| Sponsor badge or sponsor ticket contact | `sponsor_attendee` |
| Badge type is student/press/etc. | `non_business_badge` |
| CRM account is disqualified | `existing_disqualified` |
| Canceled sponsor order's contacts | `sponsor_attendee` |

- Contacts with empty email but a valid phone are **still qualified** (not `missing_contact`).
- Each badge gets one classification: `sponsor_attendee`, `qualified_non_sponsor_lead`, or `excluded`.

### Opportunity Amounts
- Use the event's `lead_opportunity_amount` for every qualified non-sponsor lead account.
- `lead_pipeline_total` = sum of all qualified lead opportunity amounts.

### CRM Actions per Lead
- Account exists in CRM → `update_existing`. No CRM account → `create_account`.
- Contact exists in CRM → `update_existing` (account-level). New contact → `create_contact`.
- Campaign member: `add_campaign_member` for all qualified leads.

### CRM Account Matching
Match badge company to CRM account by:
1. Exact `account_id` match (if present on badge).
2. Email domain match (badge email domain == CRM account `domain`).
3. Name match (fuzzy — normalize case and whitespace).

### Follow-Up Dates
- `lead_due_date`: event `end_date` + `followup_days_after_end`.
- `sponsor_finance_due_date`: event `end_date` + `sponsor_followup_days_after_end`.

## Campaign Member Actions

For event reconciliation tasks, build `campaign_member_actions` covering:
- Every badge holder.
- Every existing campaign member for the event (even those without a badge).

**Target status mapping:**
| Condition | Target Status |
|---|---|
| Sponsor who attended (has badge) | `attended_sponsor` |
| Sponsor who registered only (no badge) | `registered_sponsor` |
| Non-sponsor attendee (qualified lead) | `attended` |
| Excluded (non-business, disqualified, etc.) | `excluded` |

**Action mapping:**
| Condition | Action |
|---|---|
| Campaign member already exists, status matches target | `no_action` |
| Campaign member needed, doesn't exist | `create` |
| Excluded, no campaign member needed | `no_import` |

Use `subject_key` as a unique identifier (badge_id or account_id), sorted ascending.

## Prospecting (Tradeshow Tasks)

### Qualification
An exhibitor is qualified IFF it **manufactures or OEM-builds** platforms covered by the campaign (AUV, ROV, Underwater Camera). Determine this from the exhibitor `description` field. Be thorough: if a description mentions both an ROV and cameras, include both platforms.

### Exclusion Reasons

| Exhibitor Profile | `exclusion_reason` | `relationship_type` |
|---|---|---|
| Reseller/distributor, no manufacturing | `distributor_only` | `distributor` |
| Consulting/analytics service, no hardware | `service_only` | `service_provider` |
| Sensor component vendor only, no platform | `sensor_vendor_only` | `sensor_vendor` |
| Research institution, no commercial product | `research_only` | `research` |
| Doesn't fit target market | `not_target_market` | — |

Every exhibitor must be classified — none left unaccounted for.

### Platform Classification
Allowed platforms: `AUV`, `ROV`, `Underwater Camera`. List in this enum order. Only include platforms the exhibitor actually builds; parse descriptions carefully.

### Priority Tiers & Opportunity Sizing

| Condition | Tier | Opportunity |
|---|---|---|
| Requested demo AND interest score ≥ 90 | A | $120,000 |
| Requested demo AND interest score ≥ 80 | B | $90,000 |
| All other qualified leads | C | $50,000 |

### Ranking
Apply sort keys in order:
1. **Demo requested** first (`true` before `false`).
2. **Interest score** descending (higher first).
3. **Broader platform coverage** (more platforms first).
4. **Company name** ascending (alphabetical).

Assign 1-based contiguous rank integers.

### CRM Actions
- Exhibitor has a non-null `crm_account_id` matching a CRM account → `update_existing`.
- No CRM account → `create_account`.

### Summary
- `existing_crm_overlap_count`: count of qualified leads with existing CRM accounts.
- `existing_crm_overlap_account_ids`: those account IDs, sorted ascending.
- `platform_coverage_counts`: count of qualified leads per platform type.
- `total_estimated_opportunity_usd`: sum of all qualified lead opportunity estimates.

## Import Batch Processing

### Workflow
1. Fetch `raw_contacts` and `suppression` list.
2. **Dedup**: identify rows with the same normalized email. Keep the winning row, remove the rest.
   - **Winner selection**: prefer `partner_upload` source over `webinar_form`. When sources are equal, prefer the **later** `captured_at` timestamp.
   - **Dedup key**: normalized email (lowercase, trimmed).
3. **Remove unusable**: rows with whitespace-only/empty email AND no phone → `missing_contact`.
4. **Suppress**: match by email against suppression list → `suppressed`.
   - Suppressed contacts are **removed** from clean_contacts and counted in `removal_summary.suppressed_removed_count`. They do **not** appear in `import_action_totals.suppress` (that field stays `0`).

### CRM Matching for Import
- Match email domain against CRM account `domain` to find `existing_account_id`.
- Match normalized email against CRM contact `email` to find `existing_contact_id`.
- Account exists → `crm_action: "update_existing"`. No account → `crm_action: "create_account"`.

### Output Conventions
- `clean_contact_id` = winning row's `row_id`.
- `source_row_id` = winning row's `row_id`.
- `clean_contacts` sorted by `clean_contact_id` ascending.
- `duplicate_keys` sorted by `key` ascending.
- `removed_rows` sorted by `row_id` ascending.
- `campaign_member_import_count`: count of clean contacts with crm_action `create_account` or `update_existing`.

## Sorting Rules Summary

| List | Sort Key | Direction |
|---|---|---|
| sponsor_statuses | account_name | ascending |
| qualified_lead_accounts | account_name | ascending |
| excluded_records | company_name, then contact_name | ascending |
| badge_decisions | badge_id | ascending |
| campaign_member_actions | subject_key | ascending |
| badge_only_contacts | company_name | ascending |
| qualified_exhibitors | company_name | ascending |
| excluded_near_misses / excluded_exhibitors | company_name | ascending |
| ranked_leads | rank | ascending |
| clean_contacts | clean_contact_id | ascending |
| platforms (within an item) | enum order: AUV, ROV, Underwater Camera | — |

## Data Types & Precision

- **Currency**: integer USD (no decimals).
- **Counts**: integers.
- **Dates**: `YYYY-MM-DD` strings.
- **Timestamps**: ISO 8601 strings as returned by the API.
- **Nulls**: use JSON `null` (not the string `"null"`).

## Common Pitfalls

1. **Canceled sponsors**: Do not include canceled orders in active sponsor statuses, but their contacts still appear as `sponsor_attendee` exclusions.
2. **Proposal-only sponsors**: Count them in unpaid sponsor follow-up and sponsor statuses, but they have no invoice (invoice_id = null, paid = 0).
3. **Platform detection**: Read exhibitor descriptions holistically — "camera arrays" on an ROV counts as both ROV and Underwater Camera platforms.
4. **Empty vs missing**: Empty email string `""` is NOT the same as missing contact. A badge with phone but no email is still a valid lead.
5. **Suppressed vs clean**: Suppressed contacts are REMOVED from clean_contacts entirely; do not list them with `crm_action: "suppress"`.
6. **Source priority for dedup**: `partner_upload` beats `webinar_form`. When sources match, later `captured_at` wins.
7. **CRM matching**: Match by email domain, not company name. Company names in raw data can be abbreviations (e.g. "HelioWare Mfg." vs "HelioWare Manufacturing").
8. **Duplicates**: Dedup key is normalized email only. Same email = same person regardless of name/phone variation.
9. **All entities accounted**: Every badge, exhibitor, or raw contact must appear in exactly one output list — never leave an entity unclassified.
10. **Template fidelity**: Do not add extra fields beyond the answer template. Use only the controlled enum values specified.
