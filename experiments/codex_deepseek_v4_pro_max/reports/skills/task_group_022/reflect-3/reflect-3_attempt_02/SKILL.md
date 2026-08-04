## Atlas Commerce Operations — Task Solving Guide

This skill covers how to approach analytical, reconciliation, correction, and
health-review tasks against the Atlas Commerce Operations data service. Every
task follows the same solve‑then‑output pattern: discover the schema, translate
business definitions into precise SQL, execute queries, compute requested
metrics, classify the result against policy rules, and write a single
answer-template-conformant JSON document.

### Input layout

Every task directory contains:
- `prompt.txt` — natural-language summary and scope notes.
- `payloads/answer_template.json` — JSON Schema of the required output. The
  answer must conform exactly (no extra keys, correct types, required arrays
  non‑empty where `minItems` > 0, enum values from the listed set).
- One or more request payloads (e.g. `fulfillment_request.json`) carrying the
  full business definitions, cohort rules, time windows, money policy,
  ranking/ordering directives, classification tiers, and any correction
  parameters.

Always read all three files before writing a single SQL statement. The request
payload overrides any assumptions you may form from the prompt alone.

### Environment setup

- Base URL: `http://task-env:9022/`
- Auth header: `Authorization: Bearer atlas-ops-token-022` on every `/api/`
  call.
- Schema discovery: `GET /api/schema` returns table names and column lists;
  `GET /api/data-dictionary` provides human-readable field meanings. Call both
  before querying.
- Read‑only queries: `POST /api/sql` with `{"sql":"...","params":[...]}`.
- Write guarded mutations: `POST /api/sql/transaction` with
  `{"statements":[...],"expected_total_changes":N}`. Only `carrier_scans` and
  `inventory_movements` accept UPDATE; only `correction_audit` accepts INSERT.
  All other writes are rejected.
- Correction audit view: `GET /api/correction-audit` (read-only).

### Step‑by‑step solving

1. **Parse the request payload**: Identify the cohort definition, the time
   window(s), the cutoff timestamp, any tier/region/status filters, and every
   metric definition. Write down each metric in plain language before coding
   SQL.

2. **Discover the schema**: Call `/api/schema` and `/api/data-dictionary`. Map
   every business term in the request to concrete table/column names. Note
   foreign‑key relationships and the grain of each table.

3. **Build queries bottom‑up**: Start with a CTE or subquery that selects the
   exact eligible population. Then layer additional CTEs for each logical
   grouping (completions, exceptions, breaches, FX conversions, etc.). Keep
   queries readable; use `WITH` chains rather than deeply nested subqueries.

4. **Time‑window discipline**: Every date‑range filter must respect the
   `boundary` field (`INCLUSIVE` → `>= start AND <= end`). Cutoff evaluations
   always use `<= cutoff` — events after the cutoff do not exist for the
   analysis.

5. **Compute with full precision, round at the end**: Use unrounded values for
   intermediate comparisons and rankings. Round only when writing the final
   answer, to the decimal places specified in the template (typically 2 or 4).

6. **Apply ranking rules exactly**: Multi‑key ordering with explicit direction
   (`DESC` / `ASC`) and tiebreakers. For "top N" or "worst N", use `ORDER BY
   ... LIMIT N` after computing per‑group aggregates.

7. **Classify the final status**: Evaluate tier conditions in order (first
   matching tier wins). Compute the required rates from the unrounded
   aggregates, then test each tier's boolean conditions.

8. **For correction tasks**: Find the contradiction by comparing raw/canonical
   values. Construct the UPDATE and INSERT with the provided audit metadata
   (audit_id, correction_key, reason_code, actor, corrected_at). Submit via
   `/api/sql/transaction` with `expected_total_changes` matching the plan.
   Verify post‑correction state with a SELECT, then report `APPLIED` or
   `NOT_APPLIED`.

### Common metric patterns

| Pattern | Typical implementation |
|---|---|
| **Eligible count** | `COUNT(DISTINCT id)` over the filtered cohort |
| **Completion rate** | completed / eligible, rounded last |
| **Breach detection** | `active_time > threshold` at cutoff; unresolved items use elapsed time |
| **On‑time rate** | on-time completions / eligible total |
| **Severe exception** | incomplete + beyond grace period, OR completed but late beyond grace |
| **FX conversion** | Join `fx_rates` on currency and service date; multiply amount × `usd_per_unit` |
| **Leakage candidate** | Refund > order gross, OR duplicate reason codes on same order |
| **Median** | `PERCENTILE_CONT(0.5)` or manual even‑count averaging |
| **Units per hour** | `SUM(units) / SUM(minutes) * 60` per employee |
| **Worst/ranking** | `ORDER BY metric ASC/DESC, tiebreaker ASC LIMIT N` |

### Output discipline

- Write output to `answer.json` as a single JSON object.
- No extra keys, no commentary, no markdown fences.
- Arrays must be sorted as specified (ascending ID, descending metric, etc.).
- Enum values must match the template exactly (`HEALTHY`, `WATCH`, `CRITICAL`;
  `LOW`, `MODERATE`, `HIGH`; `STABLE`, `PRESSURED`, `AT_RISK`; `CONTROLLED`,
  `ELEVATED`, `SEVERE`; `APPLIED`, `NOT_APPLIED`).
- Numbers: use the exact `multipleOf` / `precision` from the template.
- Empty arrays are only allowed where `minItems` is 0 or absent. Where
  `minItems` ≥ 1 the array must have that many elements.

### Correction-task specifics

- The contradiction is between a raw source value and the canonical (trusted)
  value for the same field on the same row. Identify the affected scan, the
  shipment, and the conflicting field before writing any mutation.
- UPDATE only the canonical column to match the raw source truth; never alter
  raw source columns, identity fields, or unrelated rows.
- INSERT into `correction_audit` with every required column filled from the
  request payload and the observed old/new values.
- The `expected_total_changes` must equal the sum of UPDATE‑affected rows plus
  INSERT rows. If the commit does not match, the transaction rolls back.

### Traps to avoid

- **UTC assumptions**: All timestamps in the request are UTC. Do not apply
  local‑time offsets.
- **Inclusive vs exclusive boundaries**: Read the `boundary` field; do not
  assume `>=` when `>` is needed or vice versa.
- **Rounding intermediates**: Rounding before ranking or rate comparison
  changes the result. Always rank on unrounded values.
- **Implicit NULL handling**: `NULL` in a comparison yields unknown. Use
  `COALESCE` or explicit `IS NULL` checks where the business definition
  requires it (e.g. "no shipment promise" in severe exceptions).
- **Duplicate rows from JOINs**: When joining one‑to‑many, aggregate the many
  side first or use `DISTINCT` carefully to avoid inflated counts.
- **Ordering stability**: When a template says "then by X ascending", include
  that secondary sort even if the first key seems unique.
- **Transaction guardrails**: The `/api/sql/transaction` endpoint only allows
  UPDATE on `carrier_scans` and `inventory_movements`, and INSERT on
  `correction_audit`. Any other mutation is rejected. The
  `expected_total_changes` must be exact — a mismatch rolls back.
