# Output contract & pre-submission checklist

The answer is **one JSON object** with no surrounding narrative. `answer_template.json` is the schema. Graders check leaf statistics and structural fields against a reference implementation, so contract violations fail whole sections.

## Precision & types

- Round every **non-integer reported statistic** to the declared decimal places (usually 4) and encode as a JSON **number** (e.g. `-12.3456`). Do not encode numbers as strings. Do not emit `NaN` or `Infinity` (invalid JSON) — use `null` only when a statistic is mathematically unavailable.
- **Integers** (counts, n, replicate counts, seeds, iterations, fold sizes, gate pass counts) keep natural JSON integer types.
- **Booleans** keep natural JSON boolean types (`true`/`false`), never 0/1 or strings.
- Some tasks distinguish **computed-stat precision** (round) from **literal grid/threshold precision** (keep the declared literal value, e.g. `lambda_grid` = `[0.01, 0.1, 1.0, 10.0, 100.0]`, `alpha` = `0.20`). Echo grids/thresholds at their declared precision; round only computed statistics.
- Round at the **end** (compute in full float, then round for output) to avoid accumulation error.

## Ordering

- Preserve **every declared order**: state/county order, feature order, division order, lambda/alpha/l1_ratio grid order, checkpoint-replicate order, source-group/year-subset order, equation/target order, quantile-probability order, gate order.
- Do **not** independently re-sort an array that is positionally aligned to another (e.g. `delete_obesity_coefficients` aligns to `state_order`; `pc1_scores`/`cluster_labels` align to `state_order`; bootstrap weight rows align columns to `state_order`). Keep them in the same order as their reference array.
- Where the template says "sorted ascending" (e.g. `resolved_iso3`, `applied_revision_event_ids`, `anomaly_observation_keys`, `high_burden_iso3`), sort ascending — usually lexicographic on the string form (`ISO3|YEAR|indicator_id`).
- Cross-section/module year orders follow the request's year list order (e.g. 2020→2024), not necessarily numeric when the request lists them otherwise.

## Identifiers

- State codes: uppercase two-letter (`AK`, `DC`). County FIPS: text with meaningful leading zeros; county id = 2-char state + 3-char county. ISO3: uppercase (`QAA`…). Use the portal's division/region names exactly (e.g. `East South Central`).
- Country label reconciliation: match requested labels against `canonical_name`, `portal_label`, and each `alternate_labels` entry; report unique resolved ISO3 sorted ascending; `alias_resolution_count` = resolved labels differing from the canonical name.

## Nullability

- `null` only when a requested statistic is **mathematically unavailable** (e.g. a degenerate fold, a non-positive-definite matrix, an undefined ratio). Never use `null` to mean "missing data" inside a cohort — exclude missing-data units from the cohort instead.

## Pre-submission checklist

Before emitting, verify against `answer_template.json`:
1. All `required_top_level_keys` present; no extra top-level keys unless the template allows.
2. Every section's `required_keys` present.
3. Every `array_lengths` matches (scalars and `[rows, cols]` shapes for 2-D arrays like `inner_rmse_grid`, `cluster_centroids`).
4. `cardinality_rules` satisfied (aligned arrays equal their reference length; cross-module matches like `wild_cluster_bootstrap.state_order == delete_cluster_fixed_effects.state_order`).
5. Enums within `allowed_values` (gate PASS/FAIL; classification enums; advisory enums; method-name enums).
6. Ordering preserved everywhere declared; aligned arrays not independently sorted.
7. Non-integers rounded to declared decimals as JSON numbers; integers/booleans natural; no NaN/Infinity; `null` only for mathematically-unavailable stats.
8. Identifiers uppercase / exact portal names.
9. Cohort counts internally consistent (`core_balanced_observation_n == core_balanced_state_n × n_years`; `yearly_core_complete_n` length == n_years; excluded codes == all jurisdictions − balanced).
10. Decision gate booleans/strings consistent with the statistics and the declared thresholds; classification consistent with the pass count and precedence.

## Common silent-failure conventions

- PCA on mixed-unit indicators without standardization → PC1 dominated by the largest-scale indicator (~99% variance) → wrong loadings/scores/clusters/panel coefficient. Standardize (correlation PCA) unless the spec says covariance (same-unit trajectories).
- `median_income` not scaled by 1e4 where declared → ridge/elastic-net/conformal/perturbation outputs that include income drift.
- CR1 p-value df = clusters−1 (not n−k); using the wrong df changes p-values and gate outcomes.
- Bootstrap: wrong RNG (PCG32 stream-encoding, xorshift32), wrong weight set, or drawing one weight per observation instead of per cluster → all checkpoint/exceedance/quantile/p-value fields wrong.
- Conformal threshold off-by-one (`⌈(n+1)(1−α)⌉` vs quantile indexing) → coverage/width fields wrong.
- PCA sign ambiguity → loading/score signs flip wholesale; pick the largest-|loading|-positive convention deterministically.
- Re-sorting an aligned array (e.g. sorting `delete_obesity_coefficients` independently of `state_order`) → positional mismatch across the whole array.
