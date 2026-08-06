# Public Health Observatory Audit Skill

## Overview

Solve algorithmic audit tasks against the Public Health Observatory data portal. Each task asks you to complete a registered multi-module evidence audit using only the read-only portal. You must return one JSON object conforming exactly to the supplied answer template.

## Portal Access

The portal is a read-only Web application. All evidence comes from browse pages or CSV exports. Never modify data — every filter, release-resolution step, and quality exclusion must be reproducible from the portal alone.

### Data Endpoints

| Endpoint | Returns |
|---|---|
| `GET /geographies/states` | State reference: FIPS, abbreviation, name, region, census division |
| `GET /geographies/counties` | County reference: FIPS, state, name, region, RUCC, metro class |
| `GET /geographies/countries` | Country reference: ISO3, name, region |
| `GET /data/state-health` | State health observations: measure, value type, source type, value, SE, sample size, quality flags |
| `GET /data/state-socioeconomic` | State socioeconomic: poverty, income, education, unemployment, uninsured, etc. |
| `GET /data/county-health` | County health observations: same schema as state health |
| `GET /data/county-socioeconomic` | County socioeconomic: same fields as state |
| `GET /data/country-indicators` | Country indicators: indicator id, value, quality flag |
| `GET /data/revisions` | Revision notices: domain, entity, field, old/new value, status |
| `GET /download?dataset=X&format=csv` | Full CSV export of any dataset |

## Data Pipeline

### Step 1 — Release Resolution

For every analysis, you must resolve which release to use. The standard method is **Registered Final Release Resolution**:

1. Restrict to rows where `release_status == "FINAL"`.
2. Group by the natural entity key — for state health this is `(state_abbr, year, measure_id, value_type, source_type)`; for socioeconomic it is `(state_abbr, year)`; for counties add `county_fips`.
3. Within each group, pick the row with the **highest revision number**.
4. Break ties by picking the **latest `released_at`** timestamp.

Never average across releases or value-types. Always pick exactly one row per group.

### Step 2 — Quality Exclusion

After resolution, exclude any row that meets **any** of these conditions:

- `quality_flag` is `INVALID_SCALE`, `INVALID`, or `WITHDRAWN`
- `suppression_flag` is `"1"` (suppressed)
- The `value` field is empty, whitespace-only, or the literal string `null`

Suppressed, invalid, and blank values are **unavailable** — never zero-fill, never impute unless the module explicitly requires imputation.

### Step 3 — Revision Application

The revisions table records post-publication corrections:

- `APPLIED` revisions are already reflected in higher revision numbers of the same observation and do **not** require separate application after Step 1.
- `PENDING` and `WITHDRAWN` revisions must **not** alter resolved values.
- For the country domain, revision events may document scale corrections (e.g., factor-of-10 errors). Use the `status` field to decide whether an event affects the usable value.

### Step 4 — Filter by Value Type and Source Type

Most protocols specify which combination to use. Common filters:

- `AGE_ADJUSTED_AND_DIRECT_SURVEY_AND_FINAL` — use only `value_type=AGE_ADJUSTED, source_type=DIRECT_SURVEY`
- `CRUDE_AND_DIRECT_SURVEY_AND_FINAL` — use only `value_type=CRUDE, source_type=DIRECT_SURVEY`
- `FINAL` alone (for socioeconomic) — use only `release_status=FINAL`

Apply the filter **after** release resolution. Each measure in the analysis should use exactly one resolved value per geography-year.

## Cohort Construction

Every module declares a cohort. Build them in order:

1. **Basic-complete** — The core variables are all non-null, non-suppressed, and valid for a given geography-year.
2. **Primary cohort** — Basic-complete in the reference year (e.g., 2023).
3. **Balanced panel cohort** — Basic-complete in **every** requested year.
4. **Machine-learning / broad cohort** — Primary-cohort members also complete for an extended set of features.
5. **Strict dual-source cohort** — Complete for outcome, both exposure variants, and adjustments in every year.

Preserve the **exact order** of state codes, county FIPS codes, or ISO3 codes as they appear in the geography reference. Sorted ascending is the default unless the answer template specifies a different order.

## Statistical Computation (Pure Python / JS)

When numpy/scipy are unavailable, implement the following from scratch:

### Fixed Effects (Within-Transformation)

For two-way (state + year) FE:
1. Compute state means, year means, and grand means for both outcome and each predictor.
2. Transform: `y_tilde = y - y_bar_state - y_bar_year + y_bar_grand`
3. Run OLS on transformed data **without intercept**.
4. Effective df = `n_obs - n_predictors - (n_states - 1) - (n_years - 1)`

### Ridge Regression

Closed form: `beta = (X'X + lambda*I)^(-1) X'y`. Standardize all features and the outcome before fitting. For nested CV, the outer loop leaves one group out; the inner loop does the same within the training set.

### PCA

Via power iteration on the covariance matrix with deflation. Standardize features first. Use PCA on the covariance matrix (not correlation) when the protocol specifies "registered covariance PCA."

### K-Means

Deterministic farthest-first initialization: start at the first data point, then pick each subsequent centroid as the point farthest from all existing centroids. Run Lloyd's algorithm to convergence.

### Bootstrap

Implement the specified PRNG exactly (PCG32 or XorShift32). For wild cluster bootstrap-t:
1. Fit the restricted-null model (coefficient of interest set to 0).
2. Generate cluster-level wild weights from the specified distribution (Webb 6-point, Rademacher, etc.).
3. Multiply restricted residuals by weights to generate bootstrap y*.
4. Refit the full model on each bootstrap sample.
5. Compute the t-statistic (coefficient / CR1 clustered SE) for each replicate.

### Adjusted Rand Index

For clustering stability: build contingency table, compute `(sum_comb - expected) / (max - expected)`.

## Output Formatting

- Round all non-integer statistics to the declared decimal places.
- Use JSON `null` only when a statistic is mathematically unavailable.
- Never output `NaN` or `Infinity`.
- Preserve every declared array order — do not re-sort independently.
- Use uppercase two-letter state codes.
- Use portal division/region names exactly as they appear.
- Boolean fields must be JSON booleans, not strings.

## Common Pitfalls

1. **Counting wrong observations**: When a protocol specifies `AGE_ADJUSTED_AND_DIRECT_SURVEY_AND_FINAL`, count only those rows — not CRUDE or COUNTY_ROLLUP rows.
2. **Release resolution order**: Always revision DESC, then released_at DESC. Reversing this changes which value is selected.
3. **Suppressed ≠ missing**: A suppressed value (suppression_flag=1) is intentionally unavailable. Do not use it.
4. **Cohort definitions**: The balanced panel requires completeness in ALL years, not just the reference year.
5. **Within-transformation vs LSDV**: Dummy-variable FE can produce numerical instability. Use within-transformation for cleaner results.
6. **Standardization scope**: For ridge and PCA, standardize using training-set statistics only, then apply to test data.

## Module Patterns

The five tasks share recurring analytical modules. Here is how to recognize and implement each:

### Clustered Fixed-Effects + Jackknife
- **Keywords**: `delete_cluster`, `jackknife`, `TWO_WAY_FIXED_EFFECTS`
- Fit the FE model on the full cohort, then delete one cluster at a time and refit.
- Report the full coefficient, all delete-one coefficients, jackknife SE (= sqrt((n-1)/n * sum of squared deviations)), bias-corrected coefficient (= 2*full - mean_delete), and min/max influence clusters.

### Nested Cross-Validated Ridge / Elastic Net
- **Keywords**: `nested`, `leave_one_out`, `ridge`, `elastic_net`
- Outer loop: leave one group (division, state) out.
- Inner loop: within training, leave one group out to select lambda/alpha/l1_ratio.
- Report outer fold sizes, selected hyperparameters per fold, inner grid RMSEs, outer RMSEs, and pooled metrics (RMSE, MAE, Q² or R²).

### Wild Cluster Bootstrap
- **Keywords**: `wild`, `bootstrap`, `PCG32`, `XORSHIFT32`, `WEBB`
- Implement the PRNG from its definition. PCI32 is a truncated 64-bit LCG; XorShift32 is a shift-register generator.
- For Webb 6-point: weights are ±√1.5 (prob 1/6 each), ±1 (prob 1/6 each), ±√0.5 (prob 1/6 each).
- Null restriction: set the target coefficient to zero, work with restricted residuals.
- Report observed statistic, quantiles, exceedance count, p-value (= (exceedance+1)/(replicates+1)), and batch exceedance counts.

### Split / Grouped Conformal Prediction
- **Keywords**: `conformal`, `calibration`, `alpha`, `nominal_coverage`
- Split data into proper training, calibration, and test sets.
- Fit on proper training, compute absolute residuals on calibration set.
- Threshold = ⌈(1-α)(n_cal+1)⌉-th smallest absolute calibration residual.
- Prediction interval = ŷ ± threshold. Coverage = fraction of test points within interval.
- Report per-fold and aggregate coverage and mean width.

### Trajectory PCA + Clustering
- **Keywords**: `trajectory`, `covariance_pca`, `kmeans`, `leave_year_out`
- Reshape panel data into wide format: one row per geography, columns = variables × years.
- Standardize, compute covariance matrix, extract top k eigenvectors via power iteration.
- Cluster on PC scores using farthest-first K-means.
- Leave-year-out stability: repeat PCA + clustering omitting each year, compute ARI against full clustering.

### Source / Year Perturbation
- **Keywords**: `source_year`, `perturbation`, `exhaustive`, `SHAPLEY`
- Fit baseline model, then iterate over subsets of years (or source variants).
- For each subset, refit and record coefficient, p-value, and percent shift vs baseline.
- Report same-sign fraction, median/max absolute percent shift, and worst-case subset.

### Sensitivity Surface
- **Keywords**: `partial_r2`, `sensitivity`, `confounding`
- Given baseline path coefficients and standard errors, compute how the indirect effect changes under hypothetical unobserved confounding.
- Grid over R² values for mediator-confounder and outcome-confounder relationships.
- Report baseline quantities, tipping point R² (equal-strength confounding that nullifies the effect), and full surface.

## Execution Workflow

1. **Read the three inputs**: `prompt.txt` (task description), `analysis_request.json` (detailed spec), `answer_template.json` (output contract).
2. **Download all data** from the portal using CSV exports — parse with a robust CSV reader.
3. **Resolve releases** using the declared release method (almost always FINAL with max revision).
4. **Build cohorts** in dependency order: basic-complete → primary → balanced → broad → strict.
5. **Implement modules** in the declared order. Each module's `required_evidence` field tells you exactly what to report.
6. **Compute decisions**: Apply each gate formula exactly as written. Report PASS/FAIL, passed count, and the controlled classification.
7. **Format output**: Match every required key, array length, cardinality rule, and precision specification from the answer template.

## Self-Check Before Submission

- [ ] Every array length matches the template's `array_lengths` specification
- [ ] State/county/country codes use the exact portal spelling and case
- [ ] Division and region names match the portal exactly
- [ ] All non-integer values are rounded to the declared decimal places
- [ ] No `NaN`, `Infinity`, or string-encoded numbers
- [ ] `null` only for mathematically unavailable statistics
- [ ] Decision enums use exactly the values listed in the template
- [ ] Array orderings match the declared order (feature order, state order, division order, year order)
- [ ] No fields from the template's `required_keys` are missing

## Data-Only Modules (Highest Leverage)

Some answer fields depend only on correct data extraction and counting — no statistical computation needed. These are the highest-value targets for correctness:

- **Publication/cohort audit sections**: counts of resolved observations, cohort sizes, excluded geographies, year-by-year completeness counts. Get these right by carefully applying the declared filters (value_type, source_type, release_status) and quality exclusions.
- **Reconciliation sections** (country tasks): label-to-ISO3 resolution and alias counting. Build lookup tables from the geography reference, matching on canonical name, portal label, and alternate labels (semicolon-delimited).
- **Revision audit sections**: applied vs non-applied revision event IDs. Filter the revisions table by domain and status.

These sections are deterministic given correct data parsing and often account for a substantial fraction of the scored fields.
