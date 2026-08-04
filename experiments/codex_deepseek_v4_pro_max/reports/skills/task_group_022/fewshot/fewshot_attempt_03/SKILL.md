 # Atlas Commerce Operations Business Analytics Skill

 ## Purpose
 This skill provides a reusable workflow for solving analytical and correction tasks against the Atlas Commerce Operations database. It covers discovering the database schema through API endpoints, translating business definitions into SQL queries, computing analytical results, applying guarded data corrections with audit trails, and producing validated JSON output.

 ## When to Use
 Use this skill when a task involves:
 - A natural-language prompt describing a business analytics, reporting, or data-quality objective
 - Input payloads that include an answer template (JSON Schema) and a request-facts document with scope, business definitions, rules, and policies
 - A requirement to query or correct the Atlas Commerce Operations database
 - A requirement to write the result to `answer.json`

 ## Environment Access

 Read `environment_access.md` in the workspace for the base URL, authentication token, and available API endpoints. The documented endpoints are:

 | Endpoint | Method | Purpose |
 |----------|--------|---------|
 | `/api/schema` | GET | List table names and column metadata |
 | `/api/data-dictionary` | GET | Business descriptions of tables and fields |
 | `/api/sql` | POST | Execute read-only SELECT / WITH queries |
 | `/api/sql/transaction` | POST | Execute guarded write transactions (corrections only) |
 | `/api/correction-audit` | GET | Retrieve committed correction-audit records |

 All `/api/` endpoints require the header `Authorization: Bearer <token>` where `<token>` comes from `environment_access.md`. The SQL endpoint expects `{"sql": "<query>", "params": [...]}` and the transaction endpoint expects `{"statements": [...], "expected_total_changes": <n>}`.

 ## Workflow

 ### Step 1: Discover the Task Inputs

 Locate and read these files in the task working directory:

 1. **`prompt.txt`** — The business objective in natural language. It describes what the stakeholder needs, references the request-facts file, and states output requirements. It also tells you where the service lives (look for `<TASK_ENV_BASE_URL>` or similar placeholder).
 2. **`input/payloads/answer_template.json`** — A JSON Schema document that defines every required output field, its type, constraints (min/max, enums, patterns, precision), and ordering rules. The final `answer.json` must conform exactly to this schema.
 3. **`input/payloads/<request>.json`** — The request-facts file (the exact filename varies per task). It contains:
    - `request_id`, business owner, and purpose
    - **Scope**: time windows, account tiers, regions, cutoff dates, cohort definitions
    - **Business definitions**: precise English descriptions of how to classify rows (e.g., what makes an order "complete", what constitutes a "severe exception")
    - **Rules and policies**: formulas, rollup instructions, ranking orders, rounding rules, status-classification thresholds
    - **Correction parameters** (if applicable): approved correction scope, reason code, actor, audit ID

 ### Step 2: Discover the Database Schema

 Call `GET /api/schema` to learn the available tables and their columns. Then call `GET /api/data-dictionary` to understand the business meaning of each table and field. Cross-reference the data dictionary descriptions against the business definitions in the request-facts file to identify which tables, columns, and relationships are needed.

 Do **not** query SQLite metadata tables or PRAGMA interfaces through `POST /api/sql`. Only analyze business tables returned by the schema endpoints.

 ### Step 3: Map Business Definitions to SQL

 For each business definition in the request-facts file:
 - Identify the relevant tables and columns from the schema and data dictionary
 - Translate the English definition into a SQL expression (WHERE clause, CASE expression, aggregation condition)
 - Pay careful attention to:
   - **Time windows**: inclusive/exclusive boundaries, UTC timestamps
   - **Status lifecycle**: which status values matter, time-of-evaluation (at cutoff vs. historically)
   - **Multi-table relationships**: JOIN keys, cardinality, effective/is-current flags
   - **Currency and FX**: when monetary values need conversion, which rate date to use
   - **Rounding**: when to round intermediate vs. final values

 ### Step 4: Execute Analytical Queries

 Use `curl` with `POST /api/sql` for each query. The request body is `{"sql": "<query>", "params": [...]}`. The params array lets you safely substitute values without string concatenation. Start with exploration queries to verify understanding of the data, then build the computation queries.

 Tips:
 - Break complex computations into multiple queries when needed; compute intermediate results and combine them in code rather than in one giant SQL statement
 - Use CTEs (`WITH`) for readability when the query is complex
 - For median calculations with even counts: average the two middle values
 - For rates: divide counts and round only the final rate
 - For arrays in the output: collect IDs, sort them according to the template ordering rules, and include all qualifying items
 - For ranked selections (top N, worst N): compute the metric, apply the specified sort order, apply the tie-breaking rules, and take the first N

 ### Step 5: Handle Data Corrections (When Applicable)

 If the task requires a data correction (the request-facts file will contain an `approved_correction` block):

 1. **Identify the contradiction**: Query the data to find the row(s) where the raw/source value conflicts with the canonical value or business rules.
 2. **Measure pre-correction state**: Run the relevant backlog/count query before applying the correction.
 3. **Apply the correction** using `POST /api/sql/transaction`:
    - Use `UPDATE` statements only on `carrier_scans` or `inventory_movements` tables
    - Use `INSERT` statements into `correction_audit` with all required audit columns
    - Set `expected_total_changes` to the exact number of rows you expect to change (business rows + audit rows)
 4. **Verify post-correction state**: Run the same query from step 2 to confirm the change.
 5. **Retrieve the audit record** from `GET /api/correction-audit` to confirm it was persisted.
 6. Determine `APPLIED` vs. `NOT_APPLIED` based on the task's correction status rule.

 ### Step 6: Validate and Write Output

 Before writing `answer.json`:
 - Verify every `required` field from the template is present
 - Check that all types match (integer vs. number vs. string)
 - Confirm enum values are valid
 - Verify array lengths (minItems/maxItems), uniqueness, and ordering
 - Check numeric precision (decimal places, rounding)
 - Ensure no additional properties beyond the template

 Write the result as a single JSON object to `answer.json` with no commentary, narrative, or extra whitespace structures outside the JSON.

 ## Task Archetypes

 The training examples demonstrate five common archetypes:

 1. **Scorecard / Rate-based report** — Compute a cohort population, classify rows by business rules, calculate rates, rank sub-groups, identify exception items, and assign an overall status from tiered thresholds.
 2. **Financial reconciliation** — Compute monetary aggregates with currency conversion, rank reasons by net value, identify leakage candidates from multi-condition rules, and classify cohort risk.
 3. **Data-quality correction** — Detect a raw-vs-canonical contradiction, apply a minimal guarded correction via the transaction endpoint, record the audit trail, and report pre/post state.
 4. **Productivity / operational review** — Compute per-employee metrics, rank employees and teams, identify delayed high-priority items, and apply facility-status rules.
 5. **SLA / support-health review** — Classify cases by priority SLA thresholds, compute breach counts, identify severe cases, rank accounts by severity, compute median resolution time, and apply risk policy.

 ## Common Pitfalls

 - **Time boundary errors**: Always check whether the request says "inclusive" or "strictly before" for each boundary.
 - **Cutoff evaluation**: A condition evaluated "at the cutoff" considers the state as of that moment, not historical state changes after the cutoff.
 - **Denominator in rates**: Incomplete/ongoing items typically remain in the denominator even though they are not in the numerator.
 - **Rounding timing**: Most requests specify rounding only final reported rates, not intermediate values. Unrounded values govern tie-breaking and threshold comparisons.
 - **FX rate date**: When valuing cross-currency amounts, use the rate for the transaction's service date, not the report date.
 - **Correction guardrails**: Only `carrier_scans` and `inventory_movements` accept UPDATE statements; only `correction_audit` accepts INSERT statements. The `expected_total_changes` must match exactly.
