# Public Health Observatory Algorithmic Audit Skill

## Trigger

Use this skill when the task involves completing a registered algorithmic audit for the Public Health Observatory (PHO) — a structured, multi-module reproducibility and transportability assessment of a public-health association — using the PHO read-only web portal as the sole evidence source.

**Detect via:** presence of `analysis_request.json` and `answer_template.json` payloads, references to a `<TASK_ENV_BASE_URL>` portal, or terms like "registered audit," "algorithmic audit," "transportability audit," "publication gates," or "robustness decision."

## Portal

| Setting | Value |
|---------|-------|
| Base URL | `http://task-env:9023/` |
| Auth | None required |
| Protocol | HTTP GET only |

### Available Endpoints

| Endpoint | Returns |
|----------|---------|
| `GET /` | Portal root / health check |
| `GET /catalog` | Full data catalog with measure metadata |
| `GET /geographies/states` | State codes and attributes |
| `GET /geographies/counties` | County codes, state mappings, and RUCC classifications |
| `GET /geographies/countries` | Country codes, labels, aliases, and regions |
| `GET /data/state-health` | State-level health measures (value_type, source_type, release_status, sample_size) |
| `GET /data/state-socioeconomic` | State-level socioeconomic indicators |
| `GET /data/county-health` | County-level health measures |
| `GET /data/county-socioeconomic` | County-level socioeconomic indicators |
| `GET /data/country-indicators` | Country-level burden and outcome indicators |
| `GET /data/revisions` | Revision event history with event IDs and statuses |
| `GET /methodology` | Methodological notes and variable definitions |
| `GET /download` | Bulk data export |

## Workflow

### Step 1 — Read the inputs

Read all three files in the task input directory:

1. **`prompt.txt`** — natural-language task description; identifies the research question and any special constraints.
2. **`analysis_request.json`** — the registered protocol: scope, cohorts, data filters, audit module specifications, reproducibility checkpoints, robustness gates, and decision rules.
3. **`answer_template.json`** — the exact response contract: required top-level keys, field types, array cardinalities, ordering rules, precision requirements, and allowed enum values.

### Step 2 — Fetch evidence from the portal

Use only the portal endpoints. Fetch data in this order:

1. **`GET /catalog`** — confirm which measures are available and verify measure_id values match the request.
2. **Geography endpoint** — fetch the relevant geography listing (states, counties, or countries) to resolve identifiers, aliases, and group memberships (census divisions, regions, RUCC bands).
3. **Data endpoints** — fetch health and socioeconomic/country-indicator data for the requested years, applying the declared filters (value_type, source_type, release_status).
4. **`GET /data/revisions`** — resolve revision histories and identify applied vs. non-applied revision events when the protocol requires revision tracking.
5. **`GET /methodology`** — resolve any methodological details (variable definitions, quality flags, scale-break annotations).

### Step 3 — Apply cohort rules

Every request defines one or more cohorts. Construct them in this precedence:

- **Complete-case rule:** a row is complete when all requested values are present, nonsuppressed, and non-null. Never zero-fill suppressed, invalid, or missing values — treat them as unavailable.
- **Primary/reference-year cohort:** complete cases in the reference year from the declared geography universe.
- **Balanced-panel cohort:** complete cases in every requested study year (intersection across years).
- **Strict dual-source cohort:** complete for outcome, primary exposure, parallel exposure, and adjustments in every study year.
- **Machine-learning cohort:** primary-cohort members also complete for an extended set of socioeconomic fields.

Excluded jurisdictions must be reported explicitly (by code, sorted ascending).

### Step 4 — Execute each audit module in registered order

Each module in `analysis_request.json` specifies:

- **`method`** — the exact statistical procedure.
- **`cohort`** — which cohort definition to use.
- **`required_evidence`** — the outputs that must appear in the answer.

Key: preserve every declared order — feature order, state order, division order, lambda grid order, checkpoint order, leave-year-out order, subset order, source-group order. These orders are part of the registered protocol and must not be independently sorted unless the template explicitly says to.

### Step 5 — Apply robustness gates

Each gate is a Boolean condition defined in the request. Evaluate every gate against the computed evidence and report `PASS` or `FAIL` for each. Apply the decision rule's precedence ordering to produce the final classification.

### Step 6 — Fill the answer template

Produce exactly one JSON object. Follow these rules:

#### Universal rules

| Rule | Detail |
|------|--------|
| **Precision** | Round every non-integer reported statistic to the declared number of decimal places (typically 4; some protocols use 6 for computed values and 4 for grids/thresholds). Encode as a JSON number. Counts, ranks, fold numbers, seeds, PRNG states, and replicate numbers are integers. |
| **Missing** | Use JSON `null` only when a statistic is mathematically unavailable. Never emit `NaN`, `Infinity`, or `-Infinity`. |
| **Identifiers** | Use uppercase two-letter state codes, uppercase ISO3 country codes, and canonical portal names for divisions/regions exactly as returned by the geography endpoints. |
| **Ordering** | Preserve every formal order declared in the request. Do not sort an aligned result array independently. Positional alignment between arrays (e.g., state_order and coefficient vectors) is a reproducibility requirement. |
| **Cardinality** | Every array's length must match its declared cardinality rule. A state_order of length N implies all state-aligned vectors also have length N. |
| **Enums** | Use only the exact enum/classification values declared in the template or decision rule. |
| **No narrative** | Submit only the JSON object. No surrounding text, commentary, or markdown fences. |

#### Module-specific patterns

**Delete-one / jackknife modules:**
- Report the full-model coefficient, the complete delete-one vector (aligned to the cluster/state order), the mean delete-one coefficient, jackknife standard error, t-statistic, p-value, bias-corrected coefficient, and the extreme-influence unit with its coefficient.

**Nested cross-validation modules (ridge / elastic net):**
- Report the lambda (or alpha+l1_ratio) grid in declared order.
- Each outer fold reports: held-out group, held-out count, selected hyperparameter(s), the complete inner-grid RMSE values (aligned to the grid), and the outer RMSE.
- Pooled metrics: RMSE, MAE, R² (or Q²). For ridge: report the state-win count (augmented better than base).

**Wild cluster bootstrap modules:**
- Report the PRNG metadata (algorithm, seed, stream), observed statistic (coefficient, cluster-robust standard error, t-statistic), all requested checkpoints (replicate number, PRNG state, bootstrap t), exceedance count, plus-one p-value, and all requested quantiles.
- The final PRNG state must be reported when requested.

**Grouped conformal modules:**
- Report every group's calibration diagnostics: calibration size, rank/threshold, radius, held-out size, coverage fraction, mean interval width.
- Report pooled/aggregate coverage and mean width. Report the worst-coverage group.
- When state-level coverage is required, report every state's coverage and width aligned to state order.

**Trajectory PCA clustering modules:**
- Report the feature order, cohort size, leading eigenvalues and explained-variance ratios, signed loadings (aligned to feature order), all state/county scores (aligned to state/county order), centroid initialization and final centroids, cluster assignments, and all leave-one-out stability diagnostics (ARIs and agreement counts).
- Feature blocks are formed by concatenating within-year feature sequences across years in declared order.

**Source / perturbation stability modules:**
- Report the strict cohort audit, all scenario subsets in declared order, coefficient and p-value vectors for each source, shift vectors, same-sign summary, worst subset, and maximum absolute percent shift.
- When Shapley decomposition is required: report the ordered Shapley effects (aligned to the replacement-state order), the Shapley sum, and the all-replaced-minus-all-direct coefficient.

**GMM / panel modules:**
- Report design dimensions, coefficient vectors in declared term order, cluster-robust inference, first-stage diagnostics (partial F), cross-equation corrections (for mediation), Hansen J statistics, and all delete-unit diagnostics.

**Sensitivity surface modules:**
- Report baseline quantities, the full ordered surface grid (r2_mediator × r2_outcome × direction), the equal-strength tipping R², and the adjusted indirect/direct effects for every cell.

**Reconciliation modules (country tasks):**
- Resolve requested labels against the canonical country list from `/geographies/countries`. Count aliases (labels that differ from the canonical name). Report the sorted ascending set of resolved ISO3 codes.
- Track revision event IDs, anomaly/scale-break cells, and imputed cells through the quality audit pipeline.

#### Decision module

Report every gate as a Boolean (or PASS/FAIL as specified by the template), the passed-gate count, the first failed module (or NONE), and the final classification using only the allowed enum values.

## Audit module reference

These are the recurring statistical building blocks. When a protocol declares one of these methods, apply the corresponding computation pattern.

### Delete-one / jackknife inference

- **Pattern:** Fit the full model on the declared cohort; then fit delete-one models omitting each cluster unit (state, census division). Compute jackknife pseudo-values, bias-corrected coefficient, standard error, t-statistic, and p-value.
- **Weighted variant:** When reliability weights are declared, use the specified weight column (e.g., sample_size) in all fits including the delete-one fits.
- **GMM variant:** For two-step GMM with delete-state: fit the full two-step model; then refit omitting each state. Report coefficients in declared term order, Hansen J for each fit, and bias-corrected coefficients with maximum absolute shifts. Use the declared pseudoinverse cutoff for instrument matrices.
- **Output:** Full coefficient, complete delete-one vector, mean delete-one coefficient, jackknife SE/t/p, bias-corrected coefficient, minimum-delete and maximum-delete unit with coefficients.

### Nested grouped cross-validation (ridge)

- **Pattern:** Outer loop leaves out one group (census division or state) at a time. Inner loop leaves out one group from the training set. Within each outer fold: for each lambda, compute the mean inner-group RMSE across inner folds; select the lambda minimizing mean inner RMSE; train on all inner data with that lambda; predict the held-out outer group; record outer RMSE.
- **Standardization:** When "training-only standardization" is declared, center and scale continuous features using only the training-set means and standard deviations within each fold. Indicator/dummy terms are never standardized.
- **Feature maps:** Base features and augmented features have declared orders. Augmented wins count = number of outer folds where augmented outer RMSE < base outer RMSE.
- **Output:** Lambda grid, outer fold sizes, selected lambdas (aligned to fold order), inner RMSE matrix (folds × lambdas), outer RMSE vector, pooled RMSE/MAE/Q², worst outer division, augmented win count.

### Nested grouped cross-validation (elastic net)

- **Pattern:** Outer loop leaves out one group. Inner loop leaves out one group from training. Grid search over (alpha, l1_ratio) combinations. Select the pair minimizing mean inner RMSE. Report standardized coefficients for the selected model.
- **Coordinate descent:** Report the number of coordinate cycles to convergence and the number of nonzero features in the selected model.
- **Output:** Candidate grid, outer fold diagnostics (held-out states, row counts, complete inner-grid RMSE values, selected hyperparameters, standardized coefficients, outer RMSE), pooled OOF RMSE/MAE/R².

### Wild cluster bootstrap-t

- **Pattern:** Fit the source model to obtain observed coefficient, CR1 (cluster-robust) standard error, and t-statistic. Generate R bootstrap replicates using the declared PRNG (XORSHIFT32 or PCG32) with the declared seed and stream. For each replicate: apply restricted-null weights to the cluster-level scores, refit, and record the bootstrap t. Compute the exceedance count (bootstrap |t| > observed |t|) and plus-one p-value = (exceedance + 1) / (replicates + 1).
- **Checkpoints:** Record PRNG state and bootstrap t at each declared checkpoint replicate.
- **Output:** PRNG metadata, observed statistic, checkpoint rows (replicate, prng_state, bootstrap_t), exceedance count, plus-one p-value, bootstrap t quantiles at requested probabilities, final PRNG state.

### Grouped split conformal prediction

- **Pattern:** Split groups into training, calibration, and test folds. Train the source model on training groups. On the calibration group: compute nonconformity scores (absolute residuals). The threshold is the ⌈(1–α)(n_cal+1)⌉-th smallest score. On each test group: prediction ± threshold; coverage = fraction of observations inside the interval; mean width = 2 × threshold (or as reported).
- **Multi-fold / cross-fold variant:** Rotate the calibration/test assignment across folds. Each fold's threshold, coverage, and width are reported separately; pooled coverage and mean width aggregate across all folds.
- **State-level variant:** Report per-state coverage and width in addition to per-division diagnostics.
- **Output:** Per-fold diagnostics (calibration size, rank, radius, held-out size, coverage, mean width), pooled/aggregate coverage and width, worst-coverage group. When state-level is required: per-state coverage and width aligned to state order.

### Trajectory PCA clustering

- **Pattern:** Form the trajectory feature matrix by concatenating within-year feature vectors across all study years in declared order. Compute PCA via eigendecomposition of the covariance matrix. Retain the declared number of components. Initialize k-means with deterministic centroids (e.g., the three states farthest apart in PC space by declared rule). Run Lloyd's algorithm to convergence. Report cluster centroids in PC space and per-unit cluster assignments.
- **Stability:** For each leave-year-out iteration: omit all features containing that year, re-run the full PCA+k-means pipeline, and compute the adjusted Rand index between the full-data clustering and the leave-year-out clustering restricted to the same units.
- **Output:** Feature order, eigenvalues and explained-variance ratios for retained components, signed loadings (aligned to feature order), unit scores (aligned to unit order), initial centroid states, final centroids, cluster sizes and labels (aligned to unit order), leave-year-out ARIs and agreement counts, minimum ARI.

### Source / perturbation stability

- **Exhaustive source-year perturbation:** For a declared primary and parallel exposure series, enumerate all 2^K subsets of K years (or all year-subset sizes). For each subset: replace the primary source with the parallel source for those years, refit the model, and record the coefficient and p-value. Compute the absolute percent shift between each scenario's coefficient and the baseline. Report same-sign fraction, median and maximum absolute percent shift, and the worst-shift subset.
- **Exhaustive source perturbation with Shapley:** For M states with both direct and rollup source availability, enumerate all 2^M replacement combinations (bitmask 0 to 2^M–1). For each scenario: apply the specified replacements, refit the weighted model with HC3 inference, and record the coefficient, p-value, and absolute percent shift vs. the all-direct baseline. Compute exact Shapley values by averaging marginal contributions across all orderings. Report the ordered Shapley effects, Shapley sum, and all-rollup-minus-all-direct coefficient.
- **Source-group deletion:** For each ordered source group, remove its terms from the full model (keeping selected hyperparameters fixed), refit, and record the five outer-fold RMSEs, pooled RMSE, RMSE deterioration vs. full-model reference, worse-fold count, and deterioration rank.

### Difference GMM mediation

- **Pattern:** Estimate three equations: (1) total effect of exposure on outcome, (2) path A: exposure on mediator, (3) path B + direct: mediator and exposure on outcome. All use first-differenced specifications with clustered standard errors. The indirect effect = path_A × path_B with cross-equation delta-method inference accounting for the covariance between the two coefficient estimates. First-stage partial F statistics test instrument relevance for both endogenous change variables.
- **Output:** Panel dimensions, four coefficient summaries (total, path A, path B, direct) with clustered SE/t/CI, two first-stage partial F statistics, stacked indirect effect with cross-equation correction, leave-one-state-out diagnostics.

### Partial R² sensitivity surface

- **Pattern:** From baseline path-a and path-b estimates, compute the adjusted indirect effect under hypothetical confounding strengths parameterized by R²_mediator_confounder and R²_outcome_confounder. For each (r2_m, r2_o, direction) cell: compute the bias-adjusted path-b, adjusted indirect effect, adjusted direct effect, and the proportion of the baseline indirect effect remaining. The equal-strength tipping R² is the value at which both R² values equal and the indirect-effect sign flips.
- **Output:** Baseline quantities, equal-strength tipping R², complete surface grid in declared (r2_mediator asc, r2_outcome asc, direction) order.

### Country reconciliation and PCA

- **Pattern:** Resolve each requested country label against the canonical names and aliases from `/geographies/countries`. Apply revision events: "APPLIED" events modify values; other events (SUPERSEDED, WITHDRAWN) are noted but not applied. Identify anomaly/scale-break cells from quality flags. Impute remaining missing 2022 cells (e.g., by indicator median across usable countries). Run PCA on the completed matrix. Cluster countries (k=2..5) on PC scores; select best k by silhouette. Fit a region-fixed-effects panel model of life_expectancy ~ PC1 burden score for 2017–2022.
- **Output:** Reconciliation counts and resolved ISO3 set, quality audit (applied/nonapplied revision IDs, anomaly cells, missing/imputed counts, usable dimensions), PCA (retained components, PC1 variance fraction, top-3 absolute loadings), clusters (requested k, silhouette-selected k, silhouette by k, sizes, high-burden ISO3 set), panel model (N, PC1 coefficient/SE/p, R², region FE indicator), advisory enum.

## Decision rule patterns

Decision rules follow a precedence chain. The most common patterns:

- **All-gates-pass:** If every gate is PASS → primary/conclusive classification.
- **Threshold-count:** If at least K gates pass (but not all) → intermediate classification.
- **First-failure:** Walk gates in declared precedence order; the first FAIL determines the classification (e.g., `NOT_ROBUST_AT_<MODULE>`).
- **Fallthrough:** All remaining cases → default classification.

Always report every individual gate result, the passed count, the first failed module (or `NONE`), and the final classification using only the allowed enum values.

## Quality flags and missing data

- **Invalid quality flags:** `INVALID_SCALE`, `INVALID`, `WITHDRAWN` — observations with these flags are excluded before analysis.
- **Suppressed values:** Treated identically to missing — they are unavailable and never zero-filled.
- **Anomaly/scale-break cells:** Identified from the methodology endpoint; excluded from analysis and counted separately in quality audits.
- **Imputation:** When required by protocol (e.g., for PCA completeness), impute missing cells using the declared method (typically indicator median across usable units). Count imputed cells in the quality audit.

## Precision reference

| Context | Decimal places | Applies to |
|---------|---------------|------------|
| Standard reporting | 4 | Non-integer statistics: coefficients, SEs, p-values, RMSE, MAE, R², Q², coverage fractions, ARIs, loadings, scores, Shapley effects |
| Extended precision | 6 | Computed real-valued fields in county-panel protocols (train_005 pattern); grid/threshold values in those protocols stay at 4 |
| Integer | 0 | Counts, ranks, fold numbers, replicate numbers, seeds, PRNG states, observation counts, year values |
| Boolean | natural | Gate results, support flags |

When in doubt, use the precision declared in `analysis_request.json`'s `reporting` block or `answer_template.json`'s `numeric_rule`.
