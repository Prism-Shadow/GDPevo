# AsterOps Data Quality Skill — Self Condition

## Environment

- **Base URL**: `http://34.46.77.124:9021` (GDPEVO_ENV_BASE_URL). All tasks use this remote API; never use localhost.
- **Health**: `GET /api/health` — returns `record_counts` and version.
- **Catalog**: `GET /api/catalog` — lists all endpoints, fields, filters, and downloadable CSVs (`downloads` array).
- **Downloads**: `GET /downloads/<filename>` — CSV exports used for source-delta audits. The catalog lists available filenames.

### API filters

Use query-string filters on endpoints:
- `?batch_id=...` / `?person_key=...` / `?source_system=...` on CRM endpoints
- `?region=...&period=YYYY-MM` on fleet purchases
- `?wave_id=...` on logistics cost events
- `?scope=...&period=YYYY-MM` on facilities charges
- `?active=true` on fleet vehicles (filter inactive vehicles from the API call if you only need active ones)

### Reference data

- `GET /api/reference/quality_rules` — controlled enums (CRM statuses, currency rates, valid units, record statuses)
- `GET /api/reference/fuel_aliases` — fuel description-to-canonical mapping with `priority`
- `GET /api/reference/category_aliases` — category description-to-canonical mapping with `priority`

---

## Cross-Cutting Business Rules

### 1. Record Status Lifecycle (applies to: fleet, logistics, facilities)

Every record has a `record_status` field with three values (from `QR_EFFECTIVE_RECORDS`):
- **`posted`** — normal, valid record
- **`void`** — explicitly removed; always excluded from effective set
- **`amended`** — replacement record; its `amends_*_id` field points to the original (the original becomes **superseded**)

**Effective-set construction** (for computing totals, mismatch detection, etc.):
1. Start with all in-scope records.
2. Remove records where `record_status == "void"`.
3. Remove records whose ID appears as the `amends_*_id` of any amendment record (these are **superseded**).
4. The remaining records (status `posted` or `amended`) form the **effective set**.

Key points:
- An amendment record's `amends_*_id` may point to a record **outside the current scope** (different period/region). That target record is still superseded in the abstract, but only include it in your output superseded-ID lists **if it is in the in-scope data**.
- A void record can also be superseded (listed in both `void_*_ids` and `superseded_*_ids`).

### 2. Source Precedence (applies to: CRM contact, campaign)

When multiple source rows exist for the same `person_key`, select the canonical row using this precedence (highest to lowest):
1. `steward_override` — human data steward correction
2. `crm_verified` — verified CRM record
3. `partner_roster` — partner-provided data
4. `event_import` — imported from events

**Within the same source system**: pick the most recent `source_updated_at` (ISO date descending).

**Precedence override**: A person_key has a precedence override when source precedence picks a different row than "choose the newest row by date" would. Report these in `precedence_override_person_keys`.

**Lineage decisions** (`source_lineage_audit[].lineage_decision`):
- `source_precedence_override` — precedence picked a non-newest row where no steward was involved
- `active_steward_correction` — the canonical row's `source_system` is `steward_override`

### 3. Suppression Rules (applies to: CRM contact, campaign)

A source row is **suppressed** (excluded from contactability) when:
- `contact_status == "do_not_contact"`, OR
- `consent_status == "revoked"`

Suppression is checked **before** deduplication. Suppressed rows are removed from the working set before canonical selection.

**Suppressed-but-reachable**: A suppressed row that still has a usable normalized email or phone goes into `suppressed_reachable_row_ids` but is NOT included in contact counts.

### 4. Email and Phone Normalization

**Email**: `value.strip().lower()` — trim outer whitespace, then lowercase.
Check for changes: if the normalized value differs from the raw value AND the raw value is non-blank, the row counts as a normalization change.

**Phone**: Remove all non-digit characters (`re.sub(r'\D', '', value)`) — preserve country code digits present in the source. Example: `"+1-312-555-0166"` → `"13125550166"`.

**Unreachable**: A canonical contact with an empty normalized email AND empty normalized phone is `dropped_unreachable`.

### 5. Alias Resolution (applies to: fleet fuel, facilities categories)

**Matching**: Case-insensitive **substring** match — an alias matches if `alias.lower() in product_description.lower()`.

**Resolution**: Among all matches, pick the alias with the **highest `priority`** value. Its `canonical_fuel` or `canonical_category` is the resolved value.

**No match → `unmapped`**: The canonical value is `unknown`. Flag in `unmapped_description_*_ids`.

**Multiple matches → `priority_overlap`**: Flag in `alias_priority_*_ids`. The alias resolution trace must include:
- `selected_alias`: the winning alias name
- `canonical_fuel`: the resolved fuel class
- `matched_aliases`: list of ALL alias names that matched
- `audit_reasons`: list of applicable reasons (`priority_overlap`, `generic_unleaded_trap`, `selected_unknown_alias`, `unmapped_description`)

**Generic unleaded trap**: The generic alias `"unleaded"` appears as a match alongside a more specific unleaded-mapped alias (e.g., `"unleaded regular"` → unleaded, plus `"unleaded"` → unleaded). The higher-priority specific alias wins, but the generic match is flagged. Note: a description like `"Premium unleaded"` matching `"premium unleaded"` (premium_unleaded) AND `"unleaded"` (unleaded) is a priority_overlap but NOT a generic_unleaded_trap, because `"premium unleaded"` maps to `premium_unleaded`, not `unleaded`.

### 6. Currency Conversion (applies to: logistics)

Rates from quality rule `QR_CURRENCY`:
| Currency | Rate |
|----------|------|
| USD      | 1.00 |
| CAD      | 0.74 |
| EUR      | 1.08 |
| GBP      | 1.27 |

Convert: `usd_amount = round(source_amount * rate, 2)` (round to cents before aggregation). Report all USD values with exactly 2 decimal places.

### 7. Invalid Record Detection (applies to: logistics, facilities)

A record is **invalid** (excluded from effective set, reported in `invalid_*_ids`) when:
- `amount < 0` → `invalid_negative_amount`
- `amount` is null/missing → `missing_amount`
- `unit` is not in the controlled unit enum (kg, lb, mile, shipment, claim) → `invalid_unit`
- `currency` is not a recognized currency code → `invalid_currency`

Invalid records are excluded **before** effective-set construction, alongside void records.

### 8. Vehicle Mismatch Detection (applies to: fleet)

For each effective purchase, compare the resolved `canonical_fuel` with the vehicle's `expected_fuel`:
- **Match**: no issue.
- **Mismatch + vehicle has `exemption_code != "none"`**: business exception (goes to `exception_purchase_ids`, not `mismatch_purchase_ids`).
- **Mismatch + no exemption**: mismatch review (goes to `mismatch_purchase_ids`).

Vehicle review queue: sorted by `vehicle_id` ascending, then `observed_fuel` ascending.

### 9. CSV vs API Source Delta (applies to: fleet)

When a task asks for source-delta audit:
- **API** = current live data from the API endpoint (filtered to scope).
- **CSV** = the monthly export snapshot from `GET /downloads/<name>.csv` (filtered to same scope).

Categories:
- `api_only_current`: in API, not in CSV (new/amended records)
- `csv_only_legacy`: in CSV, not in API (legacy records removed from current set)
- `csv_stale`: same purchase_id in both, but API status is `void` while CSV shows `posted`
- `disagreement`: same `transaction_key` has different purchase_id sets in API vs CSV

CSV-excluded-from-totals = `csv_only ∪ csv_stale` (sorted ascending by purchase_id).

### 10. Segment Mapping (applies to: campaign)

Map `raw_segment` to canonical segment via keyword matching (case-insensitive after trimming):
- Contains `"enterprise"` → `enterprise_renewal`
- Contains `"strategic"` → `strategic_renewal`
- Contains `"smb"` or `"churn"` → `smb_churn_risk`
- Contains `"partner"` → `partner`
- Contains `"ops"` → `ops_lead`
- Otherwise → `unknown`

### 11. Campaign Member Contactability

For each campaign member, reconcile against CRM contact rows:
1. **Hard blocked** (`blocked_or_suppressed`): `member_status` is `"bounced"` or `"unsubscribed"`; OR all CRM contacts for the person_key are suppressed (do_not_contact/revoked).
2. **Needs manual review**: no CRM contact found for the person_key; OR canonical contact has no usable email/phone; OR the member is a duplicate of an already-qualified person_key (extras beyond the first).
3. **Qualified reachable**: has a canonical CRM contact with usable email or phone, not blocked or suppressed.

**Duplicate person_keys in campaign**: the member with the highest `score` wins as the canonical qualified member. Other members for the same person_key go to `needs_manual_review_ids`.

`qualified_reachable_count` = count of **unique person_keys** among qualified members (not member count).

---

## Output Ordering Rules (universal)

- **ID lists**: sort ascending lexicographically (e.g., `charge_id`, `purchase_id`, `member_id`, `row_id`, `event_id`).
- **Person key lists**: sort ascending lexicographically.
- **Enum-typed arrays within objects**: sort by the **template enum declaration order** (not alphabetically). E.g., issue_types in invalid_event_issue_types should match the order `["invalid_negative_amount", "missing_amount", "invalid_unit", "invalid_currency"]`.
- **Objects with required keys**: emit keys in the **template-declared order**.
- **Top-N outputs**: first by count descending, then by name ascending for ties.
- **Canonical contact/member/charge samples**: sorted by `person_key` (contacts), `person_key` (members), or `charge_id` (charges), matching the template's declared ordering.
- **Vehicle review queue**: ascending `vehicle_id`, then ascending `observed_fuel` (preserving one row per vehicle+fuel combination).

---

## Numeric Precision

- **Counts**: always integers.
- **USD amounts**: always 2 decimal places (round each line-item to cents before summing, then round the total).
- **Gallon totals**: 2 decimal places.

---

## Common Pitfalls

1. **Amendment amends outside scope**: An amendment (`amends_*_id`) may point to a record not in the current API response. Don't include that out-of-scope ID in superseded lists — the superseded list should only contain IDs present in the in-scope data.

2. **Void vs superseded overlap**: A void record that is also amended (someone amended a voided record) should appear in BOTH the void list AND the superseded list. They are separate concerns.

3. **Blank vs missing email/phone**: An empty string `""` is NOT a normalization change. Only non-blank values that change under normalization count.

4. **CSV snapshot staleness**: The CSV export is a point-in-time snapshot. Records may be void in the current API but still appear as `posted` in the CSV. These are `csv_stale`.

5. **Alias substring matching traps**: `"fuel"` is a substring of `"fuel surcharge"`, `"diesel fuel"`, etc. Always match all aliases, not just the first hit. The priority-based resolution handles this.

6. **Generic unleaded trap is unleaded-specific**: It only applies when the generic `"unleaded"` alias (priority 50) matches alongside a more specific alias that ALSO maps to `unleaded` (like `"unleaded regular"` at priority 80 or `"regular unleaded"` at priority 80). `"Premium unleaded"` matching `"unleaded"` as a substring is a priority_overlap but NOT a generic_unleaded_trap (the selected fuel is `premium_unleaded`, not `unleaded`).

7. **Phone country code preservation**: Normalize to digits only but keep leading country codes. `"+1-312-555-0166"` → `"13125550166"`, not `"3125550166"`.

8. **Duplicate source rows count**: Counts source rows BEYOND the first row inside each duplicate person_key group. For a group of 3 rows: duplicate_source_rows = 2.

9. **Campaign qualified count is unique people**: `qualified_reachable_count` counts distinct `person_key` values, not member count.

10. **Source precedence applies after suppression**: Remove suppressed rows first, then apply source precedence among remaining rows.

11. **Zero-gallon purchases**: Effective purchases with `gallons == 0` are still included in totals (they contribute 0 to gallon sums and their amount to cost) unless otherwise invalid. They are flagged separately in `zero_gallon_purchase_ids`.

12. **Amended records are kept as effective**: An `amended` record is part of the effective set (unless it itself is void or superseded by another amendment). The record it amends is the one that gets superseded.

---

## Output Field Conventions per Family

### CRM Contact Import
- `quality_flags`: counts at the **source-row** level (not canonical-person level). `duplicate_source_rows` counts source rows beyond the first in each duplicate group. `email_normalization_rows` / `phone_normalization_rows` count source rows where a nonblank value changes under normalization.
- `city_retained_counts`: top 3 by count desc, then city name asc for ties. Only retained canonical contacts.
- `suppressed_contact_ids`: all source rows with `do_not_contact` OR `revoked`, sorted ascending.
- `canonical_contacts`: only non-suppressed person_keys appear. Sort by `person_key` ascending.
- `source_lineage_audit`: include EVERY duplicate person_key group (including groups where all but one row were suppressed). `source_row_ids` includes all rows (even suppressed ones in the group). Sort by `person_key` ascending.

### Fleet Fuel Audit
- `gallons_by_canonical_fuel`: always emit all 6 keys (`diesel`, `unleaded`, `premium_unleaded`, `electric`, `hybrid`, `unknown`), using `0` for absent fuels. Round each to 2 decimal places.
- `vendor_mismatch_counts`: only include vendors with ≥1 purchase in `mismatch_purchase_ids`. Key by vendor name, sorted alphabetically.
- `purchase_count_evaluated`: count of effective purchases (after void/superseded removal).
- `alias_issue_counts`: based on effective purchases only. `generic_unleaded_traps` counts purchases where generic "unleaded" matched alongside a specific unleaded alias.
- `vehicle_review_queue`: sorted `vehicle_id` asc, then `observed_fuel` asc. One row per unique (vehicle_id, observed_fuel) pair. Include both mismatch and exception vehicles.
- `transaction_reconciliation`: sorted by `transaction_key` ascending. Only include transaction_keys where API and CSV disagree.
- `operations_load_decision_audit`: sorted by `purchase_id` ascending. Include ALL in-scope purchase IDs (void, effective, CSV-only).

### Logistics Cost Audit
- `corrected_total_usd`: sum of all effective events' converted USD amounts, rounded to 2 decimal places.
- `cost_type_totals_usd`: all 4 required keys (`freight`, `accessorial`, `tax_fee`, `claim`), rounded to 2 decimals each.
- `top_lane_by_cost`: the single lane with the highest aggregate corrected USD across effective events.
- `unit_correction_counts`: all 5 required keys (`kg`, `lb`, `mile`, `shipment`, `claim`).
- `non_usd_sample_event_ids`: first 10 non-USD, non-void events with a non-null amount, sorted ascending by event_id.
- `amended_event_ids_used`: amendment events that are included in the effective set (replacing their originals).
- `issue_type_counts`: all 9 required keys. `non_usd_currency` counts effective events whose source currency ≠ USD. `advisory_note` counts events with non-empty quality_notes (excluding void/invalid).

### Campaign Audience
- `domain_counts`: lowercase email domain from normalized canonical email. Only domains with ≥1 retained member. Sort keys alphabetically.
- `segment_counts`: all 6 required keys, using 0 where absent.
- `duplicate_person_keys`: person_keys that appear in >1 campaign member row, sorted ascending.
- `blocked_or_suppressed_ids`: members hard blocked by status (bounced/unsubscribed) or all CRM contacts suppressed.
- `needs_manual_review_ids`: members needing human decision (no CRM contact, unreachable, or duplicate extras).
- `canonical_member_sample`: only qualified_reachable members. For duplicates, only the highest-score member per person_key is retained; extras go to needs_manual_review.

### Facilities Charges
- `spend_by_category_usd`: all 7 required keys, rounded to 2 decimals.
- `category_counts`: all 7 required keys.
- `review_reason_counts`: all 8 required keys, using 0 where absent.
- `canonical_charge_sample`: effective charges only, sorted by `charge_id` ascending.
- `top_vendor_by_adjusted_spend`: vendor with highest total adjusted spend among effective charges.

---

## Task Family Reference

| Family | Domain | Key Endpoints | Key Reference |
|--------|--------|---------------|---------------|
| CRM Contact Import | CRM dedup + quality | `/api/crm/contact_rows` | source_system enum, QR_CRM_ENUMS |
| Fleet Fuel Audit | Fleet purchases + fuel mismatch | `/api/fleet/purchases`, `/api/fleet/vehicles` | `/api/reference/fuel_aliases` |
| Logistics Cost Audit | Shipment cost integrity | `/api/logistics/cost_events` | QR_CURRENCY, QR_COST_UNITS |
| Campaign Audience | Campaign member reconciliation | `/api/crm/campaign_members`, `/api/crm/contact_rows` | CRM enums |
| Facilities Charges | Facility spend reporting | `/api/facilities/charges` | `/api/reference/category_aliases` |
