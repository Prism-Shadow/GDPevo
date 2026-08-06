---
name: atlas-ops-reporting
description: >-
  Operating procedure for Atlas Commerce Operations reporting tasks — producing an
  exact answer.json for a request payload + JSON-Schema answer_template. Use whenever a
  task ships an input/payloads/ folder containing a *_request.json (business definitions,
  cohort, cutoffs, thresholds) plus an answer_template.json, and points at an authenticated
  Atlas workplace service (GET /api/schema, GET /api/data-dictionary, POST /api/sql, and
  optionally POST /api/sql/transaction, GET /api/correction-audit). Covers both read-only
  analytical scorecards and controlled single-field canonical corrections.
---

# Atlas Commerce Operations reporting

You are given a business reporting request against the **Atlas Commerce Operations**
database and must emit a single JSON document, `answer.json`, that conforms *exactly* to a
supplied JSON-Schema template. The request payload is the authoritative source of business
rules; the schema is the authoritative source of output shape. Your job is to translate the
business definitions into correct SQL against the live schema, compute deterministically, and
serialize the result with no commentary.

Every task in this family shares the same shape. Do not assume specific table or column names,
window dates, thresholds, or output keys — read them from the payloads each time.

## 1. Read the three inputs first

For the task at hand, before touching the network:

1. **`prompt.txt`** — names the request payload and the answer template, states whether the
   task is analytical-only or permits a correction, and fixes the output file (`answer.json`).
2. **`input/payloads/<name>_request.json`** — the authoritative business contract. Extract:
   cohort/scope (population, tier, segment, region, campaign attribution), the time window and
   its boundary inclusivity, the cutoff/`as_of` timestamp, every business definition
   (what "complete", "effective", "severe", "breach", "backlog", "leakage candidate" mean),
   rollup/grouping rules, ordering and tie-break rules, rounding rules, FX/money policy, and
   the status/risk classification tiers.
3. **`input/payloads/answer_template.json`** — a JSON Schema. Read out the exact required
   keys, types, `additionalProperties: false` (emit *only* declared keys), string `pattern`s
   (e.g. `^ORD-[0-9]{6}$`), array `minItems`/`maxItems`/`uniqueItems`, precision constraints
   (`multipleOf`, `decimal_places`, `x-precision`), and `enum` values.

The request restates the required output list, but the **template schema wins** on shape,
naming, types, and precision. Note that different templates use different keys for the same
concept (`additionalProperties` vs `additional_properties`, `multipleOf` vs `decimal_places`);
trust each template's own vocabulary.

## 2. Get access, then discover the real schema

Credentials and endpoints live in `environment_access.md` (base URL + `Authorization: Bearer`
token). Never hardcode a token or base URL from memory — read the file.

Discover before you query. Do **not** guess table/column names:

- `GET /api/schema` — table/column structure.
- `GET /api/data-dictionary` — the field context that maps business terms (e.g. "effective
  status", "productive minutes", "promised delivery") to concrete columns and code values.
- `GET /api/correction-audit` — existing audit rows (relevant to correction tasks).

Map every business term used in the request to a concrete column/value *via the dictionary*
before writing SQL. See `references/atlas-api.md` for endpoint and response details.

## 3. Query with POST /api/sql (read-only)

Submit `{"sql": "<one statement>"}`. The response is
`{"columns":[...],"rows":[[...]],"row_count":N,"truncated":bool}`.

Practical rules (observed):
- **One statement per call; no trailing `;`** (a trailing semicolon is rejected). CTEs
  (`WITH`), `WHERE`, `UNION`, aggregates and joins are fine.
- If `truncated` is `true`, the result set was capped — narrow with filters or aggregate in
  SQL rather than pulling raw rows and post-processing.
- It is read-only. For analytical tasks, never mutate data.
- `scripts/atlas_query.sh` is a thin wrapper that reads the base URL/token and JSON-escapes SQL.

Prefer pushing the whole computation into SQL (filters, joins, group-bys, medians, rankings)
so the arithmetic is deterministic and auditable, then pull small result sets.

## 4. Compute per the business contract — the cross-cutting discipline

These rules recur across every task and are where answers go wrong. Full detail in
`references/reporting-discipline.md`; the essentials:

- **Boundaries are exact UTC.** Honor the stated inclusivity of window start/end and use the
  cutoff/`as_of` timestamp for every "as of" state (open/active, delivered, resolved, backlog).
- **Cohort filters are hard gates.** Apply production-only, tier, segment, region, campaign
  attribution, and "created during the active window" exactly as written before any metric.
- **Prefer effective/canonical over raw.** When both a raw and a canonical/effective value
  exist, business metrics use the effective/canonical one.
- **Keep the full denominator.** Rates divide by the whole eligible population unless told
  otherwise (e.g. incomplete orders stay in the denominator; unresponded/active cases count
  their elapsed-at-cutoff time toward breaches).
- **Round only final reported values**, to the stated decimals. Use **unrounded** values for
  ordering, tie-breaks, and every threshold comparison.
- **Ordering and tie-breaks are literal.** Implement each sort key in order (e.g. rate
  ascending, then id ascending) and cut to the exact `maxItems`.
- **Classification is first-match, in tier order.** Evaluate status/risk tiers top-down
  (e.g. HEALTHY → WATCH → CRITICAL); the first tier whose full condition holds wins. Compute
  each rate against the denominator the policy names.
- **Medians:** for an even count, average the two central values.
- **Money/FX:** convert each row with the daily rate for that row's service_date and currency,
  aggregate in the reporting currency, and round the net only at the end.

Sanity-check internal consistency before writing (e.g. complete + incomplete = eligible;
subset counts ≤ their parent counts).

## 5. Correction tasks (only when the prompt authorizes a mutation)

Some tasks (a single raw/canonical contradiction to reconcile) authorize *one minimal
canonical correction*. If and only if the prompt permits it:

- Identify the single affected row/field from the shared records. Correct **only** the
  approved canonical field — never raw source values, source-identity fields, or unrelated rows.
- Apply the change and its audit record atomically via `POST /api/sql/transaction`, using the
  request's supplied `reason_code`, `actor`, `audit_id`, `correction_key`, `corrected_at`.
- **Verify after commit:** re-query the canonical value and check `GET /api/correction-audit`.
- Report `APPLIED` only if the success rule holds exactly (typically: exactly one business row
  and one audit row committed, and the post-change read confirms the new canonical value).
  Otherwise report `NOT_APPLIED` with the values actually observed.
- Report backlog/metrics both pre- and post-correction as the template requires.

## 6. Emit answer.json and validate

Write the result to `answer.json` — a single JSON object, no prose, no markdown, no keys
beyond those the schema declares. Then validate:

- Run `scripts/validate_answer.py answer.json input/payloads/answer_template.json` to check the
  document against the template (required keys, `additionalProperties`, patterns, enums,
  item counts, `multipleOf`/precision).
- Manually confirm array lengths, string patterns, sort order, dedup, and decimal precision
  match the schema, and that numeric precision is exact (e.g. a rate that is `multipleOf 0.0001`
  is serialized with the intended rounding, not a floating-point tail).

Only the final `answer.json` is the deliverable.
