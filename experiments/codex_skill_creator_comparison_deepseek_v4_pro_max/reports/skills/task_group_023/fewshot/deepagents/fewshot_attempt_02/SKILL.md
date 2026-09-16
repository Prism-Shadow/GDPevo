---
name: pho-audit
description: "Complete reproducible algorithmic audits for the Public Health Observatory (PHO). Use this skill when the user presents a PHO analysis request with a protocol_id, an answer_template.json, and a task-environment base URL for retrieving public health data. Covers state-level, county-level, and country-level audits across longevity, mediation, burden stratification, and weighted-robustness protocols. Handles release resolution, cohort construction, cross-validated regularized regression, jackknife and wild bootstrap inference, grouped conformal calibration, PCA trajectory clustering, sensitivity surfaces, source perturbation, and controlled decision gates."
---

# PHO Audit

## Overview

This skill enables a solver to execute Public Health Observatory algorithmic audits end to end: resolve data releases from the PHO web portal, construct analytic cohorts, run registered statistical modules, and produce an answer JSON that conforms to the supplied template.

Every PHO audit follows the same high-level sequence. Understand the request contract, resolve data, build cohorts, execute modules in registered order, and apply controlled decision rules.

## Portal API

Base URL is supplied as `<TASK_ENV_BASE_URL>` in the prompt. All endpoints are read-only GETs with no credentials.

See [references/api-endpoints.md](references/api-endpoints.md) for the full endpoint catalog, query parameters, response shapes, and field-level rules for release selection, revision priority, and value validity.

## Workflow

### 1. Absorb the Contract

Read the prompt, `analysis_request.json`, and `answer_template.json` together. Identify:
- The protocol_id (if present) — this maps to a registered method profile
- Geography scope (states, counties, or countries) and time range
- Health measures and socioeconomic fields needed
- Release filters (release_status, value_type, source_type)
- Cohort definitions (primary, balanced, broad, strict dual-source)
- Module order, method bindings, hyperparameter grids, random seeds
- Decision rules and their precedence

### 2. Resolve Publications

Fetch data from the portal endpoints for the declared geography and measures. For health data, apply the effective value_type, source_type, and release_status filters. For every entity—time—measure key, select one record by the registered priority:

1. Greatest `revision` number
2. Latest `released_at` timestamp
3. Greatest record/observation identifier

Suppressed, invalid, withdrawn, blank, or null analytic values are unavailable and never zero-filled. Count selected publications before analytic completeness exclusions when the request asks for them.

### 3. Build Cohorts

Join resolved series by stable entity and time keys. Apply the effective completeness predicate (nonsuppressed, nonmissing for all required fields). Construct:

- **Primary cohort**: complete cases in the reference year from the declared universe
- **Balanced cohort**: entities complete in every requested year
- **Broad/ML cohort**: primary-cohort members with additional field completeness
- **Strict dual-source cohort**: complete for outcome, primary exposure, parallel exposure, and adjustments in every year

Preserve entity-code order, then time order. Maintain declared feature, cluster, and group orders throughout.

### 4. Match Protocol and Execute Modules

When the request carries a `protocol_id`, look it up in [references/protocols.md](references/protocols.md). Each registered protocol entry describes the exact statistical methods for every module: algebra, standardization, solver details, cross-validation logic, random-number generation, inference, and aggregation rules. Task-local bindings (entities, years, grids, seeds, cutoffs, output labels) always come from the effective request and override any inherited defaults via the documented override resolution rules.

Execute modules in the declared order. Recompute every quantity from scratch for the current request — never carry solved values from a prior invocation.

If the request has no registered protocol_id (e.g. a one-off country briefing), read the request specification and [references/api-endpoints.md](references/api-endpoints.md) directly and execute each analytical section as declared.

### 5. Apply Decision Rules

Complete every module before evaluating gates. Evaluate effective business predicates on unrounded values. Preserve the declared module precedence order. Map the gate pattern to the controlled conclusion using only the effective request's decision mapping.

### 6. Format Output

Build one JSON object that matches every key, array length, ordering, precision, and enum constraint in the answer template. Round noninteger statistics to the requested decimal places. Report integer metadata as natural JSON integers. Use `null` only when a statistic is mathematically unavailable — never NaN or Infinity.

## Reference Files

- [api-endpoints.md](references/api-endpoints.md) — portal endpoint catalog, query parameters, response schemas, and release/validity rules
- [protocols.md](references/protocols.md) — registered protocol method profiles with exact statistical specifications
