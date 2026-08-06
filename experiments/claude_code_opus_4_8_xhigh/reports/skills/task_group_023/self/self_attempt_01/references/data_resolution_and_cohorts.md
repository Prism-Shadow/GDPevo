# Release resolution & cohort construction

This is the step that most often decides whether the downstream numbers match. Do it exactly as the
task's `analysis_request` and `answer_template` describe, and report every count they ask for.

## 1. Resolve one governing record per (entity, year, measure/field)

Raw datasets contain many rows per cell: provisional + final, multiple revisions, both value types,
both source types. Collapse to one governing record with the task's release-resolution rule. The
recurring rule (`REGISTERED_FINAL_RELEASE_RESOLUTION` / `HIGHEST_FINAL_REVISION_THEN_LATEST_RELEASE`)
is:

1. Apply the declared **filters first** (they define which rows are even eligible):
   - `release_status == FINAL` (unless the task says otherwise).
   - `value_type` == the declared type (`AGE_ADJUSTED` or `CRUDE`).
   - `source_type` == the declared type (`DIRECT_SURVEY` or, for a parallel/rollup series,
     `COUNTY_ROLLUP`). County health has no source_type column.
   - Drop rows whose `quality_flag` is in the task's `invalid_quality_flags` list (e.g.
     `INVALID_SCALE, INVALID, WITHDRAWN`), if provided.
   - Drop `suppression_flag == 1` and null/blank `value` — these are **unavailable**.
2. Among the survivors for a cell, pick the governing record by the declared priority. Default:
   **highest `revision`, then latest `released_at`, then a stable id tiebreaker** (`observation_id` /
   `record_id` / `observation_id`). Some tasks state the tuple explicitly, e.g.
   `["revision", "released_at", "observation_id"]` — follow the given order exactly.
3. A task may request a **parallel series** (e.g. CRUDE+DIRECT_SURVEY alongside AGE_ADJUSTED+DIRECT_SURVEY,
   or CRUDE+COUNTY_ROLLUP as a replacement source). Resolve each series independently with its own filter.

**Revisions dataset.** For country work (and any task that references applied restatements), the
`revisions` table drives scale-correction handling: `status == APPLIED` corrections are reflected in
later FINAL revisions and should be treated as in effect; `PENDING`/`WITHDRAWN` notices do **not**
authorize replacing a published value. Tasks that audit data quality ask you to split revision events
into applied vs non-applied ID lists and to flag unresolved scale breaks (e.g. a cell whose value is
~10× off consistent with a withdrawn/pending `SCALE_CORRECTION`) as anomalies — exclude those cells and
count them (`raw_missing`, `anomaly`, `imputed`, `usable_country/indicator`).

## 2. Never zero-fill

A suppressed, invalid, blank, or withdrawn value makes that field unavailable for that cell. Any cohort
requiring that field excludes the observation. Never substitute 0 or a mean unless the task explicitly
defines an imputation step (country tasks may define a specific post-exclusion imputation for the PCA
matrix — follow it precisely and count imputed cells).

## 3. Geography joins

- **State tasks**: join resolved health/SES rows to `states` on `state_abbr`/`state_fips` to attach
  `region` (Northeast/Midwest/South/West) and `division` (the 9 Census divisions used for
  `CENSUS_DIVISION` clustering/grouping). "50 states + DC" = the 51-jurisdiction universe.
- **County tasks**: join to `counties` for `rucc` (1–9; build RUCC indicator dummies with the declared
  reference, usually RUCC1) and `region`. Region filters like `["West", "Northeast"]` or
  `["Midwest", "South"]` subset the county universe.
- **Country tasks**: reconcile analyst labels to `iso3` via `canonical_name` + `alternate_labels`;
  report requested vs resolved label counts and alias-resolution count; attach `region` for
  region fixed effects.

## 4. Build each named cohort by its exact predicate

Tasks define several cohorts; a variable missing from the required set drops the unit. Recurring cohorts:

- **Primary / reference-year complete-case cohort** — units complete for the outcome + required
  features in the reference/primary year. Often the base for regression and CV modules.
- **Core / balanced panel cohort** — units complete in **every** analysis year (the intersection across
  years). Base for fixed-effects, GMM, and trajectory modules.
- **Machine-learning cohort** — primary-cohort members that are *also* complete for the extra ML
  features (e.g. reference-year unemployment/net_migration/uninsured).
- **Strict dual-source cohort** — complete for outcome + primary exposure + parallel exposure +
  adjustments in every year (for source-perturbation modules).

Determine each cohort's completeness predicate from `analysis_request` (e.g. "Basic-complete in 2023",
"Basic-complete in all four years", "complete for outcome and all ordered ridge features"). The
`answer_template` cohort section names the counts to report.

## 5. Report the census / cohort audit exactly

Typical required outputs (names vary): target/universe count; **selected release counts by year**;
**annual complete-case counts** (one per analysis year, in ascending-year order); primary/reference count;
balanced/panel count; ML-cohort count; state count / state census; and **excluded/complement code sets**.

- An "excluded" or "complement" list must be the *complete* complement: every code in the universe
  that is **not** in the cohort, and no others — usually **sorted ascending (ASCII)**.
- A "balanced_state_codes"/"state census" list is every unit that survives into the balanced cohort.
- Keep counts as integers (natural JSON ints), and identifiers as the exact portal strings (uppercase
  2-letter state codes, portal division names verbatim, uppercase ISO3).

Getting these counts right early is worth the effort: every downstream module runs on one of these
cohorts, so a mis-built cohort fails many template fields at once.
