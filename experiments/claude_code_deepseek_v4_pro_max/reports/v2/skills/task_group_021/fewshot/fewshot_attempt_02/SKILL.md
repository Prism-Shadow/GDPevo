# AsterOps Data-Quality Audit Skill

## Environment

**Base URL**: `http://34.46.77.124:9021` — all API calls and downloads use this origin. Never use localhost.

### Discovery endpoints
- `GET /api/health` — confirms the environment is live.
- `GET /api/catalog` — returns all available API surfaces and CSV download URLs. Always start here to discover the current data surfaces.

### Catalog structure
The catalog returns an object with keys like `apis` and `downloads`. Each API surface lists its base path (e.g. `/api/crm/contacts`, `/api/fleet/purchases`, `/api/logistics/cost-events`, `/api/crm/campaign-members`, `/api/facilities/charges`). Each download entry provides a URL to a CSV snapshot export.

### Filtering / querying
Most list endpoints accept query parameters to scope by batch, region, period, wave, campaign, or scope. Check the catalog response for parameter names. When a task mentions a batch_id, wave_id, campaign_id, scope_id, or region+period, use those as query parameters.

### Quality-rule reference
Look for a `quality-rules` or `reference` API surface in the catalog. This provides:
- **Currency conversion rates** (used to convert non-USD amounts to USD cents).
- **Fuel alias → canonical fuel class** mappings, often with a `priority` field.
- **Category alias → canonical category** mappings for vendor charge categorization.
- **Source precedence order** for contact/customer record resolution.

Always fetch the quality rules before processing data. If conversion rates or alias tables change between runs, the API is authoritative.

## Data Fetching Workflow (General Pattern)

1. `GET /api/catalog` — discover all available surfaces.
2. For each relevant surface, fetch data scoped to the task's target (batch, wave, campaign, region+period, scope+period).
3. Fetch the quality-rule reference to get conversion rates, alias tables, precedence rules.
4. Download any CSV snapshots referenced in the catalog for source-delta reconciliation.
5. Join records by shared keys (person_key, transaction_key, business_key, vehicle_id, etc.).

## Normalization Rules

### Email
- Trim outer whitespace.
- Lowercase the entire string.
- Empty string `""` when no canonical email is available.

### Phone
- Remove ALL non-digit characters: spaces, dashes, parentheses, dots, leading `+`.
- Preserve country code digits present in the source value (e.g. `+1-312-555-0166` → `13125550166`).
- Empty string `""` when no canonical phone is available.

### Currency / USD amounts
- Fetch conversion rates from the quality-rule reference API.
- For each event/charge with a non-USD currency, convert: `amount_usd = round(amount * rate, 2)`.
- Apply rounding to cents (2 decimal places) **per record before aggregation** — do not sum raw floats and round once at the end.
- Report all USD totals with exactly 2 decimal places (e.g. `237277.31`, `0.00`).
- USD-sourced amounts are used as-is (rate = 1.0).

### Domain extraction
- From the canonical (normalized) email, extract the part after `@`.
- Lowercase the domain.
- Count only for retained/qualified contacts.

## Record Lifecycle: Amendment, Supersede, and Void

These rules apply across ALL task families:

### Void records
- A record with `record_status: "void"` or `status: "void"` is excluded from effective counts and aggregations.
- Track void record IDs in `void_event_ids` / `void_purchase_ids` / decision-audit void lists.

### Amendment records
- An amendment record (identified by an `amends` field pointing to an earlier record ID, or `record_status: "amended"`) **replaces** the original in the effective set.
- The amended (newer) record is included in effective counts; the superseded (older) record is excluded.
- Track superseded IDs separately from voided IDs.

### Superseded records
- If an amendment chain exists, only the latest amendment is effective.
- Superseded records are excluded from operational totals.

### Business-key deduplication (when no amendment chain)
- When multiple records share the same `business_key` and none is an amendment, after removing voids and invalids, count the extras as duplicates.
- For task 003 (cost events): if duplicates remain, count them as `duplicate_business_key_count`.

## Source Precedence and Canonical Selection

### Contact/person record sources (Tasks 001, 004)
The source precedence order (highest to lowest) is defined in the quality-rule reference. The typical order seen in train outputs:
1. `steward_override` — steward manual correction (highest)
2. `crm_verified` — CRM verified data
3. `partner_roster` — partner-provided data
4. `event_import` — event registration data (lowest)

When multiple source rows exist for the same person_key:
1. Sort available rows by source precedence (highest first).
2. Select the highest-precedence row as canonical.
3. If two rows have the same source, use the quality-rules tiebreaker (often newest or lowest row_id).
4. Track cases where source precedence overrides "newest row" selection as `precedence_override`.

### Canonical contact selection
For duplicate person groups:
- `canonical_source` = the source of the selected row.
- `email` / `phone_digits` = normalized values from the selected canonical row.
- `city` = from the selected canonical row.
- `contact_status` = determined by suppression/consent/contactability rules (see below).

## Suppression and Contactability

### Suppression rules (Tasks 001, 004)
A contact row or campaign member is suppressed/blocked when:
- `do_not_contact` flag is true.
- Consent status is `revoked`.
- Campaign member status is `bounced` or `unsubscribed`.
- The CRM contact row has a suppression note.

**Critical**: Suppression overrides reachability. Even if a suppressed record has a valid email and phone, it is still suppressed — do not count it as reachable.

### Dropped unreachable (Task 001)
A canonical person is `dropped_unreachable` when:
- They are NOT suppressed, BUT
- They have no usable email AND no usable phone (both normalize to empty string).

### Contact status values
- `retained` — reachable, included in load.
- `dropped_unreachable` — no usable contact channels.
- `suppressed` — do-not-contact or revoked consent.
- `manual_review` — needs human decision (e.g. duplicate ambiguities).

### Campaign contactability (Task 004)
- `qualified_reachable` — has email or phone, not suppressed, not bounced, not blocked.
- `blocked_or_suppressed` — hard-blocked by status or consent.
- `needs_manual_review` — ambiguous duplicate where the canonical choice isn't clear.

## Fuel Alias Resolution (Task 002)

### Alias matching
- Match each purchase's `product_description` against the fuel alias reference table.
- An alias maps a description string to a `canonical_fuel` class.
- When a description matches multiple aliases, select by **priority** (lower number = higher priority).
- `unknown` is the fallback when no alias matches.

### Generic unleaded trap
- The alias `"unleaded"` (generic) often overlaps with more specific unleaded aliases like `"unleaded regular"` or `"premium unleaded"`.
- When a description matches BOTH a specific unleaded alias AND the generic `"unleaded"`, the specific alias wins by priority. Flag this as `generic_unleaded_trap`.
- This is not an error — it's an audit note that the alias table has overlapping entries.

### Alias resolution trace
For every purchase with nontrivial resolution (>1 match or flagged):
- `selected_alias` — the alias label that was chosen.
- `canonical_fuel` — the fuel class it maps to.
- `matched_aliases` — ALL alias labels that matched the description.
- `audit_reasons` — why this resolution needed attention (`priority_overlap`, `generic_unleaded_trap`, `selected_unknown_alias`, `unmapped_description`).

### Controlled fuel classes
`diesel`, `unleaded`, `premium_unleaded`, `electric`, `hybrid`, `unknown`

## Category Alias Resolution (Task 005)

### Vendor charge categorization
- Match each charge's `description` or `product` field against the category alias reference.
- Map to canonical categories: `fuel`, `maintenance`, `freight`, `accessorial`, `claim`, `tax_fee`, `unknown`.
- Charges with ambiguous aliases (matching multiple categories) get `review_reasons: ["ambiguous_alias"]` and are categorized as `unknown`.

## Vehicle Fuel Mismatch (Task 002)

### Expected vs observed
- Join purchases to vehicle records by `vehicle_id`.
- `expected_fuel` = what the vehicle record says it takes.
- `observed_fuel` = the canonical fuel class resolved from the purchase's product description.
- When expected ≠ observed, it's a mismatch.

### Mismatch vs exception
- A **mismatch** goes to the `vehicle_review_queue` and `mismatch_purchase_ids`.
- An **exception** (vehicle has a business exception flag) goes to `exception_purchase_ids` and gets `ops_action: "exception_documented"`.

## Source Delta: API vs CSV Snapshot (Task 002)

### Reconciliation
- The API returns **current** state; the CSV export is a **monthly snapshot**.
- Compare by `transaction_key`:
  - **api_only_current**: purchase in API, not in CSV → new record after snapshot.
  - **csv_only_legacy**: purchase in CSV, not in API → legacy record dropped from current system.
  - **csv_stale**: same transaction_key exists in both but the CSV version is stale (e.g. superseded in API).
  - **source_disagreement**: same transaction_key, but data differs between API and CSV.

### Operational exclusion
- CSV-only legacy records (`csv_only_legacy`) and stale CSV records (`csv_stale`) are **excluded from operational totals** (gallons, spend).
- Only current API records contribute to fuel totals and mismatch review.

### Reconciliation status values
`api_current_replaces_stale_csv`, `csv_only_legacy`, `csv_extra_legacy`, `csv_stale_status`

## Invalid Record Detection (Tasks 003, 005)

### What makes a record invalid (not just void/superseded)
- **Negative amount**: `amount < 0` → `invalid_negative_amount`.
- **Missing amount**: `amount` is null/absent but record is otherwise active → `missing_amount`.
- **Invalid unit**: unit value not in the controlled unit enum → `invalid_unit`.
- **Invalid currency**: currency code not recognized → `invalid_currency`.

Invalid records are excluded from effective counts and USD aggregation, tracked separately from voided/superseded records.

## Aggregation and Counting Rules

### Effective record set
The effective set = all records in scope MINUS: void records, superseded records, invalid records.

### Counting rules (apply across all tasks)
- **duplicate_person_groups** (Task 001): count of person_key values appearing in >1 source row.
- **duplicate_source_rows** (Task 001): count of source rows beyond the first in each duplicate group (total extra rows).
- **duplicate_business_key_count** (Task 003): count of business keys with >1 candidate after removing voids and invalids.
- **suppression_rows** (Task 001): count of source rows with do_not_contact or revoked consent.
- **email_normalization_rows** / **phone_normalization_rows**: count of nonblank email/phone values that change when normalized.
- **stale_or_inactive_rows**: rows marked stale or inactive.

### Gallon totals (Task 002)
- Sum gallons for all effective (non-void, non-superseded, current API) purchase records.
- Group by `canonical_fuel`. Include all 6 fuel classes (use `0.0` for absent classes).
- Round to 2 decimal places.

### Cost totals (Tasks 003, 005)
- Sum `adjusted_amount_usd` / `corrected_amount_usd` for all effective records.
- Group by cost_type or category enum. Include all required keys (use `0.00` for absent categories).
- Round to 2 decimal places.

## Output Ordering Conventions

All lists must be sorted **ascending** (lexicographic/alphanumeric):
- ID lists: `suppressed_contact_ids`, `mismatch_purchase_ids`, `exception_purchase_ids`, `void_event_ids`, `invalid_charge_ids`, etc.
- Object arrays: `canonical_contacts` by `person_key`, `vehicle_review_queue` by `vehicle_id` then `observed_fuel`, `canonical_member_sample` by `person_key`, `canonical_charge_sample` by `charge_id`, `transaction_reconciliation` by `transaction_key`.
- `alias_resolution_trace` by `purchase_id` ascending.
- `invalid_event_issue_types` by `event_id` ascending; `issue_types` arrays use template enum order.
- `decision_audit` sub-arrays: ascending by their respective key.

## Empty Values
- Empty lists: use `[]`, never `null` or missing.
- Zero counts: use `0` (integer), never `null`.
- Zero USD amounts: use `0.00` (number), never `null`.
- Empty strings for missing canonical email/phone: `""`.

## Controlled Enums (Master Reference)

### Contact sources
`crm_verified`, `event_import`, `partner_roster`, `steward_override`

### Contact status
`retained`, `dropped_unreachable`, `suppressed`, `manual_review`

### Contactability status (campaign)
`qualified_reachable`, `blocked_or_suppressed`, `needs_manual_review`

### Campaign member status
`registered`, `attended`, `no_show`, `bounced`, `unsubscribed`

### Campaign segments
`enterprise_renewal`, `strategic_renewal`, `smb_churn_risk`, `partner`, `ops_lead`, `unknown`

### Fuel classes
`diesel`, `unleaded`, `premium_unleaded`, `electric`, `hybrid`, `unknown`

### Cost types
`freight`, `accessorial`, `tax_fee`, `claim`

### Units (logistics)
`kg`, `lb`, `mile`, `shipment`, `claim`

### Charge categories (facilities)
`fuel`, `maintenance`, `freight`, `accessorial`, `claim`, `tax_fee`, `unknown`

### Review reasons (facilities)
`duplicate`, `invalid_amount`, `invalid_unit`, `missing_contact_channel`, `suppressed_contact`, `ambiguous_alias`, `superseded`, `source_conflict`

### Issue types (logistics)
`invalid_negative_amount`, `missing_amount`, `invalid_unit`, `invalid_currency`, `void_record`, `amended_record`, `duplicate_business_key`, `non_usd_currency`, `advisory_note`

### Audit reasons (fuel alias)
`priority_overlap`, `generic_unleaded_trap`, `selected_unknown_alias`, `unmapped_description`

### Lineage decisions (CRM)
`source_precedence_override`, `active_steward_correction`

### Reconciliation status (source delta)
`api_current_replaces_stale_csv`, `csv_only_legacy`, `csv_extra_legacy`, `csv_stale_status`

### Source action (ops load decision)
`current_api_loaded`, `csv_snapshot_excluded`

### Ops action (ops load decision)
`mismatch_review`, `exception_documented`, `source_snapshot_review`, `superseded_record`, `no_ops_review`

### Owner (ops load decision)
`regional_ops`, `source_integrations`, `none`

### Metric effect (ops load decision)
`included_in_fuel_totals`, `included_exception_not_mismatch`, `excluded_from_totals`

### Decision reasons (ops load)
`expected_fuel_mismatch`, `vehicle_exception`, `superseded_by_api`, `csv_stale_record`, `csv_only_legacy`, `api_current_amendment`

## Common Pitfalls

1. **Rounding before aggregation**: Convert each line to USD cents BEFORE summing. Summing raw floats then rounding gives wrong totals.

2. **Suppression vs unreachable**: Suppressed contacts go to `suppressed_contact_ids` and get status `suppressed`. Unreachable contacts (no email AND no phone, but not suppressed) go to `dropped_unreachable`. These are different categories — don't conflate them.

3. **Non-usd currency**: Records in non-USD currency ARE included in effective counts and aggregations AFTER conversion. They are NOT invalid unless the currency code is unrecognized. Track the count of non-USD records separately in `non_usd_currency`.

4. **Generic unleaded is a trap, not an error**: When "unleaded" (generic) and "unleaded regular" both match, pick the specific one. This is flagged for audit, not treated as an error.

5. **Vehicle exceptions bypass mismatch**: A vehicle with a business exception flag does NOT go to the mismatch queue even if expected ≠ observed fuel. It goes to `exception_purchase_ids` instead.

6. **Amendment chains**: If A → B → C (C amends B, B amends A), only C is effective. A and B are both superseded. If only one amendment exists (B amends A), B is effective and A is superseded.

7. **Zero-gallon purchases**: These are still effective (not void/superseded) but tracked in `zero_gallon_purchase_ids`. They contribute 0 to gallon totals.

8. **CSV snapshot staleness**: Compare API current records against CSV export records. If the same transaction_key appears in both but the CSV version is stale (superseded in API), exclude the CSV version from operational totals.

9. **Source precedence vs newest row**: When source precedence selects a different row than "pick the newest row" would, flag it as `precedence_override`. This is the key differentiator — don't just pick the newest record.

10. **Duplicate business keys after void/invalid removal**: Remove voids and invalids first, THEN check for duplicate business keys. Don't count voids as duplicates.

11. **Ordering is strict**: Evaluators check exact list order. All ID lists ascending. Object arrays sorted by their primary key. Enum-order arrays in template order.

12. **Always include all required enum keys**: In category counts and spend-by-category objects, include ALL enum keys even if value is 0 or 0.00. Missing keys fail validation.
