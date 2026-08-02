# Output contract and pre-submission self-check

The `answer_template.json` is a hard contract, not a suggestion. Graders check keys,
shapes, orders, precision, identifiers, and enum membership. Build the response object
to it field-by-field and validate before emitting.

## Global rules (consistent across variants)

- **One JSON object, nothing else.** No prose, no markdown fences, no trailing
  commentary. If the template lists `required_top_level_keys`, emit exactly those
  keys — no extras, none missing. Some templates carry an `xxx_instructions` field
  that says to *omit* it; omit it.
- **Precision.** Round every reported non-integer statistic to the declared decimal
  places and encode it as a JSON number. Most variants use **4**. Note the exception
  (train_005-style): computed real values to **6** decimals but literal grid/threshold
  fields (alpha, l1_ratio, nominal_coverage, lambda grid) to **4**. Trailing zeros
  need not be preserved. Round only at this reporting boundary — compute unrounded.
- **Types.** Counts, ranks, fold numbers, seeds, PRNG states, and replicate numbers
  are JSON integers; gate results and boolean flags are JSON booleans; do not encode
  numbers as strings.
- **Missing.** Use JSON `null` **only** where a requested statistic is genuinely
  mathematically unavailable. Never `NaN`, never `Infinity`, never a zero stand-in.
- **Identifiers.** Uppercase two-letter state codes; uppercase ISO3; portal division
  and region names spelled exactly as the portal gives them. County FIPS as text with
  leading zeros. Set-like id lists are unique and sorted ascending unless a specific
  order is declared.
- **Ordering.** Preserve every declared order (feature order, coefficient order,
  division order, state order, subset order, checkpoint order, year ascending, etc.).
  **Never independently sort an aligned result array** — arrays that "align
  positionally" to another array must share its length and order exactly.

## Cardinality / shape checks

Templates state array lengths and cross-array cardinality rules explicitly. Verify
each before submitting, e.g.:
- Fixed lengths: `analysis_years` = 5, `division_order` = 9, `lambda_grid` = |grid|,
  `first_three_weight_index_rows` = 3, checkpoint arrays = |checkpoint list|, matrix
  shapes like `inner_rmse_grid = [9, 5]` or `cluster_centroids = [3, 2]`.
- Alignment: `delete_obesity_coefficients` length = `state_n` and aligns to
  `state_order`; a module's `state_order` "must exactly match" another module's
  `state_order`; per-entity score/label arrays align to the entity order.
- Complete sets: an "excluded_state_codes" list must be *every* universe code absent
  from the cohort and no others; "one stratum for every replacement_count 0..M";
  "one effect for each and only each" ordered entity.

## Pre-submission self-check

1. Top-level keys == the template's required set (exact, no extras).
2. Every nested object has its `required_keys`; every enum value is in
   `allowed_values`; any `required_value` fields match.
3. Every array length and matrix shape matches the template; aligned arrays share
   order and length; sorted lists are actually sorted; declared orders preserved.
4. Numeric precision correct per field class (computed vs literal); integers are
   integers; booleans are booleans; no strings-as-numbers.
5. No `NaN`/`Infinity`; `null` only for genuinely-undefined statistics.
6. Gate booleans, pass count, and classification are internally consistent with the
   declared decision rule and precedence.
7. The whole response parses as a single JSON object and contains no text outside it.
