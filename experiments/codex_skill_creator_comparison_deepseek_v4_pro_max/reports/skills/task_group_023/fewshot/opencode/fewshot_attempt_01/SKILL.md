---
name: pho-audit
description: Execute registered Public Health Observatory algorithmic transportability and robustness audits using a read-only evidence portal. Use this skill whenever a task references an analysis_request.json payload from the Public Health Observatory, involves a multi-module statistical audit with controlled decision gates, or mentions PHO protocols, transportability audits, or robustness audits. Do not use for generic public-health data analysis that lacks a registered protocol.
---

# Public Health Observatory Algorithmic Audit

Complete a registered PHO multi-module statistical audit using a read-only
HTTP evidence portal. Every task supplies an `analysis_request.json` payload
and an `answer_template.json` output contract. The requested modules,
parameters, grids, seeds, cohorts, filters, and decision gates are fully
specified in the request --- never invent them.

## Required input files

- `analysis_request.json` --- registered protocol, measures, years, geography,
  publication filters, module specifications, grids, seeds, decision rules.
- `answer_template.json` --- exact output JSON shape: required keys, array
  lengths, cardinality rules, precision, enum values, ordering constraints.

The prompt text supplies the portal base URL as `<TASK_ENV_BASE_URL>`.

## Workflow

### 1. Read the contract

Parse both `analysis_request.json` and `answer_template.json` fully before
touching any data. Identify:

- The effective geography scope, years, measures, and publication filters.
- The ordered list of audit modules and their exact method, cohort, parameter,
  grid, seed, and required-evidence bindings.
- The output template's required keys, array lengths, cardinality rules,
  numeric precision, ordering constraints, and controlled enum values.

### 2. Resolve the evidence portal

Replace `<TASK_ENV_BASE_URL>` with the actual URL from the prompt. The portal
is a read-only REST API. See `references/portal-api.md` for endpoint details
and data shapes.

Fetch every requested dataset in parallel when possible. The portal endpoints
return complete datasets; filter client-side by the request's effective
geography, years, value types, source types, release status, and validity
flags.

### 3. Resolve releases and build cohorts

Follow `references/data-resolution.md` for the release-resolution, filtering,
completeness-check, and cohort-construction patterns. Key rules:

- Select one record per entity--time--measure key using the declared revision
  priority (greatest revision, then latest release timestamp, then lowest
  record identifier).
- Suppressed, invalid, withdrawn, blank, or null analytic values are
  **unavailable** and never zero-filled.
- Build each cohort from its effective completeness predicates; preserve
  declared entity, time, feature, and group orders.

### 4. Execute modules in declared order

Implement each module exactly as the request specifies. Do not reorder, skip,
or substitute modules. See `references/modules.md` for reusable implementation
patterns covering:

- **Fixed-effects / weighted regression**: double-demeaning, WLS with HC3/CR1
  inference, delete-one-cluster jackknife.
- **Nested ridge / elastic-net CV**: training-only standardization, cyclic
  coordinate descent, outer/inner fold selection by pooled RMSE, penalty
  tie-breaking.
- **Wild cluster bootstrap**: restricted-model synthetic outcomes, PCG32 or
  xorshift32 PRNG streams (never reset between replicates), CR1
  studentization, exceedance counts, plus-one p-values, nearest-rank
  quantiles.
- **Grouped split conformal**: outer-fold calibration pools, rank-based
  interval radii, symmetric inclusive intervals, pooled coverage and width.
- **Trajectory PCA clustering**: covariance PCA with Jacobi eigendecomposition,
  loading orientation, deterministic farthest-first k-means, leave-one-out
  stability with adjusted Rand index.
- **Source / year perturbation**: exhaustive subset enumeration, bitmask
  replacement, Shapley attribution, stability summaries.
- **Difference GMM / panel mediation**: residualized instruments, two-step
  efficient GMM with Moore-Penrose weighting, cross-equation delta-method
  inference.
- **Partial-R2 sensitivity surface**: confounder-strength grid, adjusted
  indirect effects, tipping-point calculation.
- **Source-group perturbation**: no-retune fold deletion, RMSE deterioration
  ranking.

### 5. Apply decision rules

Follow `references/decision-rules.md`. Evaluate every effective business
predicate on **unrounded** computed values. Count satisfied gates. Apply the
request's precedence and controlled conclusion mapping exactly.

### 6. Produce the answer

Build one JSON object conforming to `answer_template.json`:

- Every required top-level key must be present.
- Round non-integer numeric fields to the declared decimal places.
- Preserve every declared array order, state order, coefficient order, grid
  order, and checkpoint order.
- Use JSON `null` only when a statistic is mathematically unavailable; never
  emit `NaN` or `Infinity`.
- Use the exact controlled enum and Boolean values from the template.
- Omit all narrative --- the response is a single JSON object.

## References

- [Portal API](references/portal-api.md) --- endpoints, data shapes, filtering patterns.
- [Data Resolution](references/data-resolution.md) --- release selection, completeness checks, cohort construction.
- [Statistical Modules](references/modules.md) --- implementation patterns for every recurring module type.
- [Decision Rules](references/decision-rules.md) --- gate evaluation and conclusion mapping.
