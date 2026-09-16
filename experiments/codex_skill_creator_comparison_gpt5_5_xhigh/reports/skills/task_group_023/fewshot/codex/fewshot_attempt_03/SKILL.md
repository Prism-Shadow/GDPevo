---
name: pho-observatory-audits
description: Solve Public Health Observatory Web portal audit tasks from analysis_request.json and answer_template.json, including state, county, and country release resolution; cohort construction; fixed-effect, GMM, ridge, elastic-net, bootstrap, conformal, PCA, clustering, sensitivity, source-perturbation, and controlled-decision modules. Use when a task provides a PHO/Public Health Observatory portal base URL plus registered audit request/template files and asks for exactly one JSON answer.
---

# PHO Observatory Audits

## Core Workflow

1. Parse `analysis_request.json`, `answer_template.json`, and the user prompt. Treat the template as the output contract and the request as the binding analytical contract.
2. Resolve the effective request before touching data. Apply exact `protocol_id` profiles and request overrides only when they match exactly; arrays replace whole arrays, objects deep-merge by exact key, scalars replace exact paths, and unknown aliases are errors.
3. Read [references/portal.md](references/portal.md) before data access. Fetch evidence only from the task's PHO portal base URL, usually via `/download?dataset=<name>&format=csv`.
4. If the request has one of the known `protocol_id` values or the country burden template, read [references/protocol_profiles.md](references/protocol_profiles.md) and use the matching module recipe.
5. Use [references/numeric_methods.md](references/numeric_methods.md) for deterministic formulas and ordering rules. Use `scripts/pho_audit_utils.py` for portable CSV fetching, release selection, PRNGs, quantiles, linear-model covariance, PCA, clustering, and JSON rounding helpers.
6. Build a task-specific solver script in the task workspace. Keep all intermediate statistics unrounded; round only the final JSON fields to the precision declared by the template/request.
7. Validate the finished object mechanically: required top-level keys, required nested keys, list lengths, list ordering, numeric precision, enum values, booleans, integer fields, and no narrative outside JSON.

## Data Rules

- Resolve publication records independently for each declared entity-time-measure-source key using the effective release filters and priority order.
- Count selected publication records before analytic completeness exclusions whenever the template asks for release counts.
- Treat suppressed, invalid, withdrawn, blank, null, and unresolved scale-break values as unavailable. Never zero-fill.
- Preserve every declared order: request arrays, feature orders, coefficient orders, grid orders, checkpoint orders, source-group orders, geography order, and template-required output order.
- Use stable identifiers: uppercase state abbreviations, text FIPS codes with leading zeros preserved, ISO3 country ids, portal division names, and exact enum strings from the template.

## Numerical Rules

- Do all model fitting, resampling, gate evaluation, tie-breaking, and decision logic from unrounded values.
- Refit from scratch for every delete-cluster, delete-state, fold, source-perturbation, leave-year-out, or override scenario unless the effective protocol explicitly says to reuse predictions or hyperparameters.
- Use training-only scaling inside every cross-validation fit. Do not leak means, standard deviations, selected penalties, or calibration residuals from held-out data.
- For bootstrap modules, maintain one continuous PRNG stream and record checkpoints only after the requested replicate has fully completed.
- Evaluate controlled decisions only after every evidence module is complete. Count or select flags in the request's declared precedence, not by apparent importance.

## Practical Implementation

Prefer a single reproducible Python script per task that:

- Downloads or caches all needed CSV datasets from the portal.
- Constructs selected release tables, analytic cohorts, and row orders once.
- Implements each module as a pure function taking the effective request and cohort tables.
- Emits a candidate JSON file and a short validation report.

If the runtime has no scientific stack, use the pure-Python helpers in `scripts/pho_audit_utils.py` as a base. If a scientific stack is available, still mirror the formulas and tie rules in [references/numeric_methods.md](references/numeric_methods.md); library defaults often use different scaling, quantiles, folds, or intercept penalties.
