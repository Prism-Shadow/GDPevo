# Output Precision, Ordering & Conformance

The answer template is a JSON Schema. The final `answer.json` must pass it exactly. These rules generalize across every domain.

## Field names and shape
- Copy each required field name verbatim from the template. Mismatched names fail the contract.
- `additionalProperties: false` (or `additional_properties: false`) means emit **only** the listed fields. No extra keys, no metadata, no narrative.
- Nested objects listed in `required` must carry all their required sub-fields.
- The whole file is exactly one JSON object. No trailing prose, no comments, no markdown fences.

## Types
- `integer` → whole number, no decimals, no quotes.
- `number` → numeric; observe `multipleOf`, `minimum`/`maximum`.
- `string` enums → exactly one of the listed values.
- `string` patterns like `^ORD-[0-9]{6}$`, `^CASE-[0-9]{6}$`, `^ACC-[0-9]{4}$` → the IDs returned by SQL must already match; do not reformat them.

## Rounding (the most common defect)
- Discover precision from the template: `multipleOf` (e.g. `0.0001` = 4 decimals, `0.01` = 2 decimals) or `decimal_places`/`x-precision`.
- The request usually says "round only final reported rates to …". Compute at full precision, round **once**, at the end, only the value you report.
- Never round intermediate aggregates that feed another computation (e.g. regional rates that are later ranked must use unrounded values for ranking; round only the value put into the output).
- Standard round-half-up to the stated decimals, then emit exactly that many decimal places where the schema's `multipleOf` implies them.

## Ordering
- Array ordering comes from the template/request: e.g. "rate ascending, then region ascending", "units per hour descending, then employee_id ascending", "severe count desc, breach count desc, account_id asc". Reproduce it in SQL `ORDER BY` and validate the returned order.
- Lists of IDs that the request says are "sorted ascending" (e.g. severe ids, leakage ids, delayed task ids) must be emitted ascending; re-(re)quest them already sorted.
- Ties at a rank boundary follow the stated secondary key(s). If the request gives no further tie-break and a tie straddles the cutoff, do not invent one — surface ambiguity rather than guess.

## Sizes
- `minItems`/`maxItems` (or `min_items`/`max_items`) are hard limits. "Exactly two worst regions", "exactly three worst accounts", "top two reason codes", "top three employees" — these are enforced counts. If the population has fewer than the required items, the contract pre-supposes the data has enough; do not pad.
- `uniqueItems` → no duplicates in the array.

## Status / risk derivation
- Status fields are enums derived from thresholds in the **request** (not the template), evaluated against the **unrounded** computed rates.
- Rules are listed top-down with a catch-all last (HEALTHY→WATCH→CRITICAL; LOW→MODERATE→HIGH; CONTROLLED→ELEVATED→SEVERE; STABLE→PRESSURED→AT_RISK). Evaluate in that order; first match wins; the final rule catches everything else.
- A rate that lands exactly on a threshold boundary ("at least 0.88", "below 0.05") must be read as the inequality states (inclusive lower bound on the "at least"; exclusive "below").

## Self-checks before writing
- Denominator/numerator consistency: numerically, do counts add up (complete + incomplete = eligible; reopen ⊆ open-at-cutoff; pre + delta = post)?
- Pattern/enum sanity: every ID and every enum value matches the schema.
- Precision sanity: every number respects its `multipleOf`.
- Top-N sanity: the list length equals the required count and honors ordering + tie-breaks.
Only then write `answer.json`.
