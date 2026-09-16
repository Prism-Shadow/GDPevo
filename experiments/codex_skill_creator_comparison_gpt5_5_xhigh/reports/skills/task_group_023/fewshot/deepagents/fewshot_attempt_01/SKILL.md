---
name: public-health-observatory-audits
description: "Solve Public Health Observatory portal audit tasks that provide analysis_request.json and answer_template.json, especially exact protocol IDs PHO_STATE_TRANSPORT_AUDIT_V1, PHO_COUNTY_MEDIATION_TRANSPORT_V1, PHO_STATE_ROBUSTNESS_TRANSPORT_V1, PHO_COUNTY_PANEL_TRANSPORT_V1, and country_burden_revision_audit_v1 style requests. Use for deterministic publication/cohort resolution, grouped prediction audits, cluster bootstrap, conformal calibration, PCA/k-means stability, source perturbation, mediation, GMM, and controlled JSON decisions."
---

# Public Health Observatory Audits

## Core Workflow

1. Read the user prompt, `analysis_request.json`, and `answer_template.json` before fetching data. The request and template are the only output contract for the current invocation.
2. Extract the portal base URL from the prompt or environment instructions. Fetch only the allowed Observatory endpoints. A helper is available at [scripts/pho_audit_utils.py](scripts/pho_audit_utils.py).
3. Resolve one effective request before any computation. If a future request includes overrides, apply exact-key recursive object merges, full-array replacement, scalar replacement at exact paths, and no inferred aliases or type coercion.
4. Bind all entities, years, measures, source filters, feature orders, random seeds, grids, thresholds, output names, precision, and controlled labels from the active request and template. Never reuse values from examples or prior answers.
5. Resolve publication records independently for each requested series. Apply the declared status, value type, source type, quality, revision, release-time, and record-id rules. Treat suppressed, invalid, blank, and null analytic values as unavailable, never as zero.
6. Build the declared cohorts only after publication resolution. Preserve the requested entity, year, cluster, feature, fold, grid, checkpoint, and source-group orders; do not sort aligned arrays independently.
7. Execute every registered module, even when an early gate appears to fail. Evaluate gates on unrounded values, then round only reported numbers using the template precision.
8. Return exactly one JSON object matching the template. Do not add narrative. Do not add `protocol_registry_record` or other provenance unless the active template explicitly requires it.

## Protocol Methods

Before solving a recognized Observatory audit, read [references/protocols.md](references/protocols.md). It contains reusable method semantics inferred from the few-shot standards without training answer values.

Use exact protocol routing:

- `PHO_STATE_TRANSPORT_AUDIT_V1`: state fixed-effects transport audit.
- `PHO_COUNTY_MEDIATION_TRANSPORT_V1`: county mediation and transport audit.
- `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`: reliability-weighted state robustness audit.
- `PHO_COUNTY_PANEL_TRANSPORT_V1`: county panel dynamics transport audit.
- `country_burden_revision_audit_v1` or matching country burden revision prompts: country reconciliation, quality, PCA, cluster, panel, and advisory audit.

If the protocol is unrecognized, still follow the template, portal, cohort, ordering, precision, and controlled-decision rules above, but derive module formulas from the active request.

## Portal Handling

Fetch the catalog and geography endpoints first, then the necessary data endpoints. Save or cache raw responses during solving so counts can be reproduced. Useful endpoints typically include:

- `/catalog`
- `/geographies/states`, `/geographies/counties`, `/geographies/countries`
- `/data/state-health`, `/data/state-socioeconomic`
- `/data/county-health`, `/data/county-socioeconomic`
- `/data/country-indicators`
- `/data/revisions`
- `/methodology`

Inspect field names in the returned JSON instead of assuming a fixed schema. Publication rows in the examples use fields equivalent to entity identifiers, years, measure or indicator identifiers, value fields, release status, revision, release timestamp, record identifiers, source or value type, quality flags, suppression flags, and sample sizes.

## Computation Rules

Use deterministic code for all nontrivial statistics. The bundled helper includes pure-Python implementations for common tasks:

- JSON fetching and cache writing.
- Release filtering and latest-record selection.
- WLS/OLS, HC3, CR1, Student-t p-values, RMSE, MAE, and R-squared.
- Ridge and elastic-net coordinate descent.
- Xorshift32, PCG32, Webb weights, nearest-rank and type-seven quantiles.
- Jacobi PCA, deterministic farthest-first k-means, and adjusted Rand index.
- JSON rounding while preserving integer and Boolean types.

Prefer writing a task-local driver script that imports these helpers, performs the active request's data shaping, and emits the final JSON. Validate array lengths and required keys against `answer_template.json` before submitting.
