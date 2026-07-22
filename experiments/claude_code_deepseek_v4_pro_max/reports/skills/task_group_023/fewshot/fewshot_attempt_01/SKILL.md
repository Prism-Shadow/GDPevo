# Public Health Observatory — Algorithmic Transport Audit Skill

## Overview

This skill guides an agent through completing a registered algorithmic audit against the Public Health Observatory (PHO) read-only evidence portal. Every audit is defined by an `analysis_request.json` (the effective request) and an `answer_template.json` (the response contract). The agent resolves evidence from the portal, executes each declared module in order, and returns exactly one JSON object conforming to the answer template — no narrative outside the JSON.

## Portal Reference

The portal is reached at the base URL supplied as `<TASK_ENV_BASE_URL>`. All endpoints are read-only GET with no authentication required.

### Available Endpoints

| Endpoint | Purpose |
|---|---|
| `GET /` | Portal root / health check |
| `GET /catalog` | Full catalogue of available datasets, measures, geographies, releases, and metadata |
| `GET /geographies/states` | State and territory codes, names, divisions, regions |
| `GET /geographies/counties` | County FIPS codes, names, and parent state mappings |
| `GET /geographies/countries` | Country ISO3 codes, names, regions, and alias mappings |
| `GET /data/state-health` | State-level health indicators by year |
| `GET /data/state-socioeconomic` | State-level socioeconomic indicators by year |
| `GET /data/county-health` | County-level health indicators by year |
| `GET /data/county-socioeconomic` | County-level socioeconomic indicators by year |
| `GET /data/country-indicators` | Country-level indicators by year |
| `GET /data/revisions` | Revision history, statuses, and release timestamps |
| `GET /methodology` | Indicator definitions, value types, suppression rules |
| `GET /download` | Bulk data export |

### Data Resolution Protocol

Every publication record has a composite key (entity, measure, year, source, value-type). When the effective request specifies release filters:

1. Filter each publication key by the effective status, source, value type, validity, and entity bindings.
2. Select the **greatest revision** among matching records.
3. Among tied revisions, select the **latest release timestamp**.
4. Among remaining ties, select the **lowest record identifier**.
5. A suppressed, invalid, withdrawn, blank, or null value is **unavailable** for analysis and is **never zero-filled** — it counts for publication totals if requested but is excluded from analytic completeness.

Use the `/catalog` and `/methodology` endpoints to understand which measures are available for which entities and years, what value types exist, and what suppression rules apply.

## The Analysis Contract

Every audit is driven by two files provided with the task in `payloads/`:

- **`analysis_request.json`** — The effective request. It declares the protocol identifier, entities, measures, time window, module parameters, hyperparameter grids, random seeds, business predicates, and decision thresholds.
- **`answer_template.json`** — The response contract. It declares the exact JSON structure, key names, array orders, numeric precision, enum values, and Boolean types the answer must conform to.

### analysis_request.json Structure

The effective request typically contains these sections:

- **`request_id`**: A unique identifier string for this audit instance.
- **`protocol_id`**: The exact case-sensitive protocol identifier that activates the registered method profile.
- **`business_request` / `business_task`**: Human-readable description of the audit question.
- **`scope` / `geography_scope`**: Entity universe (e.g., 50 states plus DC, named regions, a list of country labels).
- **`years` / `analysis_years` / `study_years`**: The integer year range for data resolution.
- **`reference_year` / `primary_year`**: The focal year for cross-sectional analyses.
- **`outcome` / `exposure` / `mediator`**: The measure(s) forming the analytic target, with optional source and value-type filters.
- **`evidence_specification` / `publication_selection`**: Release resolution rules — value types, source types, release status, revision priority, completeness predicates, and cohort definitions.
- **`audit_modules`**: A map of module name to module configuration. Each module declares its `method`, `cohort`, parameters (features, grids, seeds, cluster definitions), and `required_evidence` (the exact output fields expected).
- **`decision_rule` / `robustness_gates`**: Business predicates evaluated on unrounded module outputs, with precedence order and controlled conclusion mappings.
- **`reporting`**: Numeric precision, ordering requirements, and the output contract filename.

### answer_template.json Structure

The answer template defines the exact response contract. It typically contains:

- **`required_top_level_keys`**: The ordered list of top-level JSON keys the answer must include.
- **`template` / `required_output` / `fields`**: For each top-level key, the required sub-keys, their types, array lengths, cardinality rules, and allowed enum values.
- **`global_rules` / `numeric_rule`**: Default precision (e.g., 4 decimal places for non-integers), ordering conventions, identifier format, and missing-value handling.
- **`cardinality_rules`**: Cross-references between arrays (e.g., "state_order length must equal state_n", "delete coefficients must align positionally with state_order").
- **`ordering` specifications**: How each list must be sorted or preserved (e.g., "state ascending", "registered division order", "year ascending").
- **`gate_values` / `allowed_values`**: The controlled vocabulary for enum fields in the decision section.

### Working with the Contract

The agent must:
1. Read both files first — the answer template defines the exact output schema, and every field declared as required must appear in the answer.
2. Match the effective `protocol_id` (case-sensitive, exact string) against the registered method profile.
3. Apply the effective request's overrides and direct bindings to produce one frozen contract.
4. Execute every module in the order declared by `audit_modules` (or the registered `module_execution_order`), using only evidence from the portal.
5. Preserve every declared array order, state abbreviation, coefficient order, grid order, checkpoint order, and source-group order in the output — as specified by the template.
6. Report numeric values at the declared precision. For computed values, use the precision from `reporting`; for literal grid/threshold values carried from the request, use their original precision.
7. Use only the controlled vocabulary for enum and Boolean fields.
8. Return a single JSON object — no narrative outside it.

## Protocol Registry and Override Resolution

Every auditable protocol is registered with a portable method profile. The profile carries **method semantics only** — it describes algorithms, not specific entities, measures, time windows, or decisions. The profile must never be reused with cached task-local values from a previous invocation.

### Protocol Activation

Activation is by **exact case-sensitive match** of the future request's `protocol_id` to the registered protocol identifier. Family membership or similar names are not a match.

### Override Resolution

The effective request may supply overrides that customize the registered method profile. Resolution follows these rules:

1. **Base**: Start from the registered method profile for the exact protocol version and any inherited canonical defaults.
2. **Direct keys**: A direct root key `k` in the request targets the canonical root key `k`.
3. **Override aliases**: A root key named `<section>_overrides` targets canonical `<section>`; `module_overrides.<module_name>` targets the canonical top-level module of that exact name; `reporting_overrides` targets reporting. Strip only the terminal `_overrides` suffix during resolution.
4. **Object merge**: Objects recursively merge by exact key.
5. **Array replacement**: An explicit array replaces the inherited array in full — never concatenate, union, or merge by position.
6. **Scalar replacement**: An explicit scalar, string, Boolean, or null replaces only the matching inherited path.
7. **Inheritance**: Absent paths inherit unchanged from the base profile.
8. **No inference**: Reject unknown targets, implicit aliases, key renaming, type coercion, and incompatible types.
9. **Single contract**: Resolve one effective contract before any data access, random draw, fit, aggregation, or decision, and use it consistently in every module.
10. **Precedence**: Task-local direct bindings and resolved overrides take precedence over inherited values at the same path.

### Instance Boundary

The following are **always taken from the effective future request**, never carried from a prior invocation:
- Entities and measures
- Calendar scope and geography
- Source filters
- Random seed and replicate schedule
- Hyperparameter grid values
- Business decision cutoffs
- Requested labels and output vocabulary

Recompute all evidence and outputs for each invocation.

## Reusable Algorithmic Modules

This section catalogues the reusable algorithmic modules that appear across the PHO audit framework. A given protocol activates a subset in a declared execution order.

### Release Resolution and Cohort Construction

**Purpose**: Resolve the analytic dataset from portal publication records.

**Method**:
1. Filter each source (health, socioeconomic) by the effective request's status, source, value type, validity, and entity bindings.
2. Select one record per declared entity–time–measure key using the ordered release priority: greatest revision, then latest release timestamp, then lowest record identifier.
3. Count selected publications before analytic completeness exclusions when the request asks for publication totals.
4. Suppressed, invalid, withdrawn, blank, or null analytic values remain unavailable and are never zero-filled.
5. Join independently resolved series by the effective stable entity and time keys.
6. Construct each analytic set (complete, balanced-panel, broad, dual-source, machine-learning) from its effective required fields.
7. Preserve entity-code then time order, and preserve every declared feature and group order.

### Weighted Linear Algebra (WLS, HC3, CR1)

**Purpose**: Provide weighted least squares and cluster-robust inference for designs with reliability weights.

**WLS**: For design X, outcome y, and positive weights w, form Xw = diag(√w) × X and yw = diag(√w) × y, then solve b = (Xw′Xw)⁻¹Xw′yw in declared column order.

**HC3**: With leverage hᵢ = diag(Xw(Xw′Xw)⁻¹Xw′)ᵢ and weighted residual ewᵢ = √wᵢ(yᵢ − Xᵢb), compute V_HC3 = (Xw′Xw)⁻¹ Xw′ diag(ewᵢ²/(1−hᵢ)²) Xw (Xw′Xw)⁻¹. Use two-sided Student-t with n−k residual degrees of freedom.

**CR1**: For ordered clusters g and cluster scores s_g = Xw_g′ ew_g, compute V_CR1 = [G/(G−1)] × [(n−1)/(n−k)] × (Xw′Xw)⁻¹ Σ_g(s_g s_g′) (Xw′Xw)⁻¹. Use two-sided Student-t with G−1 degrees of freedom.

### Cluster Jackknife / Delete-One Diagnostics

**Purpose**: Assess influence of individual clusters on coefficient estimates.

**Method**:
1. Fit the full design.
2. Delete each registered cluster in order and refit the unchanged design from scratch.
3. For each delete estimate b_−g, compute percent change = 100 × |(b_−g − b)/b|. Select greatest unrounded change; tie-break by earlier cluster order.
4. For G delete estimates and mean b̄, compute:
   - Bias-corrected coefficient: b_BC = G·b − (G−1)·b̄
   - Jackknife standard error: SE_JK = √((G−1)/G · Σ_g(b_−g − b̄)²)
5. Test b_BC / SE_JK two-sided with G−1 Student-t degrees of freedom.

### Nested Ridge Regression with Division/State Cross-Validation

**Purpose**: Regularized prediction with nested cross-validation by geographic groups.

**Scaling**: For every fit, subtract training-only feature means and divide by training sample SD (ddof=1 for state-level, population SD for county-level). Apply those moments to validation/test rows. Center the training outcome; keep the intercept unpenalized.

**Coordinate Descent Solver**: Initialize coefficients to zero. In declared feature order, for each feature j, compute the partial residual r excluding feature j, then update bⱼ = Σᵢ xᵢⱼ rᵢⱼ / (Σᵢ xᵢⱼ² + n·λ). Stop after a full sweep when max coefficient change is below the effective tolerance or at the effective sweep cap.

**Nested CV Structure**: Hold out one ordered group (division or state) per outer fold. Within each outer training set, hold out every remaining group once in the same order for inner validation. Pool all inner validation squared errors at row level, compute RMSE, select the smallest RMSE then the smaller penalty. Refit on all outer-training rows and predict the outer holdout. Each row receives exactly one out-of-fold prediction.

**Aggregation**: Pool predictions; report RMSE, MAE, and R² = 1 − SSE_pooled / SST_full_sample.

### Nested Elastic Net

**Purpose**: Regularized prediction with both L1 and L2 penalties, nested cross-validation, and weighted observations.

**Feature Construction**: Build effective raw, transformed, squared, and interaction features in declared order. Scale using training-only weighted mean and weighted population SD; center y by its training weighted mean without scaling y.

**Objective**: Minimize Σᵢ wᵢ(yᵢ − Zᵢb)² / (2 Σᵢ wᵢ) + λ[α Σⱼ |bⱼ| + (1−α) Σⱼ bⱼ²/2].

**Solver**: Cold-start b=0 for every penalty and fold; never warm-start. In cyclic feature order, set ρⱼ = Σᵢ wᵢ Zᵢⱼ (yᵢ − Σ_{l≠j} Zᵢₗ bₗ) / Σᵢ wᵢ and bⱼ = S(ρⱼ, λα) / (1 + λ(1−α)), where S(a,t) = sign(a)·max(|a|−t, 0). Stop after a complete cycle when max coefficient change is below the effective tolerance or at the effective cycle cap.

**Selection**: For each penalty, pool unweighted inner validation squared errors across rows and take RMSE. Choose smallest RMSE then smaller penalty. Cold-refit on all outer-training rows and predict the outer holdout. Determine nonzero coefficients with the effective numerical cutoff. Aggregate OOF metrics from the single prediction per row.

### Wild Cluster Bootstrap

**Purpose**: Finite-sample cluster-robust inference via restricted-null wild bootstrap with reproducible PRNG.

**Observed Statistics**: Studentize the target coefficient using cluster CR1 standard errors. Fit the restricted model without the target and retain fitted values and residuals.

**PRNG — PCG32 or Xorshift32**: Use the PRNG declared by the effective request.

- **PCG32**: Unsigned wraparound with 64-bit state and 32-bit output. Increment = 2×stream + 1. Initialize state to zero, advance, add the effective initialization value modulo 2⁶⁴, and advance. Each advance: old = state, state = old × 6364136223846793005 + increment mod 2⁶⁴, xorshifted = low32(((old >> 18) xor old) >> 27), rot = old >> 59, output = rotate_right_32(xorshifted, rot). Map output modulo 6 to weights: [−√(3/2), −1, −√(1/2), √(1/2), 1, √(3/2)].

- **Xorshift32**: x ^= x << 13, x ^= x >> 17, x ^= x << 5, masking to 32 bits after each xor. Map low bit 1 to +1, otherwise −1 (or odd state to +1, even to −1).

**Draw and Refit**: Maintain one continuous generator across all replicates. For each replicate, draw once per cluster in entity-code (or ascending state) order. Set y* = restricted_fit + restricted_residual × cluster_weight. Refit the unrestricted model, recompute CR1, and studentize. Record checkpoints only after their completed replicate, without resetting the stream.

**Test and Aggregation**: Count absolute t* ≥ |t_observed| (with effective comparison tolerance δ if declared: count t* ≥ t_observed − δ). Report plus-one p = (count + 1) / (1 + B). For sorted values x and probability p:
- Nearest-rank: x[min(B, ⌈p·B⌉) − 1] using one-based rank.
- Type-seven: h = (B−1)·p, j = ⌊h⌋, γ = h−j, result = (1−γ)·x[j] + γ·x[j+1] using zero-based indexing.
- Bootstrap-t CI: observed_coef ± q_{1−α/2} × observed_SE.

### Grouped Split/State Conformal Prediction

**Purpose**: Distribution-free prediction intervals with group-structured calibration.

**Method**:
1. For each ordered outer group, hold it out as test. Designate one group as calibration (by greatest row count then ascending group name for division-based; by registered preceding partition for cyclic; or all non-test folds for fold-based). All remaining groups form the proper training set.
2. Fit the effective model (ridge with fixed penalty, or elastic net with selected penalty) from scratch with identical training-only scaling and solver rules.
3. Compute absolute prediction residuals on calibration rows.
4. With m sorted calibration scores and effective miscoverage α, use one-based r = min(m, ⌈(m+1)(1−α)⌉) and radius q = score[r].
5. For state-grouped conformal: reduce calibration residuals to one maximum absolute residual per calibration state before ranking.

**Intervals**: Prediction ± q, inclusive on both sides.

**Aggregation**: Report fold/state coverage, mean interval width, and absolute error. Pool covered and row counts. Use held-out row counts as weights for mean width. Select worst coverage by smallest fraction then earlier group order.

### Trajectory PCA Clustering

**Purpose**: Dimensionality reduction and clustering of entity trajectories over time, with leave-period-out stability assessment.

**PCA**:
1. Build columns in effective variable-major/time-major order, organized by entity (ASCII order).
2. Standardize each column by active-sample sample standard deviation.
3. Form covariance C = Z′Z / (n−1) or Z′Z / n (per effective convention).
4. **Symmetric Jacobi eigendecomposition**: Select the largest absolute upper-triangle off-diagonal, tie-breaking by lower row then column. τ = (A_qq − A_pp) / (2A_pq), t = sign_nonnegative(τ) / (|τ| + √(1+τ²)), c = 1/√(1+t²), s = t·c, rotate A and eigenvectors, stop at the effective off-diagonal tolerance or step cap.
5. Order eigenvalues descending, then by original diagonal index for ties.
6. Flip each loading so its earliest maximum-absolute entry is positive.
7. Scores = Z × loadings.

**K-means Clustering**:
1. First center is the ASCII-first entity.
2. Each next center is the entity maximizing distance to its nearest center; tie-breaking by entity code.
3. Assign to nearest center by squared Euclidean distance; tie-breaking by lower working cluster id.
4. Update centers by member means.
5. Stop when assignments are unchanged and centers are within tolerance, or at the effective cap.
6. For empty clusters: move the ASCII-first entity among those farthest from its assigned center into the empty cluster.
7. Canonicalize final ids by centroid coordinates then working id.

**Stability**:
1. For each omitted time block in ascending order, delete that complete variable block.
2. Rebuild scaling, PCA orientation, initialization, and clustering from scratch.
3. Compute adjusted Rand index (ARI) from the contingency table:
   ARI = (Σᵢⱼ C(nᵢⱼ, 2) − expected) / (½(Σᵢ C(aᵢ, 2) + Σⱼ C(bⱼ, 2)) − expected)
   where expected = Σᵢ C(aᵢ, 2) × Σⱼ C(bⱼ, 2) / C(n, 2).
4. Align refit labels by maximum agreement, tie-breaking to the lexicographically smallest permutation.
5. Report minimum ARI across leave-period-out fits.

### Difference GMM / Two-Step GMM

**Purpose**: Instrumented estimation for panel data with cluster-robust inference.

**First-Step**: Residualize outcome, dynamic regressors, and instruments against intercept plus effective baseline terms. Moments g(θ) = Z′(y − Dθ)/n with identity weight.

**Second-Step**: Build state cluster scores s_g = Z_g′ u_g and S = Σ_g(s_g s_g′)/n. Second-step weight W is the registered Moore-Penrose inverse of S, computed with the effective relative singular-value cutoff. Solve second-step θ̂ from weighted linear moments. Hansen J = n·g(θ̂)′Wg(θ̂).

**Cluster-Robust Inference**: For cluster scores q_g = Z_g′ u_g, use the registered finite-sample cluster sandwich. For indirect effects θ = a·b, compute Var(θ) = b²Var(a) + a²Var(b) + 2ab·Cov(a,b). Use Student-t inference with cluster degrees of freedom.

**First-Stage Diagnostics**: Compute partial F from full-versus-reduced residual sums of squares using the effective instrument counts.

**Delete-State Diagnostics**: For each state deletion, rebuild rows and refit all affected equations from scratch in state order.

### Partial R² Sensitivity (Mediation)

**Purpose**: Assess sensitivity of indirect effects to unobserved confounding.

**Method**:
1. From unrounded baseline a, b, SE_b, and residual df, compute magnitude = SE_b × √(df × rY × rM / (1 − rM)).
2. For each declared direction (positive/negative), adjusted_b = b − s × magnitude, adjusted_indirect = a × adjusted_b, adjusted_direct = total − adjusted_indirect, proportion = adjusted_indirect / total.
3. Enumerate the complete effective surface in declared R² and direction order.
4. Compute the equal-strength positive tipping root from unrounded inputs.

### Source/Year/Source-Group Perturbation

**Purpose**: Assess stability of estimates to alternative data sources, time subsets, or removal of feature groups.

**Source Perturbation (State-Level)**:
1. Resolve alternate outcomes with the module's effective release filters and greatest-revision/latest-release/greatest-id precedence.
2. Order paired entities by descending absolute alternate-minus-primary difference, tied by entity code.
3. For each of 2^m replacement masks, replace entity j iff the j-th bit is set. Retain fixed weights and design, then refit.
4. Relative shift = 100 × |(b_mask − b_zero) / b_zero|.
5. For each popcount stratum, report scenario count, coefficient range, p-value range, and mean shift.
6. Compute Shapley effects: φⱼ = Σ_{S not containing j} |S|!(m−|S|−1)!/m! × [b(S∪{j}) − b(S)], preserving signed order. Verify Σⱼ φⱼ = b(all) − b(none) within numerical tolerance.

**Year Subset Perturbation**:
1. Enumerate effective time subsets by increasing subset size and lexicographic tuple order.
2. For each subset, refit the complete model (with primary and parallel series if declared), recomputing cluster-robust inference.
3. Shift = |b_alt − b| / |b| × 100. Same-sign requires both nonzero with identical sign.
4. Report median shift, maximum shift, and worst subset by greatest unrounded shift then earlier subset order.

**Source-Group Perturbation**:
1. For each declared source group and outer fold, remove exactly that group's terms and reuse that fold's selected hyperparameters without retuning.
2. Apply identical preprocessing and solver; retain all outer-fold RMSEs.
3. Deterioration = pooled RMSE − reference full-model OOF RMSE.
4. Rank groups by decreasing unrounded deterioration, then declared group order.

### Controlled Decision

**Purpose**: Synthesise module results into a structured audit conclusion.

**Method**:
1. Complete every evidence module first.
2. Evaluate every effective business predicate on **unrounded** values.
3. Count satisfied predicates for each module.
4. Apply the effective request's controlled decision mapping and precedence/tie rules.
5. The decision output uses only the approved enum values and vocabulary from the template.

**Precedence**: When the decision identifies the first module that fails a predicate, modules are evaluated in the declared precedence order, not execution order. If no module fails, the conclusion reflects full transportability.

## Answer Template Contract

The answer must:
1. Be a single JSON object — no narrative, commentary, or markdown outside it.
2. Conform exactly to the key names, nesting, and types declared in `answer_template.json`.
3. Preserve every declared array order: state abbreviations, feature names, coefficient vectors, grid values, checkpoints, division/region names, and source groups.
4. Report numeric values at the precision shown in the standard answer format (typically 4 decimal places for coefficients and statistics, integers for counts, and the declared precision for p-values).
5. Use only the controlled vocabulary for enum fields (e.g., `PASS`/`FAIL`, `true`/`false`, `NO_TRANSPORTABLE_LONGEVITY_SIGNAL`, classification labels).
6. Include the `protocol_registry_record.portable_protocol_profile` section when the task's protocol is registered — this carries method semantics only and describes how a future request would activate and customize the profile, not the current task's specific values.

## Answer Assembly Rules

### Cardinality and Cross-Referencing

The answer template often specifies cross-references between arrays. For example:
- `state_order` length must equal `state_n`.
- Delete-cluster coefficients must align positionally with the cluster order.
- Bootstrap weight/index rows must have one column per state/entity in the declared order.
- PCA scores and cluster labels must align positionally with the state/entity order.

When the template says "complete exclusion set" or "complete balanced cohort," every matching entity must appear exactly once — no more, no fewer. When the template says "ascending ASCII" or "ascending," sort by the string or integer key, respectively. When the template says "registered order" or "declared order," reproduce the order from the request or from the portal's own ordering — never re-sort.

### Protocol Registry Record Placement

For tasks that activate a registered protocol, the answer includes a `protocol_registry_record` (or it is placed as optional solved-answer provenance). This section describes the **method profile** — how the protocol activates, how overrides resolve, the instance boundary, module execution order, and the reusable algorithm descriptions. It does **not** contain any task-specific solved values (no coefficients, no p-values, no entity lists, no counts). It exists to make the method transportable to a future invocation with a different analysis request.

When the answer template does not list `protocol_registry_record` as a required top-level key, the protocol profile may be placed outside the template-required keys or omitted — follow the template's required keys list exactly.

### Precision Discipline

- **Computed non-integers**: Report at the decimal places declared in the request's `reporting` section (commonly 4 or 6 decimal places).
- **Literal values carried from the request**: Use the precision they arrived with (e.g., grid values, alpha, nominal coverage).
- **Counts, ranks, seeds, PRNG states, replicate numbers**: Always integers.
- **Boolean fields**: JSON `true` or `false`, never strings.
- **Never use**: `NaN`, `Infinity`, or string representations of numbers.

## Execution Checklist

1. **Read** `payloads/analysis_request.json` and `payloads/answer_template.json` completely.
2. **Fetch** `GET /catalog` and `GET /methodology` from the portal to understand available measures, value types, releases, and geography codes.
3. **Fetch** `GET /data/revisions` to understand revision history and identify the applicable revision events.
4. **Resolve** the effective contract: match `protocol_id`, apply any overrides, freeze one contract before any computation.
5. **Fetch** data from the relevant `/data/*` and `/geographies/*` endpoints. Download all years, entities, and measures declared in the request — don't pre-filter server-side in ways that might omit records needed for revision resolution.
6. **Resolve releases and construct cohorts**:
   - Apply the effective release priority (greatest revision → latest release timestamp → lowest record id).
   - Mark suppressed/invalid/null values as unavailable.
   - Build each declared analytic set (primary, balanced, broad, dual-source, ML-complete).
   - Count publications before analytic exclusions when the request asks for raw totals.
7. **Execute** each declared module in the declared order:
   - Fit models with the exact random seeds, hyperparameter grids, and solver settings from the request.
   - Maintain exact reproducibility: PRNG streams advance continuously across replicates; fold orders are fixed; tie-breaking rules are deterministic.
   - Record every checkpoint at its declared replicate, without resetting generator state.
8. **Evaluate** controlled decision predicates on **unrounded** values from module outputs. Apply the declared precedence — the first failing module in precedence order determines the conclusion.
9. **Assemble** the answer JSON conforming to the template's required keys, types, array lengths, and enum values.
10. **Validate** before submission:
    - Every required key present; no extra keys beyond the template.
    - Array cardinality matches declared lengths and cross-references.
    - Array ordering matches the declared convention.
    - Numeric precision matches the reporting specification.
    - Enum and Boolean fields use only the allowed values.
