---
name: pho-algorithmic-audits
description: Solve Public Health Observatory web-portal algorithmic audit tasks from analysis_request.json and answer_template.json, including exact PHO state, county, panel, mediation, robustness, and country-burden audit profiles. Use when a task asks Codex to resolve PHO releases and cohorts and return controlled JSON with clustered inference, nested ridge or elastic-net validation, wild bootstrap, grouped conformal calibration, PCA/k-means stability, mediation, GMM, sensitivity, or perturbation modules.
---

# PHO Algorithmic Audits

## Operating Rules

Use this skill for PHO web-portal audit tasks only. Treat the active prompt, `analysis_request.json`, `answer_template.json`, and the task portal as the only task evidence.

Do not reuse solved values, states, counts, coefficients, random checkpoints, classifications, or arrays from prior examples. The examples only establish reusable method semantics. Bind all entities, measures, years, source filters, grids, seeds, replicate counts, thresholds, labels, and output vocabulary from the active request.

Do not include `protocol_registry_record` or other provenance fields in the submitted JSON unless the active `answer_template.json` explicitly requires them.

Read [references/protocol-profiles.md](references/protocol-profiles.md) before computing any audit module. Use [scripts/pho_math.py](scripts/pho_math.py) as an optional pure-Python helper for linear algebra, robust covariance, PRNGs, quantiles, PCA, k-means, ARI, and silhouette calculations.

## One-Pass Workflow

1. Load the prompt, `analysis_request.json`, and `answer_template.json`. If the prompt uses a placeholder base URL, read the task's environment access file if present and use only the listed portal endpoints.
2. Resolve one effective request before data access or modeling. For exact PHO protocol IDs in the reference, apply that protocol profile and then merge any active request overrides exactly as instructed. Reject unknown override targets rather than guessing.
3. Discover portal schemas from `/catalog` and `/methodology`, then download or query only the needed public datasets. Prefer `/download?dataset=...&format=csv` when many rows are needed.
4. Resolve releases independently for every declared dataset, measure, source, year, and geography key. Suppressed, invalid, blank, null, withdrawn, or scale-broken values are unavailable and must never be zero-filled.
5. Build cohorts from the active completeness predicates. Preserve every declared order: entity order, year order, feature order, coefficient order, fold order, grid order, checkpoint order, and controlled decision order.
6. Compute all modules from unrounded data. Round only at final serialization, using the precision and JSON types declared by the active template.
7. Validate the JSON object against the template before returning it. Ensure all required keys are present, arrays have declared lengths and order, booleans are JSON booleans, unavailable numeric statistics are `null`, and no narrative surrounds the JSON.

## Portal Data

The PHO portal exposes these common datasets:

- `states`: `state_fips`, `state_abbr`, `state_name`, `region`, `division`, `is_state`.
- `counties`: `county_fips`, `state_abbr`, `county_name`, `region`, `rucc`, `metro_class`, `population_base`, latitude/longitude.
- `countries`: `iso3`, `canonical_name`, `portal_label`, pipe-separated `alternate_labels`, `region`, `income_group`.
- `state_health`: publication rows with `observation_id`, geography, year, `measure_id`, `value_type`, `source_type`, `release_status`, `revision`, `value`, `standard_error`, `sample_size`, `suppression_flag`, `quality_flag`, `released_at`.
- `state_socioeconomic` and `county_socioeconomic`: release rows with `record_id`, geography, year, `release_status`, `revision`, `released_at`, and socioeconomic fields.
- `county_health`: publication rows with `observation_id`, county/state/region, year, `measure_id`, `value_type`, `release_status`, `revision`, `released_at`, `value`, intervals, population, suppression, and quality flags.
- `country_indicators`: `observation_id`, `country_label`, `iso3`, year, `indicator_id`, `release_status`, `revision`, `released_at`, `value`, `unit`, `quality_flag`.
- `revisions`: `revision_event_id`, domain, `entity_id`, `field_id`, `effective_year`, old/new values, status, date, reason, and note.

## Implementation Notes

Use scripts for repeatability when a module involves many refits or random draws. A typical pattern is to write a task-local solver script that imports `scripts/pho_math.py`, downloads portal CSVs, computes unrounded results, and emits one JSON object. Keep that task-local script outside the skill package.

For statistical p-values, prefer an exact Student-t calculation. If no library is available, `pho_math.student_t_two_sided_p` provides a dependency-free implementation adequate for the small-cluster tests used by these audits.

For model selection and decision gates, compare unrounded values. Use rounded values only in the final JSON fields.
