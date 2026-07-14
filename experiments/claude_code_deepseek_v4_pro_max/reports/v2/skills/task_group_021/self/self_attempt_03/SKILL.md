# AsterOps Data-Quality Task Solver Skill

## Environment Setup

**Base URL**: `http://34.46.77.124:9021` (from `environment_access.md` — always overrides any localhost reference in task text).

**Key endpoints** (discoverable via `GET /api/catalog`):
- `GET /api/health` — health check
- `GET /api/catalog` — full endpoint + download listing with field schemas
- `GET /api/crm/contact_rows?batch_id=<id>` — CRM contacts by batch
- `GET /api/crm/contact_rows?person_key=<pk>` — CRM contacts by person (repeat param for multiple)
- `GET /api/crm/campaign_members?campaign_id=<id>` — campaign members
- `GET /api/fleet/purchases?region=<r>&period=<YYYY-MM>` — fleet purchases
- `GET /api/fleet/vehicles?region=<r>` — fleet vehicle registry
- `GET /api/logistics/cost_events?wave_id=<id>` — logistics cost events
- `GET /api/facilities/charges?scope=<s>&period=<YYYY-MM>` — facilities charges
- `GET /api/reference/quality_rules` — controlled enums, currency rates, record-status rules
- `GET /api/reference/category_aliases` — facilities category alias → canonical
- `GET /api/reference/fuel_aliases` — fuel product alias → canonical
- `GET /downloads/<file>` — CSV exports (see catalog for available files)

All API responses are JSON arrays. Query parameters act as filters. Use repeated query params for multi-value filters (e.g., `?person_key=A&person_key=B`).

---

## Universal Business Rules

### 1. Record Status and Amendment Chains

Records use `record_status` with controlled values (from quality rule `QR_EFFECTIVE_RECORDS`):
- `posted` — normal active record
- `void` — permanently excluded, never included in operational totals
- `amended` — a correction record that replaces a prior record

**Amendment chain resolution**:
1. A record `R` with `record_status == "void"` → excluded from effective set (`void_*_ids`)
2. A record `R` with `record_status == "amended"` → included in effective set (`amended_*_ids`)
3. If record `A` has `amends_<id_field> = B`, then `B` is superseded — **unless** `B` is `void`, in which case void status takes precedence (B is just void, not superseded)
4. A `posted` record whose ID appears as another record's `amends_*` field is **superseded** — excluded from effective set (`superseded_*_ids`)
5. Operational totals use only the effective set after removing void, superseded, and invalid records

**Important**: The `amends_*` field on amended records points to the ORIGINAL record, not the other way around. You must scan all records to build the `amends_map` (original_id → amending_id).

### 2. Source Precedence for CRM Contact Canonical Selection

When multiple source rows exist for the same `person_key`, pick the canonical row by:

**Precedence order** (from `quality_rules` controlled values for `source_system`):
1. `crm_verified` (highest)
2. `steward_override`
3. `event_import`
4. `partner_roster` (lowest)

**Tiebreaker**: When precedence is equal, pick the row with the newest `source_updated_at` (lexicographic YYYY-MM-DD comparison works).

**Suppressed rows are excluded from canonical consideration**: Rows with `contact_status == "do_not_contact"` or `consent_status == "revoked"` are removed from the eligible pool before picking the canonical. If ALL rows for a person_key are suppressed, pick among suppressed rows using the same precedence rules.

### 3. Suppression and Blocking Rules

**CRM contacts are suppressed** (hard-blocked) when:
- `contact_status == "do_not_contact"`, OR
- `consent_status == "revoked"`

**Campaign members are hard-blocked** when:
- `member_status` is `"bounced"` or `"unsubscribed"`, OR
- Their canonical CRM contact has `contact_status == "do_not_contact"`, OR
- Their canonical CRM contact has `consent_status == "revoked"`

### 4. Normalization Rules

- **Email**: Trim outer whitespace, then lowercase. Empty string if no value.
- **Phone**: Remove ALL non-digit characters (spaces, parens, dots, dashes, leading `+`). Preserve country-code digits. Empty string if no value.

### 5. Alias Resolution (Case-Insensitive Substring Match)

For both fuel aliases and category aliases:
1. Lowercase the source text and each alias
2. Check if the alias appears as a substring in the source text
3. Collect all matching aliases with their priorities
4. Select the canonical value from the alias with **highest priority**
5. Priority ties → `priority_overlap` / `ambiguous_alias` review reason

**Fuel alias special cases**:
- `generic_unleaded_trap`: The generic alias `"unleaded"` (priority 50) matches alongside a more specific unleaded alias (like `"unleaded regular"`, `"premium unleaded"`). This does NOT change the selected fuel but flags the purchase for review.
- `selected_unknown_alias`: The selected alias maps to canonical fuel `"unknown"`
- `unmapped_description`: No alias matches the product description at all → canonical fuel = `"unknown"`

**Category alias special cases**:
- `ambiguous_alias`: Multiple aliases match the raw_category with different canonical categories. The highest-priority match wins, but the charge is flagged.

### 6. Currency Conversion (Logistics)

Use rates from quality rule `QR_CURRENCY`:
- USD: 1.0
- CAD: 0.74
- EUR: 1.08
- GBP: 1.27

Convert each non-USD amount by multiplying `amount × rate`, then **round to 2 decimal places (cents)** before aggregation. Report all USD totals with exactly 2 decimal places.

### 7. Sorting Conventions

All ID lists must be sorted **ascending alphabetically** (lexicographic string sort):
- `row_id`, `purchase_id`, `event_id`, `charge_id`, `member_id` — ascending string sort
- `person_key` — ascending
- `transaction_key` — ascending

Objects in lists sorted by their primary key (as specified in template ordering notes).

### 8. Counting Conventions

- All counts are **integers** (no decimal places)
- `duplicate_source_rows` = total extra rows beyond first per duplicate group = `sum(len(group) - 1)` across all duplicate person_key groups
- `duplicate_person_groups` = count of person_keys with >1 source row (NOT the count of extra rows)
- `duplicate_business_key_count` = count of business keys with >1 non-void, non-invalid candidate after amendment handling
- `effective_event_count` / `effective_charge_count` / `purchase_count_evaluated` = count of records included in operational totals (after removing void, superseded, AND invalid records)
- `qualified_reachable_count` = count of unique people (person_keys), not campaign member rows

### 9. JSON Output Requirements

- **Always include all required keys** listed in the answer template's `required_top_level_keys` or `required_keys`, even when the value is 0, empty string, `[]`, or `{}`.
- **Object keys** like `segment_counts`, `category_counts`, `gallons_by_canonical_fuel`, `cost_type_totals_usd`, `spend_by_category_usd` must include ALL required keys from the template with 0/0.0 for absent values.
- **Use controlled enum values exactly** as specified in the template — do not invent or vary the enum strings.
- **Sort IDs lexicographically ascending** (string sort, not numeric). `"FC_BG_0000"` < `"FC_BG_0002"` < `"FC_BG_0031"` < `"FC_W_001"`.
- **Sort objects in arrays** by their primary key as specified in template ordering notes (typically `person_key`, `event_id`, `charge_id`, `purchase_id`, `member_id` ascending).
- **List-type keys within objects** (e.g., `issue_types`, `review_reasons`, `audit_reasons`) should be sorted by template enum order, not alphabetically.
- **USD amounts** always have exactly 2 decimal places (e.g., `4477.45` not `4477.4` or `4477.450`).
- **Additional properties** are allowed but not scored — don't add extra keys unnecessarily.

---

## Task-Specific Patterns

### CRM Contact Import Audit (Task Family: CRM Batch)

**Key endpoint**: `GET /api/crm/contact_rows?batch_id=<batch_id>`

**Workflow**:
1. Fetch all rows for the batch
2. Identify suppressed rows (do_not_contact or revoked)
3. Group by person_key → detect duplicate groups
4. For each person_key, pick canonical row using source precedence (excluding suppressed rows from eligible pool)
5. Determine contact_status: `suppressed` (canonical is suppressed) → `dropped_unreachable` (no email AND no phone after normalization) → `retained` (has channel)
6. Source lineage audit only for duplicate person_keys
7. `lineage_decision`: compare canonical selection by precedence vs. by newest date. If different → `"source_precedence_override"`, else → `"active_steward_correction"`
8. City counts: top 3 cities by retained count DESC, then city name ASC for ties

**Normalization changed rows**: A row is flagged if its nonblank email OR nonblank phone changes under normalization. A blank value that stays blank does NOT count.

**Suppressed reachable rows**: Suppressed rows that still have a usable email or phone after normalization (i.e., they COULD be contacted but are blocked by policy).

### Fleet Fuel Purchase Audit (Task Family: Fleet Reconciliation)

**Key endpoints**: `GET /api/fleet/purchases?region=<r>&period=<YYYY-MM>`, `GET /api/fleet/vehicles?region=<r>`, `GET /downloads/fleet_purchases_export.csv`

**Workflow**:
1. Fetch purchases from API (current state) and CSV export (snapshot state)
2. Resolve record status (void/amended/superseded) from API
3. Resolve fuel from `product_description` using fuel aliases
4. Match each effective purchase's observed fuel against vehicle's `expected_fuel`
5. If mismatch and vehicle has `exemption_code != "none"` → exception (not mismatch)
6. Zero-gallon purchases are tracked separately
7. CSV vs API reconciliation — see Source Delta patterns below

**Vehicle review queue**: Only vehicles with at least one fuel mismatch (observed_fuel ≠ expected_fuel). One entry per `(vehicle_id, expected_fuel, observed_fuel)` combination. Sort by vehicle_id ascending, then observed_fuel ascending. The `purchase_ids` list within each entry should be sorted ascending.

**Gallons by canonical fuel**: Sum gallons across all effective purchases (including zero-gallon purchases — they contribute 0 gallons). Round to 2 decimal places. Include all 6 required fuel class keys.

**Vehicle exemptions**: Vehicles with `exemption_code != "none"` that have fuel mismatches are treated as exceptions, not mismatches. The exemption codes observed are `"field_generator"` and `"rental_substitution"`. An exemption with code `"none"` means no exemption — handle normally.

**Source delta audit**:
- `api_only_current_purchase_ids`: In API results, not in CSV (e.g., amendment records added after CSV snapshot)
- `csv_only_legacy_purchase_ids`: In CSV, not in API (legacy export records no longer in source system)
- `csv_stale_purchase_ids`: Same purchase_id in both but with different record_status (CSV has stale status)
- `source_disagreement_transaction_keys`: Same transaction_key appears in both sources but with different records or states
- `csv_records_excluded_from_operational_totals`: CSV records excluded because they're not in the current API

**Transaction reconciliation** (for disagreed transaction_keys):
- `current_api_purchase_ids`: ALL API purchase_ids for this transaction_key (including void/superseded)
- `excluded_purchase_ids`: API purchase_ids excluded from operational totals (void, superseded)
- `csv_export_purchase_ids`: CSV purchase_ids for this transaction_key
- `reconciliation_status`: `"csv_stale_status"` (CSV has old status), `"api_current_replaces_stale_csv"` (API has newer records), `"csv_only_legacy"` (only in CSV), `"csv_extra_legacy"` (CSV has extra records)

**Operations load decision audit**: One row per purchase affected by mismatch, exception, amendment, or source-snapshot handling. Key mappings:
- Mismatched purchases → `ops_action: "mismatch_review"`, `owner: "regional_ops"`, `metric_effect: "included_in_fuel_totals"`, reason: `"expected_fuel_mismatch"`
- Exception purchases (vehicle has exemption) → `ops_action: "exception_documented"`, `owner: "regional_ops"`, `metric_effect: "included_exception_not_mismatch"`, reason: `"vehicle_exception"`
- Amendment purchases → `ops_action: "superseded_record"` or based on context, `source_action: "current_api_loaded"`, reason: `"api_current_amendment"`
- CSV-only legacy → `source_action: "csv_snapshot_excluded"`, `ops_action: "source_snapshot_review"`, `owner: "source_integrations"`, `metric_effect: "excluded_from_totals"`, reason: `"csv_only_legacy"`
- CSV stale records → reason: `"csv_stale_record"`
- API-only current (not in CSV) → reason: `"superseded_by_api"`

Sort the audit rows by `purchase_id` ascending.

### Logistics Cost Event Audit (Task Family: Logistics Integrity)

**Key endpoint**: `GET /api/logistics/cost_events?wave_id=<wave_id>`

**Invalid event detection** (checked on effective records, not void/superseded):
1. `invalid_negative_amount`: `amount < 0`
2. `missing_amount`: `amount` is null/missing
3. `invalid_unit`: `unit` not in `["kg", "lb", "mile", "shipment", "claim"]`
4. `invalid_currency`: `currency` not in recognized rates (USD, CAD, EUR, GBP)

Invalid events are excluded from USD aggregation but still count toward `invalid_*` issue counts.

**Issue type counts** cover ALL events (not just effective):
- `void_record`: count of void events
- `amended_record`: count of amended events
- `duplicate_business_key`: count of extra rows beyond first per duplicate business key (among non-void)
- `non_usd_currency`: count of valid effective events with non-USD currency
- `advisory_note`: count of effective events with non-empty `quality_notes`

**Non-USD sample**: First 10 non-USD, non-void events with an amount, sorted by event_id ascending.

**Top lane**: Lane with highest corrected USD total across valid effective events.

### Campaign Audience Summary (Task Family: CRM Campaign)

**Key endpoints**: `GET /api/crm/campaign_members?campaign_id=<id>`, `GET /api/crm/contact_rows?person_key=<pk>` (one call per person_key, or batch them)

**Segment mapping** from `raw_segment` (case-insensitive substring matching):
- Contains `"enterprise"` → `"enterprise_renewal"`
- Contains `"strategic"` → `"strategic_renewal"`
- Contains `"smb"` → `"smb_churn_risk"`
- Contains `"partner"` → `"partner"`
- Contains `"ops"` → `"ops_lead"`
- Otherwise → `"unknown"`

Check in this priority order — "enterprise" checked before "strategic" to handle "Enterprise Renewal" correctly.

**Duplicate campaign members**: When the same `person_key` has multiple campaign member rows, ALL those members go to `needs_manual_review` (not just the non-canonical ones).

**Qualified reachable**: Must have ALL of:
1. Not hard-blocked (member_status not bounced/unsubscribed, CRM contact not suppressed)
2. Not a duplicate person_key in the campaign
3. Has a usable email OR phone on the canonical CRM contact after normalization

**Domain counts**: Extract domain from canonical email (lowercase, after `@`). Only count retained qualified reachable members.

### Facilities Charge Audit (Task Family: Facilities Spend)

**Key endpoints**: `GET /api/facilities/charges?scope=<scope>&period=<YYYY-MM>`, `GET /api/reference/category_aliases`

**Category resolution**: Apply alias matching to `raw_category` field (not `description`). Highest-priority matching alias wins.

**Review reasons** (apply after effective record determination):
- `duplicate`: Business key appears more than once among effective charges (flag the non-first occurrences)
- `ambiguous_alias`: Multiple aliases match the raw_category
- `superseded`: Charge was superseded by amendment
- Other reasons (`invalid_amount`, `invalid_unit`, etc.) depend on specific data quality issues

**Top vendor**: Vendor with highest total adjusted spend across effective charges. Include their charge_ids sorted ascending.

**Canonical charge sample**: All effective charges sorted by charge_id ascending. Each includes the resolved category, adjusted amount, and applicable review reasons (sorted by template enum order).

---

## Common Pitfalls

1. **Amendment chains are directional**: `amends_X_id` on the AMENDING record points to the ORIGINAL. Build a reverse map to find superseded records.

2. **Void trumps superseded**: If a record is void AND targeted by an amendment, it's just void (not superseded). Only `posted` records targeted by amendments are superseded.

3. **Suppressed rows still appear in source_lineage_audit**: Even suppressed rows count toward duplicate group membership and appear in `source_row_ids`. They're just excluded from canonical selection.

4. **Email normalization**: Leading/trailing whitespace matters. `" opted+event@example.com"` → `"opted+event@example.com"` (leading space removed). Also, case normalization: `"CASE@EXAMPLE.COM"` → `"case@example.com"`.

5. **Phone normalization**: The `+` prefix is a non-digit character and must be removed. `"+1-312-555-0166"` → `"13125550166"`.

6. **Rounding before aggregation**: Convert each individual event's USD amount to cents (round to 2dp) BEFORE summing. Don't sum raw amounts and round the total.

7. **Zero-gallon purchases**: These are still effective purchases and should appear in gallons_by_fuel (contributing 0 gallons) and in zero_gallon_purchase_ids. They still count toward purchase_count_evaluated.

8. **Fuel alias matching is substring-based**: `"Diesel generator fill"` matches alias `"diesel"` (because `"diesel"` is a substring). `"EV fast charge"` matches both `"ev fast charge"` and `"ev charge"` — pick highest priority.

9. **Segment mapping order matters**: Check "enterprise" before "strategic" since "Enterprise Renewal" contains both.

10. **CSV vs API reconciliation**: The CSV export is a snapshot. The API is current state. Differences arise from records added/updated after the snapshot. CSV records not in API that have source_system `"legacy_monthly_export"` are legacy records.

11. **Person_key filtering**: The API returns ALL rows for a person_key across ALL batches. Always filter by batch_id/campaign_id when building batch-specific views.

12. **Duplicate detection for logistics**: Check business keys among non-void records only (void records don't count toward duplicates).

13. **The `amends_*` field on void records**: A void record can still be the target of an amendment. The void status takes precedence — the void record goes to void_ids, not superseded_ids.

14. **Inactive contacts**: `contact_status == "inactive"` is NOT the same as suppression. Inactive contacts are still eligible for canonical selection but are flagged in quality_flags `stale_or_inactive_rows`.

15. **Empty quality_notes**: An empty list `[]` means no advisory notes. Only non-empty lists count toward `advisory_note` issue count.

16. **`canonical_contact_row_id` in campaign sample**: This is the `row_id` from the CRM contact_rows API, NOT the campaign `member_id`. It's the canonical CRM contact row selected for the person.

17. **Inactive vehicles**: Vehicles with `active: false` should still be looked up for fuel matching — the purchase references the vehicle_id regardless of active status.

18. **Alias matching direction**: The alias must be a substring of the source text, not vice versa. `"fuel"` is a substring of `"Diesel fuel"` → match. `"Diesel fuel"` is NOT a substring of `"fuel"` → no match.

---

## Answer Verification Checklist

Before submitting, self-check:

1. ✓ All required top-level keys present in exact template order
2. ✓ All ID lists sorted ascending (lexicographic string sort)
3. ✓ All object arrays sorted by correct primary key
4. ✓ All enum values match template exactly (no typos or variations)
5. ✓ All object-type required keys present (segment_counts, gallons_by_fuel, etc.) even with 0 values
6. ✓ USD amounts have exactly 2 decimal places
7. ✓ Integer counts are whole numbers (no `.0`)
8. ✓ Void + superseded + invalid = total excluded; remaining = effective count
9. ✓ Amendment chain: void records NOT in superseded_ids
10. ✓ Currency conversion: each event rounded to cents BEFORE aggregation
11. ✓ Normalization: emails trimmed+lowercased, phones digits-only
12. ✓ Fuel alias resolution: highest priority match, check for generic_unleaded_trap
13. ✓ Category alias resolution: applied to raw_category field
14. ✓ CSV reconciliation: compare API results directly against filtered CSV rows
