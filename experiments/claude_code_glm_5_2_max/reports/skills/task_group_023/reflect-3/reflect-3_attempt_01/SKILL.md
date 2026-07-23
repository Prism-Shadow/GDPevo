---
name: pho-transportability-audit
description: Solve Public Health Observatory (PHO) reproducibility/transportability algorithmic-audit tasks. These tasks fetch surveillance + socioeconomic records from a read-only PHO data portal, resolve publication releases/cohorts under a strict evidence specification, run a set of registered statistical audit modules with exact reproducibility checkpoints (fixed seeds, PRNG streams, replicate counts, ordered arrays), apply controlled decision gates, and return one JSON object conforming to a per-task answer template. Invoke when a task references the PHO portal / a "six-module audit" / "transportability" / "publication cohort" / "robustness gates" / analysis_request.json + answer_template.json, or asks to audit whether an exposure-outcome signal survives controlled statistical gates.
---

# PHO Transportability / Algorithmic Audit

## What these tasks are

A PHO audit task gives you three files in `input/`:
- `prompt.txt` — the narrative framing.
- `payloads/analysis_request.json` — **the binding specification**: the business question, geography scope, years, evidence/cohort rules, and a set of named **audit modules** each with an exact `method`, cohort, seeds/streams/replicates, ordered features, grids, and required outputs. It also gives `robustness_gates` / `decision_rule` / `controlled_conclusion`.
- `payloads/answer_template.json` — **the output contract**: required top-level keys, per-section `required_keys`, `array_lengths`, `cardinality_rules`, orderings, enum values, and precision/type rules.

Your job: fetch portal data, resolve it exactly as the spec dictates, implement every module to its registered reproducibility checkpoints, apply the gates, and return **one JSON object** matching the template, with no narrative.

The same five-ingredient structure repeats across the task family (state, county, country scopes; longevity, diabetes, obesity, burden outcomes; FE-OLS, ridge/elastic-net CV, wild cluster bootstrap, split conformal, PCA+k-means, source/year perturbation, GMM mediation, sensitivity surfaces). Master the ingredients, then follow each task's spec literally.

## Entry procedure (do this every time)

1. **Read all three input files end to end before computing.** The template's `array_lengths`, `cardinality_rules`, `ordering`, and `enum`/`allowed_values` are hard constraints; a mis-sized or mis-ordered array fails the contract. Note every declared order (state order, feature order, division order, lambda/alpha grid order, checkpoint replicate order, source-group order) — preserve them exactly; never re-sort an aligned result array independently.
2. **Fetch the portal data as CSV.** The portal base URL is given in the prompt as `<TASK_ENV_BASE_URL>` (read it from the environment; do not hard-code). Download each dataset you need via `GET <BASE>/download?dataset=<name>&format=csv`. Browse `GET <BASE>/catalog` for the dataset list + column schemas, and `GET <BASE>/methodology` for the resolution rules. See `references/portal_and_resolution.md` for the full dataset catalog and columns.
3. **Resolve records under the evidence specification.** Apply the portal's CURRENT methodology + the request's filters exactly. The resolution is the foundation: every cohort and coefficient depends on it. See `references/portal_and_resolution.md`.
4. **Build each cohort independently** per the request's complete-case definitions (core/balanced, broad/reference, strict/dual-source, ML cohort, etc.). A jurisdiction/county/country is "complete" for a cohort only when every required variable is present, non-suppressed, non-null, and non-anomalous in every required year. Never zero-fill missing/suppressed values.
5. **Implement each module exactly as specified.** Methods, cohorts, ordered predictors/features, lambda/alpha grids, seeds, streams, replicate counts, checkpoint replicate lists, quantile probabilities, and standardization choices are all registered — replicate them literally. Reproducibility-checkpoint fields (first-N bootstrap weight rows, batch exceedance counts, PRNG final state, checkpoint t-statistics) demand an **exact PRNG implementation** (PCG32 pcg_setseq, xorshift32, etc. — see `references/modules.md`). Use pinv with a singular-value cutoff where the spec mentions a pseudoinverse cutoff.
6. **Apply the decision gates and classification** from `decision_rule` / `controlled_conclusion`. Gates are threshold rules over module statistics; the classification follows the declared precedence (e.g. all-pass → primary; ≥k → partial; else none).
7. **Emit one JSON object** conforming to `answer_template.json`. See `references/output_contract.md` for precision, type, ordering, null, and identifier rules.

## Critical, repeatedly-burned rules

- **Release resolution:** FINAL replaces PROVISIONAL; among several FINAL revisions the **highest applied revision governs** (tie-break `released_at` then record/observation id, descending). Country `APPLIED` scale corrections appear in a later FINAL revision (use the corrected value); `WITHDRAWN`/`PENDING` scale corrections are **not** applied — the cell stays at the wrong scale and is an **anomaly**.
- **Suppression/quality:** `suppression_flag==1` or blank value ⇒ unavailable, never zero-filled. Exclude `quality_flag ∈ {INVALID_SCALE, INVALID, WITHDRAWN}`. Quality flags describe review state and do **not** change release precedence.
- **Direct vs rollup, AA vs crude:** DIRECT_SURVEY is the primary state series; COUNTY_ROLLUP is a parallel estimate — never silently substitute rollup for direct. Age-adjusted values support state comparison; crude values describe observed burden. Follow each request's `value_type` filter literally; when a cohort variable is named `age_adjusted_*` it is AGE_ADJUSTED, and a bare measure name with an `AGE_ADJUSTED_AND_DIRECT_SURVEY_AND_FINAL` primary filter means resolve that measure at AGE_ADJUSTED + DIRECT_SURVEY + FINAL.
- **Mixed units:** before PCA/clustering on indicators with different units (percent vs deaths-per-100k vs years), **standardize** (correlation PCA). The methodology warns percentages and mortality rates are not interchangeable.
- **Two-way FE:** `TWO_WAY_FIXED_EFFECTS` = entity (state/county) + time (year) fixed effects. Use intercept + (n−1) entity dummies + (t−1) time dummies (full rank). A predictor's partial coefficient is invariant to other predictors' scaling/coding (Frisch–Waugh–Lovell), but the coefficient itself depends on the cohort and FE spec.
- **CR1 cluster-robust SE:** bread = (X'X)⁻¹, meat = Σ_g X_g' e_g e_g' X_g, small-sample correction G/(G−1)·(n−1)/(n−k); p-value df = G−1 (clusters).
- **Ridge/elastic-net CV:** standardize continuous features using **training-fold only** statistics; standardize the outcome only if the spec says so. Penalty excludes the intercept. Nested CV = outer fold picks test, inner CV (over training folds) selects hyperparameter, then evaluate outer.
- **Split conformal:** threshold = ⌈(n_cal+1)(1−α)⌉-th order statistic of |calibration residual|; interval = ŷ ± threshold; width = 2·threshold.
- **PCA sign convention:** make the largest-|loading| entry of each PC positive (deterministic). Covariance PCA when the spec says covariance (same-unit panel trajectories); correlation/standardized PCA for mixed-unit cross-sections.
- **Deterministic k-means:** use a declared/seeded initialization; report `initial_centroid_states`/iterations. Leave-one-out stability = recompute clustering with the held-out unit/year removed, measure ARI vs full.
- **Income scaling:** several tasks scale `median_income` by 1e4 ("per 10000"); apply it wherever the request declares it. (It does not change other predictors' OLS coefficients, but changes ridge/elastic-net/conformal/perturbation outputs that include income.)
- **Precision:** round every non-integer reported statistic to the declared decimal places (usually 4) and encode as a JSON **number**. Integers and booleans keep natural JSON types. Use `null` only when a statistic is mathematically unavailable — never `NaN`/`Infinity`. Some tasks distinguish computed-stat precision from literal grid/threshold precision (keep grids/thresholds at their literal values).

## Reusable implementation helpers

Implement a small shared resolver once (FINAL + highest-revision + suppression/quality filtering per `references/portal_and_resolution.md`) and reuse it across modules. Standard idioms — two-way FE OLS, CR1 cluster SE, ridge with training-only standardization, covariance/correlation PCA with deterministic sign, deterministic k-means, PCG32 pcg_setseq, xorshift32, Webb 6-point weights, adjusted Rand index — are specified in `references/modules.md`; implement them exactly once and reuse, do not re-derive per task.

## Files in this skill

- `references/portal_and_resolution.md` — portal datasets, columns, filters, and the full resolution rule set.
- `references/modules.md` — the audit-module archetypes and exact algorithm conventions (PRNGs, weights, CV, conformal, PCA/clustering, GMM, sensitivity).
- `references/output_contract.md` — formatting, ordering, type, null, and identifier rules with a pre-submission checklist.

## Mindset

Treat `analysis_request.json` as a registered protocol and `answer_template.json` as a schema. The graders check leaf statistics (and structural fields) against an exact reference implementation — small convention drift (PCA standardization, income scaling, CR1 df, PRNG stream encoding, sign convention) silently zeros whole modules. Get the resolution and conventions right first; then reproduce checkpoint fields exactly. Verify each module's array lengths/orders against the template before emitting.
