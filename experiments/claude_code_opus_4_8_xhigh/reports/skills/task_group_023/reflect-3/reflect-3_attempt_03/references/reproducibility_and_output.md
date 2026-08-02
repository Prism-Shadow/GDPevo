# Reproducibility, decision rule, and output contract

## Ordering (the most common cause of lost credit)

- Every list follows the **exact order declared** in `analysis_request.json`
  (feature_order, coefficient_order, division_order, instrument_order,
  checkpoint_replicates, source-group order, quantile_probabilities, lambda/alpha/
  l1 grids). Do **not** re-sort an aligned result array — its position encodes which
  entity/feature it belongs to.
- Some arrays are cross-referenced: a `state_order` shared by several modules must be
  identical everywhere; per-entity assignment arrays must align to the cohort's code
  order. Where the template says "must exactly match X", copy X.
- Where a list is explicitly "set-like … sorted ascending" (ISO3 lists, excluded-code
  lists), sort ascending ASCII and de-duplicate.

## Reference categories and transforms

- **Region dummies**: reference category is whatever the request names (often
  Northeast); include only the non-reference dummies, in declared order.
- **RUCC dummies**: RUCC1 is the reference; dummies RUCC2…RUCC9.
- **Panel end-year / period dummies**: the declared reference year (e.g. 2022) is the
  base; include the later-year indicators.
- **Income**: "per 10000" ⇒ divide by 10000; "log income" ⇒ natural log of *unscaled*
  income. Apply exactly once, in the declared feature slot.

## Precision and null policy

- Compute **unrounded**; round only when serialising.
- Round reported **non-integers** to the declared decimals (commonly 4; some requests use
  6 for computed reals and 4 for literal grid/threshold fields — honour both).
- Keep integers, counts, ranks, fold numbers, seeds, PRNG states, replicate numbers, and
  booleans as **natural JSON types** (no decimals, no quotes).
- Use JSON `null` only when a statistic is **mathematically unavailable**; never emit
  `NaN`, `Infinity`, or a zero placeholder for a missing value.
- Identifiers: uppercase state/ISO3 codes; portal division/region names spelled exactly
  as the portal spells them.

## Decision rule

1. For each gate/flag, evaluate the declared boolean from your computed statistic using
   the **exact threshold and comparator** (e.g. "bias-corrected coefficient > 0 AND
   jackknife p ≤ 0.05 AND max delete-cluster % change ≤ 25").
2. Count passing gates.
3. Map to the classification enum by the declared **precedence** (e.g. all pass ⇒
   PRIMARY/DEPLOY/CONSISTENT; ≥4 ⇒ ASSOCIATED/REVIEW/PARTIAL; else the base case). When a
   "first failed module" is required, report the earliest failing module in the declared
   precedence order (or NONE).
4. Echo the gate booleans, the pass count, and the classification exactly as separate
   fields when the template asks for them.

## Output discipline

- Emit **exactly one JSON object** with **exactly** the required top-level keys — no
  extras, no `template_instructions`, no commentary.
- Reproduce required literal values verbatim (`request_id`, method enums,
  `cluster_definition`, `nominal_coverage`, grid values).
- Respect declared array lengths and cardinality rules (e.g. "length must equal
  state_n"; "one item per balanced state code, same order").
- No prose before/after the JSON.

## Pre-submit self-check

- [ ] Every required top-level key present; no extra keys.
- [ ] Cohort counts consistent with the region/geography scope and with each other
      (universe − cohort = excluded).
- [ ] All declared orders preserved; aligned arrays not independently sorted;
      cross-referenced orders identical.
- [ ] Seeds, streams, grids, and checkpoint lists copied from the request; PRNG uses the
      named generator.
- [ ] Reference categories and transforms applied exactly once, in the right slots.
- [ ] Non-integers rounded to declared precision; integers/booleans natural; no
      NaN/Infinity; `null` only where truly undefined.
- [ ] Gate booleans and classification recomputed from the actual statistics via the
      declared thresholds/precedence.
- [ ] Output is one JSON object, no narrative.
