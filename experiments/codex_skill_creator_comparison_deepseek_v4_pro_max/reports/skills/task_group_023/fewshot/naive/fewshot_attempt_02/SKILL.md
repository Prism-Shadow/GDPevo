---
name: pho-algorithmic-transport-audit
description: Solve Public Health Observatory algorithmic transport audit tasks by resolving evidence from the PHO Web portal, applying registered statistical audit modules, and producing controlled-decision JSON output conforming to the supplied answer template.
---

# Public Health Observatory Algorithmic Transport Audit

This skill covers solving PHO-brokered algorithmic audit tasks. A task arrives as a
prompt referencing `<TASK_ENV_BASE_URL>` and two payload JSON files:
`analysis_request.json` (the audit specification) and `answer_template.json` (the
output contract).

## Step 1: Resolve the task environment

Read `environment_access.md` in the workspace root. It provides the base URL (e.g.
`http://task-env:9023/`) and the list of allowed endpoints. Use GET requests only;
the portal is read-only. The base URL must replace every `<TASK_ENV_BASE_URL>`
placeholder.

## Step 2: Read the input payloads

Read `prompt.txt`, `analysis_request.json`, and `answer_template.json` from the
task's `input/` directory. The analysis request contains:

- `protocol_id` -- identifies which registered method profile governs the audit
- Business task description (geography, years, measures, cohorts, module specs)
- `reporting` section (decimal places, output contract)
- `robustness_gates` or `decision_rule` section
- Optional `override_resolution` rules

The answer template is the exact JSON shape to return, with field types,
cardinality rules, allowed enum values, and ordering constraints.

## Step 3: Apply the override system

Many requests support an override mechanism. Resolve one effective contract before
any data access or computation:

- Direct root keys bind to the identically named canonical key.
- A root key named `<section>_overrides` targets canonical `<section>` (strip the
  `_overrides` suffix).
- `module_overrides.<module_name>` targets that exact top-level module.
- Objects merge recursively by exact key. Arrays replace entirely. Scalars,
  Booleans, and null replace only at their exact path. Absent paths inherit
  unchanged.
- Task-local direct bindings and resolved overrides take precedence over inherited
  values at the same path.
- Reject unknown targets and incompatible types.
- Freeze one effective request contract and use it consistently in every module.

## Step 4: Fetch evidence from the portal

Every task uses the same general portal API pattern. Navigate from:
- `GET /` -- the root lists available endpoints
- `GET /catalog` -- catalog of available datasets and their schemas
- `GET /geographies/states`, `/geographies/counties`, `/geographies/countries` -- entity registries
- `GET /data/state-health`, `GET /data/county-health`, `GET /data/country-indicators` -- health data
- `GET /data/state-socioeconomic`, `GET /data/county-socioeconomic` -- socioeconomic data
- `GET /data/revisions` -- revision event log (APPLIED vs non-APPLIED events)
- `GET /methodology` -- measure definitions and metadata
- `GET /download` -- bulk data export
- `GET /health` -- portal health check

**Release resolution (universal pattern)**:
For each requested publication key (dataset, measure, geography, time), filter by
the effective status, source type, value type, and validity flags. Select the
record with the greatest revision number, then the latest release timestamp, then
the lowest record identifier. Suppressed, invalid, withdrawn, blank, or null
analytic values are unavailable and never zero-filled.

**Data semantics**:
- State data uses two-letter uppercase postal codes (`state_code`).
- County data uses composite county identifiers. RUCC codes are integers 1-9.
- Country data uses uppercase ISO3 codes (`iso3`). Country labels may be aliases
  that need resolution against the `/geographies/countries` registry.
- Census divisions are the nine standard U.S. divisions: East North Central, East
  South Central, Middle Atlantic, Mountain, New England, Pacific, South Atlantic,
  West North Central, West South Central.
- Regions are the four standard U.S. Census regions: Northeast, Midwest, South,
  West.
- Release status values: `FINAL`, `PROVISIONAL`.
- Value types: `AGE_ADJUSTED`, `CRUDE`.
- Source types: `DIRECT_SURVEY`, `COUNTY_ROLLUP`.

## Step 5: Execute audit modules in order

Every protocol defines a fixed module execution order. Complete each module in
sequence, using the effective request as the sole specification. The methods for
each protocol are documented in the [protocols/](protocols/) directory:

| Protocol ID | Reference |
|---|---|
| `PHO_STATE_TRANSPORT_AUDIT_V1` | [protocols/state_transport_v1.md](protocols/state_transport_v1.md) |
| `PHO_COUNTY_MEDIATION_TRANSPORT_V1` | [protocols/county_mediation_v1.md](protocols/county_mediation_v1.md) |
| `PHO_STATE_ROBUSTNESS_TRANSPORT_V1` | [protocols/state_robustness_v1.md](protocols/state_robustness_v1.md) |
| `PHO_COUNTY_PANEL_TRANSPORT_V1` | [protocols/county_panel_v1.md](protocols/county_panel_v1.md) |
| Country burden audits (no fixed protocol_id) | [protocols/country_burden.md](protocols/country_burden.md) |

If a future request arrives with a protocol_id not listed above, apply the methods
specified directly in its `analysis_request.json` audit modules.

## Step 6: Apply decision gates and produce output

After completing all modules, evaluate every effective business predicate on
unrounded computed values. Preserve the module order declared in the request's
`decision_rule` or `robustness_gates` section for gate reporting. Count satisfied
gates and select the controlled classification per the effective decision mapping.

**Output formatting**:
- Round non-integer statistics to the declared decimal places (typically 4 or 6).
  Encode them as JSON numbers; do not add trailing zeros beyond the JSON number
  literal.
- Counts, seeds, PRNG states, replicate numbers, and fold numbers are integers.
- Entity codes use the declared canonical form (uppercase state codes, ISO3,
  division names).
- Every ordered list preserves the exact order specified by the analysis request
  or answer template. Do not independently sort aligned result arrays.
- Use JSON `null` only when a requested statistic is mathematically unavailable.
  Never emit `NaN`, `Infinity`, or string representations of numbers.
- Return exactly one JSON object conforming to the answer template. Include no
  narrative outside the JSON. Omit any `template_instructions` or
  `protocol_registry_record` keys unless the template explicitly requires them.

## Common statistical primitives

Every protocol shares these reusable building blocks. Apply them as described in
the protocol-specific method profiles under [protocols/](protocols/).

**Double-demeaning (within transformation)**: For each variable in a panel, subtract
the entity mean, subtract the time mean, and add back the grand mean. Recompute
means after every entity deletion.

**Training-only standardization**: Inside each CV fold, compute feature means and
population standard deviations (ddof=1) from training rows only. Apply those
moments to validation/test rows. Center the outcome by its training mean without
scaling it.

**Ridge regression**: Minimize SSE + lambda * sum(beta_j^2) with unpenalized
intercept. For weighted ridge, minimize sum_i w_i * (y_i - ...)^2 / (2*sum w_i) +
lambda * sum beta_j^2. Initialize coefficients at zero, cycle features in declared
order updating each beta_j, and stop when max coefficient change is below tolerance
or at the sweep cap.

**Elastic net**: Minimize SSE/(2n) + alpha * [rho * sum|beta_j| + 0.5*(1-rho) *
sum beta_j^2]. Cold-start all non-intercept coefficients at zero. Update each
beta_j by soft-thresholding the partial residual correlation in declared feature
order. The intercept is updated by the mean residual each sweep.

**CR1 cluster-robust variance**: V_CR1 = [G/(G-1)] * [(n-1)/(n-k)] *
(X'X)^-1 * sum_g(s_g * s_g') * (X'X)^-1, where s_g = X_g' * e_g. Use
two-sided Student t with G-1 degrees of freedom. For weighted models, apply
weights to X and e before forming cluster scores.

**HC3 heteroskedasticity-robust variance**: V_HC3 = (X'X)^-1 * X' *
diag(e_i^2 / (1 - h_i)^2) * X * (X'X)^-1, with h_i = diag(X * (X'X)^-1 * X').
Use two-sided Student t with n-k residual degrees of freedom.

**Jackknife**: For G delete estimates b_-g and mean bbar: SE_JK =
sqrt((G-1)/G * sum_g(b_-g - bbar)^2), b_BC = G*b - (G-1)*bbar. Test b_BC/SE_JK
with two-sided Student t, G-1 df. Select extrema by coefficient then entity code.

**PCG32 PRNG**: 64-bit state, 32-bit output. Increment = 2*stream + 1. Initialize
state to zero, advance, add seed modulo 2^64, advance. Each advance: old = state,
state = old * 6364136223846793005 + increment mod 2^64, xorshifted = low32(((old
>> 18) xor old) >> 27), rot = old >> 59, output = rotate_right_32(xorshifted, rot).
Map output modulo 6 to [-sqrt(3/2), -1, -sqrt(1/2), sqrt(1/2), 1, sqrt(3/2)].

**xorshift32 PRNG**: Unsigned 32-bit state. Each call: x xor= x << 13, x xor= x >>
17, x xor= x << 5, truncating to 32 bits after each xor. Map low bit: 1 -> +1,
0 -> -1.

**Wild cluster bootstrap**: Fit restricted model (target excluded), retain fitted
values and residuals. For each replicate, draw one weight per cluster in entity
order, form y* = restricted_fit + restricted_residual * weight, refit unrestricted
model, recompute CR1, studentize. Use absolute-tail exceedances with plus-one
p-value = (count + 1) / (B + 1). Maintain one continuous PRNG stream; record
checkpoints after their completed replicate without resetting.

**Grouped split conformal**: For each outer group held out as test, select the
calibration group with greatest row count (tiebreak: ascending group name), use
remaining groups as proper training. Fit model on proper training, predict
calibration rows, pool absolute residuals. With m calibration scores, rank r =
min(m, ceil((m + 1) * (1 - alpha))), threshold q = score[r]. Build symmetric
inclusive intervals: prediction +/- q.

**Trajectory PCA**: Build variable-major/time-major feature matrix in declared
order, standardize columns by sample SD, form covariance C = Z'Z/(n-1). Use
symmetric Jacobi eigendecomposition: find largest absolute upper-triangle
off-diagonal, tiebreak by lower row then column; compute rotation and apply.
Sort eigenvalues descending; flip each loading so its earliest maximum-absolute
entry is positive; scores = Z * loadings.

**K-means clustering (deterministic)**: First center = ASCII-first entity. Each
next center = entity maximizing minimum distance to existing centers, tiebroken by
entity code. Assign to nearest center by squared Euclidean distance, tiebroken by
lower cluster id. Update centers to member means. Stop when assignments unchanged
or at iteration cap. Canonicalize final cluster ids by centroid coordinates then
working id. Handle empty clusters by reassigning the farthest entity from its
current center.

**Adjusted Rand Index (ARI)**: From contingency table n_ij: sum_ij C(n_ij, 2) -
expected / (0.5 * (sum_i C(a_i, 2) + sum_j C(b_j, 2)) - expected), where expected
= sum_i C(a_i, 2) * sum_j C(b_j, 2) / C(n, 2). Align refit labels by maximum
agreement, tiebreaking lexicographically.

**Exhaustive perturbation (source/year)**: For m binary substitution choices,
enumerate all 2^m masks. For year subsets, enumerate by increasing size then
lexicographic order. For each scenario, refit the unchanged model design and
compute the target inference. Compute relative percent shift from baseline:
100 * abs(b_alt - b_base) / abs(b_base). Same-sign requires both nonzero with
identical sign. Shapley value for entity j: sum_{S not containing j} |S|! *
(m - |S| - 1)! / m! * [b(S union {j}) - b(S)].

**Difference GMM**: For first-differenced panel equations, instruments are lagged
levels. First-step weight W = (Z'Z)^-1. Second-step uses the efficient weight from
clustered first-step residuals. For two-equation systems, compute cross-equation
covariance from cluster score cross-products. Hansen J = n * g(theta)' * W *
g(theta). Use Moore-Penrose pseudoinverse with a relative singular-value cutoff
for near-singular weight matrices.

**Partial-R2 mediation sensitivity**: From baseline path-a coefficient a, path-b
coefficient b, SE_b, and residual df: magnitude = SE_b * sqrt(df * rY * rM / (1 -
rM)). For each (rM, rY, direction) cell: adjusted_b = b - sign * magnitude,
adjusted_indirect = a * adjusted_b, adjusted_direct = total - adjusted_indirect,
proportion = adjusted_indirect / total. Equal-strength tipping R2 is the positive
root where the indirect effect crosses zero.

**Silhouette score**: For entity i in cluster C_I: a_i = mean distance to other
entities in C_I, b_i = min_{J != I} mean distance to entities in C_J. Silhouette_i
= (b_i - a_i) / max(a_i, b_i). Singleton silhouette = 0. Average across all
entities. Select the largest unrounded mean silhouette.
