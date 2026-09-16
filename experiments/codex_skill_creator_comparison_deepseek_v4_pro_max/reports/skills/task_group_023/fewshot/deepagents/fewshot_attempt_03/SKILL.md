---
name: pho-audit-portal
description: "Public Health Observatory algorithmic audit protocol execution. Use when an analysis_request.json or prompt references a PHO registered audit protocol, when the task involves executing multi-module transportability audits for state/county/country health data via the PHO web portal, or when the solver must implement deterministic statistical methods (fixed-effects jackknife, nested ridge/elastic-net CV, wild cluster bootstrap, grouped split conformal, trajectory PCA clustering, source/year perturbation, difference GMM mediation, sensitivity analysis) from raw portal CSV data. Covers all PHO protocol families: PHO_STATE_TRANSPORT_AUDIT_V1, PHO_COUNTY_MEDIATION_TRANSPORT_V1, PHO_COUNTY_PANEL_TRANSPORT_V1, and country burden stratification audits."
license: MIT
compatibility: designed for deepagents-code
---

# Public Health Observatory Audit Portal Skill

Execute registered PHO algorithmic audit protocols against the Public Health Observatory read-only web portal. Implement all statistical methods from scratch using portal CSV data; interpret protocol specifications in `analysis_request.json` and fill `answer_template.json` with computed results.

## Quick Start

1. Read the request: Parse `analysis_request.json` to identify the protocol, scope, parameters, modules, and answer template.
2. Read the answer template: The template defines exact field names, array orders, cardinalities, enum values, and numeric precision; follow it exactly.
3. Retrieve geography: Download state/county/country reference tables from the portal to establish the entity universe and group structures.
4. Resolve data: Follow the release selection rules (see [references/data-rules.md](references/data-rules.md)) to get the analytic dataset for each module cohort.
5. Execute modules in order: Implement each module algorithm from [references/algorithms.md](references/algorithms.md) using only portal data.
6. Evaluate gates: Apply decision predicates to unrounded computed values.
7. Write answer: Exactly one JSON object conforming to the template, with no narrative outside it.

## Portal Interface

The portal lives at the base URL declared in the task environment (typically `http://task-env:9023/`). See [references/portal-api.md](references/portal-api.md) for the complete endpoint reference, CSV schemas, and download patterns.

Key retrieval pattern:
```
curl -s "BASE_URL/download?dataset=<dataset>&format=csv&<filters>"
```

Parse with Python `csv.DictReader`. Use paginated HTML only if CSV download fails.

### Efficient Data Download

- State health: One CSV request per year (hundreds of rows each)
- State socioeconomic: One request per year (about 50-100 rows)
- County health: Filter by year and optionally state; can be large
- County socioeconomic: Download by year, filter by region if needed
- Country indicators: One request per year
- Geography tables: Download full tables once (states, counties, countries)
- Revisions: Download full table once

## Geography

See [references/geography.md](references/geography.md) for state/division/region tables, county RUCC structure, and country label reconciliation rules. Always re-retrieve geography tables from the portal at runtime; do not rely on static copies.

## Data Resolution

See [references/data-rules.md](references/data-rules.md) for the full release selection algorithm, suppression rules, cohort construction patterns, geography joins, and variable transformations.

Key principles:
- FINAL releases only; highest revision wins; tiebreak by latest `released_at` then lowest record id
- Suppressed (`suppression_flag=1`), null, and invalid values are unavailable; never zero-fill
- Count selected publications before analytic completeness checks when the request asks for selected-row counts
- State socioeconomic `food_insecurity` is distinct from state health `food_insecurity` -- they come from independent sources

## Algorithms

See [references/algorithms.md](references/algorithms.md) for complete specifications of every registered statistical method. Implement each from scratch; do not substitute external packages that would change the algorithmic contract.

Core method families:
- Delete-one cluster jackknife: Two-way FE transformation (or weighted OLS), delete-one refit, jackknife inference with G-1 df, CR1/HC3 standard errors
- Nested ridge/elastic-net CV: Training-only standardization, coordinate descent solver, inner-grid selection, outer-test pooling, OOF metrics
- Wild cluster bootstrap: Null-restricted model, PCG32/Xorshift32 PRNG, Webb/Rademacher weights, CR1 studentization, plus-one p-values, nearest-rank quantiles
- Grouped split conformal: Calibration-set threshold, prediction intervals, coverage/width by fold and aggregate
- Trajectory PCA clustering: Covariance PCA with symmetric Jacobi, deterministic k-means, leave-group-out stability via adjusted Rand index, silhouette scores
- Source/year perturbation: Exhaustive subset enumeration or source-replacement grid, stability summaries, Shapley attribution
- Difference GMM mediation: Two-step GMM, cross-equation delta method, Hansen J, state-deletion diagnostics
- Sensitivity analysis: Partial R2 surface, tipping-point identification
- Source group perturbation: No-retune group deletion, outer-fold RMSE deterioration, ranking

## Protocol Families

### PHO_STATE_TRANSPORT_AUDIT_V1

Six-module state-level transportability audit. Modules: delete-cluster FE, nested ridge CV, wild cluster bootstrap, grouped split conformal, trajectory PCA clustering, source-year perturbation.
Decision: all-six-gates-pass -> PRIMARY_TRANSPORTABLE_LONGEVITY_SIGNAL; 4-5 gates -> ASSOCIATED_LONGEVITY_SIGNAL_WITH_LIMITED_TRANSPORTABILITY; otherwise NO_TRANSPORTABLE_LONGEVITY_SIGNAL.

### PHO_COUNTY_MEDIATION_TRANSPORT_V1

County mediation audit. Modules: difference GMM mediation, nested state ridge, wild cluster bootstrap, state-grouped conformal, mediation sensitivity surface, trajectory PCA clustering.
Decision: all 6 -> CONSISTENT_OBESITY_MEDIATION_AUDIT; 4-5 -> PARTIAL_OBESITY_MEDIATION_AUDIT; 2-3 -> FRAGILE_OBESITY_MEDIATION_AUDIT; otherwise NO_OBESITY_MEDIATION_AUDIT.

### PHO_COUNTY_PANEL_TRANSPORT_V1

County panel dynamics audit. Modules: delete-state two-step GMM, nested elastic net, wild cluster bootstrap, grouped conformal calibration, trajectory PCA clustering, source group perturbation.
Decision: all 6 -> DEPLOY_DIABETES_DYNAMICS; 4-5 -> REVIEW_DIABETES_DYNAMICS; otherwise RETAIN_LAGGED_DIABETES.

### Country Burden Stratification (PHO-CBR)

Country cross-section and panel audit. Steps: label reconciliation, quality/revision audit, PCA on burden indicators, k-means clustering with silhouette selection, region-FE panel model of life_expectancy against PC1 burden score, advisory classification.

## Implementation Order

Every protocol executes modules in the declared order. Within each module:

1. Construct the analytic dataset for that module cohort
2. Implement the algorithm exactly as specified in [references/algorithms.md](references/algorithms.md)
3. Collect all required evidence (fold-level, delete-level, checkpoint details)
4. Report at the declared numeric precision
5. Preserve every declared array order, identifier case, and enum value

## Common Pitfalls

- Suppressed values: Treat as missing, never as zero
- Revision selection: Always select highest FINAL revision; multiple FINAL revisions of the same record can exist for different revision numbers
- Training-only standardization: Standardize using training-set moments only; apply to validation/test
- PRNG state: Do not reset the generator between replicates; checkpoints are recorded after the replicate completes without resetting the stream
- Array order: Never sort result arrays independently of their paired reference arrays; preserve portal order or declared order
- Identifiers: Use uppercase state abbreviations and exact division/region names from the portal geography tables
- Numeric precision: Round non-integers to declared decimal places; counts, seeds, and ranks as integers
- Socioeconomic food_insecurity vs health food_insecurity: These are independent variables from separate sources; do not conflate them
- Delete-state/leave-out ordering: Always process deletions in the declared entity order; aggregate results in that same order
- Inner RMSE grid ordering: Each inner grid row must align positionally with the lambda_grid or (alpha, l1_ratio) grid order
- Conformal calibration tiebreak: When multiple groups tie for calibration selection, choose by ascending group name
- K-means canonicalization: After convergence, reorder cluster ids by centroid coordinates then original working id
