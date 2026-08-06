---
name: pho-algorithmic-audit
description: >-
  Solve Public Health Observatory (PHO) "registered algorithmic audit" analysis tasks —
  the ones that hand you a prompt.txt plus payloads/analysis_request.json and
  payloads/answer_template.json and point you at a read-only web data portal
  (a "<TASK_ENV_BASE_URL>" placeholder; a Public Health Observatory / Observatory data
  portal with /catalog, /methodology, state_health, county_health, country_indicators,
  socioeconomic, and revisions datasets). Use it whenever the request asks for a
  publication/cohort audit followed by a fixed roster of ~6 statistical "modules"
  (fixed-effects or GMM jackknife, nested ridge/elastic-net cross-validation, wild cluster
  bootstrap-t, grouped split conformal, trajectory PCA + k-means stability, source/year
  perturbation or Shapley, mediation, sensitivity surfaces) and a gated PASS/FAIL decision
  or classification, returned as one strict JSON object conforming to the answer template.
---

# PHO algorithmic-audit solver

These tasks look intimidating but are highly templated. A prompt sets a business question;
`analysis_request.json` registers a cohort/publication spec plus ~6 audit **modules** and a
**decision rule**; `answer_template.json` fixes the exact response contract. Your job is to
pull evidence from the read-only portal, reconstruct each registered design exactly, and
emit one JSON object. There is **no oracle to call while solving** — you compute everything
from the portal and the request.

## What you're given (the three inputs)

- **`prompt.txt`** — the business framing and the portal base URL placeholder. Narrative
  only; the real spec is in the JSON payloads.
- **`payloads/analysis_request.json`** — the authoritative spec: geography scope, years,
  outcome/exposure, release & cohort rules, each module's method + ordered features/grids/
  seeds + required evidence, and the decision thresholds/precedence.
- **`payloads/answer_template.json`** — the output contract: required top-level keys,
  per-block required keys, array lengths, cardinality/ordering rules, precision, enums.

## Workflow

1. **Orient on the portal.** Fetch `/catalog` and `/methodology` (relative to the base URL
   your task gives you). The catalog self-describes every dataset (columns, filters, CSV
   export, measure dictionary); methodology states the governing publication rules. Pull
   the datasets you need as CSV and load them (keep FIPS/ISO3 as text).
   → `references/data_model.md`, helper `assets/portal.py`.

2. **Build the foundation** — resolve the registered FINAL release per cell (FINAL → highest
   revision → latest `released_at` → id), apply availability (drop suppressed / null /
   task-invalid quality flags; **never zero-fill**), apply revision notices, then assemble
   the exact complete-case cohorts (per-year, balanced panel, reference/broad, strict,
   machine-learning). Join region/division/RUCC from the geography tables. This block is
   the answer template's first section and every downstream number depends on it — verify
   its integer counts and complement (excluded-code) sets carefully.
   → `references/release_and_cohorts.md`.

3. **Reconstruct each module** in the exact registered design order, transforms, grids,
   seeds and inference conventions (HC3 / CR1 SEs; named PRNG implemented bit-exactly;
   training-only standardization; covariance PCA with deterministic loading signs;
   deterministic k-means; plus-one bootstrap p-values; leave-group-out CV/conformal; exact
   Shapley). Emit each module's evidence with the template's array lengths and alignment.
   → `references/module_playbook.md`.

4. **Derive the gated decision.** Turn each module's result into its gate boolean using the
   declared threshold, count passes, and map to the classification via the declared
   precedence. This enum is a high-value, self-contained field — get the inequalities and
   precedence exactly right even if some interior numbers are approximate.

5. **Format & self-check** against the template: one JSON object, exact keys, array lengths,
   alignment, complement sets, types/enums, declared precision, `null` only for
   mathematically-undefined values, no narrative outside the JSON. Validate programmatically.
   → `references/output_contract.md`.

## Method priorities (where the points are)

- **Foundation first.** Cohort/census counts and excluded sets are exactly derivable and
  anchor everything; a wrong cohort silently corrupts every module. Nail step 2 before
  fitting anything.
- **Shape before magnitude.** Satisfy every array length / ordering / cardinality /
  type / enum rule — the grader scores leaves, so a complete, correctly-shaped answer with
  right counts and a correctly-derived decision scores even where deep numerics drift.
- **Determinism.** Every "seed", "initialization", "priority", "order" in the request is
  there to make the result reproducible — implement each convention exactly and, where the
  prose under-specifies, choose the most standard textbook definition and make it
  deterministic.
- **Read units & direction** from the measure dictionary before asserting a coefficient's
  sign in a gate.

## Reusable assets

- `assets/portal.py` — portal-agnostic loader + `resolve_final` (registered FINAL
  resolution), `available` (suppression/quality masking), and country label→ISO3
  reconciliation. Point it at your task's base URL; it contacts nothing else.
- `references/data_model.md` — datasets, columns, publication semantics, revisions, labels.
- `references/release_and_cohorts.md` — release resolution and the cohort archetypes.
- `references/module_playbook.md` — the recurring module family and exact conventions.
- `references/output_contract.md` — formatting rules, the gated decision, and a self-check.

## Pitfalls

- Resolving before filtering to the requested `value_type`/`source_type`/`release_status`.
- Treating suppressed/missing as zero, or letting a null socio field drop a whole record.
- Hardcoding a division/region map instead of reading it from the geography tables.
- Re-sorting an aligned result array, or emitting a set where an ordered list is required.
- Forgetting a transform (`_per_10000`, `log`, first-difference/lag) or the category
  reference level, so the design matrix is subtly wrong.
- Rounding before computing, or reporting the wrong decimal precision per field.
- Emitting the template's descriptor scaffolding instead of concrete values.
