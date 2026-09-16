---
name: pho-portal-audit
description: Solve Public Health Observatory web-portal audit tasks that require analysis_request.json and answer_template.json outputs, including state, county, and country release reconciliation; deterministic fixed-effect, GMM, ridge or elastic-net, bootstrap, conformal, PCA, clustering, sensitivity, source-perturbation, and controlled-decision modules. Use when a task references the Public Health Observatory portal, PHO protocol IDs, or asks for one JSON audit object from portal evidence.
---

# Public Health Observatory Audit Solver

## Start Here

1. Read the user prompt, `analysis_request.json`, `answer_template.json`, and any local `environment_access.md`.
2. Use the portal base URL from the prompt placeholder or from `environment_access.md`. Do not call judge endpoints.
3. Fetch only authorized portal evidence. Prefer CSV downloads through `/download?dataset=<name>&format=csv` after checking `/catalog` for schemas.
4. Build one effective request contract before touching analytic data. Apply direct keys and `*_overrides` by exact path only; arrays replace whole arrays, objects deep-merge, scalars replace exact paths, and unknown targets are errors.
5. Compute every requested module from scratch from portal evidence. Keep unrounded values internally, preserve declared order everywhere, and round only when serializing the final JSON.
6. Return exactly one JSON object conforming to `answer_template.json`. Do not add narrative. Do not include solved-standard provenance unless the future template explicitly requires it.

## Portal Datasets

Expect these portal datasets unless `/catalog` says otherwise:

- Geography: `states`, `counties`, `countries`
- Publications: `state_health`, `state_socioeconomic`, `county_health`, `county_socioeconomic`, `country_indicators`
- Revision metadata: `revisions`

Use text identifiers as text. Preserve leading zeros in FIPS fields. Treat suppressed, invalid, withdrawn, blank, and null analytic values as unavailable, never as zero.

## Method Reference

Read [references/pho_methods.md](references/pho_methods.md) before implementing modules. It summarizes the reusable methods inferred from the staged PHO examples without embedding their solved values.

Use [scripts/pho_stats.py](scripts/pho_stats.py) for deterministic numerical primitives. Copy or import only the functions needed for the task, then write task-local code that binds variables, cohorts, filters, grids, seeds, and output fields from the effective future request.

## Output Discipline

- Validate top-level keys, nested keys, array lengths, enum values, and numeric precision against the template.
- Preserve all registered orders: entity, state, division, fold, feature, coefficient, lambda/grid, replicate checkpoint, source group, year, and candidate-cluster order.
- Do not independently sort aligned result arrays. Sort only when the request or template explicitly says a set-like list must be sorted.
- Use JSON `null` only for mathematically unavailable requested statistics. Never emit `NaN`, `Infinity`, comments, markdown, or explanatory text.
