# Atlas Commerce Operations — Analytical Task Runner

## Purpose

Execute structured business-analytics tasks against the Atlas Commerce Operations
database. Each task supplies a natural-language prompt, a request payload with
business scope and definitions, and an output contract; this skill produces the
correct `answer.json`.

---

## Phase 1 — Connect

Read the file `environment_access.md` (at the workspace root or the nearest
ancestor directory).  It contains three mandatory fields:

| Field | Use |
|---|---|
| `base_url` | Root URL for every API call.  This value **overrides** any other base-URL reference found in task inputs (`<TASK_ENV_BASE_URL>`, `localhost`, `127.0.0.1`, `env/setup.sh`, `TASK_ENV_BASE_URL`). |
| `credentials.Authorization` | Exact `Authorization` header value — send it verbatim. |
| `allowed_endpoints` | Restrict all HTTP calls to the endpoints listed here.  Do **not** call any other endpoint even if documented elsewhere. |

If `environment_access.md` is missing or any of the three fields is absent, stop
immediately and report the gap — do not proceed.

---

## Phase 2 — Orient

Read these three inputs **in order** for the task at hand:

1. **`prompt.txt`** — Natural-language instructions.  It names the business
   owner, the review type, and the deliverable (`answer.json`).  It also tells
   you whether the task is read-only or may include a data correction.

2. **The request payload** — Referenced inside `prompt.txt` (e.g.
   `input/payloads/<name>_request.json`).  This file contains:
   - **Scope**: cohort membership, time windows, cutoffs, account/region filters.
   - **Business definitions**: what "complete", "on-time", "severe", "leakage",
     "breach", etc. mean for this task.
   - **Metric formulas**: how rates, medians, rankings, and rollups are computed.
   - **Policy rules**: status/risk classification thresholds and their precedence.

3. **`input/payloads/answer_template.json`** — The JSON Schema that the final
   output must conform to.  It defines required fields, types, constraints
   (`minimum`, `maximum`, `multipleOf`, `pattern`, `enum`, `minItems`,
   `maxItems`), and any array ordering rules.

---

## Phase 3 — Explore the data model

Call the two read-only discovery endpoints to understand the database:

```
GET {base_url}/api/schema
Authorization: {credentials.Authorization}
```

Returns table names and column names with data types.  Use this to identify
which tables and columns hold the entities referenced in the request payload
(orders, shipments, refunds, scans, tasks, cases, etc.).

```
GET {base_url}/api/data-dictionary
Authorization: {credentials.Authorization}
```

Returns human-readable descriptions of tables and columns — domain semantics,
enumeration meanings, relationship hints.  Use this to disambiguate columns
whose purpose is not obvious from the schema alone (status codes, flag columns,
timestamp meanings, foreign-key relationships).

---

## Phase 4 — Query with SQL

Submit analytical queries to the read-only SQL endpoint:

```
POST {base_url}/api/sql
Authorization: {credentials.Authorization}
Content-Type: application/json

{
  "sql": "<SELECT or WITH statement>",
  "params": []
}
```

### Query construction rules

- **Use the exact column and table names** from `/api/schema`.
- **Apply the scope from the request payload** first: time-window boundaries
  (treat them as exact UTC, inclusive where stated), account tiers, regions,
  campaign/warehouse IDs.
- **Follow the business definitions literally.**  If a definition says "an order
  is complete only when every shipment is DELIVERED by the cutoff", implement
  that exact logic — do not simplify or approximate.
- **Use the cutoff timestamp as-is.**  If the request says `as_of_cutoff` or
  `state_cutoff_at`, filter state at or before that instant.
- **For ranking/ordering**: implement every tie-break in the request payload.
  The first ordering key dominates, the last is the final tie-break.
- **For medians on even-length sets**: average the two central values.
- **Currency**: when the request specifies a currency policy, join `fx_rates` on
  `service_date` and source currency, convert each row, then aggregate.
- **Transaction time vs. business time**: distinguish creation timestamps from
  effective/service dates — the request payload tells you which one to use.

### Iterative refinement

Start with a broad query that counts the population.  Verify the count is
non-zero and plausible.  Then progressively add joins, filters, and aggregations
for each output field.  Run counts at each stage to catch join explosions or
filter mistakes.

---

## Phase 5 — Compute results

Derive every output field **strictly from SQL query results + the business
rules**.  Do not guess, assume, or use external knowledge.

### Rates and rounding

- Compute rates from their unrounded numerators and denominators **first**.
- Round **only** at the end, to the decimal places specified in the request
  payload (or implied by the answer template's `multipleOf` or `precision`
  constraints).
- If a rate is a fraction of a whole population, the incomplete/breach members
  remain in the denominator.

### Status and risk classification

- Evaluate each condition's rule in the order given by the request payload.
- The first matching condition wins — do not check later conditions once a match
  is found.
- A catch-all / "otherwise" / "all other outcomes" clause must be treated as the
  fallback when no earlier condition matches.

### Arrays and rankings

- When the answer template says `uniqueItems: true`, deduplicate.
- When the payload says "top N" or "worst N" with a sort order, sort by the
  first key descending/ascending as specified, then by each successive
  tie-break.
- When the template specifies `minItems`/`maxItems`, return exactly that many
  items (unless the population is smaller — then the template constraints would
  fail; verify your query covers the full population).

### Timestamps and durations

- Compare timestamps in UTC.
- When computing elapsed time in hours, use fractional hours (e.g.
  `EXTRACT(EPOCH FROM ...) / 3600.0`).
- A missing timestamp (e.g. no shipment promise, no response time) means the
  condition that depends on it cannot be satisfied — treat it as false/absent
  unless the payload explicitly says otherwise.

---

## Phase 6 — Write the answer

Produce exactly one JSON object that satisfies every constraint in the answer
template:

- All `required` fields present.
- No fields beyond those declared (unless `additionalProperties` is `true`).
- Every `type` matches.  Numbers use JSON number literals (no strings).
- Array ordering matches the template and payload rules.
- String patterns (e.g. `^ORD-[0-9]{6}$`) are satisfied.

Write the result to `answer.json` with **no surrounding text, commentary, or
markdown fences**.  The file must be parseable as a standalone JSON document.

---

## Phase 7 — Data correction (only when requested)

When and only when the prompt and request payload call for a data correction:

### Identify the correction target

The request payload names a single contradiction or error.  Query the raw data
to find the exact row and column that needs changing, and confirm the canonical
value the payload prescribes.

### Apply the correction

```
POST {base_url}/api/sql/transaction
Authorization: {credentials.Authorization}
Content-Type: application/json

{
  "statements": [
    {
      "sql": "<single UPDATE statement>",
      "params": []
    }
  ],
  "expected_total_changes": <exact integer>
}
```

- `expected_total_changes` is **not** a guess — compute the exact number of
  rows the UPDATE will affect (business rows) plus any audit rows the system
  inserts (typically 1 audit row per changed business row).  The transaction
  will reject if this number is wrong.
- Use only the approved values from the request payload: `reason_code`, `actor`,
  `audit_id`, `correction_key`, `corrected_at`.
- The UPDATE must target **only** the identified row and column.  Never change
  raw source values, identity fields, or unrelated rows.

### Verify

Call a post-correction SELECT through `POST /api/sql` to confirm the canonical
value now matches the approved new value.  Also call:

```
GET {base_url}/api/correction-audit
Authorization: {credentials.Authorization}
```

to retrieve the audit record the system created.  Confirm it matches every
detail in the correction_target and approved_correction.

### Report APPLIED vs NOT_APPLIED

- `APPLIED`: exactly one business row committed, one audit row committed, and
  the post-change query confirms the corrected value.
- `NOT_APPLIED`: any other outcome — wrong number of affected rows, value
  mismatch, transaction rejected, or unexpected state.

Include the full audit record and backlog analysis in the answer.

---

## Common pitfalls

| Pitfall | Prevention |
|---|---|
| Using `localhost` or a different base URL | Always read `base_url` from `environment_access.md` |
| Omitting the Authorization header | Send it on every request |
| Counting rows instead of distinct business entities | Check whether the template asks for "distinct orders" vs "rows" |
| Rounding intermediate values | Round only the final reported number |
| Forgetting the denominator includes incomplete items | Re-read the rate formula in the request payload |
| Silent join explosions inflating counts | Spot-check a few entity IDs end-to-end |
| Wrong `expected_total_changes` | Count business rows + 1 audit row per business row; verify with a dry-run SELECT |
| Changing more than the minimal canonical field | The request scope is always `MINIMAL_CANONICAL_FIELD_ONLY` |
| Extra text around answer.json | Write the JSON object and nothing else |
