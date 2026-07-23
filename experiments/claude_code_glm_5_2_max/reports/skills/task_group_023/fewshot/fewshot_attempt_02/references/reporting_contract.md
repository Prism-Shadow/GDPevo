# Reporting contract

## JSON shape

- Exactly one JSON object. No narrative, comments, or surrounding text.
- Top-level keys, per-section keys, array lengths, orderings, cardinality rules, enum values, and boolean/integer types are fixed by `answer_template.json`. Do not rename, add, omit, or reorder beyond the template.

## Precision

- Round every non-integer reported statistic to the decimal places declared in the request's `reporting` block (commonly 4; some protocols use 6 for computed reals and 4 for literal grid/threshold fields).
- Encode rounded values as JSON numbers; trailing zeros need not be preserved.
- Integer fields (counts, ranks, fold numbers, seeds, PRNG states, replicate numbers) and booleans retain natural JSON types.

## Missing / unavailable

- Use JSON `null` only when a requested statistic is mathematically unavailable (e.g. zero-variance group, singleton cluster, undefined ratio).
- Never emit `NaN`, `Infinity`, or `-Infinity`. Never zero-fill suppressed/invalid/blank/null evidence.

## Ordering (critical)

- Preserve every declared order: entity-code then time; feature/coefficient/instrument order; group/division/region order; lambda/alpha-l1 grid order; checkpoint/replicate order; source-group/subset order.
- Do not sort an aligned result array independently. Positional alignment (e.g. delete coefficients to state order, inner RMSE to grid, scores to entity order) must be maintained.
- Where the template requires sorted sets (e.g. "sorted ascending"), sort exactly as specified.

## Identifiers

- Uppercase two-letter state codes; portal division/region names exactly as returned; ISO3 uppercase. Use the declared label/enum vocabulary verbatim.

## Provenance

- Any `protocol_registry_record` / `portable_protocol_profile` is optional solved-answer provenance only. It is not solver-visible input, is not expanded or required by the answer template, and is ignored by the evaluator. Do not rely on it as input; do not emit it unless the template requires it.
