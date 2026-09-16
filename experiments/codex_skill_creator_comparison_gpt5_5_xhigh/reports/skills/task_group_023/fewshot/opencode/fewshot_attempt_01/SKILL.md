---
name: public-health-observatory-audits
description: Use for Public Health Observatory Web portal tasks that ask for registered algorithmic audits, transportability checks, robustness gates, PHO protocol IDs, or answer_template.json JSON submissions. This skill is especially relevant for state, county, and country PHO audits involving release resolution, cohorts, jackknife/bootstrap diagnostics, nested ridge or elastic-net validation, grouped conformal calibration, PCA clustering, source perturbation, GMM mediation, and controlled publication decisions.
---

# Public Health Observatory Audits

Use this skill to solve PHO audit prompts against the read-only Observatory portal. The expected output is usually one JSON object matching `answer_template.json` exactly.

## Required Workflow

1. Read the user prompt, `analysis_request.json`, and `answer_template.json` completely.
2. Use the portal URL supplied by the task, usually `<TASK_ENV_BASE_URL>`. Fetch only authorized portal endpoints. For endpoint and release-resolution guidance, read [references/portal-data.md](references/portal-data.md).
3. Resolve one effective request contract before data access or computation. Apply exact `protocol_id` matching, direct bindings, overrides, and inheritance as described in the request and [references/protocol-profiles.md](references/protocol-profiles.md).
4. Compute every declared module in registered order. Preserve every declared order: entity, state, division, feature, coefficient, fold, grid, checkpoint, source group, subset, and output key order.
5. Evaluate decision gates on unrounded values after all modules are complete. Round only for reported JSON fields using the active request/template precision.
6. Return exactly one JSON object. Do not include markdown, prose, comments, `NaN`, `Infinity`, or extra provenance fields.

## Non-Negotiables

- Treat suppressed, invalid, withdrawn, blank, or null analytic values as unavailable. Never zero-fill them.
- Do not carry values from examples, prior runs, or solved answers. All entities, measures, years, sources, seeds, grids, cutoffs, labels, enum values, and output names come from the active request/template.
- Use stable identifiers exactly as requested: state abbreviations, county FIPS/text IDs, ISO3 codes, portal division names, and requested enum strings.
- Refit models from scratch for delete-one, nested CV, bootstrap, source-perturbation, and stability modules unless the active request explicitly says to reuse fitted quantities.
- Pool row-level squared errors before RMSE when the method says pooled RMSE. Do not average fold RMSEs unless explicitly requested.
- Use training-only centering/scaling inside every CV/calibration fit. Apply those moments to validation/test rows.
- Keep unrounded internal values for model selection, tie-breaking, gates, ranking, and extrema. Round the final JSON numbers only.

## Protocol Guidance

Read [references/protocol-profiles.md](references/protocol-profiles.md) when the request mentions one of these PHO families or modules:

- `PHO_STATE_TRANSPORT_AUDIT_V1`
- `PHO_COUNTY_MEDIATION_TRANSPORT_V1`
- country burden/revision audits using country labels, burden PCA, clustering, revisions, and a life-expectancy panel model
- `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`
- `PHO_COUNTY_PANEL_TRANSPORT_V1`

If the request has an unfamiliar protocol ID, still use the common workflow and portal rules, but bind algorithm details only from the active request, template, and portal methodology.

## Helper Code

The stdlib-only helper module [scripts/pho_common.py](scripts/pho_common.py) contains reusable primitives for portal CSV loading, release selection, linear algebra, OLS/WLS covariance, ridge/elastic-net coordinate descent, PRNG streams, PCA, k-means, ARI, silhouette, conformal ranks, and recursive JSON rounding. Copy or import functions from it when writing the task-specific solver script.

The helper is not a complete solver. The solver still needs to map active request fields into the correct design matrices and output schema.
