# Atlas Commerce Operations — Analytical & Transactional Skill

## Purpose

Complete a self-contained operational data task against the Atlas Commerce Operations
workplace. Each task provides a natural-language prompt, a business-request payload with
scope/definitions/rules, and an answer-template JSON that enforces the output schema.
Produce exactly one `answer.json` that matches the template with no extra keys or
narrative.

## Input layout (every task)

```
input/
  prompt.txt                  — natural-language task brief + constraints
  payloads/
    answer_template.json       — exact output schema (required keys, types, enums, ordering)
    <request>.json             — business scope, definitions, rollups, policies, rules
```

Read **all three files** before touching the database.

## Workplace API

| Endpoint                    | Method | Purpose                                      |
|-----------------------------|--------|----------------------------------------------|
| `/api/schema`               | GET    | Full DDL for every table + every index       |
| `/api/data-dictionary`      | GET    | Column-by-column descriptions and conventions |
| `/api/sql`                  | POST   | Read-only SQL (`SELECT` / `WITH … SELECT`)   |
| `/api/sql/transaction`      | POST   | Write via `statements[]` + `expected_total_changes` |
| `/api/correction-audit`     | GET    | Read correction-audit records                |

- **Base URL**: read from `environment_access.md` (overrides any `<TASK_ENV_BASE_URL>` placeholder).
- **Auth**: `Authorization: Bearer <token>` from `environment_access.md`.
- **POST /api/sql** body: `{"sql": "<SQL>", "params": [<scalar…>]}`.
  Use parameterised queries — never interpolate values into SQL text.
- **POST /api/sql/transaction** body:
  `{"statements": [{"sql": "<SQL>", "params": [<scalar…>]}], "expected_total_changes": <int>}`.
  `expected_total_changes` is the total rows the transaction must modify (insert + update + delete);
  the endpoint rejects the commit if the actual count differs.

## Step-by-step method

### 1. Absorb the business ask

1. Read `prompt.txt` — extract the task type (analytical vs correction), deadlines/cutoffs,
   and any procedural constraints ("do not change data", "apply only the minimal correction").
2. Read the `<request>.json` payload — capture:
   - **Scope**: date windows, account populations, regions, tiers, segments, campaigns,
     warehouse IDs, import-batch IDs.
   - **Definitions**: what makes an entity eligible, complete, on-time, breached,
     a candidate, severe, etc. These are business-logic predicates.
   - **Rollups / rankings**: aggregation levels, sort orders, tiebreaks, result-size limits.
   - **Policy / status rules**: tiered classifications ordered from strictest to most
     permissive (evaluate in order, the first match wins).
   - **Rounding / precision**: which final values to round and to how many decimal places.
3. Read `answer_template.json` — every `required` key must appear in the output.
   Respect `type`, `enum`, `pattern`, `multipleOf`, `minItems`/`maxItems`, `uniqueItems`,
   `additionalProperties: false`, and any `x-list-ordering` annotations.

### 2. Understand the schema

1. Call `GET /api/schema` and `GET /api/data-dictionary`. Map every entity in the
   business scope to concrete tables and columns.
2. Internalise these conventions (they apply to every table):

| Convention           | Rule                                                                 |
|----------------------|----------------------------------------------------------------------|
| Timestamps           | ISO-8601 UTC text ending in `Z`                                      |
| Dates                | `YYYY-MM-DD` text                                                    |
| Money (minor)        | Stored in the smallest currency unit (cents); divide to get major units |
| FX rates             | `fx_rates.usd_per_unit` — multiply the minor→major converted value   |
| Integer booleans     | `0` = false, `1` = true                                              |
| Canonical fields     | Use `canonical_*` columns for analytics; `raw_*` columns are source values |
| Production filtering | `accounts.is_internal = 0 AND accounts.is_test = 0`                  |
| Effective dedup      | `ROW_NUMBER() OVER (PARTITION BY source_system, external_event_id ORDER BY ingested_at DESC) = 1` |
| Stable identifiers   | Primary-key columns (`*_id`, `*_row_id`) are the authoritative row identity |

### 3. Query the data

#### Read-only analytical SQL

- **Start with CTEs** that define the eligible population using the request scope.
- **Filter early** — apply time windows, account population, region, and segment
  filters in the innermost CTEs so every downstream step works on the smallest set.
- **Dedup correctly** — every imported table (`carrier_scans`, `refund_attempts`,
  `payment_events`, `case_events`, `order_events`, `warehouse_task_events`,
  `inventory_movements`) needs the effective-dedup pattern. The dedup column tuple is
  always `(source_system, external_event_id)` with `MAX(ingested_at)` picking the
  winning row.
- **Use canonical fields** for business logic. Raw fields are source-system values
  that may contradict the canonical truth. The exception is task 003-style
  contradiction detection: compare `raw_status` against `canonical_status` to find
  mismatched rows.
- **Time windows**: when the request says *inclusive* of both boundaries, use
  `>= start AND <= end`. When it says a cutoff, use `<= cutoff`.
- **Money in SQL**: convert minor to major by dividing (e.g. `amount_minor / 100.0`).
  For cross-currency conversions join `fx_rates` on `service_date = rate_date` (or
  `event_at` date) and the row's currency, then multiply:
  `(amount_minor / 100.0) * fx.usd_per_unit`.
- **Aggregate with GROUP BY**, then compute rates as fractions in the outer query.
  Round only the final reported numbers, not intermediate values.

#### Transactional SQL (correction tasks only)

A correction task has these signature elements in the request payload:
- `approved_correction` block with `reason_code`, `actor`, `audit_id`, `correction_key`,
  `corrected_at`
- `correction_status_rule` defining `APPLIED` / `NOT_APPLIED`

**Correction procedure:**

1. **Find the contradiction**: query the raw vs canonical fields to identify exactly
   one row where they disagree.
2. **Plan the UPDATE**: the correction changes only the canonical field to match the
   source truth. The SQL is a single `UPDATE` statement with a `WHERE` clause that
   pins the exact row by its primary key. Set the `corrected_at` and
   `correction_reason` columns as well.
3. **Plan the INSERT**: insert one row into `correction_audit` with all the fields
   from the request's `approved_correction` block plus the actual entity/field/values.
   Required audit columns: `audit_id`, `correction_key`, `entity_type`, `entity_id`,
   `source_row_id`, `field_name`, `old_value`, `new_value`, `reason_code`,
   `corrected_at`, `actor`.
4. **Submit the transaction**: `POST /api/sql/transaction` with both statements and
   `expected_total_changes` set to the sum of rows each statement should affect
   (typically 1 for the UPDATE + 1 for the INSERT = 2). The endpoint atomically
   commits or rejects.
5. **Verify**: `POST /api/sql` a post-correction query to confirm the canonical
   value is now correct, AND `GET /api/correction-audit` to confirm the audit row
   is present.
6. **Report** `APPLIED` only when the transaction succeeded (no error response),
   exactly one business row and one audit row were committed, and the post-change
   query confirms the new value. Otherwise report `NOT_APPLIED`.

### 4. Compute the answer

Translate each business definition into a concrete predicate:

| Definition pattern              | SQL / processing approach                                  |
|---------------------------------|------------------------------------------------------------|
| Count of distinct eligible X    | `COUNT(DISTINCT x_id)` after filtering                     |
| X is complete when …            | Per-entity condition aggregated across child rows; use `HAVING` or a CASE/BOOL_AND pattern |
| X is on-time when …             | Compare delivered timestamps to promised timestamps        |
| Rate = A ÷ B                    | Compute A and B as integers, divide, cast to REAL, round   |
| Severe exception condition      | Apply the 24-hour threshold rule after determining completeness/on-time status |
| Rank / top-N                    | `ORDER BY … LIMIT N` with explicit tiebreak columns        |
| Tiered classification           | Evaluate conditions top-to-bottom; first match wins        |
| Median                          | For even counts average the two central values; use `ORDER BY … LIMIT 1 OFFSET …` or window functions |

- **Round only final reported rates** to the specified decimal places (use `ROUND(value, decimals)`).
- **Sort arrays** exactly as specified (ascending IDs, or rank-order with tiebreaks).
- **Validate** every output value against the template's `type`, `pattern`, `enum`,
  `minimum`, `maximum`, `multipleOf`, `minItems`, `maxItems`.

### 5. Write the output

Write a single JSON object to `answer.json` in the working directory:
- Every key from the template's `required` array must be present.
- No extra keys beyond what the template declares (`additionalProperties: false`).
- Numbers must satisfy any `multipleOf` constraint.
- Strings must match any `pattern` regex.
- Arrays must be within `minItems`/`maxItems` bounds, contain `uniqueItems`, and
  be in the declared order.
- The file must be valid JSON with no trailing text, commentary, or explanation.

## Task-type quick reference

### Analytical / Scorecard (most common)

- Read-only; never call `/api/sql/transaction`.
- The request payload defines cohorts, metrics, rollups, and status rules.
- Compute every metric from the database; do not infer or estimate.
- Typical output: counts, rates, ranked lists, status labels.

### Reconciliation / Exposure

- Involves money: minor-unit conversion and FX rates.
- Leakage / candidate detection: compare values across related rows (e.g., refunds vs
  order gross) and apply multi-condition candidate rules.
- Reason ranking: aggregate by reason code, sort by net amount, apply tiebreaks.

### Carrier Quality / Correction

- Find exactly one raw-vs-canonical contradiction.
- Execute a minimal UPDATE + audit INSERT via `/api/sql/transaction`.
- Verify the correction post-commit.
- Report pre- and post-correction backlog counts.

### Warehouse Productivity

- Time-windowed task creation with a later state cutoff.
- Employee-level metrics: units per productive hour, completion rates.
- Team-level and facility-level aggregations with tiered status.

### Support Health

- Case lifecycle analysis with SLA thresholds per priority.
- Active-time clock: time from open to first response, time from open to resolution.
- Breach detection: compare active time against priority-specific thresholds.
- Worst-account ranking by multi-column sort.

## Guardrails

- **Never skip the schema/dictionary calls** — tables and columns are stable but the
  specific set available may vary. Always introspect before querying.
- **Always use effective dedup** on imported tables or you will double-count rows
  that were re-ingested.
- **Always filter production accounts** (`is_internal = 0 AND is_test = 0`) unless
  the request explicitly says otherwise.
- **Always use canonical fields** for business logic; raw fields are for contradiction
  detection only.
- **Never change data** on analytical tasks — use only `POST /api/sql`.
- **Respect the answer template exactly** — an extra field, a missing required field,
  a value outside an enum, or a number with wrong precision invalidates the answer.
