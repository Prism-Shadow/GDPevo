---
name: atlas-ops-reporting
description: >-
  Produce cutoff-based operational reports and controlled data corrections from the
  Atlas Commerce Operations workplace database, returning JSON that conforms exactly
  to a supplied answer_template.json. Use whenever a task points at an Atlas / "Commerce
  Operations" workplace service (a <TASK_ENV_BASE_URL> with /api/schema, /api/data-dictionary,
  /api/sql, /api/sql/transaction, /api/correction-audit) and a request payload plus an
  answer_template.json under input/payloads/, and asks for a scorecard, reconciliation,
  productivity / health review, backlog analysis, SLA breach report, or an approved minimal
  canonical correction. Covers read-only analytics and the single-row audited-correction flow.
---

# Atlas Commerce Operations reporting & correction

## What these tasks look like

Every task in this family gives you three things:

1. A `prompt.txt` with business framing and pointers to the payloads.
2. A **request payload** JSON under `input/payloads/` (e.g. `*_request.json`) holding the
   full scope, definitions, cutoffs/windows, ranking rules, rounding rules, and
   classification thresholds. **This file is the specification. The prose in `prompt.txt`
   never overrides it.**
3. An **`answer_template.json`** — a JSON Schema describing the exact output object.

You query the authenticated **Atlas Commerce Operations** service, compute the requested
figures, and write **one JSON object** to `answer.json` that conforms to the template
exactly — no commentary, no extra keys.

Most tasks are **read-only analytics**. A minority are **controlled corrections** that mutate
exactly one field of one row through the transaction endpoint with an audit record. Detect
which from the request (a `correction_status_rule`, `approved_correction` block, or
`/api/sql/transaction` mention ⇒ correction task; otherwise read-only).

## The service

Read `environment_access.md` for the base URL and bearer token. Substitute the real base URL
for any `<TASK_ENV_BASE_URL>` placeholder. Send `Authorization: Bearer <token>` on every call.

| Endpoint | Method | Use |
|---|---|---|
| `/api/schema` | GET | Real table & column names, types, keys. **Read first.** |
| `/api/data-dictionary` | GET | Field semantics: which columns are raw vs canonical/effective, status enums, the production flag, join keys. **Read second.** |
| `/api/sql` | POST | Read-only analysis. Body `{"sql": "..."}`. Returns `{columns, rows, row_count, truncated}`. |
| `/api/sql/transaction` | POST | The only write path (correction tasks). Discover its exact request shape from the schema/dictionary — do not assume. |
| `/api/correction-audit` | GET | View committed audit rows (verify a correction landed). |

**SQL engine facts (verified):** PostgreSQL dialect. `/api/sql` accepts **one statement only**
— no trailing semicolon, no multiple statements, no DDL. A restrictive guard rejects
unexpected constructs with `{"error":"query rejected"}`; keep queries to plain
`SELECT` / `WITH … SELECT` against real tables. Always check the `truncated` flag: if true you
hit a row cap — aggregate in SQL or paginate rather than trusting a partial result. Never
mutate data on a read-only (analytical) task.

## Standard workflow

1. **Read both payloads fully** (request + template) before touching the service. List every
   required output key and its type/enum/pattern/ordering/precision from the template.
2. **GET `/api/schema` and `/api/data-dictionary`.** Map each business concept in the request
   (order, shipment, refund, reversal, task, case, account, warehouse, region, team, employee,
   fx rate, carrier scan, audit) to real tables/columns. **Never guess table or column names.**
3. **Define the eligible population** from the request's scope/cohort exactly (see rules below).
4. **Compute each output** with the request's own definitions — do the heavy lifting in SQL,
   validate small results by hand.
5. **Classify** status/risk by walking the threshold rules top-down (first match wins).
6. **Assemble and validate** the JSON against the template, then write `answer.json`.

## Reusable operating rules

### Population & scope
- Almost every task restricts to a **production population** (production orders/accounts/
  shipments/tasks/cases) — find and apply the production flag from the dictionary; exclude
  test/non-production rows.
- Apply *all* stated scope filters: tier, segment, region(s), warehouse_id, campaign,
  import batch, priority, etc. The "eligible" count is the base for most rates — get it exact.
- Membership is often defined relative to the cutoff/window, not a static attribute
  (e.g. "has an effective scan in the named batch at or before the cutoff"). Encode it literally.

### Time, cutoff & windows
- Treat every timestamp as an **exact UTC boundary**. Respect stated inclusivity (usually
  inclusive on both ends: `start <= t <= end`).
- Evaluate state **as of the cutoff**, never "now". "Complete/delivered/open/resolved by the
  cutoff" means the state-driving event occurred at or before the cutoff timestamp.
- For unfinished items, "elapsed/active time" is measured **to the cutoff** (e.g. an
  unresponded case, an incomplete order). Read those edge clauses literally.

### Raw vs canonical/effective layer
- Atlas data carries a **raw/source** layer and a **canonical/effective** layer. Analytics
  use the **effective/canonical** values ("effectively DELIVERED", "effective settled refund",
  "effective final carrier status"). The dictionary says which column is which.
- Correction tasks turn on a **raw↔canonical contradiction**: fix only the canonical field;
  leave raw/source values and identity fields untouched.

### Counting grain
- Honor the exact grain each metric names: **distinct** orders vs. distinct *logical* refunds
  vs. linked reversals vs. shipments vs. tasks vs. cases. Dedupe on the correct key; one logical
  entity may span several rows, and reversals/links resolve to a parent entity.

### Rates & denominators
- Use the **denominator the request names** (usually the eligible population). Keep
  non-qualifying members *in* the denominator when told to (e.g. incomplete orders stay in).
- Compute rates on **unrounded** values.

### Money & FX (reconciliation tasks)
- Convert each row to the reporting currency using the **daily FX rate for that row's own
  service_date and currency**. Value cross-currency comparisons at the specific rate the
  request names.
- Net figures subtract the linked reversals/credits from the settled refunds. Apply display
  decimals only to the final reported amount.

### Ranking & tie-breaks
- Sort by the request's primary key (desc/asc as stated), then each secondary key, then the
  final id/label ascending. Compare on **unrounded** metric values.
- **Slice to the required size only after a full deterministic sort.** Return exactly the
  count the template requires (e.g. exactly 2 or exactly 3).

### Rounding
- Round **only the final reported rates/amounts** to the stated decimals (`multipleOf`,
  `decimal_places`, `precision`). Never round intermediate values used for comparison, sorting,
  or threshold checks.

### Classification (status / risk)
- Threshold rules are **cascading / first-match**: evaluate in listed order (e.g.
  HEALTHY→WATCH→CRITICAL, LOW→MODERATE→HIGH, CONTROLLED→ELEVATED→SEVERE, STABLE→PRESSURED→
  AT_RISK) and take the first whose condition holds; the last is the catch-all.
- Conditions are usually **compound (AND)** and use exact operators — honor `>=` vs `>`,
  `<` vs `<=`, and "strictly before". Compute the rates they reference on the named denominator.

### Medians
- Median across the exact stated population; for an **even count, average the two central
  values**. Sort the underlying (unrounded) values first.

### Correction tasks (audited single-row fix)
- Locate the one affected row via the raw↔canonical contradiction the request describes.
- Apply the **minimal canonical correction**: one field, one row, through
  `/api/sql/transaction`. Do **not** alter raw/source values, identity fields, or any unrelated
  row.
- Write the audit record using the **constants supplied in the request verbatim** (audit_id,
  correction_key, reason_code, actor, corrected_at); fill entity/source/field/old/new from the
  actual row. Report `old_value`/`new_value` as strings.
- Verify per the request's success rule (typically: exactly one business row + one audit row
  committed, and a post-change query confirms the new canonical value). Set the status to
  `APPLIED` **only** if that rule is fully satisfied; otherwise `NOT_APPLIED` with the results
  actually observed. Re-query after commit; never report success you didn't confirm.

### Output contract fidelity
- The template is authoritative. With `additionalProperties`/`additional_properties: false`,
  emit **exactly** the required keys — no extras, no nulls for absent-but-required, no comments.
- Match types precisely: `integer` vs `number`; enum members exactly; string `pattern`
  (e.g. `^ORD-[0-9]{6}$`, `^ACC-[0-9]{4}$`, `^CASE-[0-9]{6}$`); array `minItems`/`maxItems`,
  `uniqueItems`, and stated item ordering.
- `answer.json` contains **only** the JSON object. Validate it against the template before
  finishing.

See `reference/checklist.md` for a pre-submission checklist and `reference/patterns.md` for
worked SQL patterns.
