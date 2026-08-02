---
name: pho-algorithmic-audit
description: >-
  Solve a Public Health Observatory (PHO) "algorithmic audit" analysis task: given a
  task folder with prompt.txt, payloads/analysis_request.json, payloads/answer_template.json,
  and environment_access.md, fetch evidence from the read-only PHO web portal, resolve
  releases/revisions and cohorts, run the declared statistical audit modules with exact
  reproducibility, apply the controlled decision rule, and emit one JSON object conforming
  to answer_template.json. Use when the request references the PHO portal
  (<TASK_ENV_BASE_URL>, GDPEVO_ENV_BASE_URL, /catalog, /data/state-health, /data/county-health,
  /data/country-indicators, /data/revisions), a protocol_id like PHO_STATE_*/PHO_COUNTY_*,
  a six-module robustness/transportability/mediation audit, or a country burden
  reconciliation + PCA/cluster/panel briefing. Triggers: "Public Health Observatory",
  "transportable longevity signal", "registered audit", "robustness gates", "wild cluster
  bootstrap", "nested ridge/elastic-net", "grouped conformal", "trajectory PCA clustering",
  "delete-one jackknife", "difference GMM mediation", "burden PCA".
---

# PHO Algorithmic Audit Solver

## What this is

Each task in this family gives you an *analysis request* (a registered statistical
protocol) and an *answer template* (the exact output contract), and points you at one
read-only web portal (the Public Health Observatory) as the only authorized evidence
source. Your job is to recompute — from the live portal data — a large, fully-ordered
package of statistics and a final controlled classification, and return it as one JSON
object that matches the template exactly.

The numbers are *deterministic*: every task pins the seeds, grids, orders, tolerances,
and cutoffs needed to reproduce one canonical answer. There is no room for approximation
in PRNG streams, fold assignment, tie-breaking, rounding, or list order. Treat the whole
thing as a reproducibility exercise: implement the declared primitives precisely and
bind every task-specific value from the request and template — never hardcode a value
carried from any other instance.

## Inputs you are given (per task)

- `prompt.txt` — the business framing and the portal placeholder `<TASK_ENV_BASE_URL>`.
- `payloads/analysis_request.json` — the registered protocol: scope, measures, filters,
  cohorts, per-module methods + parameters, reporting rules, and the decision rule.
- `payloads/answer_template.json` — the authoritative output contract: required keys,
  array lengths, ordering rules, precision, identifier rules, enum vocabularies,
  null policy. **The template wins on output shape; the request wins on how to compute.**
- `environment_access.md` — the portal base URL (`GDPEVO_ENV_BASE_URL=...`) and the list
  of GET endpoints. Use it *only* to reach the environment over the network.

## End-to-end procedure

1. **Read all four inputs.** Substitute the real base URL from `environment_access.md`
   for every `<TASK_ENV_BASE_URL>` placeholder.

2. **Classify the task shape** (both are handled below and in the references):
   - **Six-module audit** — the request has a `protocol_id` (e.g. `PHO_STATE_*`,
     `PHO_COUNTY_*`) and an `audit_modules`/module block plus a `decision_rule`. Output
     keys are a cohort block + six module blocks + a decision block.
   - **Cross-section + panel briefing** — no `protocol_id`; template keys look like
     `reconciliation`, `quality_audit`, `pca`, `clusters`, `panel_model`, `advisory`.
   Read `references/output_contract.md` to map the template to the shape.

3. **Freeze one effective request before any computation.** If the request carries a
   `protocol_id` and/or `*_overrides` keys, resolve them into a single effective contract
   using the override rules in `references/release_and_cohorts.md` (§ Effective request).
   Do all data access, folding, random draws, fits, and decisions against that frozen
   contract, used identically in every module.

4. **Fetch evidence from the portal.** Pull the datasets you need as CSV and cache them
   locally, then compute offline. Endpoints, dataset schemas, and the download recipe are
   in `references/portal.md`. Do not invent data; use only portal records.

5. **Resolve releases/revisions and build the declared cohorts.** Filter and de-duplicate
   to one selected record per entity–time–measure key, then construct each named cohort
   (primary / balanced / broad / machine-learning / strict / dual-source). Emit the cohort
   audit fields. Rules: `references/release_and_cohorts.md`.

6. **Run each declared module** in the request's module order, binding every knob (seed,
   grid, order, tolerance, ddof, quantile method, tie-break, weight) from the effective
   request. Exact primitive definitions: `references/methods.md` and `references/prng.md`.
   Keep every intermediate value **unrounded**.

7. **Apply the controlled decision** on unrounded values, in the declared precedence,
   and map it to the template's decision/enum vocabulary. Rules: end of
   `references/methods.md` (§ Controlled decision).

8. **Assemble and validate the answer.** Produce exactly the template's required keys, in
   the declared order, at the declared precision, with declared identifiers, enums, and
   null policy. Self-check every `array_length`, `cardinality`, and enum before emitting.
   Output **one JSON object and nothing else** (no prose, no markdown fence).

## Non-negotiable discipline (read before coding)

- **Bind, never carry.** Entities, measures, years, sources, seeds, replicate schedules,
  grids, tolerances, decision cutoffs, output names, and enum vocabularies come from *this*
  request/template. The reference files describe *methods*, not answers — they contain no
  task answer values, and you must not paste any either.
- **Compute unrounded; round only at output.** Every predicate, tie-break, quantile,
  selection, and aggregate uses full-precision values. Apply the template's decimal
  precision only when writing the field. Different fields can have different precision
  (e.g. computed reals to 6 dp, literal grids/thresholds to 4 dp) — follow the template.
- **Preserve every declared order.** State/entity order, feature order, division/group
  order, lambda grid order, checkpoint order, subset order, source-group order, coefficient
  order — aligned arrays must line up positionally. Never independently sort an aligned array.
- **Missing is missing.** Suppressed, invalid, withdrawn, blank, or null values are
  *unavailable*; never zero-fill them and never treat a suppressed value as 0.
- **Determinism is exact.** PRNG state, weight maps, fold assignment, farthest-first
  initialization, Jacobi/rotation tie rules, empty-cluster handling, and label alignment
  must match the declared recipe bit-for-bit. When a method text offers a choice (e.g.
  sample vs population SD, nearest-rank vs type-seven quantiles, lowest vs greatest id
  tiebreak, `b/SE` vs `b_BC/SE` for the jackknife test), take the variant the effective
  request's method text specifies — do not default silently.
- **The provenance block is optional and ignored.** Standard answers may embed a
  `protocol_registry_record` for provenance; the evaluator ignores it and the template does
  not require it. Spend no effort on it — compute and emit the *required* keys correctly.
  If you include one, it must never stand in for a computed result.

## Suggested implementation

Write a single deterministic program (Python is convenient) that: downloads the needed
CSVs once; resolves the effective request; builds cohorts; implements each module's
primitives from `references/methods.md`/`references/prng.md` using only exact arithmetic
(no library RNG, no library ridge/EN unless you match its objective and scaling exactly);
assembles the output dict in template order; validates lengths/enums/cardinality; and
prints one JSON object. Re-run and diff to confirm determinism before submitting.

## Reference files

- `references/portal.md` — endpoints, dataset schemas, CSV download recipe, revisions,
  measure dictionary, geography references.
- `references/release_and_cohorts.md` — effective-request/override resolution, release &
  revision selection, cohort construction, missing/validity rules, country reconciliation.
- `references/methods.md` — the numerical method library (linear algebra & inference,
  penalized CV, wild cluster bootstrap, grouped conformal, trajectory PCA + k-means + ARI,
  GMM, exact Shapley, partial-R² sensitivity, cross-section PCA/panel) and the controlled
  decision.
- `references/prng.md` — exact PCG32 and xorshift32 definitions and their weight maps.
