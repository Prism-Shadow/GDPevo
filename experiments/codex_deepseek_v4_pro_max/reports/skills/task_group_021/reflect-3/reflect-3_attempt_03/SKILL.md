## Asteria Fleet Data Quality Hub – Reusable Operating Patterns

### Environment Interface

The hub exposes a read-only API at the configured base URL. Every interaction uses:
- `GET /api/catalog/collections` – available collections with source systems and date ranges
- `GET /api/catalog/schema` – public views (`v_contacts`, `v_freight_charges`, `v_fuel_transactions`, `v_fx_rates`, `v_maintenance_events`, `v_reference_aliases`, `v_source_snapshots`, `v_unit_conversions`)
- `GET /api/contacts`, `GET /api/transactions/fuel`, `GET /api/transactions/freight`, `GET /api/maintenance/events` – raw record endpoints (pagination-aware)
- `GET /api/reference/aliases`, `GET /api/reference/conversions`, `GET /api/reference/fx` – reference-lookup endpoints
- `GET /api/source-snapshots` – snapshot metadata per collection
- `POST /api/query` – authenticated SQL read query with `Authorization: Bearer` header and JSON body `{"query": "<SQL>"}`

Always use the `/api/query` endpoint for bulk retrieval; the collection GET endpoints are for discovery only. Every query requires the Bearer token.

### Collection and Snapshot Model

Every collection contains **raw rows** organised into **snapshots** from different source systems. A snapshot has a `snapshot_status` field:
- `CERTIFIED` – authoritative system of record
- `PROVISIONAL` – feed or staging source, not yet certified

When the same logical record (identical `transaction_id`, `charge_id`, `event_id`, or matching `row_id`/email) appears in multiple snapshots, the **CERTIFIED snapshot is authoritative**. Resolve overlaps by:
1. Grouping raw rows by their stable business identifier.
2. Preferring the row from the snapshot whose ID contains `certified` (case-insensitive).
3. Falling back to `provisional` only when no certified row exists.

Record a **duplicate raw count** as the number of excess rows beyond one per logical record.

### Contact Data Reconciliation (Partner Onboarding / Field Service Roster)

Contact collections contain rows from 3 source systems with known precedence:
1. **HR Directory** (highest trust for identity / employment fields)
2. **Identity Registry** (authoritative for legal identity)
3. **Dispatch** (operational scheduling)

For partner-scope collections, the precedence order is:
1. **Partner Portal** (highest)
2. **Compliance Master**
3. **CRM** (lowest)

**Clustering**: Group source rows by normalised email (Unicode NFKC, lowercased, trimmed). Rows whose email is empty, `n/a`, `none`, `na`, `null`, or `nil` after normalisation are treated as separate singleton entities. Do not cluster by source-record index alone.

**Survivor selection** within a cluster:
1. If a Compliance Master row carries a `master_hint` field starting with `MH-`, the master is the Partner Portal row whose `source_record_id` matches the hinted index.
2. Otherwise, prefer rows with `verified_flag = 1`.
3. Among equally verified rows, select by source-system precedence (highest first).

**Canonical values** are drawn from the survivor row for every field (email, phone digits, city, consent, record status, region/depot). The survivor's source system is the `city_source_system` (or equivalent provenance field). Phone is reduced to digits only; email is NFKC-normalised and lowercased.

**Quarantine**: Any source row whose normalised email is unusable AND whose phone digits are empty is a quarantine row. Quarantine rows neither contribute to canonical totals nor participate in readiness counts. The quarantine rate is `quarantine_row_count / canonical_entity_count`, rounded to 4 decimal places.

**Readiness / dispatchability**:
- An entity is **eligible** when its canonical `record_status` is `ACTIVE` and it retains at least one usable email or phone.
- A channel is **ready** only when canonical `consent_status` is `GRANTED`.
- Partition eligible entities into mutually exclusive buckets: `both` (email + phone ready), `email_only`, `phone_only`, and `not_ready` (everything else among eligible).

**Region rollup**: Count canonical entities per `region` (or `depot_code`) from the survivor's region value. Include every region enumerated in the answer contract, even when the count is zero, sorted lexicographically.

### Fuel Transaction Audit

**Alias matching**: Match each transaction's `purchased_description` against `fuel`-domain reference aliases using **case-insensitive substring** matching. Only aliases with `reference_status = 'ACTIVE'` AND whose `valid_from` ≤ transaction date ≤ `valid_to` are considered. A description matching zero aliases is **unrecognised**; matching more than one distinct canonical fuel type is **ambiguous** (both are quarantined).

**Expected-vs-actual**: When exactly one canonical fuel type is recognised but differs from `expected_fuel_type`, the transaction is a **mismatch** (retained for normalised totals but flagged).

**Invalid quantity**: Any transaction with `quantity <= 0` is quarantined regardless of alias match.

**Normalised totals**: Convert every valid transaction's quantity to litres using the `volume` kind in `v_unit_conversions`, and its amount to USD using **CERTIFIED** FX rates (`v_fx_rates` with `rate_status = 'CERTIFIED'`) keyed by `(rate_date, currency)`. USD amounts pass through unchanged. Round all aggregates to 2 decimal places. Quarantined transactions are excluded from normalised totals.

**Merchant / carrier ranking**: Order by exception count descending, then by merchant/carrier ID ascending. Fill to the requested limit with zero-count placeholders. An exception is any retained charge with a category mismatch or quarantine condition.

### Freight Charge Audit

Same pattern as fuel, but matching `description` against `freight`-domain aliases to resolve `expected_service_class` versus recognised `service_class`. Convert `billed_weight` to KG (weight kind) and `distance` to KM (distance kind). A charge is quarantined when its description has zero or multiple recognised service classes, or when `billed_weight <= 0`, or when `distance <= 0`.

### Maintenance Event Integrity

**Business-period scoping**: An event is in scope when its parsed `event_time_raw` falls within `business_period.start` through `business_period.end`. Events with missing or unparseable timestamps are included in issue counts but excluded from valid-event calculations.

**Issue categories** (non-mutually-exclusive; an event can carry multiple issues):
- `missing_timestamp` – `event_time_raw` is NULL or empty
- `invalid_timestamp` – non-NULL but unparseable (e.g. `2026-99-45 25:61`)
- `invalid_odometer` – negative odometer after conversion to KM
- `negative_labor` – `labor_hours < 0`
- `extreme_labor` – `labor_hours > 24` (a single event exceeding one day)
- `odometer_regression` – among valid events for the same asset, sorted by timestamp, any event whose KM odometer is lower than the preceding event

**Corrected distance**: For each asset, take the set of valid, non-regression events sorted by time. Subtract the first reliable odometer from the last. Sum across all assets that have at least two reliable events. Report in KM rounded to 2 decimal places.

**Asset risk ranking**: Order by `rejected_event_count` descending, then `regression_event_count` descending, then `asset_id` ascending. Rejected events are those with any issue (excluding odometer regression). Fill to the requested limit.

### Reference and Policy Decision Codes

Opaque decision codes are assigned to public stable IDs based on the record's state in the authoritative data. The standard mappings are:

| Code Family | Code | Condition |
|---|---|---|
| Identity (`IC`) | `IC-25` | Single source: Partner Portal / HR Directory |
| | `IC-40` | Single source: CRM / Dispatch |
| | `IC-70` | Single source: Compliance Master / Identity Registry |
| | `IC-90` | Multiple sources (mixed identity evidence) |
| Outreach (`OR`) | `OR-15` | Consent = `GRANTED` in evidence set |
| | `OR-35` | Consent = `PENDING` (no `GRANTED`) |
| | `OR-60` | Consent = `DENIED` (no `GRANTED` or `PENDING`) |
| | `OR-80` | Consent = `UNKNOWN` or no usable consent |
| Field Provenance (`FP`) | `FP-20` | All evidence snapshots are `CERTIFIED` |
| | `FP-55` | Mixed `CERTIFIED` and `PROVISIONAL` snapshots |
| | `FP-75` | All evidence snapshots are `PROVISIONAL` |
| Reference Policy (`RB`) | `RB-17` | Alias status = `ACTIVE` |
| | `RB-42` | Alias status = `PROVISIONAL` |
| | `RB-83` | Alias status = `INACTIVE` |
| Source Basis (`SB`) | `SB-24` | Row sourced from `CERTIFIED` snapshot |
| | `SB-61` | Row sourced from `PROVISIONAL` snapshot |
| | `SB-79` | Row appears in both (mixed) |
| Ledger Disposition (`LD`) | `LD-14` | Valid, recognised, posted normally |
| | `LD-31` | Valid charge with expected-vs-actual mismatch |
| | `LD-53` | Description matches zero recognised categories |
| | `LD-72` | Description matches multiple recognised categories (ambiguous) |
| | `LD-88` | Invalid quantity or physical measure |
| Maintenance Source (`MS`) | `MS-12` | Event from `CERTIFIED` snapshot |
| | `MS-47` | Event from `PROVISIONAL` snapshot |
| | `MS-86` | Event from unknown/other snapshot |
| History Route (`HR`) | `HR-19` | Clean event (no issues, no regression) |
| | `HR-33` | Event has at least one data-quality issue |
| | `HR-74` | Event is an odometer regression |

### Certification / Close Decision Thresholds

When the case scope provides a `status_thresholds` map, compare the computed metric (e.g. quarantine rate) to the thresholds:
- At or below `pass_max_quarantine_rate` → `PASS` / `RELEASE`
- At or below `pass_with_exceptions_max_quarantine_rate` → `PASS_WITH_EXCEPTIONS` / `REVIEW_EXCEPTIONS`
- Above → `HOLD` / `BLOCK_AND_REMEDIATE`

When the case scope provides a `status_action_map`, look up the action from the determined status.

When no explicit threshold is given, use `PASS_WITH_EXCEPTIONS` / `REVIEW_EXCEPTIONS` whenever any exception (mismatch, quarantine, regression) exists, and `PASS` / `RELEASE` only when the exception count is zero.

### Data Normalisation Rules

- **Emails**: Unicode NFKC normalise, strip whitespace, lowercase. Treat `n/a`, `none`, `na`, `null`, `nil`, and the empty string as unusable.
- **Phones**: Extract all digit characters; the result is a string of digits. No digit result means no usable phone.
- **Names**: Unicode NFKC normalise, strip outer whitespace; preserve internal casing.
- **Physical units**: Always convert to the canonical unit declared in the case scope before aggregating. Use `v_unit_conversions` with the matching `kind` (`volume`, `weight`, `distance`). The conversion factor is a multiplier from the source unit to the canonical unit.
- **Currency**: Convert to the base currency (usually USD) using `v_fx_rates` where `rate_status = 'CERTIFIED'`. Match on `(rate_date, currency)` where `rate_date` is the business date of the transaction.
- **Numeric precision**: Round all monetary and physical aggregates to 2 decimal places. Rates (quarantine rate) to 4 decimal places.

### Ordering Conventions

- All stable-ID lists (row IDs, transaction IDs, charge IDs, event IDs) are sorted **lexicographically ascending** (as strings, not numerically).
- Arrays of objects are sorted by their primary key field ascending unless a different ordering rule is specified in the answer contract.
- Region arrays: lexicographically by region code.
- Ranking arrays: by the declared primary sort descending, then tie-breaks ascending.

### Answer Contract Discipline

- Produce exactly one JSON object matching the provided answer template schema.
- Every list in the answer must have the exact `minItems`/`maxItems` length declared in the schema.
- Include zero-count entries and zero-value placeholders when the schema requires a fixed-length array.
- Do not include commentary, Markdown, or extra whitespace outside the JSON structure.
