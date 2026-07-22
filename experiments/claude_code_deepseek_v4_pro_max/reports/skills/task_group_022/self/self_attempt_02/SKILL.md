# Atlas Commerce Operations — Analytical Task Skill

## Purpose

Execute analytical business-intelligence tasks against the Atlas Commerce Operations
database service. Each task arrives as a business request payload paired with an
answer template that defines the exact output contract. Follow the pipeline below
to go from raw request through schema discovery, SQL analysis, computation,
validation, and output.

## API Surface

All tasks use the same authenticated workplace service. The base URL and
credential are provided in the environment; the resolver substitutes
`<TASK_ENV_BASE_URL>` with the actual base.

| Method | Endpoint                    | Purpose                                  | Read/Write |
|--------|-----------------------------|------------------------------------------|------------|
| GET    | `/api/schema`               | Table names, columns, types, keys        | Read       |
| GET    | `/api/data-dictionary`      | Field business meanings and enum values  | Read       |
| POST   | `/api/sql`                  | Run a read-only analytical SQL statement | Read       |
| POST   | `/api/sql/transaction`      | Run a controlled write (UPDATE / INSERT) | Write      |
| GET    | `/api/correction-audit`     | Read audit-trail records after a write   | Read       |

Authentication header for every request:

```
Authorization: Bearer atlas-ops-token-022
```

The `/api/sql` and `/api/sql/transaction` endpoints accept a JSON body with a
`statement` field containing the SQL text.

## Pipeline

Execute these phases in order. Every phase builds on the previous one.

### Phase 1 — Absorb the request

1. Read the business request payload JSON (the file named in the prompt, e.g.
   `input/payloads/fulfillment_request.json`).
2. Read the answer template JSON (`input/payloads/answer_template.json`).
3. Extract and record:
   - **Scope**: which rows belong in the analysis (account tiers, regions,
     campaigns, date windows, shipment cohorts, case populations).
   - **Cutoff(s)**: every timestamp that gates a computation. Treat them as
     exact UTC boundaries. Note whether the boundary is inclusive or exclusive.
     Some tasks have separate *window* and *state cutoff* timestamps.
   - **Business definitions**: every derived concept (complete order, on-time,
     severe exception, leakage candidate, breach, rework). Translate each into
     a computable predicate.
   - **Computation rules**: rates, rankings, rollups, FX conversions, medians,
     rounding instructions.
   - **Classification tiers**: ordered rule sets (HEALTHY→WATCH→CRITICAL,
     LOW→MODERATE→HIGH, CONTROLLED→ELEVATED→SEVERE). Apply in the stated
     order; the first matching rule wins and the final tier acts as a
     catch-all.
   - **Output schema**: the exact required fields, their types, ranges,
     patterns (`^ORD-[0-9]{6}$`, `^CASE-[0-9]{6}$`, `^ACC-[0-9]{4}$`),
     enums, array size constraints, uniqueness rules, and ordering directives.

### Phase 2 — Discover the schema

1. Call `GET /api/schema` to learn the available tables, their columns, data
   types, primary keys, and foreign-key relationships.
2. Call `GET /api/data-dictionary` to learn the business meaning of each
   column: what an enum value represents, which columns hold timestamps vs.
   dates, which hold monetary amounts and in what currency, which hold
   identifiers vs. labels.
3. Map every scope filter, cohort definition, and business predicate from
   Phase 1 onto concrete database columns. Resolve any ambiguity between raw
   and canonical representations using the data dictionary.
4. Identify join paths: which tables connect orders to shipments, refunds to
   reversals, tasks to employees, cases to accounts, scans to shipments.

### Phase 3 — Query the data

1. Build one or more SQL `SELECT` statements that enforce the scope from
   Phase 1. Include every column needed by the business definitions.
2. Submit each statement to `POST /api/sql`. The endpoint is read-only; never
   use it for writes.
3. Inspect the result rows. If the data shape is unexpected (missing columns,
   nulls where business rules assume presence, ambiguous enum values), return
   to Phase 2 and re-check the data dictionary before adjusting the query.
4. For tasks that require a controlled write (carrier quality correction,
   data fix):
   - Build the minimal `UPDATE` statement that changes only the exact
     canonical column, scoped to the exact row identified by the contradiction
     analysis.
   - Submit it to `POST /api/sql/transaction`.
   - Call `GET /api/correction-audit` to read the audit record.
   - Re-run the relevant read query to confirm the post-correction state.

### Phase 4 — Compute the result

Apply the business definitions from Phase 1 to the query results from Phase 3.

**Rates and ratios**: compute numerator and denominator as exact counts, then
divide. Round only the final reported rate. Round to the number of decimal
places specified in the request (commonly 4 for rates, 2 for monetary or
hour values). Use standard rounding (half-up or as the language default).

**Rankings**: sort by the primary criterion first, then by each tiebreaker in
the stated order. When the tiebreaker says "ascending", sort ascending even if
the primary order is descending.

**Monetary calculations**: when FX conversion applies, convert each row's
amount using the rate for that row's service date and currency. Sum converted
amounts, then round the result to the specified display decimals.

**Medians**: for an odd count, take the middle value. For an even count,
average the two central values.

**Tiered classifications**: evaluate conditions in the exact order listed.
The first tier whose conditions are all satisfied is the result. The final
tier is the catch-all and has no explicit conditions to check.

**Array outputs**: sort according to the stated ordering. Remove duplicates.
Produce exactly the required number of items (e.g., top 2, top 3). When the
eligible population is smaller than the requested count, still produce as many
as exist without padding.

### Phase 5 — Validate against the answer template

Before writing output, validate every field:

1. The object has exactly the `required` properties — no missing, no extra.
2. `integer` fields are whole numbers, not floats.
3. `number` fields satisfy `minimum`, `maximum`, and `multipleOf` (or
   `decimal_places` / `precision` annotations in the template).
4. `string` fields match their `pattern` if one is specified.
5. `enum` fields contain only one of the listed values.
6. Arrays have the required `minItems` / `maxItems`, contain no duplicates
   when `uniqueItems` is true, and are sorted according to the documented
   ordering.
7. Nested objects have exactly their required properties and no extras.

If any validation fails, return to Phase 3 or Phase 4 to correct the
computation — do not force-fit the data.

### Phase 6 — Write the output

Write exactly one JSON object to `answer.json` in the working directory. The
file must contain the validated JSON and nothing else: no markdown fences, no
surrounding narrative, no trailing text.

## Correction workflow (write tasks only)

When the task requires a controlled data correction:

1. Identify the exact contradiction from the request (one canonical field in
   one row disagrees with the raw source).
2. Build an `UPDATE` that sets only that canonical column on only that row
   to the correct canonical value. Do not alter raw source columns, source
   identity fields, or unrelated rows.
3. Submit the `UPDATE` to `POST /api/sql/transaction`.
4. Read the audit record from `GET /api/correction-audit` and select the row
   that matches the correction key, entity, and field from the request.
5. Re-query the corrected row to confirm the new canonical value is in place.
6. Report `APPLIED` only when: exactly 1 business row was affected, exactly 1
   audit row was committed, and the post-change query confirms the corrected
   value. Otherwise report `NOT_APPLIED`.

## Rounding and precision conventions

- Rates (completion rate, on-time rate, rework rate, breach rate): round to 4
  decimal places unless the request says otherwise.
- Monetary amounts (USD): round to 2 decimal places.
- Time values (hours): round to 2 decimal places.
- Apply rounding at the final step only. Carry intermediate values at full
  precision.
- When a `multipleOf` constraint appears in the answer template (e.g.,
  `0.0001`), round to that granularity.

## Time handling

- All timestamps from the request are UTC. Treat them as exact boundaries.
- `inclusive` boundaries include rows exactly at the boundary timestamp.
- A *window* defines which rows enter the analysis. A *cutoff* gates the
  state that those rows are evaluated against. They may differ — respect
  both.
- Durations and elapsed times are computed in the clock basis specified by
  the request (e.g., `SUPPORT_ACTIVE_TIME`). Use the relevant timestamps
  from the database, not wall-clock differences.

## Common identifier patterns

These patterns appear across task domains. Use them in SQL `WHERE` clauses
and validation checks:

- Order IDs: `ORD-` followed by 6 digits
- Case IDs: `CASE-` followed by 6 digits
- Account IDs: `ACC-` followed by 4 digits
- Shipment IDs: `SHIP-` or `SHP-` prefix
- Employee IDs: `EMP-` prefix
- Task IDs: `TASK-` prefix

## Common status / tier enums

These classification schemes recur. Use the exact strings:

- Overall status: `HEALTHY`, `WATCH`, `CRITICAL`
- Risk level: `LOW`, `MODERATE`, `HIGH`
- Support risk: `CONTROLLED`, `ELEVATED`, `SEVERE`
- Facility status: `STABLE`, `PRESSURED`, `AT_RISK`
- Correction status: `APPLIED`, `NOT_APPLIED`

## Error recovery

- If a query returns no rows for a scope that should have data, re-check the
  scope filters and date boundaries against the data dictionary before
  widening the search.
- If a computed rate falls outside `[0, 1]`, re-check the denominator
  definition — the denominator is typically the full eligible population, not
  a subset.
- If a tiered classification does not match expectations, verify that
  conditions were evaluated in order and that the catch-all tier was applied
  correctly.
- If the answer template validation fails on an array ordering, re-read the
  ordering directive in the request — primary order and tiebreakers are
  separate.
