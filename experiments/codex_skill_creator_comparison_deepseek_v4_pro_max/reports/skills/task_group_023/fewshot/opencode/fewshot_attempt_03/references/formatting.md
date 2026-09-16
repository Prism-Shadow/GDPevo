# Answer Formatting Reference

Every PHO algorithmic audit answer must conform exactly to the supplied
`answer_template.json`. This reference captures the universal formatting
rules that apply regardless of which protocol is being used.

## Top-Level Structure

The answer is exactly one JSON object. No narrative text, no markdown fences,
no explanatory comments outside the JSON. The JSON must contain every
required top-level key declared by the template, in any order.

When the template specifies a `required_top_level_keys` array, every one
of those keys must appear in the answer. Additional keys not in the template
should not be included unless the template explicitly allows them.

## Numeric Precision

Report non-integer statistics to the decimal places declared by the request
(typically 4). Examples:
- `3.1416` not `3.14159`
- `-1.9157` not `-1.91566`
- `0.0` for a p-value that rounds to zero at the declared precision

JSON numbers need not preserve trailing zeros. `3.5` and `3.50` are both
valid representations of a value rounded to 4 decimal places.

Counts, indices, fold numbers, seeds, PRNG states, and replicate numbers
are integers — never encode them as floats like `27.0`.

Booleans are JSON `true` or `false`, never `"true"` or `1`/`0`.

## Null Handling

Use JSON `null` only when a requested statistic is mathematically unavailable.
Examples of valid null use:
- A t-statistic when the standard error is exactly zero
- A confidence interval bound when the relevant distribution quantile is undefined

Never use `null` for:
- Missing data (those records are excluded from cohorts, not filled)
- A value that could be computed but wasn't due to sample size
- Placeholder slots in arrays

Never use `NaN`, `Infinity`, or `-Infinity` — these are not valid JSON.

## Array Ordering

Every array must appear in the exact order declared by the request and template.
Common ordering rules:

- **Entity codes**: Ascending ASCII/lexicographic order unless the template
  specifies a different order (e.g., "state ascending").
- **Feature order**: The exact sequence from the request's `feature_order`,
  `ordered_predictors`, or similar array — do not alphabetize.
- **Time periods**: Ascending year order.
- **Cluster/group order**: The declared list order (e.g., census divisions in
  a specific geographic sequence).
- **Grid values**: The declared order (e.g., lambda grid, alpha grid).
- **Checkpoint replicates**: The declared ascending order.
- **Subsets**: Lexicographic tuple order for year subsets, ascending
  replacement_count for source perturbation strata.
- **Direction order**: As declared (e.g., NEGATIVE then POSITIVE for
  sensitivity surface).

**Critical**: When two arrays are positional partners (e.g., state_order and
delete_obesity_coefficients), they must be aligned — the i-th coefficient
corresponds to the i-th state code. Never sort a result array independently
of its companion identifier array.

## Enum Values

Use only the exact enum/controlled values declared in the template. Examples:
- Gate status: `"PASS"` or `"FAIL"` (exact case)
- Classification: the exact strings from the decision_rule
- Advisory: the exact strings from the advisory allowed_values
- Method names: the exact strings from the request specification
- Division names: exact strings from the portal geography data
- State codes: uppercase two-letter abbreviations, exactly as returned by the portal

Never invent similar values. `"ROBUST_ACROSS_REGISTERED_MODULES"` is not
interchangeable with `"ROBUST"` or `"ROBUST_ACROSS_MODULES"`.

## String Identifiers

- State codes: Uppercase two-letter abbreviations (e.g., `"AK"`, `"DC"`, `"WY"`).
- County codes: FIPS codes as strings.
- ISO3 codes: Uppercase three-letter codes (e.g., `"USA"`, `"GBR"`).
- Request IDs: Exact string from the request.
- Cluster/division names: Exact strings from portal geography endpoints.
- Feature/variable names: Exact strings from the request's declared order arrays.

## Set-Like Identifier Lists

When the template says identifiers should be "unique and sorted ascending",
output a JSON array of strings with no duplicates, sorted by standard
ASCII/lexicographic order.

## Cohort Reporting

- `target_jurisdictions`: The total number of entities in the declared
  universe (e.g., 51 for 50 states + DC).
- `resolved_health_observations`: Total selected health records across all
  years before completeness filtering.
- `resolved_socioeconomic_records`: Total selected socioeconomic records
  across all years.
- `yearly_core_complete_n`: Array of 5 integers, one per analysis year in
  ascending order.
- `core_balanced_state_n`: Number of entities complete in every analysis year.
- `core_balanced_observation_n`: core_balanced_state_n * number_of_years.
- Excluded state codes: Every entity in the universe NOT in the cohort,
  sorted ascending.

## Decision Gates

Report every gate in the module order declared by the request's decision_rule.
Each gate is `"PASS"` or `"FAIL"` based on unrounded computed values compared
against the declared thresholds. Do not skip any gate — even if a gate is
conceptually dependent on an earlier one, evaluate it independently.

The `passed_gate_count` is the integer count of gates that evaluate to `"PASS"`.

The `classification` is selected by applying the declared decision mapping
to the gate results, using the declared precedence order. The `first_failed_module`
reports the first gate (by precedence) that failed, or `"NONE"` if all passed.

## Common Pitfalls

1. **Rounding too early**: Round only when writing the final JSON. Compute
   all intermediate values at full precision to avoid accumulated rounding error.

2. **Sorting positional arrays**: When `pc1_scores` must align with `state_order`,
   do not sort scores independently — they match positionally.

3. **Using the wrong degrees of freedom**: Jackknife tests use G-1 df (number
   of clusters minus one). CR1 tests use G-1 df. HC3 tests use n-k df.

4. **Flipping PCA signs incorrectly**: Orient each eigenvector so the earliest
   entry with the maximum absolute value is positive. Apply that orientation
   consistently to both loadings and scores.

5. **Forgetting to canonicalize cluster labels**: After k-means converges,
   reassign cluster ids by sorting centroids on PC1, then PC2, then PC3...
   then by original working id. Apply the remapping to all assignments.

6. **Reporting individual NaN/Infinity**: Use null. But never let a degenerate
   computation silently produce NaN — if a division by zero occurs, understand
   why and determine if null is the correct response.

7. **Mismatched array lengths**: The template's `array_lengths` and
   `cardinality_rules` are hard constraints. Every array must have exactly the
   declared length.

8. **Wrong exclusion logic**: `primary_excluded_state_codes` lists universe
   members that are NOT in the primary cohort — not the cohort members themselves.

9. **Using library defaults**: Do not let numpy/scipy/sklearn choose
   hyperparameters or random seeds. Every value comes from the request.
   Standardization must use training-only moments; predict must use those
   same moments, not recompute on test data.

10. **Carrying over values from train answers**: The skill describes methods,
    not data. Every invocation recomputes from scratch against the portal
    and the effective request.
