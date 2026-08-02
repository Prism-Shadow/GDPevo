---
name: pho-algorithmic-audit
description: >-
  Solve Public Health Observatory (PHO) reproducible / transportability /
  robustness / mediation audit tasks that ship an analysis_request.json plus an
  answer_template.json and require pulling evidence only from the read-only PHO
  web portal named in environment_access.md (<TASK_ENV_BASE_URL>). Use whenever
  a task asks for a "registered audit", "algorithmic transportability audit",
  "six-module audit", "robustness gates", "controlled decision/classification",
  release/revision resolution, cohort construction, or deterministic statistical
  modules (fixed effects, ridge/elastic-net nested CV, wild cluster bootstrap-t,
  split/grouped conformal, trajectory PCA + k-means, GMM, Shapley, partial-R2
  sensitivity) whose result must be returned as ONE JSON object conforming to a
  supplied answer template.
---

# PHO Algorithmic Audit

## 1. What this family of tasks is

Each task is a self-contained analytical audit for the fictional **Public Health
Observatory**. You are given, per task:

- `input/prompt.txt` — the business framing and the pointer to the portal.
- `input/payloads/analysis_request.json` — the **authoritative specification**:
  scope, measures, filters, cohort definitions, module list, hyperparameters,
  seeds, reproducibility rules, gate thresholds, and decision mapping.
- `input/payloads/answer_template.json` — the **output contract**: exact top-level
  keys, per-field types, array lengths/orderings, enum vocabularies, and precision.
- `environment_access.md` (repo root) — the base URL and endpoint list for the
  live portal. **This is the only channel to the data.** There is no bundled
  dataset; every number must be recomputed from portal evidence.

The deliverable is **exactly one JSON object** matching `answer_template.json`,
with **no narrative outside the JSON**.

**Nothing about the specific analysis is fixed across tasks.** Geography
(states / counties / countries), measures, years, filters, module set, feature
orders, grids, seeds, gate cutoffs, decision labels, and output key names all
change per task. Read them fresh from *this* task's `analysis_request.json` and
`answer_template.json` every time. Never carry a value, cohort, coefficient,
count, or parameter from a previous task or example into a new answer.

## 2. Golden rules

1. **The request and the template are law.** If they disagree with these notes,
   or with a prior task, they win. Bind every entity, measure, filter, order,
   grid, seed, tolerance, cutoff, threshold, and output name from them.
2. **Portal is the sole evidence source.** Pull data over the network from the
   endpoints in `environment_access.md`. Do not invent, cache stale, or
   zero-fill values.
3. **Determinism.** Every module is specified to be exactly reproducible: fixed
   release-resolution order, fixed tie-breaks, fixed PRNG, fixed iteration/
   convergence rules, fixed orderings. Implement them literally so two correct
   runs produce identical digits.
4. **Missing ≠ zero.** Suppressed, invalid/withdrawn-flagged, blank, or null
   values are *unavailable*. Exclude the record/cell per the cohort rule; never
   substitute 0. Emit JSON `null` only when a requested statistic is
   mathematically undefined — never `NaN`/`Infinity`.
5. **Preserve declared order.** Aligned arrays (state_order, feature_order,
   division_order, checkpoints, subset_order, …) must keep the request/template
   order and stay positionally aligned with their companions. Do not
   independently sort one array of an aligned set.
6. **Round only at the end.** Compute on unrounded values (gate comparisons,
   extrema selection, medians included), and round only the reported fields to
   the template's precision (commonly 4 dp; some tasks 6 dp for computed reals
   and 4 dp for literal grids/thresholds).
7. **Output shape is precise.** Include exactly the required top-level keys,
   every required child key, correct JSON types (integers/booleans as natural
   types), and only allowed enum values.

## 3. Workflow

Work top-down; do not start a module until the effective request is frozen.

1. **Read all inputs.** Parse `prompt.txt`, `analysis_request.json`, and
   `answer_template.json`. List the requested modules, their cohorts, the
   reproducibility parameters, the gate predicates, and the decision mapping.
   Then map every template field to the module/step that produces it.
2. **Freeze the effective request.** Most requests are used directly. If the
   request carries a `protocol_id` and/or `*_overrides` keys, resolve overrides
   before any computation using the deterministic merge rules in
   `references/output-contract.md` (deep-merge objects, replace arrays whole,
   replace explicit scalars/null at their path, inherit absent paths; reject
   unknown targets and type coercions). Freeze one contract used by every module.
3. **Discover the portal.** Hit `/catalog` (dataset columns + measure
   dictionary), `/methodology` (release lifecycle, suppression, direct-vs-rollup,
   quality flags, label reconciliation), and the relevant
   `/geographies/{states,counties,countries}` reference (region, census
   `division`, `rucc`, ISO3, alternate labels). See `references/portal.md`.
4. **Resolve releases.** For each requested measure/field, pull the dataset via
   the CSV download endpoint with server-side filters, then select **one record
   per (entity, year, measure[, value_type, source_type]) key** by the declared
   priority — canonically **greatest `revision` → latest `released_at` → then
   lowest/greatest record id** exactly as the request states. Apply status,
   value_type, source_type, and validity filters. Count selected publications
   *before* analytic-completeness exclusions when the template asks for release
   counts.
5. **Build cohorts.** Construct each named cohort (complete-case / balanced /
   broad / dual-source / machine-learning / primary, etc.) strictly from its
   declared required fields and validity predicates. Join independently resolved
   series on stable entity+time keys. Preserve entity-code then time order.
   Report cohort sizes, excluded entity codes, and per-year counts as the
   template requires.
6. **Run each module.** Implement each declared method with the exact linear
   algebra, standardization, folding, PRNG, tie-break, and aggregation rules in
   `references/methods.md`. Reuse shared fitted objects where the request says
   downstream modules draw on them. Keep every requested checkpoint/diagnostic.
7. **Decide.** Evaluate each gate/flag predicate on **unrounded** module
   outputs, count satisfied gates, and apply the request's controlled decision
   mapping and precedence (first-failed-module, count thresholds, tie rules)
   exactly. Preserve the declared gate-reporting order.
8. **Assemble & validate output.** Emit one JSON object with exactly the
   template's keys, orders, types, enums, and precision. Verify array lengths,
   positional alignment, integer/boolean typing, and that no `NaN`/`Infinity`
   leaked in. Print only the JSON. See `references/output-contract.md`.

## 4. Recurring building blocks (bind specifics from the request)

These appear across tasks; their names and parameters vary, so read them from
the request. Full deterministic specs are in `references/methods.md`.

- **Release/revision resolution & cohorts** — filter, dedupe to one final
  record per key, complete-case/balanced/panel construction.
- **Two-way fixed effects / WLS / OLS** — double-demeaning, reliability weights,
  design column order; **HC3** and **CR1 cluster-robust** covariance.
- **Delete-one cluster jackknife** — bias-corrected coefficient, jackknife SE/t,
  influence / max percent-change extrema.
- **Nested leave-group-out ridge / elastic-net CV** — training-only
  standardization, coordinate descent, pooled row-level RMSE selection, OOF
  metrics (RMSE/MAE/R²/Q²).
- **Wild cluster bootstrap-t** — restricted null, cluster weights, a specified
  PRNG (**PCG32** or **xorshift32**), plus-one p-value, checkpointed streams,
  order-statistic/quantile conventions.
- **Split / grouped / cross-fold conformal** — calibration selection, rank-based
  radius `q`, inclusive intervals, coverage & mean-width aggregation.
- **Trajectory PCA + deterministic k-means** — covariance PCA (Jacobi),
  eigenvalue ordering + loading orientation, farthest-first Lloyd k-means,
  silhouette selection, leave-year/leave-entity **adjusted Rand index** stability.
- **GMM (difference / two-step)**, **mediation delta method**, **exact Shapley**
  attribution, **partial-R² sensitivity surface** — as declared.
- **Controlled decision** — gates on unrounded values → classification by
  precedence.

## 5. Reference files

- `references/portal.md` — endpoints, datasets/columns, filters, the CSV
  download pattern, release-resolution and quality/revision/label semantics.
- `references/methods.md` — deterministic specifications of every recurring
  statistical module, including both PRNGs and all tie-breaks.
- `references/output-contract.md` — how to read the template variants, the
  precision/ordering/null rules, override resolution, and the optional
  `protocol_registry_record` provenance block (evaluator ignores it; it is
  **not** required and you should not fabricate it or leak task values into it).

## 6. Pitfalls

- Do **not** reuse a prior task's module list, feature order, seed, grid, gate
  cutoff, or output keys — they are task-local.
- Do **not** page-scrape truncated HTML tables when a full CSV export exists; use
  `/download?dataset=…&format=csv&<filters>`.
- Do **not** treat suppressed/withdrawn/blank as 0, and do **not** silently swap
  a county-rollup/parallel estimate for a direct-survey record.
- Do **not** round before comparing to gates, taking medians, or picking extrema.
- Do **not** independently sort one member of an aligned array set.
- Do **not** emit anything but the single JSON object required by the template.
