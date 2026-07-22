# Public Health Observatory Algorithmic Audit Skill

## When to use

Invoke this skill when the task involves:

- A Public Health Observatory (PHO) algorithmic audit, transportability assessment, or publication briefing
- An `analysis_request.json` paired with an `answer_template.json` defining a registered audit protocol
- State-level, county-level, or country-level health/socioeconomic data from the PHO read-only web portal
- Statistical modules including: fixed-effects OLS with jackknife, nested ridge/elastic-net cross-validation, wild cluster bootstrap, grouped split conformal calibration, trajectory PCA clustering, source perturbation analysis, GMM mediation, or sensitivity surfaces

## Core workflow

### Phase 1: Understand the contract

1. **Read `analysis_request.json` first.** It declares:
   - `request_id` / `briefing_id` — the audit identifier
   - Geography scope (`50_STATES_PLUS_DC`, specific `regions`, or `country_labels`)
   - Analysis years, reference year, and publication state
   - Outcome variable, exposure(s), mediator (if mediation design), and adjustments
   - Evidence specification — exact filters for health and socioeconomic records
   - Cohort definitions — which states/counties/countries belong in each cohort
   - Audit module specifications — method names, parameters, seeds, grid values, required evidence
   - Decision rules — gate conditions and classification precedence

2. **Read `answer_template.json` second.** It fixes:
   - Required top-level keys and their required sub-keys
   - Numeric precision (decimal places for computed vs literal values)
   - Array lengths and cardinality rules (e.g., `state_order` length must equal `state_n`)
   - Enum values for gate results and classification labels
   - Ordering rules — preserve declared orders, do not sort independently

3. **Never assume defaults.** Every parameter in the analysis request is binding. If a grid, seed, or cohort rule is declared, use it exactly as written.

### Phase 2: Fetch and resolve evidence

The portal serves HTML tables with CSV download support. Download full datasets via the `/download` endpoint:

| Dataset | Endpoint | Key fields |
|---------|----------|------------|
| State health | `/download?dataset=state_health&format=csv` | `state_abbr`, `year`, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `suppression_flag`, `quality_flag`, `sample_size`, `released_at` |
| State socioeconomic | `/download?dataset=state_socioeconomic&format=csv` | `state_abbr`, `year`, `release_status`, `revision`, `poverty`, `bachelors`, `median_income`, `unemployment`, `uninsured`, `food_insecurity` |
| County health | `/download?dataset=county_health&format=csv` | `county_fips`, `state_abbr`, `region`, `year`, `measure_id`, `value_type`, `value`, `population` |
| County socioeconomic | `/download?dataset=county_socioeconomic&format=csv` | `county_fips`, `state_abbr`, `region`, `year`, `poverty`, `median_income`, `bachelors`, `unemployment`, `net_migration`, `uninsured`, `population` |
| Country indicators | `/download?dataset=country_indicators&format=csv` | `country_label`, `iso3`, `year`, `indicator_id`, `value`, `unit`, `quality_flag` |
| Revisions | `/download?dataset=revisions&format=csv` | `revision_event_id`, `domain`, `entity_id`, `status`, `effective_year`, `old_value`, `new_value` |

Geography reference tables are available at `/geographies/states`, `/geographies/counties`, and `/geographies/countries`. **These are HTML tables that may be paginated.** Fetch all pages to collect every jurisdiction. State geography includes `state_fips`, `state_abbr`, `state_name`, `region`, `division`, and `is_state` (0 for DC).

#### Record resolution rules

For every dataset, apply these rules in order:

1. **Filter by release status.** Unless specified otherwise, use `FINAL` records only. Discard `PROVISIONAL` records.

2. **Filter by value type and source type.** Match the analysis request's `health_filter` (e.g., `AGE_ADJUSTED`, `DIRECT_SURVEY`, `FINAL`). The outcome variable may not declare a value type explicitly — infer it from the primary health filter.

3. **Apply quality exclusions.** Discard records whose `quality_flag` is `INVALID_SCALE`, `INVALID`, or `WITHDRAWN`. Retain `REVIEWED`, `REVISED`, `PARALLEL_ESTIMATE`, `SUPPRESSED`, and `PROVISIONAL` as flagged but do not use `SUPPRESSED` values (where `suppression_flag` is `1` or `value` is blank/em-dash).

4. **Pick the best revision per entity-year-measure.** After filtering, group by (`state_abbr`, `year`, `measure_id`) for health, or (`state_abbr`, `year`) for socioeconomic. Within each group, select the record with the **highest `revision` number**, breaking ties with the **latest `released_at`** timestamp.

5. **Never zero-fill missing values.** Suppressed, invalid, or blank values are genuinely unavailable. Mark them as missing for cohort determination.

#### Country label reconciliation

For country tasks, the analysis request provides `country_labels` as display names. The portal's `country_label` field may use multiple aliases for the same ISO3 code. To reconcile:

- Group all data rows by `country_label` and collect associated `iso3` values (ignoring empty-string ISO3s).
- Each unique label resolves to its most frequent non-empty ISO3.
- Count as "alias resolutions" any label whose text differs from the canonical country name associated with its ISO3.
- The resolved ISO3 list is the sorted set of all uniquely reconciled ISO3 codes.

### Phase 3: Build cohorts

Cohort definitions in the analysis request are precise. Common patterns:

- **Jurisdiction universe:** All 50 states plus DC for state tasks; all counties in declared regions for county tasks; all reconciled ISO3 codes for country tasks.

- **Core balanced cohort:** Jurisdictions that have non-missing, valid values for every declared core variable in **every** analysis year. The core variables are listed in `evidence_specification.core_panel_variables` or `publication_selection`.

- **Broad reference cohort:** Jurisdictions complete in the reference year for the outcome and all ordered features. Check both health and socioeconomic sources.

- **Strict dual-source cohort:** Jurisdictions complete for outcome, primary exposure, parallel exposure, and all adjustments in every analysis year.

- **Machine-learning cohort:** Primary-cohort members additionally complete for extra socioeconomic fields.

For every cohort, compute and report:
- The state/county/country count
- The observation count (states × years for balanced panels)
- The excluded jurisdiction codes (sorted ascending)
- Yearly complete-case counts

### Phase 4: Execute audit modules

Each module in `audit_modules` declares a `method`, `cohort`, and `required_evidence`. Implement the method exactly as named. Key methodological families:

#### Fixed-effects OLS with delete-one jackknife

- Build the design matrix: intercept + exposure + adjustments + (N-1) state dummies + (T-1) year dummies.
- Omit one state and one year as reference categories to avoid the dummy variable trap.
- For each state deletion: rebuild the design matrix with the reduced state set (new reference categories), re-estimate, and collect the exposure coefficient.
- Jackknife inference: pseudo-values = n × full_coef − (n−1) × delete_coef_i. Mean of pseudo-values is the jackknife estimate. SE = std(pseudo-values) / √n. t = estimate / SE. p-value from two-sided t-distribution with n−1 df (or normal approximation).
- Bias-corrected coefficient = n × full_coef − (n−1) × mean(delete_coefs).
- Report the state producing the minimum and maximum delete-one coefficient.

#### Nested ridge/elastic-net cross-validation

- **Standardize features using training-only means and standard deviations.** Never leak test data into standardization.
- **Outer loop:** Leave one group (division, state) out. Train on remaining groups.
- **Inner loop:** On the training set only, leave one inner group out for each lambda/alpha candidate. Select the hyperparameter minimizing mean inner RMSE.
- **Outer evaluation:** Fit with selected hyperparameters on all training data, predict the held-out group, compute RMSE.
- **Pooled metrics:** Compute RMSE, MAE, and Q² (1 − SS_res / SS_tot) across all outer-fold predictions concatenated.
- For elastic net: the alpha (overall penalty weight) and l1_ratio grids are searched jointly. Track nonzero coefficient counts and coordinate descent cycles.

#### Wild cluster bootstrap (restricted null)

- **PRNG matters.** The analysis request declares a specific generator (PCG32, Xorshift32) with seed, stream, and replicate count. Reproduce the declared sequence exactly — do not substitute Python's `random` module.
- **Restricted null:** Weights are Rademacher (+1/−1) applied at the cluster level — all observations in a cluster share the same weight.
- Compute the observed t-statistic using CR1 cluster-robust standard errors.
- For each replicate: generate weights, perturb residuals (y* = ŷ + w_g × resid), re-estimate the model, compute the bootstrap t-statistic using CR1 SE.
- **Bootstrap p-value:** (count of |t*| ≥ |t_obs| + 1) / (replicates + 1).
- Report checkpoint PRNG states and t-statistics at declared replicate milestones.
- Report batch exceedance counts and bootstrap-t quantiles.

#### Grouped split conformal calibration

- **Split within each group** into proper-training (≈50%), calibration (≈25%), and test (≈25%) sets.
- **Fit** the source model on proper-training data from all groups pooled.
- **Calibrate:** On the calibration fold only, compute nonconformity scores (absolute residuals). The threshold is the ⌈(1−α)(n_cal + 1)⌉-th smallest score.
- **Evaluate:** On the test fold, prediction intervals are ŷ ± threshold. Report coverage fraction, mean interval width, and MAE per group.
- **Aggregate:** Weight each group's metrics by its test-set size.

#### Trajectory PCA clustering

- Build the feature matrix: for each analysis year, include the trajectory variables in the declared order (e.g., `life_expectancy_2020`, ..., `adult_obesity_2024`).
- **Standardize** the full matrix before PCA.
- **PCA via covariance eigendecomposition.** Report eigenvalues, explained variance ratios, cumulative ratio, and signed loadings for the declared number of components.
- **K-means initialization is deterministic.** Use the first K states' PC scores as initial centroids (as ordered in the state list). Use a single initialization (`n_init=1`).
- **Cluster labels** must align positionally with the state order.
- **Leave-year-out stability:** For each omitted year, remove its columns from the feature matrix, re-run PCA and k-means (same deterministic init), compute Adjusted Rand Index against the full-data clustering, and report aligned agreement counts.

#### Source perturbation analysis

- **Exhaustive enumeration:** For the declared subset sizes (e.g., 3, 4, 5), generate all year combinations. Fit the FE model on each subset twice — once with the primary exposure series, once with the parallel/replacement series.
- Compute the absolute percent shift between primary and parallel coefficients for each subset.
- Report same-sign fraction, median and maximum shift, and the worst subset.
- For source-type perturbation (direct vs. rollup): enumerate all 2^M scenarios (where M is the number of states with both eligible records). Compute exact Shapley effects.

### Phase 5: Apply decision rules

The `decision_rule` section declares gate conditions and classification precedence. Each gate references one module's key statistic:

- Compare the computed statistic against the declared threshold using the declared inequality operator.
- Gate result is `"PASS"` or `"FAIL"` (exact strings from the template's `gate_values`).
- Count passed gates and apply the classification precedence: check the highest tier first, then fall through.
- `first_failed_module` is `"NONE"` if all pass, otherwise the first module (in declared precedence order) whose gate failed.

### Phase 6: Assemble and validate the answer

1. **Fill every required key.** The answer template's `required_top_level_keys` and each section's `required_keys` are mandatory. Missing a key is an automatic failure.

2. **Match types exactly.** Counts are integers. Computed statistics are JSON numbers at the declared decimal precision. Enum fields use the exact allowed string values. Booleans are JSON `true`/`false`, not strings.

3. **Preserve every declared order.** State orders, feature orders, division orders, checkpoint orders — do not independently sort aligned arrays.

4. **Round at the declared precision.** `numeric_decimal_places` or section-specific precision rules. Use standard rounding (round half up or round half to even — be consistent). Do not truncate.

5. **Validate cardinality.** Every array's length must match its declared companion (e.g., `state_order` length equals `state_n`; `delete_obesity_coefficients` length equals `state_order` length).

6. **Return a single JSON object** with no surrounding narrative, explanation, or commentary.

## Portal reference

### Geography

The 50 states plus DC are organized into 4 regions and 9 divisions:

| Division | States |
|----------|--------|
| New England | CT, ME, MA, NH, RI, VT |
| Middle Atlantic | NJ, NY, PA |
| East North Central | IL, IN, MI, OH, WI |
| West North Central | IA, KS, MN, MO, NE, ND, SD |
| South Atlantic | DE, DC, FL, GA, MD, NC, SC, VA, WV |
| East South Central | AL, KY, MS, TN |
| West South Central | AR, LA, OK, TX |
| Mountain | AZ, CO, ID, MT, NV, NM, UT, WY |
| Pacific | AK, CA, HI, OR, WA |

County data includes `region` (Midwest, Northeast, South, West) and RUCC (Rural-Urban Continuum Code, 1–9) from the socioeconomic dataset.

### Revisions

The revisions dataset tracks changes to published values:
- `status` values: `APPLIED` (incorporated into later final releases), `WITHDRAWN` (not applied), `PENDING` (under review).
- `domain` identifies whether the revision applies to `STATE`, `COUNTY`, or `COUNTRY` data.
- For country tasks: collect `APPLIED` and non-`APPLIED` revision event IDs separately for the quality audit.

### Quality flags

| Flag | Meaning | Action |
|------|---------|--------|
| `REVIEWED` | Standard final record | Use |
| `REVISED` | Updated in later revision | Use (highest revision wins) |
| `PARALLEL_ESTIMATE` | Alternative source/method | Use as directed |
| `PROVISIONAL` | Preliminary, not final | Discard for FINAL-only filters |
| `SUPPRESSED` | Small sample or unreliable | Discard (value is blank) |
| `INVALID_SCALE` | Scale discontinuity | Discard |
| `INVALID` | Failed validation | Discard |
| `WITHDRAWN` | Retracted | Discard |

### County RUCC (Rural-Urban Continuum Codes)

RUCC is an integer 1–9 in the county socioeconomic dataset. It is typically included as categorical indicators (RUCC2 through RUCC9, with RUCC1 as reference). The analysis request declares which RUCC codes are included.

## Common pitfalls

1. **Pagination on HTML endpoints.** `/geographies/states`, `/geographies/counties`, and other HTML endpoints may paginate results. Fetch all pages to collect complete reference data. Alternatively, derive the jurisdiction list from the downloaded CSV data, which is always complete.

2. **Revision selection is by revision number, not date.** When multiple FINAL records exist for the same entity-year-measure, pick the highest `revision` integer. The `released_at` timestamp only breaks ties.

3. **Outcome variable resolution.** The outcome (e.g., `life_expectancy`) may not declare `value_type` or `source_type` explicitly. Use the primary health filter from `evidence_specification`.

4. **Food insecurity appears twice.** In state analyses, `food_insecurity` exists as both a health measure (from state-health data) and a socioeconomic field. The ridge feature order may include a `socio_food_insecurity` entry — use the socioeconomic source for that position.

5. **CR1 cluster-robust standard errors.** The formula is CR1 (not CR0, CR2, or CR3): multiply the sandwich estimator by G/(G−1) × (n−1)/(n−k).

6. **The intercept column counts as a term.** In OLS, the total parameter count K includes the intercept, exposure(s), adjustments, state FEs (N−1), and year FEs (T−1). Degrees of freedom = n_obs − K.

7. **Ridge penalty is NOT applied to the intercept.** If standardizing features, center the outcome (subtract mean) but do not re-scale. The intercept is implicitly zero for standardized data.

8. **Deterministic k-means.** Set `n_init=1` and use the first K observations as initial centroids. Do not use random initialization.

9. **Percent shift with zero denominator.** When the primary coefficient is near zero, define the absolute percent shift as 0 (not undefined or infinite).

10. **Array ordering is part of the audit trail.** If the analysis request declares a `feature_order`, `state_order`, or `division_order`, preserve it in all output arrays. Do not sort alphabetically unless the template explicitly requires ascending sort.
