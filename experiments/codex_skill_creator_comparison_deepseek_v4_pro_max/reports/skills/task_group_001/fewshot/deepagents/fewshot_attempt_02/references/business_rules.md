# HarborCRM Business Rules

Reusable qualification logic, controlled vocabularies, sorting conventions, normalization procedures, and CRM-action classification rules. Apply these to any HarborCRM handoff task; the answer template determines the output shape.

---

## Controlled Vocabularies

### Sponsor Status Enums

From policy `sponsor_handoff.status_enums`:

| Value | Meaning |
|---|---|
| `paid_deferred` | Invoice fully paid (status `paid_deferred`) |
| `open_invoice` | Invoice partially paid (status `open`) |
| `proposal_only` | Order exists but no invoice issued |
| `not_sponsor` | No sponsor order at all (use only when template allows) |

### Platform Enums

From policy `prospecting.platform_enums` (always in this order):

```
AUV
ROV
Underwater Camera
```

When listing platforms on a qualified exhibitor, use only these values and always sort them in this enum order.

### Badge Type Values

| Badge Type | Classification |
|---|---|
| `sponsor` | Sponsor attendee |
| `attendee` | Business attendee (potential lead) |
| `student` | Non-business badge |
| `press` | Non-business badge |
| `speaker` | Non-business badge (unless also sponsor) |

### CRM Account Statuses

| Status | Meaning |
|---|---|
| `customer` | Active paying customer |
| `prospect` | Active sales prospect |
| `disqualified` | Excluded from outreach |

### Campaign Member Statuses

| Status | Meaning |
|---|---|
| `attended` | Non-sponsor who attended |
| `attended_sponsor` | Sponsor contact who attended |
| `registered_sponsor` | Sponsor contact registered but did not attend |
| `registered` | Non-sponsor registered |
| `invited` | Invited but not registered |

### Source Name Enums (Import Batches)

```
badge_scan
sponsor_form
partner_upload
webinar_form
exhibitor_form
manual_upload
```

### CRM Action Enums

| Action | When to Use |
|---|---|
| `create_account` | Company not found in CRM |
| `update_existing` | Company already in CRM |
| `create_contact` | Contact not found in CRM for that account |
| `add_campaign_member` | New campaign member to add |
| `no_action` | Already correct; no change needed |
| `no_import` | Should not be imported (excluded, missing contact, or already handled) |
| `suppress` | Email is on suppression list |

### Exclusion Reason Enums (Event Workflows)

| Value | When to Use |
|---|---|
| `sponsor_attendee` | Contact is associated with an active (non-canceled) sponsor order |
| `inactive_sponsor_record` | Sponsor order is `canceled` |
| `non_business_badge` | Badge type is `student`, `press`, or `speaker` |
| `existing_disqualified` | CRM account has `status` = `disqualified` |

### Exclusion Reason Enums (Tradeshow Workflows)

| Value | When to Use |
|---|---|
| `distributor_only` | Exhibitor `relationship_type` is `distributor` |
| `service_only` | Exhibitor `relationship_type` is `service_provider` |
| `sensor_vendor_only` / `sensor_only` | Exhibitor `relationship_type` is `sensor_vendor` |
| `research_only` | Exhibitor `relationship_type` is `research` |

Check the answer template for the exact enum string (e.g., some templates use `sensor_vendor_only`, others `sensor_only`).

### Exclusion Reason Enums (Import Batches)

| Value | When to Use |
|---|---|
| `duplicate` | Row removed as duplicate of a winning row |
| `missing_contact` | Row has empty or missing `contact_name` |
| `suppressed` | Row's email matches a suppression list entry |

---

## Qualification Logic

### Sponsor Status Classification (Event Workflows)

1. Fetch `GET /api/events/{event_id}/orders` (or `/sponsor_packages`) and `GET /api/finance/invoices?event_id={event_id}`.
2. For each order:
   - If `order_status` is `canceled`: this is an inactive sponsor record. Exclude it from `sponsor_statuses`. Its contacts appear as `inactive_sponsor_record` in exclusions.
   - If `order_status` is `confirmed` and an invoice exists for the same `account_id`:
     - Invoice `status` `paid_deferred` → sponsor status `paid_deferred`. The `paid_amount` and `open_balance` come from the invoice. `open_balance` = `amount` - `paid_amount`.
     - Invoice `status` `open` → sponsor status `open_invoice`. `open_balance` = `amount` - `paid_amount`.
   - If `order_status` is `proposal_sent` and no invoice exists → sponsor status `proposal_only`. `invoice_id` is null, `paid_amount` is 0, `open_balance` is 0.
3. The `package_amount` or `amount_usd` for the sponsor status entry is the order `amount`.

### Non-Sponsor Lead Qualification (Event Workflows)

A badge qualifies as a non-sponsor lead when **all** of these hold:

1. The company is NOT an active sponsor (no non-canceled sponsor order for that company).
2. The badge type is NOT `student`, `press`, or `speaker` (must be `attendee` or `sponsor` — but `sponsor` badges from canceled/inactive sponsors may qualify if the company is not otherwise a sponsor; check the data).
3. The company does NOT have a CRM account with `status` = `disqualified`.

Non-qualifying badges go into `excluded_records` with the appropriate reason.

### Badge Classification (Event/Badge Workflows)

1. If badge `badge_type` is `sponsor` and company matches a non-canceled sponsor order → classification `sponsor_attendee`.
2. If badge qualifies as non-sponsor lead → classification `qualified_non_sponsor_lead`.
3. If badge `badge_type` is `student`, `press`, `speaker`, or similar non-business type → classification `excluded`, reason `non_business_badge`.
4. If company has disqualified CRM account → classification `excluded`, reason `existing_disqualified`.
5. If badge has no `contact_name` or it is empty → classification `excluded`, reason `missing_contact`.

### Exhibitor Platform Qualification (Tradeshow Workflows)

1. Read each exhibitor's `description` field.
2. Check case-insensitively for platform keywords:
   - `AUV` → platform AUV
   - `ROV` → platform ROV
   - `Underwater Camera` or `underwater camera` → platform Underwater Camera
3. An exhibitor qualifies when it covers at least one target platform AND its `relationship_type` is null (meaning it is an OEM/builder, not a distributor, service provider, sensor vendor, or research entity).
4. Exhibitors with non-null `relationship_type` go into `excluded_near_misses` or `excluded_exhibitors` with the corresponding exclusion reason.

### Import Batch Deduplication

1. Normalize all emails to lowercase and trim whitespace.
2. Group rows by normalized email. Within each group with more than one row:
   - Winner: the row with the **earliest** `captured_at` timestamp.
   - Tiebreaker (if same timestamp): lower `row_id` string sort order.
   - The winning row gets the `clean_contact_id` equal to its own `row_id`.
   - All other rows in the group are duplicates and are removed.
3. Duplicate rows get removal reason `duplicate`.

### Import Batch Suppression

1. Fetch `GET /api/import_batches/{batch_id}/suppression`.
2. Build a set of suppressed normalized (lowercase, trimmed) emails.
3. Any surviving (non-duplicate) row whose normalized email matches the suppression set gets `crm_action` = `suppress` and removal reason `suppressed`.

### Import Batch Unusable Removal

1. Any surviving (non-duplicate, non-suppressed) row with empty or whitespace-only `contact_name` gets removal reason `missing_contact` and `crm_action` = `no_import`.

---

## CRM Action Classification

### Account Matching

Match a company from event/tradeshow/import data to a CRM account by:

1. **Name match**: case-insensitive exact or near match. Accept slight variations like "Acme Corp." matching "Acme Corporation" when the shared domain or industry confirms identity.
2. **Domain match**: if a contact has an email domain (e.g., `acme.example`) and a CRM account has that same domain, consider it a match.

When no CRM account matches → `crm_action` = `create_account` (or `create_account_contact_campaign_member` for badge workflows).
When a CRM account matches → `crm_action` = `update_existing` (or `create_contact_campaign_member` / `add_campaign_member` depending on contact state).

### Contact Matching

Within a matched CRM account, check if a contact with the same name or email already exists in `GET /api/crm/contacts?account_id={account_id}`:

- If no matching contact → `create_contact`
- If a matching contact exists → `update_existing` (for contact) or `no_action` (if data matches)

### Campaign Member Decisions (Event/Badge Workflows)

1. Fetch `GET /api/crm/campaign_members?event_id={event_id}`.
2. For each badge or lead:
   - If an existing campaign member record exists for the account+contact+event → decide update or no_action based on current vs target status.
   - If no existing campaign member record → `create`.

**Target status assignment:**
- Sponsor attendee (attended) → `attended_sponsor`
- Sponsor contact (registered but didn't attend) → keep `registered_sponsor` (no change)
- Non-sponsor qualified lead (attended) → `attended`

**Subject key format:**
- Existing CRM contact: `{account_id}:{contact_id}`
- Badge-only lead (no CRM contact): `badge:{badge_id}`

---

## Contact Normalization

### Email

1. Trim leading and trailing whitespace.
2. Convert to lowercase.
3. If no email provided (null, empty string, or whitespace-only), use empty string `""`.

### Phone

1. Strip all non-digit characters (spaces, hyphens, parentheses, dots, plus signs).
2. Keep only digits 0-9.
3. If no phone provided, use empty string `""`.

---

## Follow-Up Date Calculation

Both dates are computed from the event object.

**Lead follow-up due date:** `event.end_date` + `event.followup_days_after_end` days.

**Sponsor finance follow-up due date:** `event.end_date` + `event.sponsor_followup_days_after_end` days.

Format as YYYY-MM-DD.

For tradeshow workflows without event metadata, use the show's `end_date` plus a reasonable offset (the prompt will specify if needed; otherwise it is not required in the template).

---

## Priority Tier Assignment (Tradeshow Workflows)

### For demo/interest-scored rankings:

| Priority Tier | Criteria | Opportunity Estimate (USD) |
|---|---|---|
| A | `requested_demo` = true AND `interest_score` >= 90 | 120000 |
| B | `requested_demo` = true AND `interest_score` >= 80 (but < 90) | 90000 |
| C | All other qualified leads | 50000 |

### For platform-based tiering (no demo/interest data):

| Priority Tier | Criteria |
|---|---|
| A | Multiple target platforms covered |
| B | Single target platform covered |

The answer template determines which tiering scheme applies.

---

## Sorting Rules

Apply these consistently; the answer template may restate them.

| Section | Sort Key(s) | Direction |
|---|---|---|
| `sponsor_statuses` | `account_name` | ascending |
| `qualified_lead_accounts` | `account_name` | ascending |
| `qualified_exhibitors` | `company_name` | ascending |
| `ranked_leads` | `rank` | ascending |
| `excluded_records` (events) | `company_name`, then `contact_name` | ascending both |
| `excluded_near_misses` / `excluded_exhibitors` | `company_name` | ascending |
| `clean_contacts` | `clean_contact_id` | ascending |
| `duplicate_keys` | `key` | ascending |
| `removed_rows` | `row_id` | ascending |
| `badge_decisions` | `badge_id` | ascending |
| `campaign_member_actions` | `subject_key` | ascending |
| `badge_only_contacts` | `company_name` | ascending |
| `sponsor_finance_accounts` | account_name | ascending |
| Platform lists within an item | enum order: AUV, ROV, Underwater Camera | — |
| `existing_crm_overlap_account_ids` | account_id | ascending |
| `qualified_non_sponsor_account_names` | account_name | ascending |
| `unpaid_sponsor_account_names` | account_name | ascending |

---

## Revenue and Count Aggregation

### Sponsor Revenue Totals (Event Workflows)

- `paid_deferred`: sum of `package_amount` (or `amount_usd`) for all sponsors with status `paid_deferred`.
- `open_invoice`: sum of `package_amount` for all sponsors with status `open_invoice`.
- `proposal_only`: sum of `package_amount` for all sponsors with status `proposal_only`.
- `open_invoice_balance`: sum of `open_balance` across `open_invoice` sponsors.

### Lead Pipeline Total

Sum of `opportunity_amount` across all `qualified_lead_accounts`.

### CRM Action Counts

Count each distinct action across accounts, contacts, and campaign members:

- `accounts_create`: count of `create_account` actions.
- `accounts_update`: count of `update_existing` actions for accounts.
- `contacts_create`: count of new contacts to create.
- `contacts_update`: count of existing contacts to update.
- `campaign_members_create`: count of new campaign members to create.
- `campaign_members_update`: count of existing campaign members to update.

### Aggregate Counts (Tradeshow Workflows)

- `qualified_total`: number of qualified exhibitors.
- `platform_counts`: count of exhibitors covering each platform (one exhibitor may contribute to multiple platform counts).
- `priority_counts`: count of exhibitors per priority tier.
- `excluded_near_misses_total`: number of excluded near-miss exhibitors.

### Exclusion Counts (Event Workflows)

Count each exclusion reason across all badges or excluded records:
- `sponsor_attendee`
- `non_business_badge`
- `existing_disqualified`
- `missing_contact`

### Import Action Totals

Count surviving clean contacts by `crm_action`:
- `create_account`: clean contacts needing new accounts.
- `update_existing`: clean contacts matching existing CRM accounts.
- `no_import`: rows not imported (includes duplicates, missing contacts — but exclude suppressed rows from `no_import` count unless the template merges them).
- `suppress`: rows removed due to suppression.

Check the template: `no_import` may count rows that are unusable but not suppressed (e.g., missing_contact, duplicate). Suppressed rows are counted separately under `suppress`.

### Campaign Member Import Count

Number of surviving clean contacts that should become campaign members. This equals `create_account` + `update_existing` counts (those with `crm_action` not equal to `no_import` or `suppress`).

---

## Cross-Cutting Rules

1. **Never add undeclared fields.** The output must exactly match the answer template shape.
2. **All monetary values are integers.** No decimals, no string formatting.
3. **Null vs empty string:** Use `null` for absent values (e.g., `invoice_id` when none exists, `crm_account_id` when not matched). Use `""` for known-empty strings (e.g., normalized email when no email was supplied).
4. **Boolean fields:** Use JSON `true`/`false`, not strings.
5. **Dates:** Always YYYY-MM-DD format.
6. **Timestamps:** Pass through ISO format from the API.
7. **When a sponsor order has order_status `canceled`:** Its contacts are excluded as `inactive_sponsor_record`. The order amount does NOT contribute to sponsor revenue totals. The company is NOT treated as a current sponsor for lead qualification.
8. **When a CRM contact has `opted_out` = true:** Treat as disqualified/excluded from outreach. Do not include in qualified leads.
9. **When multiple CRM accounts could match:** Prefer the account with the most recent activity or the one whose `status` is `customer` or `prospect` (not `disqualified`).
