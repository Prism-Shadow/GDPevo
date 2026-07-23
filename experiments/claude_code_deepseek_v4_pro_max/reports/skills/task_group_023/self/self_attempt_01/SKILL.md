# Public Health Observatory Algorithmic Audit Skill

## Purpose

Execute a registered multi-module algorithmic audit using the Public Health Observatory (PHO) read-only web portal. Produce a single JSON response conforming exactly to a provided answer template — no narrative outside the JSON.

## When to Use

Invoke this skill when the task involves:
- A PHO analysis request (`analysis_request.json`) with declared audit modules
- A companion answer template (`answer_template.json`) specifying the output contract
- A read-only web portal exposing health, socioeconomic, and geographic data

## Prerequisites

The task environment must provide (or reference) these three artifacts:

| Artifact | Purpose |
|---|---|
| `environment_access.md` | Base URL of the portal and its allowed endpoints |
| `analysis_request.json` | Full specification: geography, years, measures, cohort rules, module parameters, decision rules |
| `answer_template.json` | Exact output contract: required keys, array lengths, cardinality rules, numeric precision, enum values |

## Workflow

### Phase 1 — Resolve the Portal

1. Read `environment_access.md` to obtain the portal `base_url` and enumerated `allowed_endpoints`.
2. The portal root (`GET /`) typically provides an index of available resources.
3. Use `GET /catalog` to discover available datasets, measures, value types, source types, and release metadata.
4. Use `GET /geographies/*` endpoints to enumerate valid geography codes (states, counties, countries) and their groupings (census divisions, regions).

### Phase 2 — Parse the Analysis Request

Read `analysis_request.json` fully. Extract and confirm these required sections:

- **Scope**: geography, analysis years, reference year, outcome variable, exposures/mediators
- **Publication/cohort rules**: release status filters, value-type/source-type filters, revision priority, complete-case criteria, balanced-panel criteria, exclusion rules
- **Audit modules**: each module declares its method, target cohort, parameters (seed, grid, replicates, alpha, lambda, etc.), and required evidence
- **Reporting rules**: numeric decimal places, ordering requirements, identifier conventions
- **Decision/robustness gates**: per-module pass/fail thresholds and the precedence rule that maps gate results to a controlled conclusion

### Phase 3 — Fetch and Filter Evidence

For each dataset endpoint referenced by the analysis request, fetch the data and apply the declared filters **in order**:

1. **Release filter**: keep only rows with the declared `release_status` (typically `FINAL`).
2. **Revision selection**: for multiple releases of the same geography×year×measure, apply the declared revision priority (e.g., `revision` then `released_at` then `observation_id`).
3. **Value-type / source-type filter**: keep only rows matching the declared `value_type` (e.g., `AGE_ADJUSTED`, `CRUDE`) and `source_type` (e.g., `DIRECT_SURVEY`, `COUNTY_ROLLUP`).
4. **Validity filter**: exclude rows flagged `INVALID_SCALE`, `INVALID`, or `WITHDRAWN`. Never zero-fill suppressed or missing values.
5. **Complete-case filter**: keep only geography units (states, counties, countries) that are non-null for every required variable in the relevant year(s).

### Phase 4 — Execute Audit Modules

Execute every module declared in `analysis_request.json` in the specified order. Each module must produce every piece of required evidence listed under `required_evidence`.

#### Common Module Types and Their Execution Patterns

**Cohort Audit Module** — Resolve publication records and report cohort dimensions:
- Count resolved records per year for each dataset (health, socioeconomic)
- Count complete-case units per year
- Identify excluded unit codes
- Report primary-cohort count, balanced-cohort count, and any strict-cohort counts

**Delete-Cluster Inference Module** — Fit a full model, then delete one cluster at a time:
- Fit the declared model (OLS, GMM, weighted regression) on the full cohort
- For each cluster (state, census division), refit without that cluster and record the target coefficient
- Compute jackknife bias correction, standard error, t-statistic, p-value
- Identify minimum-delete and maximum-delete coefficient/states
- Preserve the cluster order declared in the analysis request

**Nested Ridge/Elastic Net CV Module** — Outer/inner cross-validation:
- For each outer fold (grouped by state, census division, or random partition):
  - Within the outer training set, run inner CV over the declared `lambda_grid` (and `l1_ratio` grid for elastic net)
  - Select the best hyperparameter by inner RMSE
  - Evaluate on the held-out outer fold
- Apply training-only standardization: compute mean/sd on training data only, then transform train and test
- Report every outer fold's selected hyperparameters, inner RMSE grid, outer RMSE
- Report pooled metrics (RMSE, MAE, Q²/R²)

**Wild Cluster Bootstrap Module** — PRNG-based restricted-null resampling:
- Fit the source model on the observed data and record the target coefficient, cluster-robust standard error, and t-statistic
- Seed the declared PRNG (XORSHIFT32, PCG32) with the declared seed
- For each replicate, generate wild weights, refit under the restricted null, and record the bootstrap t-statistic
- At each checkpoint replicate, record the PRNG state and the current bootstrap t-statistics
- Compute the exceedance count, plus-one p-value, and requested quantiles

**Grouped/Conformal Calibration Module** — Out-of-fold coverage assessment:
- Use OOF predictions from the nested CV module (or refit with fixed hyperparameters)
- For each group (census division, state), compute calibration nonconformity scores
- Apply the split-conformal algorithm: sort calibration scores, pick the threshold at the declared rank
- Report per-group coverage, mean interval width, MAE, and aggregate summaries
- Identify the worst-coverage group

**Trajectory PCA Clustering Module** — Dimensionality reduction + stability:
- Construct a trajectory feature matrix: each unit is a geography, each feature is a variable×year concatenation
- Run PCA on the feature matrix (covariance or correlation as declared)
- Run deterministic k-means on the retained principal components with the declared cluster count and initial centroids
- Report the leading spectrum, loadings, scores, centroids, cluster sizes, and labels
- For leave-year-out stability: omit each year, recompute the trajectory features, rerun PCA+k-means, compute adjusted Rand index against the full-data clustering
- Report all leave-year-out ARIs and the minimum

**Source Perturbation Module** — Stability under alternative data sources or subsetting:
- For source-year perturbation: enumerate all subsets of `n` years, refit the model on each subset, record coefficients and p-values; compute same-sign fraction and median absolute percent shift
- For source-rollup perturbation: enumerate all scenarios where a subset of states use an alternative data source; compute exact Shapley effects
- For source-group deletion: remove each declared group of terms from the model, refit, report RMSE deterioration, worse-fold count, and rank

### Phase 5 — Apply Decision Rules

For each module's required evidence, evaluate the declared gate condition:

- Gates are specified as threshold comparisons on specific statistics (coefficient sign, p-value, RMSE, R², coverage, ARI, etc.)
- Each gate evaluates to `PASS` or `FAIL`
- Count passing gates
- Apply the decision precedence rule: map the gate-passing pattern to the controlled conclusion vocabulary

### Phase 6 — Format and Return

1. Build the output object strictly according to `answer_template.json`.
2. Every required key must be present; no extra keys.
3. All arrays must be the declared length and in the declared order.
4. All cardinality rules must be satisfied (e.g., `state_order` length matches `state_n`; `delete_obesity_coefficients` aligns positionally with `state_order`).
5. Numeric values: round non-integer statistics to the declared decimal places; integers and booleans use natural JSON types.
6. Use `null` (never `NaN` or `Infinity`) when a statistic is mathematically unavailable.
7. Return the single JSON object with no surrounding narrative, markdown fences, or explanatory text.

## Cross-Cutting Operating Rules

These rules apply across all modules and are derived from patterns observed in every registered PHO audit protocol:

### Data Handling
- **Never zero-fill**: suppressed, invalid, blank, or missing values are unavailable — represent them as `null` in output when a statistic cannot be computed.
- **Revision priority is fixed**: when multiple releases exist for a geography×year×measure, sort by descending `revision`, then descending `released_at`, then descending `observation_id` (or `record_id`), and take the first.
- **Cohort definitions stack**: the `balanced_panel_cohort` is the intersection of complete-case units across all analysis years; the `primary_cohort` is complete-case in the reference year only; `machine_learning_cohort` extends the primary cohort with additional complete-case requirements.
- **Filter chaining**: apply release-status → value-type → source-type → validity → completeness in that order.

### Statistical Conventions
- **Cluster-robust inference**: state- or division-clustered standard errors (CR1/CR1-S) unless otherwise specified.
- **Training-only standardization**: compute mean and standard deviation on the training partition only; apply the same transform to test data.
- **PRNG determinism**: seeds are part of the registered protocol; PRNG type (XORSHIFT32, PCG32) and stream are declared and must be respected for reproducibility.
- **Checkpointing**: bootstrap modules declare specific replicate numbers at which PRNG state and t-statistics must be recorded.
- **Restricted null**: bootstrap resampling is performed under the null hypothesis (coefficient constrained to zero), not under the observed model.
- **Delete-one diagnostics**: delete-one-cluster (state/division) jackknife uses the same model specification as the full fit; bias correction follows the standard jackknife formula.

### Ordering and Identifiers
- **State codes**: uppercase two-letter USPS abbreviations (e.g., `AL`, `CA`, `NY`). When a `state_order` is declared, all per-state arrays must align positionally with it.
- **Census divisions**: use the portal's division names exactly as returned by the API.
- **ISO3 codes**: uppercase three-letter country codes, sorted ascending when in a set-like list.
- **Feature/grid order**: every declared feature order, lambda grid, alpha grid, l1_ratio grid, and year order must be preserved in output arrays.
- **Aligned position**: when the template declares a cardinality rule linking two arrays (e.g., `pc1_scores` aligns with `state_order`), the correspondence is positional, not keyed.

### Output Discipline
- **No narrative**: the answer is exactly one JSON object. No markdown, no preamble, no commentary.
- **Controlled vocabulary**: conclusions and gate values use only the enum values declared in the answer template.
- **Precision**: floating-point values are rounded to the declared number of decimal places and encoded as JSON numbers (trailing zeros need not be preserved, but the value must be accurate to the declared precision).

## Portal Endpoint Reference

The PHO portal exposes these standard read-only endpoints (verify against `environment_access.md`):

| Endpoint | Returns |
|---|---|
| `GET /` | Portal index and resource listing |
| `GET /catalog` | Available datasets, measures, metadata |
| `GET /geographies/states` | State codes, names, census divisions, regions |
| `GET /geographies/counties` | County FIPS, names, states, RUCC codes |
| `GET /geographies/countries` | Country names, ISO3 codes, regions |
| `GET /data/state-health` | State-level health measures |
| `GET /data/state-socioeconomic` | State-level socioeconomic variables |
| `GET /data/county-health` | County-level health measures |
| `GET /data/county-socioeconomic` | County-level socioeconomic variables |
| `GET /data/country-indicators` | Country-level burden and health indicators |
| `GET /data/revisions` | Revision history and event tracking |
| `GET /methodology` | Measure definitions, scales, value-type documentation |
| `GET /download` | Bulk data export |

### Data Record Conventions
- Health records carry: `observation_id`, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `released_at`, `quality_flag`, `value`, `sample_size`, and geography identifiers.
- Socioeconomic records carry: `record_id`, `field_name`, `release_status`, `revision`, `released_at`, and `value`.
- Revision records carry: `revision_event_id`, `event_type` (`APPLIED`/`NONAPPLIED`), affected observations, and timestamps.
- Country indicators carry: ISO3, year, `indicator_id`, `value`, and scale-break/quality flags.

## Task Execution Checklist

Before returning the answer, verify:

- [ ] Portal base URL resolved from `environment_access.md`
- [ ] All requested endpoints fetched; no fabricated data
- [ ] Release, revision, value-type, source-type, and validity filters applied in order
- [ ] Cohort definitions computed correctly (complete-case per year → balanced intersection → strict dual-source)
- [ ] Every audit module executed with declared parameters
- [ ] All required evidence arrays present and at declared lengths
- [ ] All positional alignments preserved (state_order, feature_order, division_order, year_order)
- [ ] Numeric values rounded to declared decimal places
- [ ] Integer metadata and booleans use natural JSON types (not floats)
- [ ] Missing statistics represented as `null`, never `NaN` or `Infinity`
- [ ] Controlled vocabulary used for gates (`PASS`/`FAIL`) and conclusions
- [ ] Single JSON object returned with no narrative outside it
