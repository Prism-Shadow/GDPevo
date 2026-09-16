---
name: pho-registered-audits
description: Solve Public Health Observatory registered audit tasks that use a TASK_ENV_BASE_URL portal plus analysis_request.json and answer_template.json. Use this skill for state, county, or country Observatory algorithmic audits involving release/cohort resolution, fixed effects, GMM, ridge or elastic-net validation, wild cluster bootstrap, conformal calibration, PCA clustering, source perturbation, sensitivity surfaces, or controlled JSON decisions.
---

# Public Health Observatory Registered Audits

## Operating Rule

Use only the future task's prompt, `analysis_request.json`, `answer_template.json`, and the authorized Public Health Observatory portal. Do not reuse values from examples or prior runs. The template controls the final JSON shape, key names, enum values, ordering, booleans, and numeric precision.

Read [references/methods.md](references/methods.md) before computing modules. Import [scripts/pho_audit_utils.py](scripts/pho_audit_utils.py) when deterministic portal download, release selection, matrix algebra, bootstrap PRNG, PCA, k-means, conformal ranks, or rounding helpers would reduce implementation risk.

## Workflow

1. Read the prompt and both payload files completely. Replace `<TASK_ENV_BASE_URL>` with the actual base URL from the task environment.
2. Freeze one effective request before data access. Apply direct request keys and any `*_overrides` by exact-path deep merge: objects merge recursively, arrays replace whole arrays, scalars replace exact paths, and unknown targets are errors.
3. Download evidence from the portal through `/download?dataset=<name>&format=csv` plus query filters. Use `/catalog` and `/methodology` only to confirm schema, filters, current policy, and identifier semantics.
4. Resolve releases independently for each requested geography, year, measure, value type, source, and status. Select by the effective revision priority; treat suppressed, invalid, withdrawn, blank, and null analytic values as unavailable, never as zero.
5. Build every declared cohort from the selected records. Preserve the effective entity, time, feature, fold, grid, checkpoint, and source-group order. Never sort an aligned array independently after fitting.
6. Execute all modules before the decision module. Evaluate gates on unrounded values; round only when writing the final JSON.
7. Validate the final object against `answer_template.json`: exact top-level keys when required, all required nested fields, declared array lengths, natural JSON integer and boolean types, finite numbers or `null` only where allowed, and no narrative outside the JSON.

## Portal Notes

Prefer CSV downloads over scraping HTML tables:

```bash
curl -fsS "$TASK_ENV_BASE_URL/download?dataset=state_health&format=csv"
curl -fsS "$TASK_ENV_BASE_URL/download?dataset=state_socioeconomic&format=csv"
curl -fsS "$TASK_ENV_BASE_URL/download?dataset=county_health&format=csv"
curl -fsS "$TASK_ENV_BASE_URL/download?dataset=county_socioeconomic&format=csv"
curl -fsS "$TASK_ENV_BASE_URL/download?dataset=country_indicators&format=csv"
curl -fsS "$TASK_ENV_BASE_URL/download?dataset=revisions&format=csv"
```

Use filtered downloads when the request narrows year, measure, geography, release status, value type, source type, or revision. Also download geography tables (`states`, `counties`, `countries`) for region, division, RUCC, canonical country names, and aliases.

## Output Discipline

Keep full-precision intermediate values in memory. Use the request or template precision at serialization time. If a field is a literal grid value or threshold, preserve the declared literal precision semantics; JSON numbers do not need trailing zeros.

Do not include optional provenance or protocol-registry records unless the future template explicitly requires them. The reusable method profiles in the reference are instructions for the solver, not answer content.
