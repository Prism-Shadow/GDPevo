# Request Resolution, Release Resolution, and Cohorts

These three steps run **before any modeling**, in this order. They are reusable
method; all task-local values (filters, priority order, fields, cohort
definitions) come from the effective request.

## 1. Resolve one effective request (override resolution)

Some protocols ship a registered method profile plus canonical defaults and let
the request override them. Fold everything into **one frozen effective contract**
before any data access, fit, draw, or decision, and use it identically in every
module. Rules (consistent across protocols):

- **Base.** Start from the registered method profile and inherited canonical
  defaults for the **exact protocol version**.
- **Direct keys.** A direct request key `k` binds to the canonical root key `k`.
  Inside a named section/module, a child key `k` binds to only the identical child
  path.
- **Override aliases.** A root key `<section>_overrides` targets canonical
  `<section>`; `module_overrides.<module_name>` targets the canonical top-level
  module of that exact name; `reporting_overrides` targets `reporting`. Strip only
  the terminal `_overrides` suffix during target resolution.
- **Merge, in request document order:**
  - Objects recursively merge by exact key.
  - Arrays **replace whole arrays** — never concatenate, union, or merge by
    position.
  - Explicit scalars/strings/booleans/null replace only their exact path.
  - Absent paths inherit unchanged.
- **Validation (reject before resolving):** no array concatenation, no positional
  patching, no inferred aliases, no key renaming, no type coercion, no unknown
  targets, no incompatible types. Task-local direct or resolved values win at the
  same path over inherited values.
- **Single contract.** Resolve exactly one effective request; use it everywhere.

If the request carries no profile/overrides, the effective request is the request
itself — still freeze it before modeling.

## 2. Release / revision resolution

For each requested publication key (entity × time × measure × value-type ×
source), resolve **one** final record. Steps:

1. **Filter** by the effective bindings: `release_status` (typically `FINAL`),
   `source_type` (e.g. `DIRECT_SURVEY` vs `COUNTY_ROLLUP`), `value_type` (e.g.
   `AGE_ADJUSTED` vs `CRUDE`), validity (`suppression_flag`, `quality_flag`,
   non-null `value`), and geography scope (states/counties/countries + any region
   filter).
2. **Select one** record per declared key using the **declared release priority
   order**. The typical chain is greatest `revision` → latest `released_at`
   timestamp → record identifier, but:
   - The priority *order* is declared in the request (some protocols order by
     revision → released_at → id; others differ).
   - The record-id tie-break **direction is task-local** — at least one protocol
     uses *lowest* id, another uses *greatest* id. Read it from the effective
     request; do not assume.
3. **Validity of the selected value.** A selected record whose analytic `value` is
   suppressed, invalid, withdrawn, blank, or null remains publication evidence but
   is **analytically unavailable** — **never zero-fill**. Count selected
   publications *before* analytic-completeness exclusions when the request asks
   for selected counts.
4. **Revision events** (`/data/revisions`, `status=APPLIED`): only `APPLIED`
   events authorize publication use. Pending/withdrawn notices do not replace
   published values. Use them in quality-audit modules (applied vs non-applied
   event ids, unresolved scale-break anomalies where `old` vs `new` differ by a
   large factor, imputation accounting).
5. **Direct vs rollup / primary vs parallel.** Keep direct survey as the primary
   series; treat rollups as parallel estimates. When a module exposes a
   "primary series" and a "parallel series" (or "baseline" vs "replacement"
   source), resolve each independently with its own filters — perturbation modules
   depend on this distinction.

Tie-break selection must be reproducible: when revision and timestamp tie, the
record-id rule (with its declared direction) decides. Re-derive; never cache.

## 3. Cohort construction

Join the independently resolved series by the effective **stable entity** and
**time** keys (e.g. `state_abbr`×`year`, `county_fips`×`year`, `iso3`×`year`).
Then construct each declared cohort from its required fields. Common cohort types:

- **Complete-case (primary) cohort.** Entities complete on the outcome and all
  declared adjustment fields for the reference/primary year. Validity = selected
  health values present/nonsuppressed/non-null and the declared socioeconomic
  fields non-missing (plus any RUCC/region attribute rule).
- **Balanced panel cohort.** Intersection of complete-case entities across **every
  requested analysis year** (or the declared balanced years). Used by panel/FE and
  trajectory modules.
- **Broad reference cohort.** Reference-year complete cases for the outcome and all
  ordered features (e.g. ridge features). Used by predictive modules.
- **Strict dual-source cohort.** Entities complete for outcome, primary exposure,
  parallel exposure, and adjustments in **every** analysis year. Used by
  source-perturbation modules.
- **Machine-learning cohort.** Primary-cohort members also complete for the
  declared ML-only fields (e.g. unemployment, net_migration, uninsured).

Construction rules:

- **Ordering.** Preserve **entity-code then time** order (e.g. state/county FIPS or
  ISO3 ascending, then year ascending). Preserve every declared feature order and
  group order. Never independently re-sort an aligned result array.
- **Completeness is field-specific.** A null in one socioeconomic field does not
  invalidate sibling fields unless the cohort definition requires that field.
- **Weights.** If the request declares a reliability weight (e.g. a selected
  `sample_size`), carry it as a **fixed positive weight** through every fit in the
  module that requires it — including source-perturbation refits — unless
  overridden. Do not recompute or renormalize it across refits.
- **Exclusions.** Report excluded entity codes (e.g. excluded states/counties) in
  the declared order and format when the template requires it.
- **Counts.** Report requested counts exactly as defined: selected rows by year,
  yearly complete counts, primary/balanced/ML cohort sizes, cluster/group counts,
  observation counts. These are computed for the invocation, never copied.

## 4. Feature and design assembly

After cohorts are built, assemble each module's design matrix in the **declared
column order** with the declared transformations:

- Transformations named in the request (e.g. `median_income_per_10000`,
  `log_income` = natural log of unscaled median_income, squared terms
  `<x>_squared`, interactions `<a>*<b>`, lagged levels, period changes/deltas,
  RUCC indicators with the declared reference level dropped).
- Region/division/RUCC/period indicators built from the geography reference, with
  the declared reference category omitted and the remaining indicators in declared
  order.
- Panel/dynamic designs: adjacent-change rows ordered by entity then end-period;
  lagged levels and dynamic changes derived in declared order; instrument lists
  and coefficient lists in declared order.

The assembled design is the shared input to the analytic modules in
[`module_methods.md`](module_methods.md).
