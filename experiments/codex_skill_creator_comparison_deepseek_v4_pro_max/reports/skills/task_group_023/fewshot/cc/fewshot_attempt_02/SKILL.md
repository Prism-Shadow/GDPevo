---
name: pho-audit-solver
description: Solve Public Health Observatory algorithmic audit tasks. Use this skill whenever the user mentions a Public Health Observatory audit, a PHO protocol, an analysis_request.json with audit modules, or needs to complete a registered algorithmic audit against the Observatory web portal. Also use this skill when the user references state/county/country health data analysis with robust statistical methods (delete-cluster jackknife, nested ridge/elastic-net CV, wild cluster bootstrap, grouped conformal, PCA trajectory clustering, source perturbation) tied to answer_template.json output contracts. The skill should be consulted even when the user only hints at "observatory data," "algorithmic audit," "publication board," or "transportability" analysis.
---

# Public Health Observatory Algorithmic Audit Solver

Solve registered algorithmic audit tasks using the Public Health Observatory
(PHO) read-only data portal at `<TASK_ENV_BASE_URL>`. Each task arrives as an
`analysis_request.json` that declares the protocol, measures, cohorts, module
specifications, and decision rules, paired with an `answer_template.json` that
fixes the output contract.

## Workflow

### Phase 1 — Understand the contract

Read both payloads in full before touching the portal:

1. **analysis_request.json** — the protocol identifier, business task, scope,
   evidence specification, audit module declarations (methods, cohorts,
   parameters, required evidence), reporting rules, and decision logic.

2. **answer_template.json** — the exact keys, types, array lengths, ordering
   rules, and precision requirements for the output JSON.

Never invent keys, reorder arrays, or change numeric precision from what the
template demands. Use the natural JSON types requested: integers for counts,
numbers for decimals, strings for identifiers, Booleans for flags.

### Phase 2 — Resolve geography and methodology

Pull the geography reference and any methodology documents that affect data
interpretation before touching observation endpoints. See
[references/portal_api.md](references/portal_api.md) for the complete endpoint
catalog.

**Essential reads before data pulls:**
- `/geographies/states` — maps state abbreviations to regions and census divisions
- `/geographies/counties` — maps county FIPS to state, region, RUCC, metro class
- `/geographies/countries` — maps country labels to canonical names and ISO3 identifiers
- `/methodology` — inspect documents relevant to the task's data type:
  - `release-lifecycle` for revision precedence rules
  - `suppression` for missing-value handling
  - `state-estimates` for direct vs. rollup source semantics
  - `publication-values` for crude vs. age-adjusted use
  - `aliases` for country label reconciliation
  - `indicator-direction` for country indicator interpretation
  - `country-revisions` for revision notice status semantics
  - `quality` for quality flag interpretation
  - `rucc` for Rural-Urban Continuum Code categories
  - `socioeconomic-fields` for field revision independence

### Phase 3 — Resolve data releases

Every data endpoint supports CSV download via `/download?dataset=<name>&format=csv`
with the same filter parameters. **Prefer CSV downloads** for bulk numeric work;
parse HTML tables only when the task requires inspecting individual metadata
fields the CSV does not expose.

**Release resolution rule (universal):**
For every measure-entity-year combination, resolve the *single* authoritative
record by applying these filters in order:

1. **Filter** by the effective release status (usually `FINAL`), value type,
   source type, and geography bindings declared in the request.
2. **Select** the record with the greatest revision number among matching records.
3. **Break ties** by latest `released_at` timestamp, then by lowest
   `observation_id` (health) or `record_id` (socioeconomic, county).
4. **Suppressed/missing**: Records with `suppression_flag=1`, `value='—'`,
   blank, or null value are resolved as unavailable. Never zero-fill them.

**Revision semantics:**
- `FINAL` with revision `N` where `N` is the highest number is authoritative.
- `PROVISIONAL` records are never selected when `FINAL` is the filter.
- A higher `revision` number always beats a lower one regardless of timestamp.

**Value type / source type:**
- `AGE_ADJUSTED` values support cross-state comparisons.
- `CRUDE` values describe observed burden.
- `DIRECT_SURVEY` is the primary publication series.
- `COUNTY_ROLLUP` is a parallel estimate; never silently substitute for direct.

See [references/data_resolution.md](references/data_resolution.md) for the
full resolution algorithm with worked edge cases.

### Phase 4 — Build cohorts

Every task declares one or more cohorts. Build each independently from the
resolved data, never mixing cohort construction logic.

**Common cohort types:**

- **Complete-case cohort** — entities with non-null, nonsuppressed values for
  every field in a specified set, for a specific year.
- **Balanced panel cohort** — entities complete in every requested year for
  every required field.
- **Broad cohort** — reference-year complete cases for an expanded set of
  features (typically used in ridge/elastic-net modules).
- **Strict dual-source cohort** — entities complete for an outcome, a primary
  exposure, a parallel (alternate-source) exposure, and adjustments in every
  requested year.

**Ordering**: Within each cohort, sort entities by their stable code (state
abbreviation, county FIPS, ISO3), then by time within each entity. Preserve
every declared feature order; never sort a feature-ordered array independently.

See [references/cohort_construction.md](references/cohort_construction.md) for
the complete cohort construction rules.

### Phase 5 — Execute audit modules in registered order

Each module in the request declares its method, cohort, and parameters.
Implement them exactly as described in
[references/statistical_modules.md](references/statistical_modules.md). Key
principles:

- **Independence**: Resolve each module's data independently from the effective
  request. A module that declares a specific cohort uses only that cohort.
- **Reproducibility**: Random processes use the declared seed and stream. Cycle
  through PRNG states exactly as specified; never reset the generator between
  draws within a module except where explicitly checkpointed.
- **Order**: Execute modules in the declared order. Within a module, process
  folds, entities, years, and replicates in the stable sort order specified.
- **Precision**: Compute with unrounded values throughout. Round only at
  reporting time, to the declared decimal places.

The modules encountered across protocols are:

1. **release_resolution_and_cohorts** — publication filtering and cohort construction
2. **delete_cluster_fixed_effects** — two-way FE OLS with delete-one-cluster jackknife
3. **nested_ridge_division_cv** / **nested_elastic_net** — grouped nested cross-validation
4. **wild_cluster_bootstrap** / **wild_cluster_bootstrap_t** — restricted-null cluster wild bootstrap
5. **grouped_split_conformal** / **grouped_conformal_calibration** — grouped split conformal prediction
6. **trajectory_pca_clustering** — covariance PCA with k-means and leave-one-out stability
7. **source_year_perturbation** / **source_group_perturbation** / **exhaustive_source_perturbation** — source stability audits
8. **difference_gmm_mediation** — difference-GMM mediation with delta-method inference
9. **mediation_sensitivity_surface** — partial-R2 confounding sensitivity
10. **controlled_decision** / **decision_audit** — gated decision rules

Each module's full specification is in [references/statistical_modules.md](references/statistical_modules.md).

### Phase 6 — Assemble the answer

Build one JSON object with every required top-level key from the template.
Follow these rules:

- **Numeric precision**: Round non-integer statistics to the declared decimal
  places. Integers (counts, years, seeds, replicate numbers, ranks, PRNG
  states) are natural JSON integers.
- **Identifiers**: Uppercase state abbreviations, portal division names exactly
  as they appear in the geography reference, ISO3 codes uppercase, country
  labels as resolved.
- **Ordering**: Every list preserves the exact order declared by the request
  or the natural sort order (state code, year, entity code). Never sort an
  aligned result array independently of its companion arrays.
- **Missing**: Use JSON `null` only when a statistic is mathematically
  unavailable (e.g., division by zero, undefined quantile). Never emit `NaN`
  or `Infinity`.
- **Booleans**: Use JSON `true`/`false`, not strings.
- **Enum values**: Use exactly the allowed values strings declared in the
  template.

### Phase 7 — Submit

Return exactly one JSON object conforming to the answer template. Do not
include narrative, markdown fences, or commentary outside the JSON.

## Portal navigation

The portal provides a `<TASK_ENV_BASE_URL>` that is substituted by the task
prompt. All references below use `<TASK_ENV_BASE_URL>` as the root.

Read [references/portal_api.md](references/portal_api.md) for:
- Every endpoint URL and its filter parameters
- Field schemas for state health, county health, state/county socioeconomic,
  country indicators, geographies, and revisions
- CSV download URLs
- Methodology document URLs and their content summaries

## Key methodology rules

These rules come from the portal's methodology documents and apply across
all modules:

1. **Highest final revision governs.** When multiple FINAL records exist for
   the same measure-entity-year, take the one with the greatest revision
   number. Break ties by latest `released_at`, then by lowest id.

2. **Provisional records are never authoritative when FINAL is requested.**

3. **Direct survey beats county rollup.** Direct survey estimates are the
   primary state publication series. County rollups are parallel estimates
   for coverage review.

4. **Suppressed is not zero.** A suppressed (`—`), blank, or null value means
   the observation is unavailable for analytic use. Never impute zero.

5. **Age-adjusted for comparison, crude for burden.** Age-adjusted values
   support state comparisons. Crude values describe observed burden and
   retain population structure.

6. **Country labels must be reconciled.** Portal labels may differ from
   canonical names. The geography reference `/geographies/countries` provides
   the mapping from portal labels to canonical names and ISO3 identifiers.

7. **Revision notices for countries.** APPLIED scale corrections are
   reflected in later final revisions. PENDING and WITHDRAWN notices do
   not authorize replacement of published values.

8. **Socioeconomic fields are independently revised.** A null in one
   socioeconomic field does not invalidate other fields in the same record.

9. **Quality flags are metadata, not filters.** Retain quality flags in
   audit extracts; they describe review state but do not change release
   precedence.

10. **RUCC 1-3 are metropolitan; 4-9 are nonmetropolitan.**
