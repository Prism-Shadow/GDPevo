---
name: pho-algorithmic-audits
description: Solve Public Health Observatory web-portal audit tasks that provide analysis_request.json and answer_template.json, including state, county, and country public-health release resolution, cohort construction, regression, GMM, ridge or elastic-net validation, wild-cluster bootstrap, grouped conformal calibration, PCA clustering, perturbation audits, and controlled JSON decisions.
---

# PHO Algorithmic Audits

Use this skill for Public Health Observatory tasks that require computing a structured JSON answer from the read-only portal. The portal evidence, the active `analysis_request.json`, and the active `answer_template.json` are the authority. Do not reuse solved values from any prior task.

## Required Workflow

1. Read the prompt, `analysis_request.json`, and `answer_template.json` completely.
2. Resolve one effective request before any data access or computation:
   - Use an exact protocol profile only when `protocol_id` exactly matches the case-sensitive identifier in [protocol-methods.md](references/protocol-methods.md).
   - Apply direct keys by exact path. A root `<section>_overrides` targets `<section>`, `module_overrides.<module>` targets that exact module, and `reporting_overrides` targets reporting.
   - Deep-merge objects, replace arrays whole, and replace explicit scalars only at their exact paths. Reject unknown targets, inferred aliases, positional patches, and type coercion.
3. Load only authorized portal data through `<TASK_ENV_BASE_URL>`:
   - Inspect `/catalog` and `/methodology` if schema or current policy is unclear.
   - Prefer CSV exports such as `/download?dataset=state_health&format=csv`; add query filters only when they exactly match portal filter names.
   - The utility module [pho_tools.py](scripts/pho_tools.py) can download CSV rows and provides deterministic math helpers without third-party packages.
4. Resolve releases independently for every requested source. Filter by the effective geography, years, measures, value type, source type, release status, and quality rules. Select one publication row per entity-time-measure key using the effective priority.
5. Build every requested cohort from selected records only. Suppressed, invalid, withdrawn, blank, and null analytic values are unavailable and must never be zero-filled. Publication counts may include selected but analytically incomplete records when the template asks for release counts.
6. Preserve all declared order:
   - Feature arrays, coefficient arrays, grids, checkpoints, folds, source groups, and decision gates keep request/template order.
   - Entity arrays use the requested stable identifier order, usually ASCII/ascending code order or the portal's registered geography order.
   - Never sort one aligned array without sorting every companion array through the same key.
7. Compute all modules before applying decision gates. Evaluate gates using unrounded values. Round only fields that are reported, at the precision declared by the active request/template.
8. Return exactly one JSON object. Use only template keys and controlled enum values unless the active template explicitly permits extra provenance.

## Portal Data

The portal datasets observed in this task family are:

- `states`: `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state`
- `counties`: `county_fips`, `state_abbr`, `county_name`, `region`, `rucc`, geography metadata
- `countries`: `iso3`, `canonical_name`, `portal_label`, `alternate_labels`, `region`, `income_group`
- `state_health`: state-year-measure rows with value type, source type, release metadata, value, standard error, sample size, suppression and quality flags
- `state_socioeconomic`: state-year final socioeconomic fields and release metadata
- `county_health`: county-year-measure rows with release metadata, value, suppression and quality flags
- `county_socioeconomic`: county-year socioeconomic fields and release metadata
- `country_indicators`: country-year-indicator rows with release metadata, value, unit, and quality flag
- `revisions`: revision events with domain, entity, field, effective year, status, and old/new values

Use `/download?dataset=<dataset>&format=csv` to bulk export. The browse pages show valid filter names and offer a matching CSV link.

## Method Profiles

Read [protocol-methods.md](references/protocol-methods.md) before implementing any statistical module. It contains the reusable profile semantics for:

- `PHO_STATE_TRANSPORT_AUDIT_V1`
- `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`
- `PHO_COUNTY_MEDIATION_TRANSPORT_V1`
- `PHO_COUNTY_PANEL_TRANSPORT_V1`
- Country burden revision audits with country label reconciliation, revision/anomaly audit, PCA burden scores, clustering, and region-adjusted panel modeling

Do not emit the method profile itself in the final answer unless the active answer template explicitly requires it.

## Output Checks

Before submitting, validate the object against `answer_template.json`:

- Required top-level keys all present; no narrative outside JSON.
- JSON numbers are finite. Use `null` only when a requested statistic is mathematically unavailable.
- Integers and booleans are natural JSON types.
- Arrays have the declared length and order.
- Gate flags and final classification use only controlled values from the active template.
