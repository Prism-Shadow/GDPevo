---
name: pho-algorithmic-audits
description: Solve Public Health Observatory portal audits from analysis_request.json and answer_template.json, especially exact protocol IDs PHO_STATE_TRANSPORT_AUDIT_V1, PHO_COUNTY_MEDIATION_TRANSPORT_V1, PHO_STATE_ROBUSTNESS_TRANSPORT_V1, PHO_COUNTY_PANEL_TRANSPORT_V1, and country burden revision PCA or clustering audits. Use for Web-only PHO tasks requiring release resolution, cohort construction, clustered models, nested validation, bootstrap checkpoints, conformal calibration, PCA clustering, perturbation audits, and controlled JSON decisions.
---

# PHO Algorithmic Audits

Use this skill for Public Health Observatory tasks that provide an `analysis_request.json`, an `answer_template.json`, and a portal base URL. Produce the requested JSON answer only; do not add prose around it.

## Core Rule

Treat the future request as the only source of task-local bindings. Do not reuse solved values, entity lists, year ranges, measures, seeds, grids, thresholds, labels, or classifications from prior examples. Recompute every requested field from the authorized portal data and the effective request.

If a request has one of the exact supported protocol IDs, read [references/protocol-methods.md](references/protocol-methods.md) and apply that profile. If there is no protocol ID but the task is a PHO country burden revision, PCA, clustering, or panel audit, use the country burden section in the same reference.

## Workflow

1. Parse `analysis_request.json` and `answer_template.json`.
2. Resolve an effective request before data access or computation. Direct keys bind by exact name. Keys ending in `_overrides` target the same canonical section after removing only that suffix. Recursively merge objects, replace arrays in full, replace scalars at the exact path, and reject unknown targets or incompatible types.
3. Download portal CSVs through `/download?dataset=DATASET&format=csv` unless the request explicitly requires browsing a filtered endpoint. Keep FIPS and other identifiers as strings. Use `/catalog` and `/methodology` only to confirm schema and policy.
4. Resolve final releases independently for every requested series. Apply all status, source, value type, quality, suppression, validity, revision, timestamp, and record-id rules from the effective request or matching protocol profile. Suppressed, invalid, blank, and null analytic values are unavailable; never zero-fill them.
5. Build the requested complete-case, balanced, broad, strict, machine-learning, or panel cohorts from the resolved records. Preserve the declared entity, time, feature, fold, source, checkpoint, and output orders.
6. Fit every registered module from scratch. For deletion, bootstrap, stability, and perturbation modules, recompute preprocessing and model state inside each refit unless the profile explicitly says to reuse a fitted quantity.
7. Evaluate gates and controlled decisions on unrounded values. Round only when populating the final JSON, using the template's precision and natural JSON types. Emit `null` only for mathematically unavailable statistics; never emit `NaN` or `Infinity`.
8. Validate the final object against the template: required keys, enum values, cardinalities, numeric precision, list order, and absence of narrative text.

Do not include a `protocol_registry_record` in the final answer unless the future template explicitly asks for it. Registry records in solved standards are reusable-method provenance, not solver-visible output.
