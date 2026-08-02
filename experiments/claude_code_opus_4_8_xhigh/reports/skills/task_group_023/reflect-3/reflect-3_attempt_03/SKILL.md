---
name: pho-registered-audit
description: >-
  Solve "Public Health Observatory" (PHO) registered algorithmic-audit tasks: a
  business prompt plus a formal analysis_request.json (protocol: cohorts,
  statistical modules, seeds/grids, robustness gates, decision rule) and a strict
  answer_template.json (output contract), backed by a read-only public-health
  data portal. Use this whenever a task hands you an analysis_request.json /
  answer_template.json pair that references a health-observatory Web portal and
  asks for one JSON object of resolved releases, cohorts, multi-module diagnostics,
  and a controlled decision. Covers state / county / country geographies and the
  recurring six-module audit anatomy (fixed-effects & jackknife, nested ridge /
  elastic-net CV, wild cluster bootstrap-t, grouped conformal, trajectory
  PCA + k-means + ARI, source/year perturbation & Shapley).
---

# Public Health Observatory — registered algorithmic-audit playbook

## 1. Recognise the task family

Every task in this family gives you three inputs (names may vary slightly):

- **`prompt.txt`** — business framing (who is deciding what). It is context only; the
  *authoritative* spec is the JSON payloads.
- **`payloads/analysis_request.json`** — the registered protocol. It declares the
  geography scope, analysis years / reference year, outcome / exposure / adjustment
  variables, evidence & cohort definitions, an ordered set of **audit modules**
  (each with its exact method name, cohort, feature order, seeds, grids,
  checkpoints), the **robustness gates**, and the **decision rule**.
- **`payloads/answer_template.json`** — the output contract: required top-level keys,
  per-field types, array lengths, ordering rules, identifier rules, precision, and
  cardinality constraints. Your deliverable is **exactly one JSON object** conforming
  to it, with **no narrative** outside the JSON.

Access to the evidence portal is described in the task's own access file (an
`environment_access.md` or equivalent that lists the base URL and the allowed
read-only routes). **Read that file to learn how to reach the portal in the current
environment** — do not assume routes; the portal is read-only and exposes a catalog,
geography references, per-domain data tables, a revisions table, a methodology
library, and a bulk CSV/table export. Pull the full tables once and compute locally.

**Produce the final answer JSON directly.** There is no validation or feedback service
to call at solve time; correctness comes from following the protocol exactly.

## 2. The fixed workflow

1. **Parse both payloads completely.** List every required output key and its
   constraints from `answer_template.json`; list every module, order, seed, grid, and
   threshold from `analysis_request.json`. These two lists are your checklist.
2. **Extract the portal data.** Load every relevant table in full (geography
   references, the domain health/socioeconomic/indicator tables, and the revisions
   table). Keep FIPS / ISO3 identifiers as **text** (leading zeros are meaningful).
3. **Resolve final releases** independently per cell — see
   `references/resolution_and_cohorts.md`. This is the foundation; get it exactly
   right before any modelling.
4. **Build the declared cohorts** (complete-case, primary/reference-year, balanced
   panel, ML/augmented, strict dual-source, broad reference). Report their counts and
   sorted code lists.
5. **Run each audit module** in the declared order using the method named — see
   `references/module_playbook.md`. Reproduce seeds, PRNG streams, grids, feature
   orders, and checkpoints **exactly**.
6. **Evaluate the gates and decision rule** from your computed statistics and emit the
   classification enum by the declared precedence.
7. **Serialise to the template**: exact keys, orders, lengths, precision, identifier
   casing, literal required values. Validate structure before returning.

## 3. What to read next (bundled references)

- **`references/portal_data_model.md`** — the datasets, their columns, the categorical
  vocabularies (value types, source types, release/revision/quality flags, reason
  codes), and the geography facts (regions, the 9 census divisions, RUCC bands).
- **`references/resolution_and_cohorts.md`** — the release/revision resolution
  algorithm, suppression & scale-break (anomaly) handling, country-label
  reconciliation, and every cohort pattern.
- **`references/module_playbook.md`** — one section per recurring statistical module
  with the estimator, the reproducibility knobs, and the fields it must emit.
- **`references/reproducibility_and_output.md`** — ordering, reference categories,
  transforms, precision/rounding, null policy, decision-rule mechanics, output
  discipline, and a pre-submit self-check.
- **`scripts/audit_toolkit.py`** — dependency-light, endpoint-free helper functions
  (final-revision resolution, cohort intersection, XORSHIFT32 / PCG32 generators,
  deterministic farthest-first k-means, adjusted Rand index, jackknife SE, WLS + HC3,
  nearest-rank conformal quantile, plus-one bootstrap p-value, exact Shapley). Adapt
  them to the exact method names in the request.

## 4. The five habits that decide correctness

1. **Resolution before modelling.** Almost every downstream number depends on picking
   the right FINAL record (highest applied revision), honouring suppression, and never
   zero-filling. A single mis-resolved cell shifts a whole cohort.
2. **Order is data.** The request fixes feature/coefficient/division/state/checkpoint/
   source-group orders and the template forbids re-sorting aligned arrays. Carry these
   orders literally; align cross-module arrays (e.g. a shared `state_order`).
3. **Reproduce, don't approximate, the stochastic pieces.** Bootstrap checkpoints, GMM
   steps, k-means initialisation, and Shapley enumeration follow the *named* algorithm
   with the *given* seed/stream. Match the algorithm exactly or the reproducibility
   fields will not match.
4. **Compute unrounded; round only on output.** Round only reported non-integers to the
   declared decimals; keep integers and booleans as natural JSON types; use `null` only
   when a statistic is mathematically undefined (never `NaN`/`Infinity`/zero).
5. **Sanity-check counts.** Region membership is fixed (Northeast 9, Midwest 12,
   South 17, West 13 jurisdictions incl. DC = 51). Cohort state counts should be
   consistent with the region scope; DC is included in "50 states + DC".
