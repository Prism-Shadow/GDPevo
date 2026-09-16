---
name: pho-algorithmic-audits
description: Use for Public Health Observatory portal tasks that require a JSON-only answer from analysis_request.json and answer_template.json, especially PHO_* protocol_id audits, registered multi-module statistical audits, release/cohort reconciliation, bootstraps, grouped validation, PCA/clustering, source perturbation, or controlled decision gates.
---

# Public Health Observatory Algorithmic Audits

Use this skill when a task asks you to solve a Public Health Observatory audit from a web-only/read-only portal and local `analysis_request.json` plus `answer_template.json`.

## First Moves

1. Read the prompt, `analysis_request.json`, and `answer_template.json` completely.
2. Read [references/protocols.md](references/protocols.md) when the request has a `protocol_id`, asks for a registered algorithmic audit, or uses PHO portal publication/revision language.
3. Identify the task environment base URL from the prompt placeholder, environment notes, or runtime context. Query only the allowed read-only portal endpoints.
4. Build one effective request before fetching or computing anything:
   - Activate a bundled protocol profile only when the `protocol_id` is an exact case-sensitive match.
   - Apply direct request keys and `*_overrides` with exact-path deep merge rules from the protocol reference.
   - Treat arrays as full replacements, not patches or concatenations.
   - Reject unresolved aliases, unknown override targets, and incompatible types rather than guessing.

## Evidence Handling

- Download full tables with `/download?dataset=<name>&format=csv` when row-level computation is needed; use browse endpoints only for inspection.
- Resolve health, socioeconomic, geography, country, and revision records independently using the effective release filters and tie-breakers.
- Count selected publication records before analytic completeness exclusions when the template asks for release counts.
- Suppressed, invalid, withdrawn, blank, null, or unresolved anomaly values are unavailable. Never zero-fill.
- Preserve every declared order: states, divisions, features, lambda grids, folds, checkpoints, source groups, output keys, and controlled enum values.
- Keep stable identifiers as text. Do not drop leading zeros from FIPS-like identifiers.

## Computation Rules

- Use unrounded values for fitting, inference, gate checks, tie-breaking, and downstream modules. Round only when writing the final JSON.
- Refit models from scratch for delete-cluster, delete-state, leave-year, fold, source, and perturbation diagnostics unless the effective protocol explicitly says to reuse hyperparameters.
- Standardize only from the active training sample in each fit. Apply those moments to validation/test rows.
- Pool row-level squared errors before RMSE unless the request explicitly asks for another aggregation.
- For randomization modules, implement the declared generator, seed, stream, draw order, checkpoint schedule, weight/sign mapping, exceedance rule, and quantile definition exactly.
- For PCA and clustering, rebuild scaling, orientation, initialization, and labels for every stability refit. Use the protocol's tie-breakers.
- Evaluate controlled decision predicates on unrounded statistics and apply only the request's precedence order.

## Useful Helper

[scripts/pho_common.py](scripts/pho_common.py) contains portable Python helpers for downloading portal tables, selecting latest publications, OLS/WLS inference, CR1/HC3 covariance, ridge and elastic-net coordinate descent, xorshift/PCG random streams, PCA/k-means, ARI, and conformal quantiles. Use it as a library or copy small functions into a task-local solver. It intentionally contains no task-specific solved values.

## Final Answer Contract

- Return exactly one JSON object and no narrative when the prompt/template requires it.
- Match the template's top-level keys, nested key names, array cardinalities, order, enum strings, numeric precision, integer fields, booleans, and null handling.
- Do not add provenance, registry, or method-profile keys unless the future `answer_template.json` explicitly requires them.
- Before submitting, run a local structural check: parse the JSON, compare required keys/cardinalities against the template, verify array alignment, and confirm every reported gate/classification follows from unrounded computed values.
