## Asteria Fleet Data Quality Hub — Reconciliation Skill

### Environment

Set `<TASK_ENV_BASE_URL>` from the task environment (e.g. `http://task-env:9021`).

All read-only GET endpoints are public. The query endpoint requires an `Authorization: Bearer <token>` header supplied in `environment_access.md`.

Available GET endpoints:
- `/api/catalog/collections` — list all data collections with source systems, record counts, and time ranges
- `/api/catalog/schema` — field definitions for every public view
- `/api/contacts` — raw contact records across source systems
- `/api/transactions/fuel` — fleet fuel and charging transactions
- `/api/transactions/freight` — carrier invoice charge lines
- `/api/maintenance/events` — maintenance-log events
- `/api/reference/aliases` — domain-scoped alias-to-canonical mappings
- `/api/reference/conversions` — unit-conversion factors
- `/api/reference/fx` — daily currency exchange rates
- `/api/source-snapshots` — snapshot metadata per collection

`POST /api/query` accepts `{"query": "<SQL>"}` and returns `{"columns":[...], "rows":[[...],...], "row_count":N, "truncated":bool}`. The underlying views are listed in the schema; use standard `SELECT`, `WHERE`, `GROUP BY`, `ORDER BY`, `LIMIT`. Paginate large result sets.

### General Workflow

1. Read `payloads/case_scope.json` for the collection ID, business cutoff, and task-specific configuration.
2. Read `payloads/answer_template.json` for the exact output contract — field names, types, enums, array lengths, and ordering rules.
3. Query `/api/catalog/collections` to confirm the target collection and its source systems.
4. Query `/api/catalog/schema` to understand field meanings and types.
5. Query `/api/source-snapshots` for the target collection to identify authoritative and provisional snapshots.
6. Fetch the raw data from the appropriate view, ordering by the logical primary key (e.g. `row_id`, `transaction_id`, `charge_id`, `event_id`) and then by `snapshot_id`.
7. Reconcile, deduplicate, classify, and normalise according to the domain rules below.
8. Assemble the answer JSON exactly matching the template contract. All arrays must have the specified length and ordering. All numbers must respect the declared precision.

### Source Snapshot Resolution

- Every collection has one or more snapshots. Prefer the snapshot with `snapshot_status = 'CERTIFIED'` as authoritative.
- When the same logical record appears in multiple snapshots, retain the CERTIFIED occurrence. If both are CERTIFIED or neither is, retain the row with the later `ingested_at`.
- The duplicate raw count = `total_raw_rows − unique_logical_ids`.

### Contact Domain Rules

Applies to collections in the `contacts` family (e.g. partner onboarding, field-service roster, dealer contacts).

#### Identity Clustering

- Cluster source rows into canonical people by **normalised email** (Unicode NFKC, trimmed, lowercased).
- Rows whose email is absent, empty, or a sentinel (`N/A`, `None`, `NULL`, `none`, whitespace-only) each form their own singleton cluster.
- The `master_hint` column on Identity Registry / Compliance Master rows carries `MH-NNNN` identifiers. A row whose `master_hint` starts with `MH-` is the designated master record for its cluster.

#### Survivor Selection

For every cluster pick one survivor row (the canonical master ID):
1. The row whose `master_hint` matches `^MH-` (if any).
2. Otherwise the verified row from the most-trusted source (Compliance Master / Identity Registry first, then Partner Portal / HR Directory).
3. Otherwise any verified row.
4. Fall back to the last row in the cluster.

#### Quarantine

A source row is quarantined when **both** of the following are true:
- The email is not usable (absent, sentinel, or lacks `@`).
- The phone is not usable (absent, sentinel, or has zero digits after stripping non-digits).

The quarantine row set is the deduplicated, lexicographically sorted list of such row IDs.

#### Channel Readiness

An entity is _readiness-eligible_ when its survivor is `ACTIVE` and has at least one usable email or phone.
For each eligible entity classify the survivor into exactly one readiness bucket:

| Bucket       | Condition                                         |
|-------------|---------------------------------------------------|
| `both`       | usable email AND usable phone AND consent GRANTED |
| `email_only` | usable email only AND consent GRANTED             |
| `phone_only` | usable phone only AND consent GRANTED             |
| `not_ready`  | consent is not GRANTED, or no usable channel      |

Consent ranking for canonical-consent synthesis: `GRANTED` > `PENDING` > `DENIED` > `UNKNOWN`. When synthesising a canonical consent value for a cluster, take the best (lowest rank-number) consent across all cluster members.

#### Canonical Field Synthesis

When the answer contract asks for canonical values:
- **Name**: prefer Identity Registry / Compliance Master (cleanest Unicode form), then HR Directory / Partner Portal.
- **Email**: normalise (trim, lowercase) from the survivor row.
- **Phone**: digits-only from any cluster member with a usable phone.
- **City**: majority vote across cluster members.
- **`city_source_system`**: the source system of the row that supplied the canonical city.

#### Region / Depot Rollups

Count canonical entities by the survivor's `region` value. The set of expected regions is enumerated in the answer template; include every region even when its count is zero.

### Fuel Transaction Domain Rules

Applies to collections in the `fuel` family.

#### Fuel-Type Recognition

Use the `/api/reference/aliases` with `domain = 'fuel'` and `reference_status = 'ACTIVE'`. Each active alias maps an `alias_text` to a `canonical_value` (one of `DIESEL`, `UNLEADED`, `PREMIUM_UNLEADED`, `BIODIESEL`, `ELECTRIC_CHARGE`).

Match the `purchased_description` against alias texts using **case-insensitive whole-word-boundary search** (`\balias_text\b`). A description that matches aliases pointing to exactly one canonical fuel type is _uniquely recognised_. A description that matches aliases pointing to two or more different canonical types is _ambiguous_. A description that matches no active alias is _unrecognised_.

#### Classification

- **Invalid quantity**: `quantity IS NULL OR quantity <= 0`
- **Unrecognised**: description matches zero active aliases
- **Ambiguous**: description matches two or more different canonical types
- **Mismatch**: uniquely recognised but recognised ≠ `expected_fuel_type`
- **Valid**: uniquely recognised AND recognised = expected (enter normalised totals)

Unrecognised, ambiguous, and invalid-quantity transactions are quarantined and excluded from normalised totals. Mismatched transactions ARE included in normalised totals (they represent real spend).

#### Normalisation

- Convert volume to litres using `/api/reference/conversions` with `kind = 'volume'`.
- Convert spend to USD using `/api/reference/fx` with `rate_status = 'CERTIFIED'`. Match the transaction's `purchased_at` date to the rate's `rate_date`. USD-denominated amounts use a factor of 1.0.
- Round all normalised monetary and physical values to 2 decimal places.

### Freight Transaction Domain Rules

Same pattern as fuel but adapted for the freight domain:

- Use `/api/reference/aliases` with `domain = 'freight'` and `reference_status = 'ACTIVE'`.
- Canonical service classes: `STANDARD`, `EXPRESS`, `REFRIGERATED`, `HAZMAT`, `OVERSIZE`.
- Match `description` against freight alias texts with word-boundary search.
- Convert weight to KG (`kind = 'weight'`) and distance to KM (`kind = 'distance'`).
- Quarantine reasons: `unrecognized_alias`, `ambiguous_alias`, `invalid_weight` (weight ≤ 0 or absent), `invalid_distance` (distance ≤ 0 or absent).
- Quarantined charges do not enter normalised totals; valid class mismatches do.
- Carrier ranking: order by `mismatch_spend_usd` descending, then `carrier_id` ascending. The exception count for a carrier is the distinct count of retained charges that are either a class mismatch or quarantined.

### Maintenance Event Domain Rules

#### Authoritative Snapshot

Use the CERTIFIED snapshot as authoritative. The `snapshot_status` in `v_source_snapshots` determines this.

#### Event Validity Checks

An event is invalid (rejected) if any of the following hold:
- **Missing timestamp**: `event_time_raw IS NULL`
- **Invalid timestamp**: `event_time_raw` cannot be parsed as ISO-8601
- **Invalid odometer**: `odometer_value IS NULL OR odometer_value < 0`
- **Negative labour**: `labor_hours < 0`
- **Extreme labour**: `labor_hours > 100` (look for a clear gap in the distribution; typical values cluster below 12 hours while outliers spike at 120)

#### Odometer Regression

After filtering out invalid events, group remaining events by `asset_id`. Within each asset, sort by `event_time_raw` ascending. For every consecutive pair, if the later odometer reading (converted to KM) is strictly less than the earlier reading, both events are flagged as regression events and the asset is a regression asset.

Convert odometer values to KM using `/api/reference/conversions` with `kind = 'odometer'`.

#### Corrected Distance

For each asset with at least two valid (non-regression) odometer readings, compute `last_reliable_km − first_reliable_km`. Sum across all assets and round to 2 decimal places.

#### Asset Risk Ranking

Order by `rejected_event_count DESC`, then `regression_event_count DESC`, then `asset_id ASC`. Take the top N as specified in the case scope.

### Control Codes (Opaque Asteria Identifiers)

Several answer contracts require Asteria control codes. These are opaque enumerated values drawn from a fixed pool per family. Common families and their pools:

| Family              | Code pool                        |
|--------------------|----------------------------------|
| Identity           | IC-25, IC-40, IC-70, IC-90      |
| Outreach           | OR-15, OR-35, OR-60, OR-80      |
| Field Provenance   | FP-20, FP-55, FP-75             |
| Reference Policy   | RB-17, RB-42, RB-83             |
| Source Basis       | SB-24, SB-61, SB-79             |
| Ledger Disposition | LD-14, LD-31, LD-53, LD-72, LD-88 |
| Maintenance Source | MS-12, MS-47, MS-86             |
| History Route      | HR-19, HR-33, HR-74             |

To select a code for a given entity or decision point, examine the relevant data characteristics:

- **Reference Policy (RB)**: map `reference_status` → RB code: `ACTIVE` → RB-17, `PROVISIONAL` → RB-42, `INACTIVE` → RB-83.
- **Source Basis (SB)**: if only the CERTIFIED snapshot contains the record → SB-24; only a PROVISIONAL snapshot → SB-61; both → SB-79.
- **Ledger Disposition (LD)**: clean match → LD-14; mismatch → LD-31; ambiguous → LD-53; unrecognised → LD-72; invalid quantity/measure → LD-88.
- **Maintenance Source (MS)**: CERTIFIED snapshot → MS-12; PROVISIONAL → MS-47; legacy/other → MS-86.
- **History Route (HR)**: clean event → HR-19; regression event → HR-33; rejected event → HR-74.
- **Identity / Outreach / Field Provenance**: codes are inferred from how many sources agree, consent patterns, and which source supplies the canonical field. The exact inference rules are domain-specific; use the enumerated pool values and pick the code that best describes the data-quality characteristics.

### Certification and Release Decision

Most answer contracts conclude with a status-action pair. The mapping is:

| Status               | Action               |
|---------------------|---------------------|
| PASS                | RELEASE             |
| PASS_WITH_EXCEPTIONS| REVIEW_EXCEPTIONS   |
| HOLD                | BLOCK_AND_REMEDIATE |

Compute the relevant exception rate (quarantine rate, mismatch rate, contest rate) and apply the thresholds declared in the case scope. When the case scope declares a fixed outcome (e.g. `"odometer_regression_status": "HOLD"`), use it directly.

### Ordering and Output Rules

- All ID arrays must be sorted lexicographically and deduplicated.
- All ranking arrays must match the sort criteria declared in the case scope or answer template.
- Regional / depot / category breakdown arrays must include every member of the enumerated set, sorted lexicographically, even when the count is zero.
- Round floating-point values to the precision declared in the answer template (typically 2 decimal places for monetary and physical measures, 4 decimal places for rates).
- Output exactly one JSON object. Do not wrap in Markdown, do not include commentary.

### Common Pitfalls

- **Overlapping snapshots**: Always check for duplicate logical IDs. The provisional snapshot often overlaps the certified one.
- **Sentinel values**: Empty strings, `N/A`, `None`, `NULL`, `none`, and whitespace-only strings signal missing data for email/phone fields.
- **Alias matching granularity**: Use word-boundary matching (`\b`), not arbitrary substring matching. Without word boundaries, `'unleaded'` spuriously matches inside `'premium unleaded'` and causes false ambiguity.
- **Currency normalisation**: Always use CERTIFIED FX rates only. Match on the transaction's date, not the snapshot date.
- **Unit conversion**: Check the `kind` field — distance, weight, volume, and odometer each have separate conversion tables.
- **Null vs zero**: `quantity = 0` and `quantity IS NULL` are both invalid. Distinguish them only when the answer contract requires separate reason counts.
