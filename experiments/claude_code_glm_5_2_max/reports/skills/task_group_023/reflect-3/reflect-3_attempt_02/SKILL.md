# Public Health Observatory Algorithmic Audit Skill

## Overview

This skill solves algorithmic audit tasks against the Public Health Observatory (PHO) data portal. Each task requires fetching health and socioeconomic data from the portal, resolving publication cohorts, running multiple statistical audit modules, applying controlled decision gates, and returning a single JSON object conforming to the task's answer template.

## Portal Access

- **Base URL**: Read from the task's `<TASK_ENV_BASE_URL>` placeholder (replace in prompt).
- **Authentication**: None required.
- **Endpoints** (all GET unless noted):
  - `/` — Portal home
  - `/catalog` — Dataset catalog with column schemas, measure dictionaries, and filter documentation
  - `/geographies/states` — 51-row state reference (FIPS, abbreviation, name, region, division, is_state)
  - `/geographies/counties` — ~1,224-row county reference (FIPS, state abbreviation, name, region, RUCC, metro class, population, lat/lon)
  - `/geographies/countries` — Up to 72-row country reference (ISO3, canonical name, portal label, alternate labels, region, income group)
  - `/data/state-health` — State health observations (observation_id, state FIPS/abbr, year, measure_id, value_type, source_type, release_status, revision, value, standard_error, sample_size, suppression_flag, quality_flag, released_at)
  - `/data/state-socioeconomic` — State socioeconomic records (record_id, state FIPS/abbr, year, release_status, revision, released_at, poverty, bachelors, median_income, unemployment, uninsured, food_insecurity, population, quality_flag)
  - `/data/county-health` — County health observations (observation_id, county_fips, state_abbr, region, year, measure_id, value_type, release_status, revision, released_at, value, low_ci, high_ci, population, suppression_flag, quality_flag)
  - `/data/county-socioeconomic` — County socioeconomic records (record_id, county_fips, state_abbr, region, year, release_status, revision, released_at, poverty, median_income, bachelors, unemployment, net_migration, uninsured, population, quality_flag)
  - `/data/country-indicators` — Country indicator observations (observation_id, country_label, iso3, year, indicator_id, release_status, revision, released_at, value, unit, quality_flag)
  - `/data/revisions` — Revision notices (revision_event_id, domain, entity_id, field_id, effective_year, old_value, new_value, status, issued_at, reason_code, note)
  - `/methodology` — Methodology page
  - `/download?dataset=<name>&format=csv` — Bulk CSV download for any dataset

## Data Resolution Protocol

### Registered Final Release Resolution
For each (geography, year, measure) tuple, select exactly one record:
1. Filter by the task's declared value_type, source_type, and release_status (typically `FINAL`).
2. Exclude records with quality_flag in `["INVALID_SCALE", "INVALID", "WITHDRAWN"]`.
3. Exclude suppressed records (`suppression_flag == 1`) and null/NaN values.
4. When multiple records remain for the same key, select the one with the **highest revision number**, then **latest released_at** timestamp.
5. Never zero-fill missing values; treat them as unavailable.

### County Health Resolution
- County health data has **no source_type column**; filter only on value_type and release_status.
- Revision selection: highest revision, then latest released_at (same as state health).
- County health records also include `low_ci` and `high_ci` fields.

### Socioeconomic Resolution
- Filter by release_status (typically `FINAL`).
- Same revision/released_at tiebreaking.
- Individual field nulls (e.g., `net_migration` missing) make that county-state-year incomplete for that field only.

### Country Label Reconciliation
- Match requested labels against `canonical_name`, `portal_label`, and pipe-delimited `alternate_labels` in the countries reference table.
- Each matched label resolves to a single ISO3 code.
- Count aliases: resolved labels that differ from the canonical name.

### Revision Notices
- Applied revisions (`status == "APPLIED"`) modify published values; these are already reflected in the resolved data.
- Non-applied revisions (PENDING, WITHDRAWN, etc.) are recorded but not applied.
- Scale-break anomalies flagged in quality may require exclusion from PCA matrices.

## Cohort Construction Rules

Tasks declare specific cohort definitions. Common patterns:

- **Primary cohort**: Reference-year complete cases — jurisdictions where all required health measures and socioeconomic fields are non-null, nonsuppressed, and non-missing.
- **Balanced panel cohort**: Intersection of jurisdictions complete in *every* requested analysis year.
- **Machine learning cohort**: Primary cohort members also complete for additional fields (e.g., unemployment, net_migration, uninsured in the reference year).
- **Strict dual-source cohort**: Jurisdictions complete for outcome, primary exposure, parallel exposure, AND all adjustment variables in *every* analysis year.
- **Broad reference cohort**: Reference-year complete cases for outcome and all requested feature variables (health + socioeconomic).

Always report: cohort sizes, excluded jurisdiction codes, and yearly complete-case counts.

## Audit Modules

### 1. Delete-Cluster Fixed Effects (Two-Way FE OLS with Jackknife)
- **Method**: Two-way (entity + time) fixed effects OLS via within-transformation (demeaning).
- **Cohort**: Core balanced panel.
- **Within-transformation**: For each variable, subtract entity mean and time mean, add grand mean: `y_it_demeaned = y_it - y_i. - y_.t + y_..`
- **Cluster-robust variance (CR1)**: Cluster by entity (state), computing meat as sum of `X_s' e_s e_s' X_s` over clusters.
- **Delete-one-entity jackknife**: Re-estimate model omitting each entity in turn; compute jackknife SE as `sqrt((g-1)/g * sum((theta_d - theta_mean)^2))`, bias-corrected coefficient as `g * theta_full - (g-1) * theta_mean`.
- Report: full coefficient, all delete-one coefficients, jackknife inference, bias correction, extreme deletions.

### 2. Nested Division/State Ridge CV
- **Method**: Nested leave-one-group-out ridge regression with inner cross-validation.
- **Cohort**: Broad reference cohort (single reference year).
- **Inner CV**: Within each outer training fold, leave one subgroup out to select the best lambda from the declared grid.
- **Standardization**: Compute mean and std on training data only; apply to test data.
- **Ridge**: Solve `(X'X + lambda*I) beta = X'y` where X and y are standardized/centered.
- Report: outer fold sizes, selected lambdas, inner RMSE grid, outer RMSE vector, pooled RMSE/MAE/Q-squared, worst group.

### 3. Wild Cluster Bootstrap
- **Method**: Restricted-null wild cluster bootstrap-t using the declared PRNG (PCG32 or XORSHIFT32) and weight distribution (typically Webb 6-point).
- **Restricted model**: Fit FE model *without* the target coefficient (under H0); obtain restricted residuals.
- **Bootstrap**: For each replicate, generate a weight index per cluster from the PRNG, multiply residuals by Webb weights, construct bootstrap y from restricted fit + weighted residuals, re-estimate unrestricted model, compute t-statistic.
- **p-value**: `(exceedance_count + 1) / (replicates + 1)` where exceedance = |bootstrap t| >= |observed t|.
- **PRNG state**: Track the seed, stream, and report checkpoint replicate PRNG states as requested.
- Report: observed statistic, all checkpoints, exceedance test, requested quantiles, terminal generator state.

### 4. Grouped Split Conformal Prediction
- **Method**: Leave-one-group-out conformal calibration with ridge fit.
- **Conformal threshold**: `quantile(|calibration_residuals|, ceil((1-alpha)*(n_cal+1))/n_cal)`.
- **Interval**: `[prediction - threshold, prediction + threshold]`.
- Report: all group assignments, calibration counts, thresholds, per-fold coverage/width/MAE, aggregate coverage and mean width.

### 5. Trajectory PCA Clustering
- **Method**: Covariance PCA on multi-year trajectory features, deterministic k-means, leave-year-out ARI stability.
- **PCA**: Compute covariance matrix on centered data, eigendecompose, retain declared number of components.
- **K-means**: Initialize with specific centroid points (e.g., first/middle/last states alphabetically, or declared initialization); iterate Lloyd's algorithm until convergence.
- **Stability**: For each omitted year, remove that year's features, re-run PCA+k-means on remaining features, compute Adjusted Rand Index against reference clustering.
- Report: spectrum, loadings, scores, initialization, centroids, sizes, labels, leave-year ARI arrays.

### 6. Source/Year Perturbation
- **Source perturbation (state)**: Re-estimate the model swapping each data source (e.g., AGE_ADJUSTED vs CRUDE, DIRECT_SURVEY vs COUNTY_ROLLUP) across all combinations; compute coefficient shifts and same-sign fractions.
- **Year perturbation (state)**: Re-estimate over all year subsets of declared sizes (e.g., C(5,3)=10 subsets of size 3); compute percent shifts relative to baseline.
- **Exhaustive source perturbation (county)**: Enumerate all 2^M scenarios for M dual-source jurisdictions; compute Shapley attribution for each jurisdiction's contribution to coefficient shift.
- Report: subset order, coefficients for each source/year combination, shift vectors, same-sign summaries, worst subsets.

### 7. Difference GMM Mediation
- **Method**: State-clustered difference GMM with cross-equation delta inference.
- **Three equations**: Total (outcome ~ exposure + controls), Path A (mediator ~ exposure + controls), Direct (outcome ~ exposure + mediator + controls).
- **Instruments**: Lagged levels instrumenting changes.
- **Indirect effect**: `a * b` with delta-method SE and cross-equation covariance correction.
- Report: four clustered coefficient summaries, two first-stage partial F statistics, stacked indirect effect, all state-deletion diagnostics.

### 8. Mediation Sensitivity Surface
- **Method**: Partial R-squared mediation sensitivity analysis.
- **Grid**: Cross R2_mediator_confounder × R2_outcome_confounder values.
- **Bias direction**: Compute adjusted indirect effect under each confounding scenario for both NEGATIVE and POSITIVE bias.
- Report: baseline quantities, equal-strength tipping R2, complete ordered sensitivity surface.

### 9. Nested Elastic Net
- **Method**: Division/state-grouped nested elastic net with training-only standardization.
- **Alpha**: Declared mixing parameter.
- **Lambda grid**: Declared grid; inner CV selects best lambda per outer fold.
- Report: every outer fold with complete inner grid, selected lambda, nonzero count, coordinate cycles, outer RMSE, and pooled metrics.

## Decision Gates and Classification

Each task declares specific gate thresholds and a classification precedence rule. Common patterns:

- **All gates pass** → strongest classification (per task's controlled vocabulary)
- **At least N gates pass** → intermediate classification (per task's declared precedence)
- **Otherwise** → weakest classification

Gate evaluation uses *exact* threshold comparisons as stated in the analysis request (e.g., `p <= 0.05`, `Q-squared >= 0.85`). Apply gates strictly; do not round before comparison.

## Output Rules

1. **One JSON object** — no narrative outside the JSON.
2. **Numeric precision**: Round to declared decimal places (typically 4 for computed statistics; 4 or 6 as specified).
3. **Identifiers**: Use uppercase two-letter state codes and portal division/region names exactly as provided.
4. **Ordering**: Preserve every declared array order; do not sort independently.
5. **Missing values**: Use `null` (JSON null) only when a requested statistic is mathematically unavailable; never use NaN or Infinity.
6. **Integer types**: Counts, ranks, fold numbers, seeds, PRNG states, and replicate numbers are JSON integers.
7. **Boolean types**: Gate pass/fail values are JSON booleans.
8. **Enum values**: Use exact controlled vocabulary from the answer template (e.g., "PASS"/"FAIL", classification strings).
9. Follow the answer template's `required_top_level_keys`, `required_keys` per section, and `array_lengths` exactly.

## Implementation Notes

- Use **within-transformation** (demeaning) for two-way FE models rather than dummy variables; dummy variable matrices become singular when deleting entities.
- Always **reset DataFrame indices** before extracting numpy arrays to avoid index misalignment bugs.
- For **PCG32 PRNG**: Initialize with `state = (seed + inc) & mask`, step once, add `inc`; each step: `state = (old * 6364136223846793005 + inc) & mask`, output: `rotate_right(((old >> 18) ^ old) >> 27, old >> 59)`.
- **Conformal threshold**: Use the exact quantile formula `ceil((1-alpha)*(n+1))/n`, not a simple `(1-alpha)` quantile.
- **sklearn.metrics.adjusted_rand_score** handles the ARI computation correctly for trajectory stability.
- For **weighted regression** (WLS + HC3): Compute diagonal weight matrix, solve weighted normal equations, then compute HC3 sandwich using leverage-adjusted residuals.
- When fetching data, use the `/download?dataset=...&format=csv` endpoint for bulk retrieval; use HTML endpoints only for interactive exploration.

## Common Pitfalls

1. **Revision resolution**: Multiple records for the same (entity, year, measure) are legitimate; always resolve by highest revision then latest released_at.
2. **Suppressed values**: `suppression_flag == 1` means the value is suppressed/unavailable; treat as missing, never zero-fill.
3. **Source type confusion**: State health has `DIRECT_SURVEY` and `COUNTY_ROLLUP` source types; county health has no source_type column.
4. **Cohort intersection**: Balanced cohorts require completeness in *every* year; use set intersection, not union.
5. **Within-transformation vs dummies**: For FE models with entity deletion (jackknife), use within-transformation to avoid singular matrices from empty dummy columns.
6. **JSON serialization**: Numpy int64/float64 types are not JSON-serializable; convert to native Python types before writing.
7. **Conformal coverage**: Low coverage often indicates incorrect threshold computation; verify the quantile formula.
