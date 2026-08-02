---
name: pho-algorithmic-audit
description: >-
  Solve Public Health Observatory (PHO) registered algorithmic-audit tasks. Use
  when a task gives an analysis_request.json plus an answer_template.json and
  points to a read-only PHO web portal (state/county/country health &
  socioeconomic data), asking for a multi-module statistical audit —
  release/cohort resolution, fixed-effects / GMM / ridge / elastic-net,
  nested cross-validation, wild cluster bootstrap-t, split/grouped conformal,
  trajectory PCA + deterministic k-means stability, source perturbation /
  Shapley — returned as one JSON object conforming to the template. Recompute
  every value live from the portal; never reuse numbers across tasks.
---

# PHO algorithmic audit

You are handed three things per task:

- `prompt.txt` — the business framing and the portal reference `<TASK_ENV_BASE_URL>`.
- `payloads/analysis_request.json` — the **registered spec**: bindings (entities,
  measures, years, sources, filters), the ordered audit **modules** (each with a
  `method` name and `required_evidence`), reporting rules, and the
  **decision rule**.
- `payloads/answer_template.json` — the **response contract**: exact top-level
  keys, per-field types, array lengths/orderings, enum values, precision.

Deliverable: **exactly one JSON object** conforming to the template, with no
narrative outside it. This is a reproducibility audit — a favorable headline
coefficient is never sufficient; the grader checks the full ordered evidence and
every checkpoint, so numbers must match a specific deterministic recipe.

## Golden rules

1. **The request is law; recompute everything.** Bind every entity, measure,
   field, year, source, seed, grid, tolerance, threshold, PRNG, model form,
   order, and decision mapping from *this* request. Do not hardcode or carry over
   any value from another task or from these instructions.
2. **The portal is the only evidence.** Pull live via `/download?...&format=csv`.
   See `references/portal.md`.
3. **Resolve one effective request first**, then use it consistently across all
   modules (data access, folds, draws, fits, decisions).
4. **Full precision until reporting.** Carry unrounded values through every
   computation. Round only when emitting a field, to the declared decimals.
   **Evaluate every decision predicate/gate on unrounded values.**
5. **Preserve every declared order** (entity code → time; feature; group;
   cluster; checkpoint). Never independently re-sort an aligned array; positional
   alignment between arrays (e.g. scores ↔ state_order) is graded.
6. **Missing means unavailable, never zero.** Suppressed / invalid / withdrawn /
   blank / null values are excluded, never zero-filled. Emit JSON `null` only
   when a statistic is mathematically undefined — never `NaN`/`Infinity`.
7. **Match the contract exactly:** required keys, array lengths, enum spellings,
   integer-vs-number-vs-boolean types, and identifier casing (uppercase state
   codes / ISO3; portal division & region names verbatim).
8. **Output only the template keys.** A `protocol_registry_record` provenance
   block is optional, method-only, and ignored by the grader — do not let it
   substitute for, or perturb, the required analytical keys.

## Workflow

1. **Connect & orient.** Read `environment_access.md` for the base URL. `GET /`,
   `/catalog` (confirm datasets/columns/measure dictionary), and the relevant
   `/methodology` docs — methodology rules bind validity, suppression, revision,
   and release semantics and *change the numbers*.
2. **Parse both payloads.** Enumerate the ordered modules and their
   `method`/`required_evidence`; map every template field to the module and
   statistic that produces it, noting length/order/precision/enum constraints.
   Resolve overrides if a `protocol_id` is present (see `references/methods.md`).
3. **Resolve releases.** For each publication cell apply the effective filters
   and the declared selection priority (greatest revision → latest `released_at`
   → the declared id tie-break). Count selected publications before completeness
   exclusions when asked. (`references/methods.md` §1.)
4. **Build cohorts.** Join resolved series on entity+time; construct each named
   cohort (complete-case / balanced panel / broad reference / strict dual-source)
   from its required-field predicates; preserve order; record sizes/exclusions.
   (§2.)
5. **Run each module in order**, following the matching recipe in
   `references/methods.md` and honoring any formula/order/tie-break the request
   or a methodology doc states explicitly (it overrides the default). Keep the
   fitted objects; downstream modules (bootstrap, conformal, sensitivity,
   perturbation) reuse them.
6. **Decide.** Evaluate each gate on unrounded values in reporting order, then
   apply the request's exact decision mapping / precedence and enum values. (§13.)
7. **Assemble & self-check** (below), then emit the single JSON object.

## Module → recipe map

Match the request's `method` strings to `references/methods.md`:

| Request method (varies) | Recipe |
|---|---|
| release resolution / publication selection | §1 |
| cohort / balanced-panel / dual-source construction | §2 |
| two-way fixed-effects OLS, delete-one jackknife | §3, §4 |
| weighted regression, HC3 / CR1 inference | §5 |
| nested ridge / elastic-net leave-group-out CV | §6 |
| wild cluster bootstrap-t (PCG32 or xorshift32) | §7 |
| split / grouped conformal calibration | §8 |
| trajectory PCA + deterministic k-means + ARI / silhouette | §9 |
| two-step linear GMM (Hansen J, difference GMM) | §10 |
| source / source-year perturbation, exact Shapley | §11 |
| partial-R² mediation sensitivity surface | §12 |
| controlled decision / precedence | §13 |

Not every task uses every module, and future tasks may name a method not listed.
When that happens, implement it from its `required_evidence` and any cited
methodology doc, applying the same disciplines (deterministic tie-breaks,
training-only scaling, single continuous PRNG stream, unrounded decisions,
declared orders).

## Self-check before submitting

- Top-level keys == template's `required_top_level_keys` (plus optional ignored
  provenance); no extras, none missing.
- Every array has the declared length and order; positionally-aligned arrays line
  up (e.g. `delete_*_coefficients` ↔ `state_order`; PC scores/labels ↔ order).
- Non-integers rounded to the declared decimals **and encoded as JSON numbers**;
  counts/ranks/seeds/PRNG-states/replicates are integers; flags are booleans.
- Enum fields use an allowed spelling exactly; identifiers are correctly cased.
- `null` only for mathematically-unavailable stats; no `NaN`/`Infinity`.
- Gate booleans, passed-count, and classification are internally consistent and
  derived from unrounded statistics.
- Output is a single valid JSON object with no surrounding text.

## Reference files

- `references/portal.md` — reaching the portal, `/download` usage, dataset
  schemas, methodology library.
- `references/methods.md` — the canonical, parameter-bound recipes (§1–§13) and
  the override/binding-resolution rules.
