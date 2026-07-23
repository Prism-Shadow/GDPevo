---
name: pho-algorithmic-transport-audit
description: Solve Public Health Observatory registered algorithmic-transport audit requests — a prompt plus analysis_request.json and answer_template.json whose evidence comes only from the Observatory Web portal. Use whenever a PHO audit task asks you to resolve portal publications/cohorts, run a declared set of reproducible statistical audit modules (delete-cluster/jackknife fixed effects or GMM/mediation, nested ridge or elastic-net CV, restricted-null wild cluster bootstrap, grouped split conformal, trajectory PCA + deterministic k-means + stability, source/year/group perturbation, partial-R2 sensitivity), and return exactly one JSON object conforming to the template. Carries method only; binds every task-local value from the effective request and never carries solved values across invocations.
---

# Public Health Observatory Algorithmic-Transport Audit

## When to use

Activate when a request consists of:

- a **prompt** directing you to the Observatory Web portal at `<TASK_ENV_BASE_URL>` (resolved from `environment_access.md`),
- an **`analysis_request.json`** declaring the audit: a `protocol_id` or `request_id`, scope (geography, years, reference year), cohorts, an ordered set of audit modules, reproducibility bindings, a `reporting` block, and a `decision_rule`,
- an **`answer_template.json`** fixing the output contract,

and asks for **exactly one JSON object** computed only from portal evidence, with no narrative.

This covers state-level, county-level, and country-level PHO audits (longevity/transport, mediation/transport, robustness/transport, panel/transport, burden-revision). Do not activate for unrelated tasks, and do not activate on family membership or subject-matter similarity alone — a declared protocol id, when present, is the exact activation key.

## Core discipline (read first)

This skill is **REUSABLE_METHOD_ONLY**. It carries method semantics, not instance values.

- **Bind everything task-local from the effective request:** entities, measures, fields, time coordinates, geography, source filters, random seed/stream/replicate schedule, hyperparameter grids, reporting cutoffs, output names, and business predicates. Never invent these from memory or carry them from any prior solved answer.
- **Never carry solved analytical values across invocations.** Recompute every coefficient, p-value, count, and label from the effective request and authorized portal evidence. Any solved standard answer present in the workspace is provenance only — it is not solver-visible input, is not expanded or required by the answer template, and is ignored by the evaluator.
- **One effective contract.** Resolve a single effective request before any data access, fold, random draw, fit, aggregation, or decision, and use it in every module.
- **Evidence only from the portal.** Reach the network only via `environment_access.md` (base URL + allowed GET endpoints). See `references/portal_evidence.md`.
- **No contamination.** If the working directory contains material outside the expected request files, stop and report rather than solving.

## Procedure

1. **Inventory and guard.** Confirm the working directory holds only the expected request files (the prompt, `analysis_request.json`, `answer_template.json`, and `environment_access.md`). Stop and write a contamination report if anything unexpected is present.
2. **Resolve the effective request** (`references/effective_request.md`). Verify the exact protocol id when declared; fold direct keys and `<section>_overrides` / `module_overrides.<module>` / `reporting_overrides` aliases; deep-merge objects, replace whole arrays, replace explicit scalars/strings/booleans/null only at their paths; inherit absent paths; reject unknown targets, array concatenation/positional patching, inferred aliases, key renaming, and type coercion. Freeze one effective contract.
3. **Read the contract.** Parse `answer_template.json` for required top-level keys, per-section required keys, array lengths and orderings, cardinality rules, enum/boolean types, and precision. The template is authoritative for field names and structure.
4. **Pull evidence** (`references/portal_evidence.md`). Fetch only the portal endpoints you need; resolve publications and geography; never zero-fill.
5. **Execute modules in declared order.** Run release/cohort resolution first, then each declared audit module, then the controlled decision. Use the shared numerical conventions in `references/numerical_conventions.md` and the module catalog in `references/module_families.md`. Preserve every declared order.
6. **Decide.** Evaluate every gate on **unrounded** values, count passes, and apply the request's decision rule (count-threshold classification or first-failed-module precedence). See `references/numerical_conventions.md` § Decision.
7. **Emit** (`references/reporting_contract.md`). Produce exactly one JSON object conforming to the template. Round reported non-integers to the declared precision; keep integers/booleans as natural JSON types; use JSON `null` only when a statistic is mathematically unavailable (never `NaN`/`Infinity`); preserve every declared list order; no narrative.

## What is reusable vs. task-local

| Reusable (this skill) | Task-local (bind from the request) |
|---|---|
| override-resolution algorithm | exact protocol_id string |
| release-resolution priority form | analysis years, reference year, geography scope |
| cohort taxonomy & construction rules | which cohorts are requested and their completeness predicates |
| module-family methods (FE/jackknife, ridge/elastic-net, wild bootstrap, conformal, PCA+kmeans+ARI, perturbation, mediation/GMM, sensitivity) | which modules, their feature/coefficient/instrument order, grids |
| PRNG families (PCG32, xorshift32) & plus-one p | chosen PRNG, seed, stream, replicate count, checkpoint schedule, quantile probabilities |
| numerical conventions (CR1/HC3/WLS, RMSE pooling, rank intervals, ARI) | cutoffs, thresholds, classification vocabulary |
| reporting discipline | numeric precision (4 or 6 dp), exact field names |

## References

- `references/effective_request.md` — protocol gating and override merge
- `references/portal_evidence.md` — portal access, data model, release resolution, cohorts
- `references/numerical_conventions.md` — shared math across all modules + decision
- `references/module_families.md` — the recurring audit modules and their registered variants
- `references/reporting_contract.md` — precision, ordering, null, JSON shape
