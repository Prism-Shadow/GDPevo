---
name: atlas-ops-analytical-scorecard
description: >-
  Use when a task delivers a business "scorecard", "reconciliation", "review",
  "backlog", or "correction" as three files — a prompt, a request-policy JSON
  (scope, business definitions, rollups, tie-breaks, rounding, status rules),
  and an answer_template.json — to be computed against an authenticated,
  read-only SQL workplace/operations database and written as one JSON object to
  answer.json. Covers eligibility cohorts, "effective/canonical" entity
  reduction, exact UTC windows, rate/rounding rules, worst/top-N ordering with
  tie-breaks, ordered status-rule cascades, and single-row canonical
  corrections with an audit record.
---

# Operations analytical scorecard & correction tasks

These tasks share one shape: a natural-language prompt points at a **request
payload JSON** (the authoritative policy) and an **answer_template.json** (the
exact output contract), and asks you to compute production results from an
authenticated operations database and write one JSON object to `answer.json`.
They are read-only **analytical** tasks unless the request explicitly asks you
to *apply a correction*. Your answer is graded on exact values and exact
conformance, so precision on definitions, boundaries, rounding, and ordering is
everything.

The environment (base URL, auth, and the available endpoints — schema,
data-dictionary, read-only SQL, and, for correction tasks, a transactional SQL
and correction-audit view) is described in the run's own access file. Read that
file each time rather than assuming; do not hardcode hosts or credentials.

## Work in this order

### 1. Read all three inputs before touching the database
- **prompt.txt** — the framing, the output filename (`answer.json`), and the
  "conform exactly, no commentary/extra fields" requirement.
- **request payload JSON** — the source of truth. Extract, verbatim, every:
  scope/cohort filter, `business_definitions`, money/FX policy, time windows
  and their `inclusive/exclusive` boundary flag and cutoff, `rollups`,
  ranking/`tie_break`/`limit` rules, `rounding` rule, and the ordered
  status/risk rule list. Re-read each definition literally — small clauses
  ("incomplete orders remain in the denominator", "no shipment promise does not
  satisfy the first condition", "at least two … with the same normalized reason
  code") change the answer.
- **answer_template.json** — the JSON Schema you must satisfy: required keys,
  scalar types (integers stay integers), ID `pattern`s, array `minItems`/
  `maxItems` and stated ordering, numeric precision (`multipleOf` /
  `decimal_places` / `x-precision`), and `additionalProperties:false`.

### 2. Discover the real data model — never guess names
The request describes fields in **business/logical** terms (e.g. a rate on a
warehouse's region, or `fx_rates.usd_per_unit`); physical table and column
names can differ. Use the environment's schema and data-dictionary endpoints to
learn the actual tables, columns, and units, and to map each logical concept to
storage. Do not rely on database catalog introspection from inside SQL — the
query layer only serves the documented business tables. If a discovery endpoint
is unavailable, map names from whatever context the environment does expose
before writing queries, and state any assumption you were forced to make.

### 3. Compute with read-only SQL, holding full precision
The query service is SQLite-dialect SQL over the operations tables. Build up
each required output with explicit queries and verify intermediate counts.
- **Boundaries are exact UTC.** Apply window start/end with the exact
  `inclusive`/`exclusive` semantics stated; compare against the stated cutoff,
  not "now".
- **Reduce to effective/canonical entities first.** When raw vs. canonical
  values, versions, or multiple rows per business entity exist, collapse to the
  one *effective* record (e.g. latest-wins / final status / supersession)
  before you count or aggregate. "Logical" refunds/shipments/cases may span
  several rows; a "complete" order may require *every* associated shipment to
  satisfy a condition. Net figures apply reversals/offsets before comparison.
- **Apply eligibility exactly.** Production-only populations, segment/region/
  tier/warehouse filters, campaign attribution within an active window, and
  membership predicates all narrow the cohort — and the cohort is usually the
  denominator.
- **Money/time conversions** use the policy's basis (e.g. the daily FX rate for
  each row's service date and currency; active-clock vs. wall-clock elapsed
  time). Value comparisons (refund vs. order gross) at the rate/date the policy
  names.
- **Round only at the end.** Carry unrounded values through all logic and
  comparisons; round only the *final reported* rates/amounts to the template's
  stated decimals.

### 4. Ordering, selection, and ID lists
- **Worst/top-N:** sort by the **unrounded** metric in the stated direction,
  then by each stated tie-break key in order (typically the id ascending), then
  take exactly N. Report each metric rounded per the template, but rank on the
  unrounded value.
- **ID/list outputs:** dedupe, keep only members that truly satisfy the
  definition, ensure each matches the template's `pattern` exactly, and sort as
  specified (usually id ascending).

### 5. Status / risk classification
Evaluate the status rule list **in order** and assign the **first** tier whose
full condition holds; if none, the explicit fallback tier. Build each condition
from the *unrounded* rates and the exact comparators (`>=`, `<`, thresholds,
and USD/count sub-conditions) as written. A tier usually requires *all* of its
clauses.

### 6. Correction / mutation tasks (only when explicitly requested)
When the request asks you to apply a correction:
- Find the single raw↔canonical contradiction it describes. Change **only** the
  one approved minimal canonical field on **exactly one** business row. Leave
  raw/source values, source identity fields, and unrelated rows untouched.
- Use the environment's controlled transactional endpoint to commit, in one
  transaction, the business-row update **and** its audit record. Populate the
  audit record from the request's approved-correction block (audit id,
  correction key, entity type/id, source row id, field name, old/new value,
  reason code, corrected timestamp, actor).
- **Verify** with a follow-up read that the canonical value changed. Report the
  success status per the request's rule: e.g. `APPLIED` only when exactly one
  business row and one audit row committed and the post-change query confirms
  the new value; otherwise `NOT_APPLIED` with the results actually observed.
- Report backlog/impact counts both pre- and post-correction as the template
  requires, and compute any delta as (post − pre).

### 7. Emit exactly one conforming JSON object
Write `answer.json` as a single JSON object with only the required keys, in the
right types, at the right precision, with arrays of the right length and order,
and IDs matching their patterns. No prose, no extra keys.

## Pre-submission self-check
- [ ] Every `required` key present; no extra keys (`additionalProperties:false`).
- [ ] Integers are integers; each rate/amount rounded to the template's decimals
      (`multipleOf`/`decimal_places`/`x-precision`) — and only rounded at the end.
- [ ] Rankings computed on **unrounded** values; every tie-break applied in
      order; arrays hold exactly the stated count and ordering.
- [ ] All ID strings match their regex `pattern`; lists deduped and sorted.
- [ ] Cohort/eligibility, window boundaries (inclusive/exclusive), and cutoff
      applied exactly; denominators match the request's wording.
- [ ] "Effective/canonical/logical" reduction applied before counting.
- [ ] Status/risk chosen by first-matching tier in the listed order.
- [ ] (Correction tasks) exactly one business row + one audit row changed, raw
      values preserved, post-change verified, status reported per the rule.
- [ ] Output is valid JSON with no commentary.

## Recurring traps
- Reading rates off rounded intermediate values, or rounding before comparing
  to a status threshold.
- Dropping incomplete/ineligible items that the definition keeps in the
  denominator.
- Treating a business/logical field name as a physical column without checking
  the data dictionary.
- Ranking on the rounded metric, or forgetting the id-ascending tie-break.
- Off-by-one on inclusive vs. exclusive window edges, or using current time
  instead of the stated cutoff.
- On corrections: editing raw/source fields, touching more than one row, or
  reporting `APPLIED` without a confirming post-change read.
