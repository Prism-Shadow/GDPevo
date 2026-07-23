---
name: pho-registered-audit
description: Complete a Public Health Observatory (PHO) registered algorithmic audit. Resolve final releases/revisions from the read-only PHO portal, build the declared cohorts, run the six registered audit modules deterministically (delete-one-cluster jackknife / two-step GMM, nested leave-group-out ridge or elastic-net, restricted-null wild cluster bootstrap-t, grouped split conformal, trajectory PCA + deterministic k-means, exhaustive source/year/group perturbation), apply the robustness gates, and emit exactly one JSON object conforming to answer_template.json. Use when a task names the PHO portal at <TASK_ENV_BASE_URL>, ships analysis_request.json + answer_template.json, and demands a reproducibility/transportability audit with a controlled decision.
---

# Public Health Observatory — Registered Algorithmic Audit

This skill completes any **PHO registered algorithmic audit** task. Every such task has the
same shape: a read-only portal is the sole evidence source; an `analysis_request.json`
declares the protocol (geography, years, outcome/exposure, cohorts, audit modules, gates,
decision rule); an `answer_template.json` fixes the response contract (keys, orders,
lengths, types, precision, enums). The domain varies (state longevity, county mediation,
country burden, state diabetes, county diabetes dynamics) but the **operating procedure is
constant**. Follow it exactly.

## What you receive
- `prompt.txt` — restates the gates and the submission constraint (one JSON object, no narrative).
- `payloads/analysis_request.json` — the protocol (the "what to compute").
- `payloads/answer_template.json` — the contract (the "how to format").
- `environment_access.md` — the portal base URL and the only allowed GET endpoints.

## Governing principles (non-negotiable)
1. **Portal is the only evidence source.** Fetch everything from `<TASK_ENV_BASE_URL>` via the
   allowed GET endpoints. No external data, no fabricated values, no recalling outcomes from
   memory. See `references/portal.md`.
2. **Resolve releases and revisions independently and reproducibly.** Final replaces
   provisional; the highest *applied* final revision wins; pending/withdrawn revisions never
   replace; declared `revision_priority` tie-breaks. See `references/portal.md`.
3. **Never zero-fill.** Suppressed or missing values are unavailable. The cohort drops the
   jurisdiction/year, never imputes zero. Use JSON `null` only when a *statistic* is
   mathematically undefined (e.g., a degenerate fit), never for missing source data.
4. **Preserve every declared order.** State order, feature/coefficient order, grid order,
   division order, checkpoint-replicate order, source-group order, subset order. Do **not**
   re-sort an array that is positionally aligned to another (e.g., delete-coefficients align
   to `state_order`; PCA scores align to `state_order`). Sort only where the template says so.
5. **Deterministic numerics.** Use the exact RNG (PCG32 / XORSHIFT32), seed, stream,
   replicate count, and weight scheme declared. Record checkpoint PRNG states + t-statistics
   at the declared checkpoint replicates, plus-one p-value, requested quantiles, and the
   terminal generator state. Compute in full precision; round only at output.
6. **Match the contract exactly.** Required keys, `array_lengths`, `cardinality_rules`,
   types (integer vs number vs boolean vs enum), precision, identifier casing, enum values.
   See `references/contract.md`.
7. **One JSON object, no narrative.** Submit exactly one JSON object conforming to
   `answer_template.json`. No markdown, no commentary, no surrounding text.

## Procedure

### 0. Read the contract first
Open `answer_template.json` and enumerate, per top-level key: required sub-keys, array
lengths, ordering, types, precision, and enum/allowed values. Then open `analysis_request.json`
and map each module to its cohort, ordered features, grids, seeds, replicates, checkpoints,
and `required_evidence`. **Reverse-engineer the deliverable shape before computing anything**
— the contract tells you which arrays must align with which.

### 1. Pull the portal
- `GET /catalog` — column schemas, available filters, row counts, measure dictionary.
- `GET /geographies/{states,counties,countries}` — jurisdiction, region, division, rucc,
  canonical-name/alias reference.
- `GET /download?dataset=<d>&format=csv&<filters>` — machine-readable records (CSV with
  header). Filter query params mirror the catalog's documented filters
  (`state_abbr`, `year`, `measure_id`, `value_type`, `source_type`, `release_status`,
  `revision`, `region`, `county_fips`, `iso3`, `country_label`, `indicator_id`, …).
- `GET /data/revisions` — revision events (`status` = APPLIED/PENDING/WITHDRAWN,
  `reason_code`, `effective_year`, old/new values).
- `GET /methodology` and `GET /methodology?doc=<slug>` — resolution policy. Read the
  **CURRENT** docs; ignore **DRAFT** and **SUPERSEDED** docs for publication decisions.

Pull the full datasets you need (filter per measure/year/value_type/source_type to keep
payloads small), then resolve locally. Do not trust a single filtered view to be the
universe — cross-check against `/geographies` for the jurisdiction universe
(e.g., 50 states + DC = 51).

### 2. Resolve the evidence
For each requested (jurisdiction, year, measure, value_type, source_type):
1. Keep `release_status = FINAL` only (final replaces provisional).
2. Among final records, keep the **highest applied** revision; break remaining ties with the
   declared `revision_priority` (typically `revision`, then `released_at`, then `observation_id`
   / `record_id`).
3. Ignore revision events whose `status` is PENDING or WITHDRAWN — they do not authorize
   replacement.
4. Drop any record whose `quality_flag` is in the request's `invalid_quality_flags`
   (e.g., `INVALID_SCALE`, `INVALID`, `WITHDRAWN`). Other quality flags (e.g., `REVIEWED`,
   `STALE`) are retained — they describe review state, not release precedence.
5. Treat suppressed (`suppression_flag`) or blank `value` as **unavailable**; never zero-fill.
6. Respect source/value-type semantics: `DIRECT_SURVEY` is the primary state series;
   `COUNTY_ROLLUP` is a parallel coverage estimate that must not silently replace direct
   records. `AGE_ADJUSTED` for state comparisons; `CRUDE` for observed burden (primary vs
   parallel exposure).
7. For countries: reconcile `portal_label`/`alternate_labels` to stable `iso3` via the
   `countries` geography file (alias resolution).

Record the resolution in the cohort section of the answer (release counts by year, excluded
jurisdictions, yearly complete-case counts, etc.) — the template requires it.

### 3. Build the cohorts
Construct each cohort **independently** from resolved records, per the request's definitions:
- **PRIMARY** — reference-year complete-case from the jurisdiction universe.
- **BALANCED** — complete across **all** study years (intersection across years).
- **BROAD / REFERENCE** — reference-year complete for the outcome **and** every ordered
  ridge/elastic-net feature.
- **ML / machine-learning** — primary cohort members also complete for the extra ML fields.
- **STRICT_DUAL_SOURCE** — complete for outcome + primary exposure + parallel exposure +
  adjustments in **every** study year.

"Complete" = every requested value present, nonsuppressed, nonmissing, and not carrying an
invalid quality flag. Track the **complete exclusion set** (every universe jurisdiction absent
from a cohort, and no others) — templates demand e.g. `primary_excluded_state_codes`,
`core_balanced_excluded_state_codes`, `strict_excluded_state_codes`.

### 4. Run the six audit modules
Each request declares six modules. Execute each **exactly as specified** — method, cohort,
ordered features, grids, seeds, replicates, checkpoints — and produce the `required_evidence`.
The six recurring families and their deterministic execution notes are in
`references/modules.md`. Summary:

1. **Delete-one-cluster fixed-effects / two-step GMM / jackknife** — full coefficient, every
   per-deletion diagnostic, bias-corrected inference, influence summary.
2. **Nested leave-group-out ridge / elastic-net CV** — outer + inner folds, grids, selected
   hyperparameters, per-fold inner grids, outer RMSE, pooled metrics, worst group.
3. **Restricted-null wild cluster bootstrap-t** — observed CR1 SE/t, exceedance/tail count,
   plus-one p-value, requested quantiles, checkpoint PRNG states + t-stats, terminal state.
4. **Grouped split conformal** — per-group thresholds/coverage/widths/MAE, aggregate
   calibration, worst group.
5. **Trajectory PCA + deterministic k-means** — spectrum, loadings, scores, deterministic
   centroids, Lloyd update count, labels; leave-year-out and/or delete-state ARI stability.
6. **Exhaustive source/year/group perturbation** — all subsets/groups, coefficient + p-value
   vectors, percent shifts, same-sign summary, worst subset; exact Shapley when declared.

### 5. Apply the gates and decision
Evaluate every gate against its **declared** threshold (in `robustness_gates` /
`decision_rule` / `controlled_conclusion` — do not invent thresholds). Report per-gate
PASS/FAIL (or boolean), the passed/supported count, `first_failed_module` (or `NONE`), and
the classification per the declared precedence rule (e.g., all-pass → primary; ≥N → partial;
else → none). The decision is mechanical once the gates are computed.

### 6. Emit and self-check
Serialize **one** JSON object. Before submitting, run the pre-submission checklist in
`references/contract.md`:
- Exactly the required top-level keys; every required sub-key present.
- Every `array_lengths` / `cardinality_rules` satisfied.
- Shared `state_order` is byte-identical across the modules the template says must match.
- Aligned arrays align positionally; sorted lists sorted exactly as specified.
- Precision correct (4 dp default; 6 dp for computed reals where declared; integers/booleans/
  enums as natural JSON types); no `NaN`/`Infinity`; `null` only for mathematically undefined
  statistics.
- Identifiers: uppercase state codes, portal division/region names verbatim, ISO3 uppercase.
- No narrative, no markdown fences — just the JSON object.

## Anti-patterns (do not)
- Do not substitute a map/set for an ordered list the template declares as a list.
- Do not re-sort a positionally-aligned array "for readability".
- Do not zero-fill, mean-impute, or forward-fill missing source data.
- Do not silently swap `COUNTY_ROLLUP` for `DIRECT_SURVEY` (or `CRUDE` for `AGE_ADJUSTED`).
- Do not change the seed, replicate count, RNG family, or checkpoint schedule.
- Do not round intermediate results; round only the final reported values.
- Do not emit multiple JSON objects, trailing prose, or markdown code fences.
- Do not apply DRAFT or SUPERSEDED methodology docs to publication decisions.

## References (deeper detail, read as needed)
- `references/portal.md` — full endpoint list, dataset schemas/filters, methodology doc map,
  and the release/revision/quality/suppression/alias resolution rules in full.
- `references/modules.md` — the six module families: inputs, deterministic execution, RNG,
  and the exact evidence each must produce.
- `references/contract.md` — output-contract rules and the pre-submission checklist.
