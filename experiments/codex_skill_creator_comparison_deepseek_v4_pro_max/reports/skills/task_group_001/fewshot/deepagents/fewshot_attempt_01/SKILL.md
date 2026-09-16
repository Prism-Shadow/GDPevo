---
name: harbor-crm-integration
description: "Build integrated HarborCRM workflows that join event, CRM, finance, trade-show, import-batch, and policy endpoints into reconciled, classified, and structured outputs. Use when the task involves: (1) post-event CRM handoff or reconciliation, (2) trade-show exhibitor prospecting with qualification and tiering, (3) import-batch cleaning, deduplication, and CRM import preparation, (4) cross-domain data joining across HarborCRM API segments, or (5) template-driven JSON output construction with controlled-enum classification and sorting rules."
license: MIT
compatibility: designed for deepagents-code
---

# HarborCRM Integration

## Core workflow

Every HarborCRM task follows the same skeleton:

1. Fetch the answer template from the task payload and read every field, enum, and sort rule.
2. Discover the task's domain anchors (event_id, show_id, batch_id) from the prompt.
3. Pull all relevant domain records in parallel where possible:
   - **Core entity** — event, trade show, or import batch metadata.
   - **Related children** — orders/badges/sponsor-packages, exhibitors/meeting-interest, raw-contacts/suppression.
   - **CRM cross-reference** — accounts, contacts, opportunities, campaign members.
   - **Policies** — always fetch `/api/policies`; they encode qualification criteria.
4. Build an in-memory join graph across domains. Match on ids where available (account_id, event_id, company_id), and fall back to company/contact name matching when normalizing.
5. Classify every entity into the controlled enums the template requires.
6. Apply all declared sort orders.
7. Compute derived numeric totals, counts, and follow-up dates.
8. Emit the JSON object matching the template shape and nothing else.

Produce the final JSON on stdout or write it to the path the runner provides. Never include prose outside the JSON payload.

## API base URL

The runner supplies the API base URL, typically as `<TASK_ENV_BASE_URL>` or another explicit variable in the prompt. Every endpoint below is relative to that base.

## Endpoint quick reference

For the full endpoint catalog, see [references/endpoints.md](references/endpoints.md). Common entry points by domain:

| Domain | Key endpoints |
|---|---|
| Events | `/api/events`, `/api/events/{event_id}`, `/api/events/{event_id}/orders`, `/api/events/{event_id}/badges`, `/api/events/{event_id}/sponsor_packages` |
| Finance | `/api/finance/invoices?event_id=…`, `/api/finance/invoices?account_id=…` |
| CRM | `/api/crm/accounts`, `/api/crm/contacts`, `/api/crm/opportunities`, `/api/crm/campaign_members` |
| Trade shows | `/api/tradeshows`, `/api/tradeshows/{show_id}`, `/api/tradeshows/{show_id}/exhibitors`, `/api/tradeshows/{show_id}/meeting_interest` |
| Import batches | `/api/import_batches`, `/api/import_batches/{batch_id}`, `/api/import_batches/{batch_id}/raw_contacts`, `/api/import_batches/{batch_id}/suppression` |
| Policies | `/api/policies` |

CRM endpoints support filters via query params: `?status=…`, `?owner_region=…`, `?event_id=…`, `?account_id=…`. Use them to narrow responses early.

## Classification rules

### Sponsor status

Determine by comparing the sponsor's invoice paid amount against the package amount (or order total):

- **paid_deferred** — invoice exists and paid_amount >= package amount.
- **open_invoice** — invoice exists and paid_amount < package amount. Include open_balance (package_amount - paid_amount).
- **proposal_only** — no invoice exists.

An inactive or canceled sponsor record is not a sponsor for the current event; classify it under exclusion rather than sponsor_statuses.

### Lead qualification

A non-sponsor entity qualifies as a lead when:

- The company is not a sponsor (not in the event's sponsor orders).
- The badge type is business/professional (not press, student, academic, guest, speaker-only when those are flagged as non-business in policies).
- The CRM account is not already marked disqualified (check account status fields or policy rules).
- The contact name and either email or phone are present (no "missing contact").

### Exhibitor prospecting qualification

For trade-show tasks, an exhibitor qualifies when:

- It is an OEM/builder of the target product category (per policy rules).
- It is not a distributor-only, service-only, or sensor-vendor-only entity (check exhibitor relationship_type or category fields against policy).
- Platform coverage matches the allowed platform enums in the template.

### Exclusion reasons

Use only the exclusion reasons declared in the template's enum. Common reusable reasons:

| Reason | When to apply |
|---|---|
| `sponsor_attendee` | Contact belongs to a confirmed sponsor account for this event. |
| `non_business_badge` | Badge type is press, student, academic, guest, or similar non-business category. |
| `existing_disqualified` | CRM account status is disqualified, closed, or marked non-target per policy. |
| `inactive_sponsor_record` | Sponsor order is canceled or status indicates no active participation. |
| `distributor_only` | Exhibitor's relationship type is distributor and policy excludes distributors. |
| `service_only` | Exhibitor is a service provider, not a product OEM. |
| `sensor_vendor_only` | Exhibitor makes only sensors/components, not complete target platforms. |
| `missing_contact` | Contact name is absent or both email and phone are empty/null. |
| `duplicate` | Row is a duplicate of another row (use the winning row). |
| `suppressed` | Contact appears in the suppression list for the batch. |

### CRM action classification

| Action | Condition |
|---|---|
| `create_account` | Company not found in existing CRM accounts. |
| `update_existing` | Company found in CRM accounts by account_id or normalized name match. |
| `create_contact` | Contact not found in existing CRM contacts for the account. |
| `update_existing` (contact) | Contact found in CRM contacts for the account. |
| `add_campaign_member` | Lead is qualified and not already a campaign member for the event. |
| `no_import` | Entity is excluded; do not create any CRM records. |
| `suppress` | Contact is in the suppression list; mark for suppression. |
| `no_action` | Already present with correct status; no change needed. |

## Normalization rules

### Email

Lowercase, trim whitespace, remove display-name prefixes (everything before the last `<` if angle-bracket syntax is present). If the field is null/empty, use `""`.

### Phone

Strip all non-digit characters. If the result is empty or the field is null, use `""`. Do not add a leading country code unless the source already includes one.

### Company name

Trim whitespace. When matching against CRM accounts, normalize both sides by lowercasing and stripping punctuation/suffixes like `Inc.`, `LLC`, `Ltd.`, `Corp.`. Use the highest-confidence match.

## Deduplication

When a batch contains duplicate contacts:

1. Group by normalized email.
2. Within each group, pick the winner: the row with the most complete data (non-empty phone, contact name, and company name). Break ties by earliest `captured_at` timestamp.
3. The winner becomes the `clean_contact_id` and `source_row_id`. All other rows in the group are removed with reason `duplicate`.
4. Dedup happens before suppression and before CRM matching.

## Sorting rules

Apply sorts in the exact order and direction the template specifies. Common patterns:

- Sponsor statuses: `account_name` ascending.
- Qualified leads: `account_name` / `company_name` ascending (unless ranked by priority).
- Excluded records: `company_name` ascending, then `contact_name` ascending.
- Badge decisions: `badge_id` ascending.
- Campaign member actions: `subject_key` ascending.
- Clean contacts: `clean_contact_id` ascending.
- Duplicate keys: `key` ascending.
- Removed rows: `row_id` ascending.
- Ranked leads: `rank` ascending (1-based contiguous).

Enum-valued lists (platforms, priority tiers) sort in the order the template declares the enum values.

## Follow-up date defaults

When the task asks for follow-up due dates and a specific policy rule is not present:

- **Lead follow-up**: 21 calendar days after the event end date (or 14 days after the task run date if no event end date is available).
- **Sponsor finance follow-up**: 17 calendar days after the event end date.

If a policy endpoint provides explicit follow-up offsets, use those instead.

## Opportunity amounts

When the task specifies a per-lead opportunity amount, use the event's lead opportunity amount from the event endpoint or opportunities endpoint. When the task specifies tiered amounts (A/B/C), apply the tiering rules exactly as described in the prompt and map them to the declared tiers in the template.

## Aggregate counts

Every count field in the template must match the actual number of records in its corresponding list. Cross-check: for every array produced, verify `array.length` equals the related count field. Platform and priority counts are always non-negative integers summing to the qualified total.

## Template conformance

1. Never add fields not declared in the answer template.
2. Never omit a required top-level or item-level key.
3. Never use an enum value outside the template's declared set.
4. Match the template's date format (always `YYYY-MM-DD`).
5. All currency amounts are integers (USD).

## Parallel API strategy

Pull data in waves to minimize round-trips while respecting inter-endpoint dependencies:

- **Wave 1** (all parallel, no dependencies): Policies, CRM accounts, CRM contacts, events/tradeshows/import-batches, exhibitors.
- **Wave 2** (after wave 1, keyed by ids): Event orders, badges, sponsor packages, invoices, opportunities, campaign members, meeting interest, suppression.
- Join and classify in memory after both waves complete.

This two-wave pattern covers every task shape in the HarborCRM domain.
