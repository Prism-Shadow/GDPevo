# Output Contract & Pre-Submission Self-Check

The `answer_template.json` is the binding contract. These rules hold across the whole PHO audit family; apply them in addition to anything the template states explicitly.

## Numeric discipline

- **Precision.** Round every reported non-integer to the decimal places the template declares. Two regimes recur: 4 decimals (most tasks) and 6 decimals for computed real values with 4 decimals for literal grid/threshold fields. Use the template's rule, not a default.
- **JSON numbers.** Encode rounded values as JSON numbers; trailing zeros need not be preserved.
- **Integers.** Counts, ranks, fold numbers, seeds, PRNG states, replicate numbers, and cluster counts are JSON integers — never floats, never strings.
- **Booleans.** Gate flags and `region_fixed_effects`-style fields are JSON booleans (`true`/`false`), never 0/1 or strings.
- **Missing.** Use JSON `null` ONLY when a requested statistic is mathematically unavailable (e.g., a degenerate fit). Never `NaN`, never `Infinity`, never zero-fill. Suppressed/invalid/blank source values are unavailable, not zero.

## Ordering

- **Formal orders are fixed.** Preserve every order the request declares: state, division, region, feature/term, coefficient, instrument, lambda/alpha/l1_ratio grid, checkpoint replicate, source-group, scenario stratum, leave-out year/state. Do not re-sort a positionally-aligned array.
- **Identifier sets are sorted only where declared.** Where the template says "sorted ascending" (e.g., excluded state codes, resolved ISO3, high-burden membership), sort; otherwise preserve the formal order.

## Identifiers

- Uppercase two-letter state codes (and DC). Portal division and region names exactly as the portal returns them. ISO3 uppercase. Set-like identifier lists unique and sorted ascending only where the template declares it.

## Positional & cross-module alignment

- Where an array is "aligned positionally" to another (e.g., delete-one coefficients to cluster order; PCA scores to state order; cluster labels to state order), the two arrays must have equal length and index-for-index correspondence.
- Where the template requires cross-module equality (e.g., a bootstrap `state_order` must exactly equal the delete-cluster `state_order`; trajectory assignments must align with the balanced cohort's state-code order), verify the identical ordering is reused — do not re-derive independently.

## Enumerations

- Use ONLY the controlled enum values the template lists (gate PASS/FAIL; classification strings; advisory strings; first-failed-module names; method identifiers where the template fixes a `required_value`). No synonyms, no casing changes, no extra values.

## Cardinality

- Every array length the template declares must match exactly. Every cardinality rule (e.g., "complete exclusion set: every universe state absent from the cohort, and no others"; "one assignment for each and only each balanced-cohort state") must be satisfied — neither under- nor over-filled.

## Pre-submission self-check checklist

Run this before emitting the JSON. Each item must pass.

1. **Top-level keys.** Exactly the template's `required_top_level_keys`, no more, no less.
2. **Sub-keys.** Every `required_keys` / `required_output` field present; no template-instruction or descriptor placeholders left.
3. **Array lengths.** Every declared length matches (e.g., 5 years, 9 divisions, 16 source subsets, 20 batch counts, grid lengths).
4. **Cardinality.** Each cardinality rule satisfied exactly — complete sets, one-per-item, no extras.
5. **Ordering.** Every formal order preserved; only declared "sorted ascending" lists sorted.
6. **Alignment.** All positionally-aligned arrays equal length and index-correspondent; all cross-module-equal arrays identical.
7. **Enums.** Every enum field uses an allowed value verbatim.
8. **Precision.** Non-integers rounded to the declared places; integers/booleans correct JSON types.
9. **Null discipline.** `null` used only for mathematically unavailable statistics; no `NaN`/`Infinity`; no zero-filling.
10. **Identifiers.** State codes uppercase; division/region names exact; ISO3 uppercase.
11. **Reproducibility.** Declared seed(s), PRNG family, checkpoint-replicate list, and final PRNG state all present and in declared order.
12. **Decision.** Gate booleans derived from declared thresholds; classification from declared precedence; controlled enum only.
13. **Format.** Exactly one JSON object; no narrative, no markdown fence, no trailing text.

If any item fails, fix and re-check before submitting. Submit only the JSON object.
