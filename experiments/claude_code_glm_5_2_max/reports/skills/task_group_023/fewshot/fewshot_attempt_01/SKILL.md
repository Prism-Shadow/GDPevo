---
name: pho-algorithmic-audit
description: Solve Public Health Observatory (PHO) registered algorithmic audit tasks. Fetch evidence from the read-only PHO Web portal, resolve final releases/revisions, build cohorts, run the declared deterministic statistical modules in order, apply the controlled decision, and emit exactly one JSON object conforming to answer_template.json. Use when a task provides analysis_request.json + answer_template.json and references the PHO portal (TASK_ENV_BASE_URL), asking for a reproducible multi-module audit (release/cohort resolution, regression/ridge/elastic-net, wild bootstrap, conformal, PCA/clustering, perturbation/sensitivity/mediation) ending in a controlled classification.
---

# PHO Algorithmic Audit

This skill solves **Public Health Observatory (PHO) registered algorithmic audit**
tasks. Every such task asks the same thing in different clothing: pull auditable
evidence from the read-only PHO Web portal, resolve one final publication per
declared key, build the declared cohorts, run a fixed sequence of deterministic
statistical modules, evaluate controlled decision gates, and return **one JSON
object** that conforms exactly to `answer_template.json`.

The method is reusable. The numbers are not. Re-derive every value for the
invocation at hand from the portal and the effective request — never carry a
solved coefficient, p-value, entity list, count, or classification across tasks.

## When to activate

Activate when **all** are present:

- A prompt referencing the Public Health Observatory portal at `<TASK_ENV_BASE_URL>`.
- `analysis_request.json` declaring a `protocol_id` (or equivalent request id), a
  geography/year scope, an outcome/exposure, an evidence specification, a set of
  named audit modules each with a `method`/`standard_method` and parameters, and a
  `decision_rule` / `controlled_*` mapping.
- `answer_template.json` fixing the output contract (keys, types, array orders,
  precision, enum/boolean rules).
- `environment_access.md` giving the portal base URL and allowed endpoints.

Do not activate on mere similarity of subject matter — match the task shape above.

## Inputs you must read, in order

1. `environment_access.md` — portal base URL (`GDPEVO_ENV_BASE_URL`) and the
   allow-list of endpoints. **This is the only way to reach the running
   environment.** Use only the listed endpoints over the network.
2. `analysis_request.json` — the registered request. Identify: `protocol_id`,
   geography scope, analysis years, reference/primary year, outcome, exposure(s)
   and any mediator, the evidence specification (release method, filters, revision
   priority, validity, missing rule), the cohort definitions, every named module
   with its method + parameters + `required_evidence`, and the decision rule.
3. `answer_template.json` — the response contract. Note required keys, types,
   array lengths, declared orderings, precision, enum/boolean rules, and any
   `global_rules` / `template_instructions`.

Read every payload in each train example when learning; for a live task, read the
one request/template pair supplied.

## Procedure

### 1. Resolve one effective request first
Before touching any data, fold any overrides/canonical defaults into a single
**effective request** and freeze it. See
[`references/request_and_release.md`](references/request_and_release.md) for the
override-resolution rules (direct keys, `<section>_overrides` /
`module_overrides.<name>` / `reporting_overrides` aliases, deep-merge objects,
replace-whole arrays, reject renames/coercions/unknown targets). One contract,
used identically by every module.

### 2. Fetch portal evidence
Reach the portal only through `environment_access.md`. Pull the catalog for
schema, then fetch the rows you need as CSV via
`/download?dataset=<name>&format=csv&<filter>=<value>&...`. Pull `/methodology`
for release/suppression/value-type/label rules and `/data/revisions` for revision
events. See [`references/portal.md`](references/portal.md) for the dataset
catalog, columns, filters, and gotchas (leading-zero FIPS, country label aliases,
superseded methodology docs, direct-vs-rollup sources).

### 3. Resolve releases and build cohorts
For each requested measure×year×geography×value-type×source, filter to the
declared status/source/value-type/validity, then select **one** record per
declared entity-time key using the **declared release priority order**
(revision → release timestamp → record id; the record-id tie-break *direction is
task-local* — read it from the request). Suppressed/invalid/withdrawn/blank/null
analytic values are unavailable and are **never zero-filled**. Then construct each
declared cohort (complete-case, balanced panel, broad, dual-source, ML) from its
required fields, preserving entity-code-then-time order and every declared
feature/group order. Details in
[`references/request_and_release.md`](references/request_and_release.md).

### 4. Run the modules in declared order
Execute modules in the request's declared order (typically: release/cohort first,
then analytic modules, then the controlled decision). Each module's exact
algorithm is the **reusable method** in
[`references/module_methods.md`](references/module_methods.md): two-way fixed
effects / weighted OLS / HC3 / CR1 cluster variance, delete-one-cluster jackknife,
GMM / difference-GMM mediation, nested leave-one-group-out ridge / elastic-net,
wild cluster bootstrap (PCG32-Webb or xorshift32-Rademacher), grouped split
conformal, covariance PCA (Jacobi), deterministic k-means + silhouette, ARI
stability, source/year/group perturbation + exact Shapley, partial-R²
sensitivity, and the country reconciliation/quality-audit variant. Bind every
parameter (seed, stream, replicate schedule, grids, cutoffs, feature order) from
the effective request — do not invent or reuse values.

### 5. Evaluate the controlled decision
Complete **every** module first. Evaluate every business predicate on **unrounded**
values, preserve the declared gate order, count satisfied predicates, and apply
**only** the request's classification mapping and precedence/tie rules. See
[`references/reporting_and_decision.md`](references/reporting_and_decision.md).

### 6. Emit the answer
Return exactly **one JSON object** conforming to `answer_template.json`: every
required key, declared array order, declared precision (round only reported
fields), natural JSON types for integers/booleans, exact enum/identifier casing,
`null` only where a statistic is mathematically unavailable (never `NaN` /
`Infinity`). No narrative outside the JSON.

## Hard constraints

- **Recompute, don't recall.** Never copy a solved value, entity list, count, or
  classification from any example. The standard answers are method illustrations,
  not a lookup table.
- **Determinism is the deliverable.** Use the exact declared PRNG, seed, stream,
  draw order, ordering, and tie-breaks. One continuous PRNG stream per bootstrap;
  record checkpoints only after the listed replicate completes; never reset.
- **Order is sacred.** Preserve every declared order (entity, time, feature,
  group, coefficient, grid, checkpoint, source). Never independently re-sort an
  aligned array.
- **Precision discipline.** Evaluate gates and select extrema on unrounded values;
  round only when reporting. Honor the task's decimal-places rule (commonly 4;
  some tasks use 6 for computed reals and 4 for literal grid/threshold values).
- **Missing means missing.** Suppressed/invalid/blank/null analytic values are
  unavailable; never zero-fill, never impute unless the request's quality-audit
  module explicitly authorizes it.
- **Portal only.** No evidence from outside the PHO portal; no endpoint outside
  `environment_access.md`'s allow-list.

## Optional provenance

Standard answers frequently include a top-level `protocol_registry_record`
containing a `portable_protocol_profile` (`classification: REUSABLE_METHOD_ONLY`).
It is **optional provenance, ignored by the evaluator**, never solver-visible
input, and never expanded by the template. You may omit it. If you include it,
carry method semantics only — never task-local solved values — and keep it
consistent with the effective request's `protocol_id`.

## References

- [`references/portal.md`](references/portal.md) — dataset catalog, columns,
  filters, CSV download, methodology, revisions.
- [`references/request_and_release.md`](references/request_and_release.md) —
  override resolution, release/revision resolution, cohort construction.
- [`references/module_methods.md`](references/module_methods.md) — reusable
  algorithms for every audit module family.
- [`references/reporting_and_decision.md`](references/reporting_and_decision.md) —
  reproducibility, precision/null rules, controlled decision.
