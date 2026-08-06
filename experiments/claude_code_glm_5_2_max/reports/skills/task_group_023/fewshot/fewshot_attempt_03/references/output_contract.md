# Output Contract

`answer_template.json` is the binding response contract. The final answer is **exactly one
JSON object** with no surrounding narrative, no code fences, no trailing commentary. These
rules translate the template's `numeric_rule`, `ordering_rule`, `identifier_rule`,
cardinality, and enum constraints into practice.

## Structure

- Emit every required top-level key, in the order the template lists them.
- Emit every required field. Omit any `template_instructions` / `description` / metadata key
  that the template says to omit.
- Do not add keys the template does not require. Do not substitute maps or sets where the
  template specifies a list with a declared order.
- A `protocol_registry_record` block is **not** solver-visible input, is not required or
  expanded by the template, and is ignored by the evaluator — do not emit one unless the
  effective template requires it.

## Numeric precision

- **Round every non-integer reported statistic** to the decimal places the effective request
  declares (commonly 4; some protocols declare 6 for computed reals and 4 for literal
  grid/threshold fields). Encode rounded values as JSON **numbers** (JSON numbers need not
  preserve trailing zeros).
- **Integers stay integers** (counts, ranks, fold numbers, seeds, PRNG states, replicate
  numbers, observation counts, cluster counts). **Booleans stay booleans.**
- Literal grid and threshold values that the request declares (lambda, alpha, l1_ratio,
  nominal_coverage, quantile probabilities, gate cutoffs) are reported at their declared
  precision, not recomputed.
- **Decide on unrounded values; round only for reporting.** Every gate/predicate, tie-break,
  argmax/argmin, and selection uses full-precision values. Rounding happens only when writing
  a field into the JSON.
- Use JSON `null` **only** when a requested statistic is mathematically unavailable (e.g. a
  degenerate fit, an empty cluster, a singular step). Never use `NaN` or `Infinity`. Never
  zero-fill a missing/suppressed value.

## Ordering

- **Every list retains the exact order specified by `analysis_request.json`.** Do not sort an
  aligned result array independently of its declared companion array.
- Aligned arrays (e.g. `state_order` ↔ `delete_obesity_coefficients` ↔ `pc1_scores` ↔
  `cluster_labels`; `lambda_grid` ↔ each inner-RMSE row; `ordered_rollup_state_codes` ↔
  `ordered_shapley_effects`; `subset_order` ↔ coefficient/p-value/shift vectors) must align
  positionally. If a template gives a `cardinality` rule like "one assignment for each and
  only each state code in …", honor both the membership and the order.
- Where the template gives an explicit `ordering` string (e.g. "year ascending", "state
  ascending", "registered division order", "replicates 1,2,4,…", "r2_mediator ascending,
  r2_outcome ascending, NEGATIVE then POSITIVE", "descending absolute loading; indicator_id
  ascending breaks an exact tie"), follow it verbatim.
- Set-like identifier lists that the template says to "sort ascending" are unique and sorted
  ascending (e.g. resolved ISO3, applied revision event ids, anomaly keys, excluded state
  codes).
- Tie-breaks (smallest RMSE → smaller penalty/alpha/l1_ratio; greatest shift → smaller mask;
  farthest-first → entity code; max-agreement alignment → lexicographically smallest
  permutation) are part of the ordering contract — apply them exactly.

## Identifiers

- **State codes:** uppercase two-letter (`CA`, `NY`, `DC`). Use the portal's `states`
  reference as the universe (50 states + DC where the request says so).
- **Division / region names:** spelled exactly as the portal geography reference returns them
  (e.g. `East North Central`, `Middle Atlantic`, `New England`). When a module says
  "registered division order," use the order the request declares or the portal's catalog
  order.
- **ISO3:** uppercase (e.g. `QAA`). Reconcile portal labels to ISO3 via the `countries`
  reference.
- **FIPS:** text with meaningful leading zeros (state FIPS 2-char, county FIPS = 2-char state
  + 3-char county).
- **Revision event ids / observation ids / record ids:** verbatim strings from the portal.

## Cardinality and length

- Where the template gives an `array_lengths` / `length` / `cardinality`, the array must have
  exactly that many elements (e.g. `feature_order` length 13, `division_order` length 9,
  `lambda_grid` length 5, `subset_order` length 16, `batch_exceedance_counts` length 20,
  `by_replacement_count` one stratum per `replacement_count 0..M`).
- "Complete exclusion set" / "complete strict balanced cohort" cardinalities mean: **every**
  qualifying entity and **no others**. Do not sample or truncate. If coverage is bounded (e.g.
  a top-N), the request will say so; otherwise enumerate exhaustively.

## Controlled decision / enums

- Gate fields take only the controlled values the template allows (e.g. `PASS`/`FAIL`, or
  booleans `true`/`false`).
- Classification / conclusion fields take only the enum values the template lists (e.g.
  `PRIMARY_TRANSPORTABLE_LONGEVITY_SIGNAL`,
  `ASSOCIATED_LONGEVITY_SIGNAL_WITH_LIMITED_TRANSPORTABILITY`,
  `NO_TRANSPORTABLE_LONGEVITY_SIGNAL`; or
  `ROBUST_ACROSS_REGISTERED_MODULES` / `NOT_ROBUST_AT_<MODULE>`; or
  `DEPLOY_…` / `REVIEW_…` / `RETAIN_…`).
- `first_failed_module` enums include `NONE` when all gates pass.
- Count fields (`passed_gate_count`, `supported_module_count`) are integers consistent with
  the gate values.
- Evaluate gates on unrounded values; the count and classification follow from those raw
  evaluations, not from rounded reported numbers.

## Final check before submitting

1. Exactly one JSON object; no narrative, no fences.
2. Every required top-level key present, in template order; no extra metadata keys.
3. Every array at its declared length and order; aligned arrays positionally consistent.
4. Identifiers exact (case, spelling, leading zeros).
5. Non-integers rounded to the declared precision; integers/booleans natural types; `null`
   only for mathematically unavailable; never `NaN`/`Infinity`.
6. Gates and classification use only controlled enum values; counts consistent.
7. Re-derive every value from the portal evidence and the effective request — nothing carried
   from any other task.
