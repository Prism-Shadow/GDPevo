## When to Use

Use this skill whenever a task involves reconciling data from the **Asteria Fleet Data Quality Hub** — a read-only REST API backed by multiple source systems. The task prompt will reference `<TASK_ENV_BASE_URL>`, `payloads/case_scope.json`, `payloads/answer_template.json`, and `environment_access.md`. Typical domains include partner onboarding, fuel auditing, maintenance history, field-service rosters, and freight accrual.

## Input Contract

Every task provides four inputs. Treat them as the sole sources of truth:

- **`prompt.txt`** — Natural-language description of the objective, expected outputs, and business rules. It names the relevant API endpoints and may define eligibility or readiness conditions.
- **`payloads/case_scope.json`** — Business parameters: `collection_id`, business cutoff or `as_of` timestamp, focus-entity lists, decision-panel IDs, ranking limits, certification thresholds, and action maps.
- **`payloads/answer_template.json`** — The strict output contract. Every key, type, enum value, array length, sort order, uniqueness constraint, and numeric precision declared there is binding. The answer object must conform exactly; no extra keys are allowed.
- **`environment_access.md`** — Runtime connection details: the base URL (`GDPEVO_ENV_BASE_URL`), the `Authorization: Bearer` token, and the list of available GET and POST endpoints.

## API Access

Read the base URL from the environment variable `TASK_ENV_BASE_URL` (or `GDPEVO_ENV_BASE_URL`). All API calls use the base URL and the Bearer token from `environment_access.md`.

**Catalog and schema discovery:**
- `GET /api/catalog/collections` — list available collections; match the one named in `case_scope.json`.
- `GET /api/catalog/schema` — return the schema for all public views. Use this to understand column names, types, and which views map to which collections.

**Source snapshots:**
- `GET /api/source-snapshots` — identify which snapshot is authoritative for the target collection at the given cutoff. Typically the most recent `CERTIFIED` snapshot with `snapshot_ts <= cutoff`. Fall back to `PROVISIONAL`, then `STALE`. The authoritative snapshot ID is required in the final output.

**Domain data (pagination-aware):**
- `GET /api/contacts` — contact records (partner onboarding, field-service rosters).
- `GET /api/transactions/fuel` — fuel purchase transactions.
- `GET /api/transactions/freight` — freight charge transactions.
- `GET /api/maintenance/events` — maintenance event records.

These endpoints may return paged results. When the collection is larger than a single response page, iterate through all pages. The prompt will indicate when pagination is expected.

**Reference data:**
- `GET /api/reference/aliases` — alias mappings for reference IDs.
- `GET /api/reference/conversions` — unit conversion factors.
- `GET /api/reference/fx` — foreign exchange rates.

**Authenticated SQL queries:**
- `POST /api/query` with header `Authorization: Bearer <token>` and `Content-Type: application/json`. Body: `{"query": "<SQL SELECT or WITH>"}`. Use for ad-hoc filtering, aggregation, or joining when the GET endpoints are insufficient. All queries run against public views.

## Reconciliation Workflow

Work through these phases in order for every task:

### Phase 1 — Discover
1. Fetch the catalog (`/api/catalog/collections`) and confirm the target `collection_id` exists.
2. Fetch the schema (`/api/catalog/schema`) to understand the public views and column semantics.
3. Identify the authoritative snapshot: query `/api/source-snapshots`, filter to the target collection, select the snapshot with `snapshot_ts <= cutoff` and status priority `CERTIFIED > PROVISIONAL > STALE`.

### Phase 2 — Fetch Source Records
4. Retrieve all source rows for the authoritative snapshot within the business cutoff using the domain GET endpoint or `POST /api/query`. Use `WHERE snapshot_id = '<id>'` when querying. If the population scope is `ALL_COLLECTION_ROWS`, include every row; otherwise filter as specified in `case_scope.json`.
5. If reference data (aliases, conversions, FX) is needed for normalization, fetch it now.

### Phase 3 — Deduplicate and Reconcile
6. Identify overlapping source records from different sources that represent the same logical entity. Clustering keys depend on the domain:
   - **Contacts**: name + email + phone proximity; identity fields may conflict across sources.
   - **Transactions (fuel/freight)**: transaction/charge ID; multiple raw rows may map to the same logical transaction from different source snapshots.
   - **Maintenance events**: event ID; duplicate raw occurrences may exist from overlapping data loads.
7. For each cluster, select a **survivor row** — the single source row treated as canonical. Survivorship rules depend on the domain and are described in the prompt.
8. Track every duplicate group: list all member row IDs, identify the survivor, and record the retained source snapshot.

### Phase 4 — Identify Quality Issues
9. Classify each logical entity or transaction:
   - **Mismatch**: expected vs. actual category/class differs (e.g., fuel type, service class).
   - **Unrecognized**: cannot assign to exactly one recognized category.
   - **Quarantine**: record with unresolvable physical measures (negative, missing, extreme), invalid timestamps, no usable contact channel, or other data-quality blockers.
   - **Invalid**: events with missing/invalid timestamps, negative labor hours, odometer regressions.
10. **Quarantined records must be excluded from all normalized totals** (spend, volume, weight, distance). They still appear in the output's quarantine/issue lists.

### Phase 5 — Resolve Decision Panels
11. For every public stable ID listed in `case_scope.json` (focus clusters, decision panels, reference rows, source-retention rows, ledger-routing rows, event panels), assign the correct opaque **control code** from the enum in `answer_template.json`.
12. **Control codes are not documented in the task materials** — their meanings must be inferred from the reconciled data. The code assignment follows consistent patterns:
    - Codes with lower numeric suffixes generally indicate higher confidence, fewer exceptions, or cleaner source alignment.
    - Codes with higher numeric suffixes indicate lower confidence, more exceptions, or contested source alignment.
    - Specific assignments must be derived by matching the entity's reconciliation outcome (survivorship, source agreement, quality flags) to the code system.

### Phase 6 — Compute Aggregates and Rankings
13. Compute normalized totals over **valid, non-quarantined** records only (count, volume/weight, distance, spend). Apply unit conversions using `/api/reference/conversions` and FX rates using `/api/reference/fx` when needed.
14. Compute category/service-class subtotals sorted by category name ascending.
15. Compute focus-entity rollups (per asset, per region/depot), readiness partitions, and ranked lists as specified in the scope.

### Phase 7 — Certify
16. Compute the quarantine rate: `quarantine_count / logical_entity_count` (or the metric defined in the prompt).
17. Apply the `status_thresholds` from `case_scope.json`:
    - If quarantine rate ≤ `pass_max_quarantine_rate` → `PASS` → `RELEASE`
    - Else if quarantine rate ≤ `pass_with_exceptions_max_quarantine_rate` → `PASS_WITH_EXCEPTIONS` → `REVIEW_EXCEPTIONS`
    - Else → `HOLD` → `BLOCK_AND_REMEDIATE`
18. Some tasks define domain-specific certification gates (e.g., odometer regression) that override or supplement the rate-based logic. Respect those gates.

## Domain-Specific Rules

### Contact Reconciliation (partner onboarding, field-service rosters)
- **Deduplication key**: name + contact point proximity. Identity-watchlist cases that cannot be auto-resolved remain **contested**.
- **Survivorship**: select the row from the most authoritative source when fields conflict. Source precedence is defined by the task (e.g., HR Directory > Identity Registry > Dispatch for identity fields).
- **Readiness eligibility**: an entity is eligible only when `canonical_record_status = ACTIVE` and at least one usable channel (email or phone) exists.
- **Channel readiness**: a channel is ready only when `canonical_consent_status = GRANTED`.
- **Quarantine trigger**: no usable contact channel (no valid email AND no valid phone).
- **Control families**: `IDENTITY` (IC-*), `OUTREACH` (OR-*), `FIELD_PROVENANCE` (FP-*).

### Fuel Audit
- **Logical transaction**: identified by `transaction_id`; duplicates arise from multiple raw rows for the same ID.
- **Category mismatches**: expected fuel type vs. actual fuel type differ. Unrecognized descriptions cannot be assigned to exactly one recognized category.
- **Quarantine triggers**: negative/zero volume, missing fuel type.
- **Normalization**: convert all volumes to canonical unit (L) using conversion factors; convert all amounts to base currency (USD) using FX rates.
- **Control codes**: reference decisions use `RB-*`; transaction-level decisions use `SB-*` (source basis) and `LD-*` (ledger disposition).

### Maintenance History Audit
- **Logical event**: identified by `event_id`; duplicates arise from overlapping snapshot loads.
- **Quality checks**: missing/invalid timestamps, invalid/negative odometer readings, negative labor hours, extreme labor values, odometer regression (current reading < prior reading for the same asset).
- **Odometer regression** is a hard certification gate: if any regression exists → `HOLD` / `BLOCK_AND_REMEDIATE`.
- **Control codes**: `MS-*` (maintenance source), `HR-*` (history route).

### Freight Accrual
- **Logical charge**: identified by `charge_id`; duplicates arise from overlapping source occurrences.
- **Service-class mismatches**: expected class vs. actual class differ.
- **Quarantine triggers**: unresolvable class or physical measures, missing weight/distance.
- **Carrier ranking**: sort by `mismatch_spend_usd` descending, then `carrier_id` ascending. Exposure = normalized USD on valid charges whose recognized class differs from expected class.
- **Control codes**: reference rows use `RB-*`; source retention uses `SB-*`; ledger routing uses `LD-*`.

## Control Code Reference

All codes are opaque. Assign them by matching the entity's reconciliation outcome to the code tier implied by the numeric suffix (lower = cleaner, higher = more exceptions):

| Family | Codes |
|--------|-------|
| Identity | IC-25, IC-40, IC-70, IC-90 |
| Outreach | OR-15, OR-35, OR-60, OR-80 |
| Field Provenance | FP-20, FP-55, FP-75 |
| Reference Basis | RB-17, RB-42, RB-83 |
| Source Basis | SB-24, SB-61, SB-79 |
| Ledger Disposition | LD-14, LD-31, LD-53, LD-72, LD-88 |
| Maintenance Source | MS-12, MS-47, MS-86 |
| History Route | HR-19, HR-33, HR-74 |

## Certification Status Map

| Status | Action |
|--------|--------|
| PASS | RELEASE |
| PASS_WITH_EXCEPTIONS | REVIEW_EXCEPTIONS |
| HOLD | BLOCK_AND_REMEDIATE |

## Output Rules

1. Return exactly **one JSON object** conforming to `payloads/answer_template.json`. Do not include commentary, Markdown fences, or surrounding text.
2. Every key in `required_top_level_keys` (or `properties` if no such key exists) must be present. No additional top-level keys are permitted.
3. All enum values must match exactly (case-sensitive). Use only values present in the live data or supplied in the scope.
4. Arrays must respect declared `length`/`minItems`/`maxItems` constraints.
5. Sort arrays according to the ordering rule declared in the template (lexicographic ascending, numeric ascending, or a custom sort clause).
6. Floating-point fields must use the declared `precision_decimal_places` (typically 2). Integer fields must be exact whole numbers.
7. Use stable IDs exactly as they appear in the public API responses or the case scope. Do not invent, renumber, or transform IDs.
8. Every list in a decision panel must include exactly the entries requested in `case_scope.json`, in the order specified by the answer template.

## Error Handling

- If an API endpoint returns an error, retry once. If it persists, report the failing endpoint in your reasoning but continue with available data where possible.
- If a required reference value (conversion factor, FX rate) is missing, treat the affected record as quarantined.
- If the answer template declares a `length` that conflicts with the available data, the declared length takes precedence; fill or truncate as appropriate and note the discrepancy.
