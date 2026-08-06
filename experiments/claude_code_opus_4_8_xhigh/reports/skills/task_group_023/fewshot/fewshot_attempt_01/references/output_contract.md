# Output contract — conforming to answer_template.json

`answer_template.json` is authoritative for the *shape* of the answer. Read it fully and
treat every stated rule as a hard constraint. Emit **one JSON object and nothing else** — no
narrative, no code fence, no trailing text.

## How to read the template

- **Required top-level keys.** Output exactly these keys (the audit shape: a cohort/release
  block + six module blocks + a decision block; the briefing shape: reconciliation,
  quality_audit, pca, clusters, panel_model, advisory). Do not add or omit required keys.
- **`required_keys` per object.** Provide every listed field of each nested object.
- **`array_lengths` / `length` / `cardinality`.** Enforce exact lengths (e.g.
  `division_order: 9`, `inner_rmse_grid: [9, 5]`, checkpoint counts) and cardinality rules
  ("one item per state code in balanced_state_codes, and no others"). Nested matrices must
  have the stated shape.
- **`ordering`.** Follow it literally: "state ascending", "registered division order",
  "replicates 1,2,4,…", "r2_mediator ascending, r2_outcome ascending, NEGATIVE then
  POSITIVE", "lambda grid order". Aligned arrays (e.g. `delete_obesity_coefficients` vs
  `state_order`, `pc1_scores` vs `state_order`) must align **positionally**; never sort one
  side independently.
- **Cross-references.** When the template says an array "must exactly match" another
  (e.g. a module's `state_order` == the fixed-effects `state_order`), reuse the same order.
- **`required_value` / enum `allowed_values`.** Echo required literals (e.g. `request_id`)
  exactly, and pick decision/advisory/`conclusion` values only from the allowed set.

## Numeric precision

- Apply the template's decimal rule per field. Common cases: round every non-integer
  reported statistic to **4** decimals; some templates use **6** decimals for computed reals
  while keeping literal grids/thresholds at 4. Counts, ranks, fold numbers, seeds, PRNG
  states, and replicate numbers are **integers**.
- Round **only at output**. All predicates, tie-breaks, selections, and quantiles use
  full-precision values.
- Encode numbers as JSON numbers (not strings). Trailing zeros need not be preserved.

## Identifiers

- Uppercase two-letter state codes; uppercase ISO3; portal division/region names spelled
  exactly as in the geography reference. FIPS/ISO3 are text with meaningful leading zeros.
- "Set-like" identifier lists are unique and sorted ascending unless an aligned/registered
  order is specified.

## Null / missing policy

- Use JSON `null` **only** when a requested statistic is genuinely mathematically
  unavailable. Never emit `NaN` or `Infinity`. Never zero-fill a missing data cell to force a
  value.

## Provenance block

Standard answers may carry a top-level `protocol_registry_record` (method-only provenance).
It is **not** required by the template and is **ignored by the evaluator** — do not rely on
it and do not let it replace a computed field. Prefer to emit only the template's required
keys; if you include provenance, keep it method-only (no task answer values leaked from
elsewhere).

## Pre-submission checklist

1. All required top-level keys present, none extra where the template forbids extras.
2. Every nested object has its `required_keys`.
3. Every array length / matrix shape / cardinality matches.
4. Every ordering rule satisfied; aligned arrays line up positionally.
5. Cross-referenced orders are identical where required.
6. Enums/`required_value`s are exact strings from the allowed set.
7. Precision applied per field; integers are integers; no NaN/Infinity; nulls only where
   mathematically unavailable.
8. The decision block is consistent with the per-gate results computed on unrounded values.
9. Output parses as a single JSON object with no surrounding text. Re-run the solver and
   diff to confirm determinism.
