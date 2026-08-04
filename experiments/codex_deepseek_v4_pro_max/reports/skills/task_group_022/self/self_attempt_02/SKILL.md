This skill defines a reusable operating procedure for analytical tasks backed by the Atlas Commerce Operations workplace API. The procedure is stateless: every run starts from the same discovery steps, applies business logic from supplied payloads, and produces a single validated JSON answer.

## Mandatory execution order

Perform every step in the sequence below. Do not skip discovery, do not assume table or column names, and do not query metadata tables or PRAGMA interfaces. If a step fails, stop and report the failure; do not guess.

### Step 1 — Resolve the workplace base URL

The prompt supplies a base URL via the placeholder `<TASK_ENV_BASE_URL>`. Strip angle brackets and any surrounding whitespace, then use the resulting value as the root for all `/api/` calls. Treat the resolved URL as read-only configuration for the remainder of the run.

### Step 2 — Authenticate every API call

Every `/api/` request must carry the header `Authorization: Bearer atlas-ops-token-022`. POST calls to `/api/sql` and `/api/sql/transaction` also require `Content-Type: application/json`. No other authentication mechanism is needed.

### Step 3 — Discover the data model

Call `GET /api/schema` and `GET /api/data-dictionary`. Read both responses completely before writing any SQL.

- From `/api/schema`: extract every table name, every column name per table, and the declared column types.
- From `/api/data-dictionary`: extract field-level business meanings, relationships (foreign-key or logical), enumerated domain values, and unit-of-measure annotations.
- Build a mental (or scratchpad) mapping of business concepts to physical table.column references. Keep it available for query construction.
- Do **not** query `sqlite_master`, `PRAGMA`, or any other metadata interface through `POST /api/sql`.

### Step 4 — Load and parse the request payloads

The prompt references one or more payload files under `input/payloads/`. Common files:

- **Business request** JSON (e.g. `fulfillment_request.json`, `refund_reconciliation_request.json`). Contains:
  - `request_id` and ownership metadata.
  - `scope` or `cohort`: which rows are in-scope (account tier, date windows, warehouse, region, campaign, batch, etc.).
  - `business_definitions` or `reporting_definitions`: formula semantics and classification criteria.
  - Status/risk/classification tier tables: ordered lists of named outcomes with boolean or threshold conditions. Always evaluate in the given order; the first satisfied condition wins. An `otherwise` or final catch-all entry captures everything that falls through.
  - `rounding` or precision rules: decimal places, `multipleOf`, rounding targets.
  - `required_output`: the top-level keys the caller expects.
- **Answer template** JSON (e.g. `answer_template.json`). A JSON Schema document that defines:
  - `required` property names and their order.
  - `type`, `minimum`, `maximum`, `multipleOf`, `minItems`, `maxItems`, `uniqueItems`, `pattern`, `enum`, `additionalProperties: false`.
  - Array item schemas and ordering rules (often described in `description` or `x-list-ordering` fields).

Parse both payloads into memory before writing any output. The template is the authoritative contract for the answer shape; every required key must be present and every constraint must be satisfied.

### Step 5 — Query the workplace data (read-only path)

Use `POST /api/sql` for all read-only analytical queries.

Request body:
```json
{"sql": "<SELECT or WITH query>", "params": ["<scalar>"]}
```

Rules:
- Use query parameters (`?` placeholders with the `params` array) for all literal values derived from the request payload (dates, IDs, tier labels, region lists, cutoff timestamps). Never interpolate literals into the SQL string.
- Filter to the exact scope defined by the business request (date windows, account populations, regions, campaigns, batches, etc.).
- Apply business definitions from the request faithfully. When a definition references a derived concept (e.g. "complete order", "severe exception", "effective settled refund"), build the corresponding SQL expression or subquery.
- For time-window filters, honour the `boundary` field: `inclusive` / `INCLUSIVE` means `>= start AND <= end`.
- When a cutoff timestamp is given, use it consistently for state evaluation (e.g. "as of cutoff", "delivered by cutoff").
- Retrieve all columns needed for business-rule evaluation; do not rely on in-memory joins across separate queries unless the data volume makes it unavoidable.

### Step 6 — Compute business metrics

Apply every rule from the business request in code (not in additional SQL), unless the rule is trivially expressible in the original query.

Standard computation patterns found across tasks:

- **Counts**: distinct eligible entities, completed/incomplete subsets, breach counts, exception counts.
- **Rates**: numerator divided by denominator (watch for zero-denominator; produce `0` or `0.0` as appropriate for the field type). Round only the final reported rate to the specified decimal places.
- **Rankings**: sort by one or more metric columns, then by a stable identifier ascending as tie-break. Take the top N or bottom N as specified.
- **Tiered classification**: evaluate ordered conditions from top to bottom; the first matching tier is the result. If no tier matches and an explicit `otherwise` tier exists, use it.
- **Rollups by group**: group rows by a category column (e.g. region, reason code, account), compute per-group metrics, then sort and truncate.
- **Median**: sort the values, pick the middle (odd count) or average the two middle values (even count). Round to the specified precision.
- **FX conversion**: when a request specifies an FX basis, join to the declared rates table, match on currency and service date, and apply `value * usd_per_unit`.
- **Leakage / exception detection**: evaluate boolean conditions per entity; collect IDs of entities that satisfy any condition.

### Step 7 — Data-correction path (only when the prompt explicitly instructs a write)

Some tasks require a single controlled data correction. When the prompt states a correction must be applied:

1. Identify the exact contradiction from the raw data by comparing source and canonical values.
2. Use `POST /api/sql/transaction` for the guarded write.
   Request body:
   ```json
   {
     "statements": [
       {"sql": "<UPDATE carrier_scans SET col = ? WHERE ...>", "params": [...]},
       {"sql": "<INSERT INTO correction_audit (...) VALUES (...)>", "params": [...]}
     ],
     "expected_total_changes": 2
   }
   ```
3. The transaction endpoint accepts:
   - `SELECT` / `WITH` queries (read-only within the transaction).
   - Guarded `UPDATE` statements on `carrier_scans` or `inventory_movements`.
   - `INSERT` statements into `correction_audit` with all audit columns populated.
4. Set `expected_total_changes` to the exact number of business + audit row changes.
5. After the transaction, run a verification `SELECT` to confirm the canonical value has changed.
6. Retrieve the audit record via `GET /api/correction-audit` or a `SELECT` on the audit table.
7. Populate `correction_target`, `mutation_result`, `audit_record`, `backlog_analysis`, and `correction_status` from the template, using `APPLIED` only when exactly one business row and one audit row committed and the post-change query confirms the correction.

### Step 8 — Assemble the answer object

Build a single JSON object that satisfies every constraint in the answer template:

- Include every key listed under `required`, and no others (`additionalProperties: false`).
- Match the declared `type` for each property.
- Respect `minimum`, `maximum`, `multipleOf`, `minItems`, `maxItems`, `uniqueItems`, `pattern`, and `enum`.
- Order array elements exactly as specified (by metric descending then ID ascending, or by ID ascending, etc.). Do not add or omit elements.
- Round numeric values at the final step, using the precision declared in the template or business request.
- Use `integer` type (no decimal point) for counts; use `number` for rates and monetary values.
- Escape strings per the JSON spec; output only ASCII-safe UTF-8.

### Step 9 — Validate and write answer.json

- Before writing, validate the assembled object programmatically against the template's constraints.
- Write the validated object to `answer.json` in the working directory with `json.dump` or equivalent (no extra whitespace beyond standard formatting, no trailing newlines that would break strict JSON parsers, but a single trailing newline is acceptable).
- The file must contain only the JSON object — no surrounding text, no markdown fences, no commentary.

### Step 10 — Stop

Do not perform any additional actions after writing `answer.json`. If the prompt mentions a read-only constraint ("do not change workplace data", "analytical only"), confirm that no write endpoint was called.

## Universal constraints

- **No metadata queries**: never send `SELECT ... FROM sqlite_master` or `PRAGMA ...` through `POST /api/sql`.
- **No interpolation**: all SQL literal values go through `params`.
- **No guesswork**: if the schema or data dictionary is ambiguous, re-read it or query a small sample; do not infer column meanings.
- **One answer, one file**: produce exactly `answer.json`. No supplementary files, no logs, no narrative output.
- **Idempotent discovery**: every run re-fetches `/api/schema` and `/api/data-dictionary`; do not cache across runs.
