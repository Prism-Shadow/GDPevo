---
name: pho-algorithmic-audits
description: Solve Public Health Observatory portal audit tasks that provide analysis_request.json and answer_template.json, including state, county, and country health/socioeconomic algorithmic audits with strict release resolution, reproducible cohorts, regression, resampling, conformal calibration, PCA, clustering, perturbation, and controlled JSON decisions. Use this skill whenever a prompt mentions the Public Health Observatory portal, PHO protocol_id values, registered audit modules, or asks for one JSON answer from portal evidence.
---

# Public Health Observatory Algorithmic Audits

Use this skill to complete one Observatory audit from the provided prompt, `analysis_request.json`, `answer_template.json`, and the read-only portal named in the prompt. The answer must be computed fresh from that request and portal evidence.

## Required References

- Read [references/portal-and-data.md](references/portal-and-data.md) before network access or release resolution.
- Read [references/protocol-methods.md](references/protocol-methods.md) when `analysis_request.json` contains one of the exact protocol IDs listed there, or when the task resembles the country burden audit.
- Read [references/statistical-primitives.md](references/statistical-primitives.md) before implementing any model, bootstrap, PCA, clustering, conformal, or perturbation module.
- Optionally import helpers from [scripts/pho_audit_helpers.py](scripts/pho_audit_helpers.py) instead of rewriting common linear algebra, PRNG, PCA, k-means, ARI, CSV, and rounding code.

## Non-Negotiables

- Use only the task prompt, the two payload JSON files, and the authorized Observatory portal evidence. Do not use cached solved outputs, evaluator assumptions, or outside datasets.
- Treat the protocol profiles in this skill as method semantics only. Never carry over solved counts, coefficients, selected states, cluster memberships, PRNG states, p-values, decisions, or other analytical values.
- Resolve one effective request before any data access that depends on request fields. Apply exact-key overrides by deep-merging objects, replacing arrays whole, replacing scalars at their exact paths, and rejecting unknown or incompatible override targets.
- Preserve every declared order. Do not sort arrays unless the template says a field is set-like or sorted.
- Keep unrounded values internally through all gates and decisions. Round only the emitted fields at the precision declared by the request or template.
- Return exactly one JSON object and no narrative. Omit helper/provenance sections unless the active template explicitly requires them.

## Workflow

1. Parse the prompt, `analysis_request.json`, and `answer_template.json`.
   - Record the base URL replacing `<TASK_ENV_BASE_URL>`.
   - Identify `protocol_id`, requested years, geography, measures, filters, release priority, module order, random seeds, grids, precision, and controlled decision vocabulary.
   - Build a checklist from the template's required top-level keys and nested required keys.

2. Fetch evidence from the portal.
   - Prefer full CSV downloads over paginated HTML tables.
   - Save local working extracts if useful, but base every extract on the active request and portal data.
   - Read the catalog and relevant methodology pages to confirm columns, current release policy, suppression handling, geography IDs, country aliases, and revision semantics.

3. Resolve releases and cohorts.
   - Filter each dataset by the active release status, measure, year, geography, value type, source type, and quality/validity rules before selecting one record per entity-time-measure key.
   - Apply the active release priority exactly. When a request names revision/released_at/identifier priority, use that order and its declared tie direction; protocol references give tie directions for known profiles.
   - Suppressed, blank, null, invalid, withdrawn, or scale-break values are unavailable and never zero-filled.
   - Count selected publication rows before analytic completeness exclusions only when the template requests publication counts.
   - Construct complete-case, balanced-panel, broad, strict dual-source, or machine-learning cohorts from the effective required fields. Retain entity, time, feature, cluster, fold, source-group, and grid order from the request.

4. Compute modules independently and reproducibly.
   - Rebuild all fits from scratch for each deletion, fold, bootstrap replicate, source scenario, or omitted time block.
   - Use training-only scaling inside every cross-validation or conformal refit.
   - Maintain the registered PRNG stream continuously; record checkpoints only after the requested replicate completes.
   - Pool row-level errors for RMSE/R2 unless the request explicitly says otherwise.
   - For PCA/clustering, rebuild scaling, eigensystem orientation, initialization, and label alignment in each stability refit.

5. Evaluate controlled gates.
   - Complete all modules first, then evaluate predicates on unrounded computed values.
   - Apply the request's precedence and controlled output labels exactly.
   - Use JSON booleans for booleans, integers for counts/seeds/ranks, numbers for finite real values, and `null` only when a requested statistic is mathematically unavailable.

6. Validate the final JSON before submitting.
   - Compare top-level keys, nested keys, cardinalities, enum values, numeric precision, and array alignment against `answer_template.json`.
   - Verify no `NaN`, `Infinity`, stringified numbers, extra narrative, or task-local stale values appear.
   - Recompute compact cross-checks such as cohort counts, fold counts, PRNG checkpoint count, gate count, Shapley sum, pooled coverage denominators, and set/list ordering.
