---
name: pho-audit-solver
description: Solve reproducible Public Health Observatory algorithmic audits. Use this skill whenever the task references a Public Health Observatory data portal, an analysis_request.json with audit modules, an answer_template.json contract, or asks to run registered algorithmic audit procedures on health/socioeconomic surveillance data. This covers state-level transport audits, county-level mediation or panel audits, country burden stratification, and any task that combines PHO portal data retrieval with deterministic statistical modules.
---

# PHO Audit Solver

Solve Public Health Observatory algorithmic audits end-to-end. Every audit follows the same structure: resolve data from the portal, execute registered statistical modules, and return a single JSON answer conforming to the provided template.

## Workflow

Follow this sequence for every audit:

1. **Read the request**: Parse `analysis_request.json` for the protocol, modules, parameters, and reporting rules. Read `answer_template.json` for the exact output contract (required keys, array lengths, numeric precision, enum values).

2. **Resolve the portal base URL**: The prompt provides a placeholder like `<TASK_ENV_BASE_URL>`. Replace it with the actual base URL before any HTTP request.

3. **Retrieve data**: Query the portal for all required datasets. See [references/portal_api.md](references/portal_api.md) for endpoint details.

4. **Resolve releases and construct cohorts**: Apply the release resolution and cohort construction rules. See [references/release_and_cohort.md](references/release_and_cohort.md).

5. **Execute modules in registered order**: Implement each audit module using the algorithms in [references/modules.md](references/modules.md). Use the bundled [scripts/compute.py](scripts/compute.py) for deterministic statistical computations; read it, understand the functions available, and call them for the heavy numeric work.

6. **Apply decision rules**: Evaluate the business predicates from the request against unrounded module results. Apply the request's decision mapping and precedence rules.

7. **Format the answer**: Produce a single JSON object matching the answer template exactly. Follow the global rules: numeric precision (round non-integers to the declared decimal places), identifier format (uppercase state codes, portal labels), ordering (preserve every declared order), missing values (use `null` only when mathematically unavailable, never `NaN` or `Infinity`).

## Key principles

**Reproducibility**: Every algorithm is deterministic given the same input and seed. Follow the specifications exactly — do not substitute libraries, add noise, or approximate. The portal data, release resolution, and algorithm implementations must produce identical results on repeated runs.

**Release resolution**: The portal may have multiple releases per observation. Always select by greatest revision number, then latest `released_at` timestamp, then lowest observation/record ID. Filter by the effective status, value type, source type, and geography bindings from the request. Suppressed, invalid, withdrawn, blank, or null analytic values are never zero-filled — they reduce the available sample.

**Cohort discipline**: Build each analytic set from its declared required fields. Sort by entity code then time. Balanced cohorts require complete data in all analysis years; broad cohorts require complete data in the reference year. Dual-source cohorts require both primary and parallel series to be complete.

**Ordering is part of the answer**: State order, feature order, division order, lambda grid order, subset order, checkpoint order — every declared or derived order carries information. Do not sort results independently.

**Compute first, round last**: Keep all intermediate values unrounded. Round only when writing the final JSON answer, applying the declared decimal places to non-integer values.

**One effective request**: Resolve all overrides and bindings before accessing data. Use the same effective request throughout every module.

## Answer format

Return exactly one JSON object. No narrative, no markdown fences, no commentary outside the object. Every top-level key required by the answer template must be present. Lists must have the exact cardinality and order declared by the template. Use the controlled enum and Boolean values exactly as specified.

## Using the compute script

The bundled `scripts/compute.py` provides deterministic implementations of the core statistical algorithms. Read the script to understand available functions before implementing any module. The script handles:

- Double demeaning (within transformation)
- OLS without intercept
- Jackknife calculations
- Ridge regression with coordinate descent
- Elastic net
- Wild cluster bootstrap with PCG32 and XORSHIFT32 PRNGs
- PCA via covariance matrix with Jacobi eigendecomposition
- K-means clustering
- Conformal prediction
- Adjusted Rand index

For each module, use the corresponding functions from the script. If a module needs a computation not directly covered, implement it following the algorithm specification in [references/modules.md](references/modules.md) with the same deterministic rigor.

## Module reference

For detailed algorithm specifications covering every registered module, read [references/modules.md](references/modules.md). For portal interaction details, read [references/portal_api.md](references/portal_api.md).
