---
name: pho-audit-solver
description: "Solve Public Health Observatory (PHO) registered algorithmic audit tasks. Use when a task references a PHO portal, PHO protocol IDs (PHO_STATE_TRANSPORT_AUDIT_V1, PHO_COUNTY_MEDIATION_TRANSPORT_V1, PHO_STATE_ROBUSTNESS_TRANSPORT_V1, PHO_COUNTY_PANEL_TRANSPORT_V1), registered six-module or multi-module audits, algorithmic transportability or robustness analyses, burden-stratification briefings, or PHO publication-board decisions. Handles state, county, and country data across health, socioeconomic, and revision endpoints."
license: MIT
compatibility: designed for deepagents-code
---

# PHO Audit Solver

Solve Public Health Observatory algorithmic audit tasks by completing the
declared modules against the portal API and returning one JSON object
conforming to the attached answer template.

## Core Workflow

1. Parse the request: extract protocol_id, geography scope, analysis years,
   measures, cohorts, and module specifications from analysis_request.json.
2. Resolve the TASK_ENV_BASE_URL from the prompt. Query the portal for all
   required data using the download endpoints or filtered queries.
3. Apply publication resolution to select authoritative records: highest
   revision, then latest release timestamp, then lowest record ID. Exclude
   suppressed, invalid, and withdrawn values; never zero-fill them.
4. Build the requested cohorts (core balanced, broad, strict, panel) from
   resolved records following the request completeness rules.
5. Execute each declared audit module in the specified order using the
   portal data. Preserve every declared entity order, feature order, grid
   order, and checkpoint order from the analysis request.
6. Apply the controlled decision rules and return the completed JSON object.

## Portal Data Access

See [references/portal_api.md](references/portal_api.md) for the complete API
reference including all endpoints, query parameters, column schemas,
methodology documents, and geography references.

Use scripts/download_portal_data.py to bulk-fetch all datasets as CSV when
the task needs full data:

```bash
python3 scripts/download_portal_data.py <TASK_ENV_BASE_URL> <output_dir>
```

## Publication Resolution

See [references/publication_resolution.md](references/publication_resolution.md)
for the exact release-selection algorithm. In brief:

- Filter by release_status, value_type, source_type, and validity as specified
  in the analysis request.
- For each entity-year-measure combination, pick the record with the greatest
  revision, then latest released_at, then lowest observation_id/record_id.
- Suppressed, invalid, withdrawn, blank, or null values are unavailable and
  never zero-filled.

## Cohort Building

See [references/cohort_patterns.md](references/cohort_patterns.md) for the
standard cohort patterns used across all protocol families. Key patterns:

- Core balanced: entities complete for all required variables in every
  analysis year.
- Broad/reference-year: entities complete for outcome and all features in a
  single reference year.
- Strict dual-source: entities complete for outcome, primary exposure,
  parallel exposure, and adjustments in every analysis year.
- Panel: entities complete for all required variables in every year.

Entity ordering is always by state/county/country code ascending (ASCII).

## Statistical Modules

See [references/statistical_modules.md](references/statistical_modules.md)
for the complete reusable implementations. The standard module library:

| Module | Description |
|--------|-------------|
| Release Resolution and Cohorts | Publication selection and cohort assembly |
| Delete-One Cluster Fixed Effects | Two-way demeaning, OLS, delete-one jackknife |
| Nested Ridge / Elastic Net CV | Leave-group-out cross-validation with grid search |
| Wild Cluster Bootstrap | PCG32 or XORSHIFT32 paired bootstrap t-test |
| Grouped Split Conformal | Out-of-fold conformal prediction intervals |
| Trajectory PCA Clustering | Covariance PCA, k-means, leave-time-out stability |
| Source Perturbation | Exhaustive source/year substitution, Shapley attribution |
| Controlled Decision | Gate evaluation with precedence |

All modules must be executed exactly in the declared order. Preserve every
entity-code order, feature order, grid order, and checkpoint order from the
effective request. Use the exact PRNG algorithms (PCG32 or XORSHIFT32) when
specified with their full wraparound state and output mapping as documented
in the statistical modules reference.

## Answer Format

Return one JSON object conforming to the attached answer_template.json.
Round all non-integer reported statistics to the precision declared in the
request (typically 4 or 6 decimal places). Use JSON null only when a
statistic is mathematically unavailable. Preserve every formal array order
from the request. Do not include narrative outside the JSON object.
