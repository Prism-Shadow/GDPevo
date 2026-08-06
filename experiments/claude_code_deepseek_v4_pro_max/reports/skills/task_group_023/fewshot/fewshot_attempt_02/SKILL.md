# Public Health Observatory Algorithmic Audit Skill

Activate when a task references a Public Health Observatory (`PHO_*`) protocol, an `analysis_request.json` paired with an `answer_template.json`, or a registered algorithmic audit over health/socioeconomic evidence served from a read-only Observatory web portal.

## Overview

This skill executes registered algorithmic audits for the Public Health Observatory. Every audit follows the same pattern:

1. Read the three input artifacts: the task prompt, `analysis_request.json`, and `answer_template.json`.
2. Access the Observatory web portal at the base URL specified in the task (typically the `<TASK_ENV_BASE_URL>` placeholder) using only the allowed endpoints.
3. Resolve evidence — publication records, releases, revisions — according to the effective request's filters.
4. Execute each declared audit module in the registered order, applying the exact method specification.
5. Construct a single JSON output object conforming to the answer template, preserving every declared order, identifier, precision, and type.
6. Evaluate the controlled decision gates and return the mandated classification.

## Input Artifacts

### analysis_request.json

The formal protocol specification. Key structural sections:

- **Identity**: `request_id`, `protocol_id`, `business_task` — use `protocol_id` for method-profile activation; never activate on family or similarity.
- **Scope**: `geography_scope`, `analysis_years`, `reference_year`, `regions` — the time, space, and entity bindings for this invocation.
- **Outcome, exposure, mediator, covariates**: The variable bindings for the statistical models.
- **Evidence specification**: Filter rules (`release_status`, `value_type`, `source_type`), validity exclusions (`invalid_quality_flags`), missing-value rules (suppressed/invalid/blank values are unavailable and never zero-filled), cohort definitions.
- **Audit modules**: Ordered named modules, each with `method`, `cohort`, cluster/group definitions, feature/predictor orders, hyperparameter grids, seed/stream/replicate schedules, and `required_evidence`.
- **Robustness gates / decision rules**: Predicates evaluated on unrounded values; controlled classification mappings with precedence.

#### Override resolution (advanced)

When the request includes `_overrides` suffixed keys or direct rebindings, resolve one effective contract before any data access:

- A direct root key `k` binds to canonical root `k`; inside a named section/module, a child key targets only the identical child path.
- A root key named `<section>_overrides` targets canonical `<section>`; `module_overrides.<module_name>` targets that exact top-level module. Strip only the terminal `_overrides` suffix.
- Merge in request document order: objects merge recursively by exact key; arrays replace whole; scalars/strings/Booleans/null replace only at their exact path; absent paths inherit unchanged.
- Reject unknown targets, type coercion, implicit aliases, array concatenation, and positional patching.
- Task-local direct bindings and resolved overrides take precedence over inherited values at the same path.

### answer_template.json

The output contract. Defines `required_top_level_keys`, field-by-field types, array lengths, numeric precision (typically 4 decimal places for non-integers), identifier conventions (uppercase two-letter state codes, portal division names, ISO3 codes sorted ascending), and strict ordering rules. Also defines controlled enum values for gate states and classifications.

**Critical rules**:
- Never reorder declared lists — preserve the exact order from the analysis request.
- Align positionally — when a cardinality rule says "must match state_order", values must appear in the same sequence.
- Use JSON null only for mathematically unavailable statistics; never NaN or Infinity.
- Round non-integers to the declared decimal places (encode as JSON numbers).
- Counts, seeds, PRNG states, replicate numbers, and fold numbers are integers.

## Portal Evidence Access

The portal is read-only. Retrieve evidence by issuing HTTP GET requests to the enumerated endpoints in `environment_access.md`.

### Endpoint reference

| Endpoint | Content |
|---|---|
| `GET /` | Portal root / health check |
| `GET /catalog` | Available datasets and measures |
| `GET /geographies/states` | State code/name mappings |
| `GET /geographies/counties` | County FIPS, name, state, RUCC codes |
| `GET /geographies/countries` | Country names, ISO3, region codes |
| `GET /data/state-health` | State-level health measures |
| `GET /data/state-socioeconomic` | State-level socioeconomic data |
| `GET /data/county-health` | County-level health measures |
| `GET /data/county-socioeconomic` | County-level socioeconomic data |
| `GET /data/country-indicators` | Country-level development/burden indicators |
| `GET /data/revisions` | Revision event records |
| `GET /data/methodology` | Measure definitions and metadata |
| `GET /download` | Bulk data access |

### Evidence resolution

For every requested measure and geography:

1. **Filter** by the effective status, source type, value type, validity flags, and geography bindings from the request.
2. **Select one record per entity-time-measure key** using the declared revision priority: greatest revision number, then latest `released_at` timestamp, then lowest record/observation identifier.
3. **Count** selected publications before analytic completeness exclusions when the template requests publication counts.
4. **Treat suppressed, invalid, withdrawn, blank, or null analytic values as unavailable** — they are never zero-filled.
5. **Join resolved series** by the effective stable entity and time keys. Preserve entity-code then time order.

## Reusable Audit Module Methods

The answers reveal a registry of standard methods. When a future request references one of these by name, apply the corresponding method specification below. If a request introduces a new method name not listed here, execute it as literally specified in that request — these profiles are a starting point, not a closed set.

### Release resolution and cohort construction

Filter each publication key independently. Count selected publications before completeness exclusions. Construct cohorts from effective nonmissing and validity predicates:

- **Complete case**: All required analytic fields are present, nonsuppressed, non-null, and pass validity flags.
- **Balanced panel**: Entity is complete-case in every requested year.
- **Broad/ML cohort**: Reference-year complete cases that are also complete on expanded covariate sets.
- **Strict dual-source**: Complete for outcome, primary exposure, parallel/secondary exposure, and all adjustments in every analysis year.

Preserve declared entity, time, feature, and cluster order throughout.

### Delete-cluster fixed effects / jackknife

**Transform**: For each modeled variable, compute \\(z_{it} = x_{it} - \bar{x}_{i\cdot} - \bar{x}_{\cdot t} + \bar{x}_{\cdot\cdot}\\) (entity-demeaned, time-demeaned, grand mean added back). Solve OLS without an intercept in declared predictor order.

**Delete-one**: Remove the whole cluster, recompute every mean, and refit from scratch in entity-code order.

**Jackknife inference**: For \\(G\\) delete estimates \\(b_{-g}\\) and mean \\(\bar{b}\\):
\\[SE_{JK} = \sqrt{\frac{G-1}{G} \sum_g (b_{-g} - \bar{b})^2}\\]
\\[b_{BC} = G \cdot b - (G-1) \cdot \bar{b}\\]

Test \\(b_{BC} / SE_{JK}\\) with two-sided Student-t and \\(G-1\\) degrees of freedom. Select extrema by coefficient then entity code.

### Nested ridge / elastic-net cross-validation

**Folds**: Hold out one outer group; within each outer training set, hold out every remaining group once in the same order.

**Scaling**: Per fit, compute training-only feature means and sample/population standard deviations (ddof=1 for ridge, population for elastic-net); apply to validation/test rows. Center the outcome by its training mean.

**Ridge solver**: Minimize \\(\text{mean}((y - Xb)^2) + \lambda \sum_j b_j^2\\), intercept unpenalized. Cycle in declared feature order: \\(b_j = \frac{\sum_i x_{ij} r_{ij}}{\sum_i x_{ij}^2 + n\lambda}\\) where \\(r\\) excludes feature \\(j\\). Stop at max-change tolerance or sweep cap.

**Elastic-net solver**: Minimize \\(\frac{\sum_i w_i (y_i - Z_i b)^2}{2\sum_i w_i} + \lambda\left[\alpha\sum_j |b_j| + \frac{1-\alpha}{2}\sum_j b_j^2\right]\\). Cold-start all coefficients at zero. Cyclic update: \\(b_j = \frac{S(\rho_j, \lambda\alpha)}{1 + \lambda(1-\alpha)}\\) with \\(S(a,t) = \text{sign}(a)\max(|a|-t, 0)\\) and \\(\rho_j = \frac{\sum_i w_i Z_{ij}(y_i - \sum_{l\neq j} Z_{il}b_l)}{\sum_i w_i}\\).

**Selection**: Pool inner validation squared errors at row level, take RMSE, choose smallest RMSE then smaller penalty (and then smaller alpha, then smaller l1-ratio for elastic-net). Refit on all outer-training rows and predict all outer rows.

**Aggregation**: Pool exactly one outer prediction per eligible row. Report RMSE, MAE, and \\(R^2 = 1 - \frac{SSE}{\sum_i (y_i - \bar{y}_{\text{full}})^2}\\) (or \\(Q^2\\) for ridge). Determine nonzero coefficients with the effective numerical cutoff.

### Wild cluster bootstrap

**Observed**: Fit the full model, compute cluster-robust standard errors:
\\[V_{CR1} = \frac{G}{G-1} \cdot \frac{n-1}{n-k} \cdot (X'X)^{-1} \sum_g (s_g s_g') (X'X)^{-1}\\]
where \\(s_g = X_g' e_g\\). Studentize the target coefficient: \\(t = b / \sqrt{V_{CR1}[j,j]}\\).

**Restricted model**: Remove the target predictor, fit, retain fitted values and residuals in entity order.

**PRNG**: Use the declared generator:
- **PCG32**: 64-bit state, 32-bit output. Let increment = \\(2 \cdot \text{stream} + 1\\). Initialize state to zero, advance, add the seed modulo \\(2^{64}\\). Each advance: \\(\text{state} = \text{old} \cdot 6364136223846793005 + \text{increment} \pmod{2^{64}}\\); xorshifted = low32 of \\(((\text{old} \gg 18) \oplus \text{old}) \gg 27\\); rot = \\(\text{old} \gg 59\\); output = rotate-right-32(xorshifted, rot). Map to weights by the declared scheme.
- **XorShift32**: \\(x \mathbin{\oplus}= x \ll 13\\), \\(x \mathbin{\oplus}= x \gg 17\\), \\(x \mathbin{\oplus}= x \ll 5\\), masking to 32 bits after each xor. Map low bit: 1 → +1, 0 → -1 (or odd → +1, even → -1).

**Resampling**: Maintain one continuous generator. For each replicate, draw once per cluster in entity-code order. Form \\(y^* = \hat{y}_{\text{restricted}} + e_{\text{restricted}} \cdot w_{\text{cluster}}\\). Refit the unrestricted model, recompute CR1, and studentize.

**Inference**: Two-sided absolute exceedances: \\(p = \frac{1 + |\{|t^*| \ge |t_{\text{obs}}|\}|}{1 + B}\\). For sorted values \\(x\\) and probability \\(p\\), nearest-rank quantile is \\(x_{[\min(B, \lceil p \cdot B \rceil)] - 1}\\) (one-based rank). Record checkpoints after their completed replicate without resetting the stream.

### Grouped split conformal calibration

**Partition**: For each ordered outer group, use it as the test set. Choose the calibration group from remaining groups by greatest row count then ascending group name. Use all others for proper training.

**Fit**: Train the declared model from scratch with the effective penalty and identical scaling/solver rules.

**Intervals**: Sort \\(m\\) absolute calibration residuals. With effective miscoverage \\(\alpha\\), use one-based rank \\(r = \min(m, \lceil (m+1)(1-\alpha) \rceil)\\) and radius \\(q = \text{score}[r]\\). Symmetric inclusive intervals: \\([\hat{y} - q, \hat{y} + q]\\).

**Aggregation**: Report fold coverage (fraction of test rows inside interval), mean width (\\(2q\\)), and MAE. Aggregate overall coverage and width by outer-test row counts. Choose worst by smallest coverage fraction then earlier group order.

### Trajectory PCA and clustering

**PCA**: Build columns in declared variable-major/time order. Standardize each column by active-sample standard deviation with ddof=1. Form covariance matrix \\(C = Z'Z / (n-1)\\).

**Eigendecomposition — symmetric Jacobi**: Select the largest absolute upper-triangle off-diagonal, tying by lower row then column. \\(\tau = (A_{qq} - A_{pp}) / (2A_{pq})\\), \\(t = \text{sign}(\tau) / (|\tau| + \sqrt{1 + \tau^2})\\), \\(c = 1/\sqrt{1+t^2}\\), \\(s = t \cdot c\\). Rotate \\(A\\) and eigenvectors. Stop at the off-diagonal tolerance or step cap.

**Ordering and orientation**: Order eigenvalues descending, then by original diagonal index on ties. Flip each loading vector so its earliest maximum-absolute entry is positive. Scores = \\(Z \times \text{loadings}\\).

**K-means clustering**: Use squared Euclidean distance on the effective leading scores.
- First center: ASCII-first entity.
- Each next center: entity maximizing minimum distance to existing centers, tied by entity code.
- Assignment: nearest center, tied by lower working id.
- Update: arithmetic member means.
- Convergence: unchanged assignments or iteration cap. Reassign empty clusters by moving the ASCII-first entity farthest from its assigned center.
- Canonicalize final ids by centroid coordinates then working id.

**Stability — leave-one-out**: For each omitted time block in ascending order, rebuild scaling, PCA, orientation, initialization, and clustering from scratch. Compute adjusted Rand index:
\\[ARI = \frac{\sum_{ij} \binom{n_{ij}}{2} - E}{0.5(\sum_i \binom{a_i}{2} + \sum_j \binom{b_j}{2}) - E}\\]
where \\(E = \frac{\sum_i \binom{a_i}{2} \sum_j \binom{b_j}{2}}{\binom{n}{2}}\\). Align refit labels by maximum agreement, tying to lexicographically smallest permutation.

### Source/feature perturbation

**Enumeration**: Enumerate effective subsets in increasing subset size then lexicographic tuple order. Keep the effective analytic set unchanged. For each subset, refit the complete model from scratch, recomputing standard errors and inference.

**Aggregation**: Shift = \\(100 \cdot |b_{\text{alt}} - b| / |b|\\) (percent). Same-sign requires both nonzero with identical sign. Compute the ordinary median of ordered shifts. Choose worst by greatest unrounded shift, then earlier subset order (or smaller mask).

**Shapley** (when requested): For ordered entity \\(j\\), \\(\phi_j = \sum_{S \not\ni j} \frac{|S|! (m - |S| - 1)!}{m!} [b(S \cup \{j\}) - b(S)]\\). Preserve signed \\(\phi\\) order and verify \\(\sum_j \phi_j = b(\text{all}) - b(\text{none})\\).

### GMM / instrumental variables

**Difference GMM**: Create adjacent-change rows in entity then end-period order. For each equation: \\(W = (Z'Z)^{-1}\\), \\(\hat{\beta} = (X'Z W Z'X)^{-1} X'Z W Z'y\\). Cluster scores \\(q_g = Z_g' u_g\\); use the registered finite-sample cluster sandwich. For two-equation systems, use the corresponding cross-cluster score product.

**Two-step linear GMM**: First-step identity weight. Build state scores \\(s_g = Z_g' u_g\\) and \\(S = \sum_g (s_g s_g') / n\\). Second-step weight = Moore-Penrose pseudoinverse of \\(S\\), with registered relative singular-value cutoff. Hansen \\(J = n \cdot g(\hat{\theta})' W g(\hat{\theta})\\).

**Indirect effect**: For \\(\theta = a \cdot b\\), \\(\text{Var}(\theta) = b^2 \text{Var}(a) + a^2 \text{Var}(b) + 2ab \text{Cov}(a,b)\\). Student-t inference with cluster degrees of freedom.

**First-stage diagnostics**: Partial F from full-versus-reduced residual sums of squares using effective instrument counts.

### Partial R² sensitivity surface

From unrounded baseline \\(a\\), \\(b\\), \\(SE_b\\), and residual df:
- Magnitude = \\(SE_b \cdot \sqrt{df \cdot r_Y \cdot r_M / (1 - r_M)}\\)
- For each declared direction: \\(b_{\text{adj}} = b \mp s \cdot \text{magnitude}\\), \\(\text{indirect}_{\text{adj}} = a \cdot b_{\text{adj}}\\), \\(\text{direct}_{\text{adj}} = \text{total} - \text{indirect}_{\text{adj}}\\), \\(\text{proportion} = \text{indirect}_{\text{adj}} / \text{total}\\).
- Enumerate the complete surface in declared \\(R^2\\) and direction order.

### Weighted least squares with HC3

For design \\(X\\), outcome \\(y\\), and positive weights \\(w\\):
- \\(X_w = \text{diag}(\sqrt{w}) \cdot X\\), \\(y_w = \text{diag}(\sqrt{w}) \cdot y\\)
- \\(b = (X_w' X_w)^{-1} X_w' y_w\\) in declared column order.
- \\(h_i = \text{diag}(X_w (X_w' X_w)^{-1} X_w')\\), \\(e_{w,i} = \sqrt{w_i} (y_i - X_i b)\\)
- \\(V_{HC3} = (X_w' X_w)^{-1} X_w' \cdot \text{diag}\left(\frac{e_{w,i}^2}{(1-h_i)^2}\right) \cdot X_w (X_w' X_w)^{-1}\\)
- Two-sided Student-t with \\(n-k\\) residual degrees of freedom.

### Source-group perturbation

For each declared source group and outer fold in order: remove exactly the group's terms, reuse that fold's full-model selected hyperparameters without retuning, apply identical preprocessing and solver. Pool squared errors across folds for RMSE. Deterioration = group RMSE minus full-model OOF RMSE. Count folds where the group RMSE exceeds the corresponding full-model fold RMSE. Rank groups by decreasing unrounded deterioration, then declared group order.

## Controlled Decision

Execute after all evidence modules are complete:

1. Evaluate every effective business predicate (gate) on **unrounded values**.
2. Preserve the declared module order for gate reporting.
3. Count satisfied predicates.
4. Apply the effective request's precedence rules: if the rule says "ALL must pass," check every gate. If it says "first failed module," scan the declared order and stop at the first unsatisfied gate.
5. Return the mandated classification string from the effective request's controlled vocabulary.

Never second-guess or override the request's decision mapping. The classification values are exact enum strings from the request/template.

## Output Construction

1. Start with the required top-level keys from `answer_template.json`.
2. For each key, produce exactly the fields the template declares. Omit `template_instructions` or `description` keys from the output.
3. Preserve every array order — align positionally when cardinality rules say "must match state_order" or "values must align positionally."
4. Report numeric values at declared precision (use `toFixed` or equivalent rounding, encode as JSON numbers). Counts, seeds, PRNG states, and replicate numbers are integers.
5. Use uppercase two-letter state codes, portal division/country names exactly, and ascending ASCII sort for set-like identifier lists.
6. Use JSON null only when a requested statistic is mathematically unavailable (e.g., undefined ratio, empty set).
7. Include the `protocol_registry_record` at the top of the output only if the template reserves a key for it — otherwise do not include it. When including it, carry forward the reusable method profiles as shown in the reference answers; never carry task-local values or solved analytical values across invocations.

## Execution Checklist

Before beginning computation:

- [ ] Read `analysis_request.json` and `answer_template.json` completely.
- [ ] Resolve any overrides to produce one frozen effective request.
- [ ] Identify the protocol_id for method-profile activation.
- [ ] Confirm the portal base URL from the task prompt.
- [ ] Note the declared module execution order.
- [ ] Note every seed, stream, replicate count, hyperparameter grid, feature order, and group order — these are binding.
- [ ] Understand each gate predicate and the controlled classification mapping.

During computation:

- [ ] Fetch evidence from the portal using only the declared filters and revision priorities.
- [ ] Execute modules in the registered order — later modules may depend on earlier module results (e.g., conformal calibration reuses nested predictions).
- [ ] Do not warm-start across folds or penalties unless explicitly instructed.
- [ ] Preserve random generator state continuity — one continuous stream per bootstrap; record checkpoints after their completed replicate without resetting.
- [ ] Use unrounded values for all intermediate decisions; only round at output time.

Before submitting:

- [ ] Verify every required key is present.
- [ ] Verify every array has the declared length.
- [ ] Verify positional alignment for all cardinality-constrained arrays.
- [ ] Verify rounding to declared decimal places.
- [ ] Verify controlled vocabulary match for all enum fields.
- [ ] Verify no narrative text outside the JSON object.
