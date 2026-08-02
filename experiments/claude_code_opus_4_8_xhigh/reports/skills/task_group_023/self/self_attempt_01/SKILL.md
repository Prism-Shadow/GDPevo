---
name: pho-registered-algorithmic-audit
description: >-
  Operating manual for completing a Public Health Observatory (PHO) "registered
  algorithmic audit" task. Use whenever the prompt asks you to audit a public-health
  association/mediation/trajectory signal using the read-only PHO Web portal at
  <TASK_ENV_BASE_URL>, resolve FINAL releases/revisions into cohorts, run a fixed
  set of registered statistical modules (cluster jackknife / two-way FE / GMM,
  nested leave-group-out ridge or elastic-net CV, restricted-null wild cluster
  bootstrap-t, grouped split-conformal calibration, trajectory PCA + deterministic
  k-means with leave-one-out ARI, and source/year/sensitivity perturbation), apply
  declared gates and a precedence decision rule, and return ONE JSON object that
  conforms exactly to answer_template.json. Triggers: "Public Health Observatory",
  "registered ... audit", "analysis_request.json", "answer_template.json",
  "transportable ... signal", "state-health/county-health/country-indicators",
  "REGISTERED_FINAL_RELEASE_RESOLUTION", "wild cluster bootstrap", "split conformal",
  "trajectory PCA", "adjusted Rand index", modules that must each PASS/FAIL a gate.
---

# Public Health Observatory — Registered Algorithmic Audit

This skill is a reusable playbook for a recurring task family. Each task hands you three
inputs and one authoritative data source:

- `input/prompt.txt` — the business framing and the decision the board must make.
- `input/payloads/analysis_request.json` — the **registered protocol**: scope, release/cohort
  rules, an ordered set of audit *modules* (each with a named method, cohort, orders, grids,
  seeds, and `required_evidence`/`required_audit_outputs`), the numeric gates, and the
  precedence **decision rule**.
- `input/payloads/answer_template.json` — the **output contract**: required top-level keys,
  per-section `required_keys`, `array_lengths`, `cardinality_rules`, orderings, precision,
  identifier rules, and allowed enum/boolean values.
- The **PHO Web portal** at `<TASK_ENV_BASE_URL>` (the base URL is provided by the
  environment, e.g. via `environment_access.md` / `GDPEVO_ENV_BASE_URL`) — the *only* evidence
  source. It is read-only.

The two payloads are, together, a **complete and self-checking specification**. `analysis_request`
tells you what to compute; `answer_template` tells you the exact shape, orders, and lengths of the
answer. Read both in full before writing any code. Treat every `required_evidence` string and every
`required_keys`/`array_lengths`/`cardinality_rules` entry as a checklist item you must satisfy.

## Golden rules

1. **Portal is the sole source of truth.** Do not invent, recall, or web-search values. Pull every
   number from the portal. Use `<TASK_ENV_BASE_URL>` from the environment; never hardcode a base URL.
2. **Determinism over cleverness.** Every method is "registered": fixed feature/coefficient/division/
   state/grid/checkpoint orders, fixed seeds and PRNG streams, fixed k-means initialization,
   training-only standardization. Reproduce the *declared* procedure exactly; do not substitute a
   library default that reorders, reshuffles, or re-centers.
3. **Preserve every declared order.** Aligned arrays are positional. Never sort an aligned result
   array independently. Only sort where the template says "sorted ascending" (usually set-like ID
   lists and excluded/complement sets).
4. **Never zero-fill missing data.** Suppressed / invalid / blank / withdrawn values are
   *unavailable*. They drop the observation from any cohort that requires that field; they are never
   imputed as 0. Use JSON `null` only where a statistic is mathematically undefined — never `NaN`/`Inf`.
5. **Read thresholds and grids from `analysis_request`, not from memory or this skill.** Seeds, lambda/
   alpha grids, replicate counts, checkpoint lists, coverage/coefficient thresholds, and decision
   precedence differ per task. This skill describes *shapes*, not values.
6. **Output is one JSON object, no narrative.** It must satisfy the template exactly. Do a final
   contract check (keys present, array lengths equal, orders aligned, precision applied, enums/booleans
   legal) before submitting.

## Workflow

Work as a single deterministic pipeline — ideally one script (Python + numpy is a good fit) that you
can re-run, because exact reproduction of jackknife/bootstrap/PCA arithmetic by hand is infeasible.

1. **Read all three inputs end to end.** Extract: geography scope, years, reference/primary year,
   outcome, exposure(s)/mediator, adjustments, the health/socioeconomic filters, the named cohorts,
   the ordered module list, and the gate + decision definitions.
2. **Learn the portal.** Hit `/`, `/catalog`, and `/methodology` first. `/catalog` lists every dataset,
   its columns, its filterable fields, and the measure dictionary. `/methodology?doc=...` states the
   resolution rules you must apply. See `references/portal.md`.
3. **Download the evidence.** Pull each needed dataset as CSV via `/download?dataset=<name>&format=csv`
   (add filters as query params). There is no JSON API; CSV is the machine-readable path.
4. **Resolve FINAL releases / revisions.** For every (entity, year, measure/field), collapse the raw
   rows to one governing record using the task's release-resolution rule. Apply value-type / source-type
   / status / quality / suppression filters. See `references/data_resolution_and_cohorts.md`.
5. **Build each named cohort** by its exact completeness predicate, and report the requested census/count
   audit (yearly complete counts, cohort sizes, excluded/complement code sets, state census). Same file.
6. **Run each audit module in the declared order**, emitting every piece of `required_evidence`. The six
   recurring module families and their generic recipes are in `references/audit_modules.md`.
7. **Evaluate gates and classify.** Compute each gate boolean from module outputs against the declared
   threshold, count passes, and apply the precedence rule to pick the enum conclusion (including any
   "NOT_ROBUST_AT_<first failed module>" style label). See `references/output_contract.md`.
8. **Assemble and validate the JSON** against `answer_template.json`, then submit only that object.

## Module map (what recurs across tasks)

Every task is a variation on the same six-module skeleton (names, cohorts, grids, and seeds differ):

| Family | Typical registered names | What it audits |
| --- | --- | --- |
| Cluster jackknife / FE / GMM | two-way FE OLS delete-one-cluster; reliability-weighted delete-one-division; difference/two-step linear GMM | Sign, significance, and influence-robustness of the focal coefficient under cluster deletion |
| Nested leave-group-out penalized CV | nested LOO-division ridge; leave-state-out elastic-net; state-blocked nested elastic-net | Genuine out-of-group predictive value (pooled RMSE/MAE/R²/Q²) |
| Restricted-null wild cluster bootstrap-t | PCG32 / XORSHIFT32 Webb or paired wild bootstrap-t | Cluster-robust significance via bootstrap p-value + t-quantiles + PRNG checkpoints |
| Grouped split-conformal calibration | grouped/cross-fold split conformal ridge/elastic-net | Prediction-interval coverage and width by group and pooled |
| Trajectory PCA + deterministic k-means | covariance PCA + deterministic 3-means + leave-year-out / delete-state ARI | Existence of a stable multi-year trajectory structure |
| Source / year / sensitivity perturbation | exhaustive source-year FE perturbation; direct-vs-rollup with exact Shapley; partial-R² mediation surface; no-retune group-deletion | Robustness of the signal to source/year swaps or confounding |

Details, evidence checklists, and determinism notes for each are in `references/audit_modules.md`.

## Reference files

- `references/portal.md` — endpoints, dataset schemas, measure dictionary, CSV download, methodology rules.
- `references/data_resolution_and_cohorts.md` — release/revision resolution, filters, completeness &
  cohort construction, missing-data handling, geography joins (region / census division / RUCC / ISO3).
- `references/audit_modules.md` — the six module families: generic recipes, required evidence, and the
  determinism traps to avoid.
- `references/output_contract.md` — reading the template, precision/ordering/identifier discipline,
  gate evaluation, precedence decision logic, and the pre-submission checklist.
