 # Atlas Commerce Operations — Analytical Workload Skill

 ## Overview

 Use this skill whenever a task requires querying or correcting business records
 hosted by an **Atlas Commerce Operations** workplace service. The service
 exposes an authenticated REST/JSON API that lets you inspect the database
 schema, read business data through parameterised SQL, and, when a
 correction is requested, apply guarded mutations inside a transaction.

 The workspace is provisioned separately per task.  Always locate the base URL
 from the task materials first—it may appear as an `environment_access.md`
 file or as a `<TASK_ENV_BASE_URL>` placeholder in the prompt.

 ## Connection & Authentication

 - **Base URL:** supplied by the task environment (e.g. `http://task-env:9022/`).
 - **Auth header:** `Authorization: Bearer atlas-ops-token-022` on every
   `/api/` call.
 - All endpoints return JSON.

 ## API Endpoints

 ### Discovery endpoints (GET)

 | Endpoint                 | Purpose |
 |--------------------------|---------|
 | `GET /api/schema`        | List business tables and their columns.  Always call first. |
 | `GET /api/data-dictionary` | Human-readable descriptions of tables, columns, and codes. |
 | `GET /api/correction-audit` | View committed correction-audit rows.  Use for verification after a mutation. |

 ### Read-only SQL (POST)

 `POST /api/sql`
 - Content-Type: `application/json`
 - Body: `{"sql": "<SELECT or WITH query>", "params": [<scalar>, ...]}`
 - `params` is optional and defaults to `[]`.

 Rules:
 - Only SELECT and WITH (CTE) statements are allowed.
 - Do **not** query SQLite metadata tables or PRAGMA interfaces.  Use the
   schema and data-dictionary endpoints instead.
 - Use the business table and column names returned by `/api/schema`.

 ### Transaction endpoint (POST)

 `POST /api/sql/transaction`
 - Content-Type: `application/json`
 - Body:
   ```json
   {
     "statements": [
       {"sql": "<statement>", "params": [...]},
       ...
     ],
     "expected_total_changes": <integer 0–12>
   }
   ```

 Allowed statements (1–6 per call):
 - `SELECT` / `WITH` queries.
 - **Guarded** `UPDATE` on `carrier_scans` or `inventory_movements` only.
 - `INSERT` into `correction_audit` with all audit columns populated.

 Use this endpoint only when the task explicitly requires a data correction.
 Always follow up with a read-only query to verify the change before reporting
 `APPLIED`.

 ## Task Input Structure

 Every task follows the same input layout:

 ```
 input/
   prompt.txt          — business narrative, role, and instructions
   payloads/
     answer_template.json  — strict JSON Schema for the output
     <request>.json        — scoping facts, business rules, window/cutoff,
                             metric definitions, rounding, classification policy
 ```

 The **answer template** is the output contract.  The **request payload**
 contains the domain-specific business logic that the SQL queries must
 implement.

 ## General Workflow

 1. **Read the inputs.**  Open `prompt.txt`, the request payload, and the
    answer template.  Understand the cohort, the time window or cutoff, the
    metric definitions, and the output schema.

 2. **Discover the schema.**  Call `GET /api/schema` and
    `GET /api/data-dictionary`.  Map every business concept in the request
    (e.g. “order”, “shipment”, “refund”, “case”, “task”) to concrete tables
    and columns.

 3. **Build and run analytical queries.**  Submit `POST /api/sql` calls to
    progressively filter, join, and aggregate the data.  Use CTEs (`WITH`)
    for readability.  Apply every filter, condition, and classification rule
    from the request payload exactly as written.

 4. **Apply business logic.**  Follow the request definitions for:
    - **Unit boundaries** (inclusive/exclusive windows).
    - **Rounding rules** (how many decimal places, when to round).
    - **Classification / risk tiers** (apply conditions in the order given;
      the first matching tier usually wins).
    - **Ranking / ordering** (sort criteria and tie-breaks).
    - **Severity or exception definitions** (computed from query results, not
      hard-coded lists).

 5. **(Correction-only) Execute the approved mutation.**  When the prompt
    asks for a data correction:
    - Identify the exact row, column, old value, and new value from the
      business data.
    - Construct an `UPDATE` + `INSERT` pair inside a single
      `POST /api/sql/transaction` call.  Set `expected_total_changes`
      correctly (typically 2: one business row + one audit row).
    - Re-query the corrected row and any downstream aggregates.
    - Report `APPLIED` only if the post-change query confirms the corrected
      value and the mutation result shows the expected row counts.

 6. **Produce the answer.**  Build a single JSON object that matches every
    `required` field, every type constraint, every `enum`, and every ordering
    rule in the answer template.  Arrays must be sorted as specified and
    contain no duplicates.  Numbers must use the exact precision requested.
    Write the result to `answer.json` with no commentary outside the JSON.

 ## SQL Patterns

 ### Parameterised queries

 Always use `params` for user-supplied values instead of string
 interpolation:

 ```json
 {"sql": "SELECT * FROM orders WHERE created_at >= ? AND created_at <= ?",
  "params": ["2026-04-01T00:00:00Z", "2026-04-30T23:59:59Z"]}
 ```

 ### CTEs for multi-step logic

 Break complex business rules into CTE stages:

 ```sql
 WITH eligible AS (
   SELECT ...
   FROM orders
   WHERE campaign_id = ? AND created_at BETWEEN ? AND ?
 ),
 with_shipments AS (
   SELECT ... FROM eligible LEFT JOIN shipments ...
 )
 SELECT ... FROM with_shipments
 ```

 ### Aggregation and ordering

 When the request specifies ranking (e.g. top N, worst N), embed the sort
 criteria and tie-breaks directly in `ORDER BY ... LIMIT N`.

 ## Time and Date Handling

 - All timestamps from the API are in UTC ISO-8601 format.
 - Use the boundary rules from the request (`inclusive` / `exclusive`) in
   `WHERE` clause comparisons.
 - Cutoff semantics: “at or before cutoff” → `<=`, “strictly before” → `<`.

 ## Currency and FX

 When a task involves multi-currency money:
 - Join against the `fx_rates` table on the relevant date and currency pair.
 - Convert values to the reporting currency before summing or comparing.
 - Round reported monetary amounts to the decimal places in the template
   (typically 2).

 ## Error Handling

 - If a SQL query returns an error, read the message, adjust the query, and
   retry.  Do not silently skip failures.
 - If the schema or data dictionary is missing an expected column, re-read
   the discovery endpoints—the actual column name may differ slightly from
   the request’s terminology.
 - When a transaction fails, report `NOT_APPLIED` and include the actual
   observed state rather than fabricating a success.

 ## Output Checklist

 Before writing `answer.json`, verify:
 - Every `required` field from the template is present.
 - No extra fields beyond those in the template.
 - Array sizes match `minItems`/`maxItems` constraints.
 - Array items are sorted as specified and unique.
 - Numeric precision matches `multipleOf` or decimal-place requirements.
 - Enum fields contain only allowed values.
 - String patterns (e.g. `^ORD-[0-9]{6}$`) are satisfied.
 - The file contains only the JSON object (no markdown fences, no commentary).
