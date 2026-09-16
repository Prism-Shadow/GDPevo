---
name: pho-observatory-audits
description: Solve Public Health Observatory web-portal audit tasks requiring exact JSON outputs from analysis_request.json and answer_template.json. Use for PHO algorithmic publication audits over state, county, or country data, including exact protocols PHO_STATE_TRANSPORT_AUDIT_V1, PHO_COUNTY_MEDIATION_TRANSPORT_V1, PHO_STATE_ROBUSTNESS_TRANSPORT_V1, PHO_COUNTY_PANEL_TRANSPORT_V1, and country burden revision/PCA/cluster/panel audit requests.
---

# PHO Observatory Audits

## Core Workflow

1. Read the task prompt, `analysis_request.json`, and `answer_template.json` before fetching evidence.
2. Resolve `<TASK_ENV_BASE_URL>` from the task environment and use only the public portal endpoints. Read [portal_schema.md](references/portal_schema.md) before downloading data.
3. If `analysis_request.json` has one of the exact protocol IDs listed below, read the matching section in [protocol_profiles.md](references/protocol_profiles.md). Do not activate a profile by similar subject matter or family name.
4. Freeze one effective request contract before computation. Apply direct keys and `_overrides` aliases exactly as the active profile says; arrays replace whole arrays, objects merge recursively, and unknown targets fail before evidence resolution.
5. Fetch only the required datasets. `scripts/fetch_portal.py` can download CSV files from the portal into a local working directory.
6. Resolve releases independently for every requested source, measure, geography, and year. Select records using the request's ordered revision/release/id priority; suppressed, invalid, withdrawn, blank, or null analytic values are unavailable and are never zero-filled.
7. Build every cohort from the effective completeness predicates. Preserve all declared entity, time, feature, fold, grid, checkpoint, cluster, and output orders. Never independently sort aligned result arrays.
8. Complete every module before evaluating controlled decisions. Evaluate gates on unrounded values, then round only at final JSON serialization.
9. Return exactly one JSON object conforming to the template. Emit no narrative, comments, NaN, Infinity, or extra keys unless the template explicitly requires them.

## Protocol Selection

- `PHO_STATE_TRANSPORT_AUDIT_V1`: state fixed-effects, nested ridge, PCG32 Webb bootstrap, grouped conformal, trajectory PCA/k-means, source-year perturbation.
- `PHO_COUNTY_MEDIATION_TRANSPORT_V1`: county mediation, difference GMM, nested leave-state ridge, paired xorshift bootstrap, state-grouped conformal, partial-R2 sensitivity, state trajectory PCA.
- `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`: state reliability-weighted WLS/HC3/CR1, division jackknife, weighted elastic-net, xorshift bootstrap, grouped conformal, trajectory PCA, exhaustive source perturbation with Shapley effects.
- `PHO_COUNTY_PANEL_TRANSPORT_V1`: county balanced panel changes, delete-state two-step GMM, state-blocked nested elastic-net, state wild bootstrap, cross-fold conformal, county trajectory PCA, source-group deletion.
- Country burden revision audits: no embedded protocol profile was present in the examples. Use the request/template shape and the country section in [protocol_profiles.md](references/protocol_profiles.md).

## Implementation Notes

Use small deterministic scripts for repeatability. `scripts/pho_common.py` contains reusable helpers for release selection, JSON-safe rounding, xorshift32, PCG32 Webb indices, finite-sample conformal ranks, adjusted Rand index, and deterministic farthest-first k-means. Read or import it when implementing bootstrap, clustering, or release-resolution code.

For modeling code, implement the active profile's formulas directly. Keep unrounded fitted objects for downstream modules such as bootstrap, sensitivity, conformal calibration, source perturbation, and controlled gates. If a final field is a literal grid value, threshold, seed, PRNG state, replicate number, count, rank, fold number, or Boolean, preserve its natural JSON type.

## Final Checks

- Every required top-level key from `answer_template.json` is present exactly once.
- Every list length, order, enum, and aligned array matches the template and effective request.
- Counts are integers, Booleans are Booleans, and reported nonintegers use the requested decimal precision.
- Set-like identifier lists are unique and sorted only when the template says they are set-like.
- The answer contains no task-specific values from prior examples; all evidence is recomputed from the current portal data and current request.
