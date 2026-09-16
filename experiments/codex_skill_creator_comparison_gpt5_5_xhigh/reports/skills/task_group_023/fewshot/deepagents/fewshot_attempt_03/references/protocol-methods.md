# PHO Protocol Methods

This reference contains reusable method semantics only. Bind all task-local values from the active request and portal evidence.

## Portal Data

Prefer CSV downloads:

- `states`: state FIPS, abbreviation, name, region, division, state/DC flag.
- `counties`: county FIPS, state abbreviation, region, RUCC, population and location fields.
- `countries`: ISO3-like identifier, canonical name, portal label, alternate labels, region, income group.
- `state_health`: state-year-measure publications with value type, source type, release status, revision, value, standard error, sample size, suppression flag, quality flag, release timestamp.
- `state_socioeconomic`: state-year socioeconomic records with release status, revision, release timestamp, fields such as poverty, bachelors, median income, unemployment, uninsured, food insecurity, population, and quality flag.
- `county_health`: county-year-measure publications with value type, release status, revision, release timestamp, value, confidence limits, population, suppression flag, and quality flag.
- `county_socioeconomic`: county-year socioeconomic records with poverty, median income, bachelors, unemployment, net migration, uninsured, population, quality flag, release status, revision, and timestamp.
- `country_indicators`: country-year-indicator publications with status, revision, timestamp, value, unit, and quality flag.
- `revisions`: revision event id, domain, entity, field, effective year, old and new values, status, issued date, reason, and note.

Filter and join with typed keys, but keep identifiers as strings. Read methodology pages for current policy when the request points to label aliases, revision notices, quality flags, suppression, release lifecycle, value types, state estimates, RUCC, or socioeconomic comparability.

## Shared Mechanics

### Effective Requests

For exact protocol profiles, activate only on the exact case-sensitive `protocol_id`. Similar subject matter or family IDs are not enough. Resolve the complete effective request once, then use it unchanged in all modules.

Task-local bindings include entities, measures, years, geography, source filters, invalid flags, random seeds, replicate schedules, hyperparameter grids, fold counts, tolerance values, business cutoffs, output key names, enum labels, and precision.

### Release Resolution And Cohorts

Resolve one selected record per entity-time-measure-field key after applying request filters. Common precedence is final status, greatest revision, latest `released_at`, then the protocol's specified record-id tie breaker. Some profiles require the lowest id and others the greatest id; use the matching profile or request text.

Count publication rows before analytic completeness exclusions when requested. For analytic cohorts, unavailable values include suppression flags, invalid or withdrawn quality flags, blank strings, nulls, and unresolved scale breaks. Do not fill them with zero. Build complete cohorts by intersecting exactly the fields and periods named in the request.

### Linear Models And Inference

Fit OLS in declared column order. For fixed effects, double-demean each modeled variable as value minus entity mean minus time mean plus grand mean and fit without an intercept. In delete-cluster refits, remove the whole cluster, recompute all means or weights, and refit from scratch.

For weighted least squares, use `sqrt(weight)` transformed `X` and `y`. HC3 uses leverage from the weighted design and residuals scaled by `sqrt(weight)`. CR1 cluster covariance uses ordered cluster score sums and the finite-sample factor `[G/(G-1)]*[(n-1)/(n-k)]`. Use two-sided Student t with the effective residual or cluster degrees of freedom.

For delete-cluster jackknife with `G` delete estimates and mean `bbar`, use:

- `SE=sqrt((G-1)/G*sum((b_delete-bbar)^2))`
- `bias_corrected=G*b_full-(G-1)*bbar`
- test statistic from the coefficient specified by the profile, with two-sided Student t and `G-1` degrees of freedom.

### Ridge And Elastic Net

Standardize only from the training rows in every fit. Apply the same moments to validation or test rows. Keep the intercept unpenalized. Pool row-level validation squared errors before RMSE; do not average fold RMSEs unless explicitly requested.

Ridge profiles use coordinate descent or direct linear algebra as specified. Elastic-net profiles use cold starts unless explicitly allowed to reuse hyperparameters. Break selection ties toward smaller penalties, then smaller l1 ratios, then declared order.

### Bootstrap Streams

Maintain one continuous PRNG stream across replicates. Record checkpoints only after the listed replicate is fully fit.

Use the requested generator:

- Xorshift32: unsigned 32-bit state; apply shifts 13, 17, 5 with masking after each xor. Map odd output to `+1` and even output to `-1` unless the request states another mapping.
- PCG32 Webb: initialize with the effective seed and stream, draw once per ordered cluster, map output modulo six to the Webb weights in the request profile.

Restricted-null wild bootstrap fits the model without the target term, forms synthetic outcomes from restricted fitted values plus cluster-weighted residuals, refits the unrestricted model, recomputes the registered standard error, studentizes, counts two-sided or absolute-tail exceedances as specified, and reports plus-one p-values.

### Conformal Calibration

Use the prediction source declared by the request. Split by the effective group or fold order. Compute absolute calibration residuals, sort them, and use the finite-sample nearest-rank rule in the profile, usually `min(m, ceil((m+1)*coverage_or_1_minus_alpha))`. Intervals are inclusive and symmetric unless the template says otherwise. Aggregate coverage by requested rows or groups and select worst groups by unrounded values and declared tie rules.

### PCA, Clustering, And Stability

Build trajectory matrices in the exact variable-major, time-major, or request-declared order. Standardize columns using the profile's sample or population convention. Use covariance `Z'Z/(n-1)` for sample profiles and `Z'Z/n` for population profiles. Sort eigenpairs descending and orient each retained loading so the earliest maximum-absolute loading is positive.

Use deterministic k-means:

1. First center is the smallest identifier or ASCII-first entity required by the profile.
2. Each next center is the entity farthest from its nearest existing center, with identifier tie breaks.
3. Assign to nearest center with lower cluster id on equality.
4. Update centroids by member means and stop when labels stop changing or the effective cap is reached.
5. Canonicalize labels only as the profile says.

For stability, rebuild scaling, PCA, initialization, and clustering after each omitted year, state, or block. Compute adjusted Rand index from the contingency table. When reporting aligned changes, choose the label permutation with maximum agreement and deterministic lexicographic tie breaks.

## PHO_STATE_TRANSPORT_AUDIT_V1

Use for state adult-obesity longevity transportability audits.

- Release and cohorts: resolve health and socioeconomic final records independently. Core balanced cohorts require all core fields in every effective year. Broad reference cohorts require the reference-year outcome and all ordered ridge features. Strict dual-source cohorts require outcome, primary exposure, parallel exposure, and adjustments in every effective year.
- Delete-cluster fixed effects: fit two-way fixed-effects OLS on the core balanced panel with declared predictors. Delete one state at a time in state-code order, recompute double-demeaning, calculate jackknife inference, bias correction, and coefficient extrema by coefficient then state code.
- Nested ridge by census division: hold out one ordered division as the outer fold and each remaining division as inner validation. Use training-only sample standardization, centered outcome, unpenalized intercept, coordinate descent in declared feature order, row-pooled inner RMSE selection, and row-pooled outer metrics including `Q^2=1-SSE/SST`.
- Wild cluster bootstrap: use the same double-demeaned fixed-effects matrix, CR1 cluster covariance, restricted model without the target, PCG32 Webb weights, state-code draw order, batch exceedance counts, plus-one p-value, and nearest-rank quantiles.
- Grouped split conformal: for each ordered division as test, choose calibration among the remaining divisions by greatest row count then ascending division name. Fit ridge with the fixed penalty, use nearest-rank absolute residual thresholds, and aggregate row-weighted coverage and width.
- Trajectory PCA clustering: use effective outcome and exposure trajectories in declared feature order, sample covariance, deterministic three-means, complete state scores, labels, centroids, and leave-year-out ARI/agreement arrays.
- Source-year perturbation: enumerate time subsets by increasing size and lexicographic tuple order. Hold the strict cohort fixed. Refit primary and parallel double-demeaned models for each subset, compute CR1 p-values, percent shifts from the baseline, same-sign fraction, median shift, and worst subset by unrounded shift then subset order.
- Decision: complete all six modules, evaluate gates on unrounded values in request order, count passes, and apply only the request's classification mapping.

## PHO_COUNTY_MEDIATION_TRANSPORT_V1

Use for county poverty-to-obesity mediation transport audits.

- Publication and linked cohorts: resolve county health and socioeconomic releases by requested filters and priority. Primary cohorts are effective-year complete cases; balanced panels require complete basic data in all requested years; machine-learning cohorts add requested ML fields.
- Primary mediation models: fit total-effect, path-a, and direct/path-b OLS designs using the request's exposure, mediator, outcome, transformations, RUCC reference, and covariate order. Preserve unrounded fits for bootstrap and sensitivity.
- Difference GMM mediation: create adjacent change rows in entity then end-period order. Use declared lagged instruments. For each equation, compute `W=(Z'Z)^-1` and `beta=(X'ZWZ'X)^-1 X'ZWZ'y`. Use state-cluster sandwich scores. For `theta=a*b`, use delta variance `b^2 Var(a)+a^2 Var(b)+2ab Cov(a,b)`. Compute first-stage partial F from reduced versus full residual sums of squares. Rebuild every delete-state diagnostic from scratch.
- Nested state ridge: leave one state out, with inner leave-one-state folds. Use effective base and augmented feature maps, training-only population standardization, unpenalized intercept, row-pooled RMSE, tie to smaller penalty, and aligned fold diagnostics.
- Paired state wild bootstrap: for each target equation, remove only that target in the restricted model. Use one continuous xorshift32 stream, drawing states in ascending order and reusing the same state signs across paired equations in a replicate. Report checkpoints, two-sided plus-one p-values, bootstrap-t quantiles, and intervals.
- State grouped conformal: assign states in ascending order to cyclic partitions. For each test partition, use the registered preceding partition for calibration and the rest for proper training. Reduce calibration residuals to one maximum absolute residual per calibration state, then use the finite-sample state-rank threshold.
- Partial-R2 sensitivity: enumerate mediator-confounder R2, outcome-confounder R2, and bias directions in declared order. From baseline `a`, `b`, `SE_b`, and residual df, adjust `b` by the profile magnitude formula, recompute indirect, direct, and proportion, and compute equal-strength tipping from unrounded inputs.
- State trajectory PCA: aggregate balanced-panel measures to state-period means in declared order, sample-standardize, run PCA, deterministic k-means, and leave-period ARI.
- Decision: evaluate the six named support flags on unrounded module outputs and choose the first applicable class from request precedence.

## PHO_STATE_ROBUSTNESS_TRANSPORT_V1

Use for reliability-weighted state association robustness audits.

- Release and cohort: filter publications by effective status, source, value type, validity, and geography. Select greatest revision, latest timestamp, then greatest record id. Use the selected direct outcome sample size as the fixed positive reliability weight, including source-perturbation fits unless overridden.
- Weighted models: implement WLS, HC3, and CR1 exactly as in shared mechanics. Use declared design columns, reference categories, and reliability weights.
- Cluster jackknife: delete each registered census division, refit weighted design, compute percent changes, bias-corrected coefficient, jackknife SE, two-sided p-value, and most influential division by unrounded percent change then earlier division order.
- Nested weighted elastic net: hold out each registered division externally and each remaining division internally. Build raw, transformed, squared, and interaction features in declared order. Use weighted training means and weighted population SDs. Cold-start each penalty. Pool unweighted validation errors, select by RMSE then smaller penalty, refit, report nonzero counts, coordinate cycles, OOF RMSE, MAE, and R2.
- Wild division bootstrap: studentize the weighted target with CR1, fit restricted weighted model, use xorshift32 in registered division order, record checkpoints, count absolute exceedances with the profile's comparison tolerance if any, use the profile's quantile type, and report final PRNG state.
- Grouped conformal: reuse outer predictions and selected penalties. For each held-out division, calibrate by refitting on other training divisions and pooling absolute residuals. Use the declared coverage rank, report ordered diagnostics, pooled coverage, weighted mean interval width, and worst division.
- Trajectory PCA clustering: build variable/time blocks in declared order over the balanced cohort, sample-standardize, orient loadings, run deterministic k-means on retained scores, handle empty clusters as specified, and perform leave-year stability with aligned assignment changes.
- Exhaustive source perturbation: resolve direct and alternate outcome sources. Order paired entities by descending absolute alternate-minus-primary difference, tied by entity code. Enumerate masks from zero to `2^m-1`, replacing entity `j` when bit `j` is set, while preserving direct weights. For each stratum, report coefficient and p-value ranges and mean shifts. Compute exact signed Shapley effects in the ordered entity sequence and verify their sum.
- Decision: evaluate modules in the request's precedence and return the first failed controlled conclusion or the all-robust conclusion.

## PHO_COUNTY_PANEL_TRANSPORT_V1

Use for county panel diagnosed-diabetes dynamics transport audits.

- Publication balanced panel: resolve county health and socioeconomic records independently by effective final filters and revision priority. Keep only counties complete for all balanced years with valid geography. Create adjacent-change panel rows ordered by entity identifier then end period, deriving lagged levels, dynamic changes, indicators, and interactions in declared order.
- Delete-state two-step GMM: residualize outcome, dynamic regressors, and instruments against intercept plus baseline terms. Use identity first-step moments, state score covariance, registered Moore-Penrose inverse cutoff, second-step weighted moments, Hansen J, full and delete-state refits, jackknife bias correction, and maximum delete-state shifts.
- State-blocked nested elastic net: allocate states to folds by descending retained-entity counts, assigning to the smallest fold with lower fold id on ties. Within each fit, standardize declared continuous terms by training population moments, leave indicators unchanged, cold-start, and coordinate-descent the elastic-net objective in coefficient order. Traverse alpha and l1-ratio grids in declared order, pool inner squared errors, tie to smaller alpha then smaller l1 ratio, refit outer models, and pool OOF metrics.
- State wild cluster bootstrap: fit full unpenalized OLS with state CR1 for the target. Fit restricted model without the target, generate xorshift32 state signs in ascending state order, refit full models, recompute CR1, count absolute-tail exceedances, compute plus-one p, nearest-rank quantiles, and requested checkpoints.
- Cross-fold grouped conformal: use nested elastic-net OOF predictions in original analytic-row order. For each held-out fold, calibrate on absolute OOF residuals from all other folds. Use `min(m, ceil((m+1)*coverage))`, then report fold, state, RUCC-band, prediction-bin, overall, and minimum-state calibration diagnostics.
- County trajectory PCA clustering: build variable-major county trajectories in declared variable and end-period order. Standardize with population moments and covariance `Z'Z/n`. Select candidate k by largest unrounded silhouette, tied to smaller k. For each state deletion, rebuild the full pipeline at selected k and report ARI against retained full labels.
- Source group perturbation: for each declared source group and outer fold, remove exactly that group's terms, reuse the full-model selected hyperparameters without retuning, apply the same preprocessing and solver to remaining terms, report fold RMSEs, pooled deterioration from full OOF RMSE, worse-fold count, and rank by decreasing unrounded deterioration then declared order.
- Decision: evaluate the six gates in order on unrounded values and return the first applicable controlled decision.

## Country Burden Revision PCA Audit

Use when a PHO country request asks to reconcile country labels, audit revisions or anomalies, build a burden PCA, cluster countries, run a region-adjusted panel model, and issue a controlled advisory.

- Reconcile every requested label against `countries.canonical_name`, `portal_label`, and comma-separated `alternate_labels`. Count aliases when the requested label resolves but differs from the canonical name. Output unique resolved ISO3 identifiers in sorted order unless the template specifies another order.
- For requested burden indicators and panel outcomes, select final country indicator records by effective year, ISO3, indicator, revision, timestamp, and record-id policy. Applied revision events authorize corrected later final revisions. Pending, draft, withdrawn, or non-applied events are audit evidence but do not authorize replacement.
- Treat unresolved scale breaks and nonusable anomaly flags as unavailable. Count raw missing cells before anomaly exclusions, anomaly cells separately, and imputed cells after quality exclusions. Impute only for the completed PCA matrix; keep audit counts separate from imputed analytic values.
- Orient burden indicators so higher PC1 means higher burden. Use the portal dictionary direction and request's burden indicator list. Standardize indicators before PCA, sort loadings by descending absolute value with indicator-id tie breaks, and report signed coefficients.
- For requested three-segment burden clustering, cluster on retained burden scores, then label clusters by mean PC1 burden as low, middle, and high. Evaluate candidate k values exactly as requested, use average silhouette with deterministic tie breaks, and output set-like ISO3 lists sorted ascending.
- For panel association, rebuild country-year PC1 scores from the requested panel span using the same burden orientation and quality rules. Fit life expectancy on PC1 burden with region fixed effects when requested. Report coefficient, standard error, p-value, R-squared, and whether fixed effects were included.
- Advisory decisions should follow the request/template controlled values. A typical adverse-gradient rule prioritizes the high-burden cluster when the region-adjusted PC1 coefficient is negative and statistically supported; otherwise use the request's weaker monitoring or no-gradient categories.
