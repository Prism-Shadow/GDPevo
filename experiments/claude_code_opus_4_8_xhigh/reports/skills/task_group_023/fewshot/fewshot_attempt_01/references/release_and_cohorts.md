# Effective request, release resolution, and cohort construction

Everything here is *method*. Bind the actual measures, filters, fields, years, and orders
from the effective request; the examples below name portal fields, not answer values.

## Effective request (freeze one contract first)

Some requests declare a `protocol_id` and may carry override keys. Resolve to a single
effective contract *before any data access, fold, draw, fit, or decision*, and use it
identically in every module.

1. **Trigger.** A registered method profile activates only on an exact, case-sensitive
   `protocol_id` match. Family membership or a similar name is not a match. You are not
   given the profile as input — you reconstruct the effective contract from the request's
   own module descriptions plus these method rules.
2. **Direct keys.** A root key binds to the canonical root key of the identical name;
   inside a named section/module, a child key targets only the identical child path.
3. **Suffix aliases.** A root key named `<section>_overrides` targets canonical
   `<section>`; `module_overrides.<module>` targets that exact top-level module;
   `reporting_overrides` targets `reporting`. Strip only the terminal `_overrides` suffix.
4. **Merge semantics.** Apply resolved entries in request document order. Objects merge
   recursively by exact key; **arrays replace whole arrays** (never concatenate/union/
   position-patch); explicit scalars/strings/Booleans/null replace only their exact path;
   absent paths inherit unchanged.
5. **Validation.** Reject unknown targets, inferred aliases, key renames, and type
   coercions before resolving. Task-local direct bindings win over inherited values at the
   same path. Freeze the merged contract; do not re-resolve mid-run.

## Release & revision resolution (select one record per key)

For each requested publication key (entity × time × measure, plus value_type/source_type
where applicable), among portal records:

1. **Filter** by the effective bindings: `release_status` (typically `FINAL`),
   `value_type`, `source_type`, entity/geography scope, and the requested year set. Drop
   records failing the validity predicate (see below).
2. **Select one** surviving record by the declared release priority. The canonical order
   is: **greatest `revision`**, then **latest `released_at`** timestamp, then a
   **record-id tiebreak**. The id tiebreak direction is a binding knob — some protocols
   take the *lowest* `observation_id`/`record_id`, others the *greatest*; use whichever the
   effective request's release method states. (Requests often spell this as a
   `revision_priority` / `revision_selection` list such as `["revision","released_at",
   "observation_id"]`.)
3. **Count before completeness exclusions when asked.** "Resolved health observations" /
   "selected release counts by year" count the *selected* records, before dropping rows for
   analytic completeness. A selected-but-suppressed/null record still counts as selected
   evidence but is analytically incomplete.

### Validity / missing predicate

A selected value is **available** only if it is non-suppressed (`suppression_flag == 0`),
its `value` is non-blank/non-null, and its `quality_flag` is not in the request's invalid
set (e.g. an `invalid_quality_flags` list like `INVALID_SCALE`/`INVALID`/`WITHDRAWN`).
Socioeconomic records are validated on the requested fields being non-null (sparse nulls
in *other* fields of the same record don't invalidate the requested fields). **Never
zero-fill** an unavailable value; the entity simply lacks that cell.

## Cohort construction (join and filter)

Resolve each measure/series independently, then join by the stable entity and time keys
(state_abbr / county_fips / iso3, and year). Preserve entity-code order then time order,
and preserve every declared feature and group order. Build each named cohort from *its*
effective required fields; a request may define several with different completeness bars:

- **Primary / reference-year cohort** — entities complete for the required variables in
  the reference year (over the full jurisdiction universe).
- **Balanced / balanced-panel cohort** — entities complete for the core variables in
  **every** analysis year (intersection across years).
- **Broad reference cohort** — reference-year complete cases for the outcome and *all*
  ordered model features (e.g. every ridge feature).
- **Machine-learning cohort** — a base cohort further restricted to completeness on the
  extra ML features in the reference year.
- **Strict / dual-source cohort** — complete for outcome + primary exposure + parallel
  exposure + adjustments in **every** analysis year.

Report the exact cohort audit the template asks for: yearly complete counts, per-year
selected release counts, cohort sizes, observation/panel-row totals, and the **excluded**
entity-code lists (every universe code absent from the cohort, and no others), each in the
declared order (usually ascending ASCII state/entity codes).

### Panel / change-row construction (dynamic models)

When a module models *changes*, build adjacent-period change rows ordered by entity then
end-period, deriving lagged levels, first differences, reference indicators (e.g. RUCC
dummies with RUCC1 reference, end-year dummies with the earliest end-year as reference),
period interactions, and any squared/interaction terms in the declared column order.
`median_income` is often rescaled ("per 10000") and income may be modeled as a natural log
— apply exactly the declared transform.

## Country label reconciliation & quality audit (cross-section shape)

For the country-briefing shape (no `protocol_id`):

1. **Reconcile** each requested label against `countries.portal_label`, `canonical_name`,
   and pipe-separated `alternate_labels`; resolve to one `iso3`. Counts: requested labels,
   uniquely resolved labels, and how many resolved labels differ from the canonical name
   (alias resolutions). Return unique ISO3s sorted ascending.
2. **Apply revisions.** From `revisions` (matching domain/entity/field/effective_year),
   partition applicable events into **APPLIED** vs non-APPLIED (`PENDING`/`WITHDRAWN`);
   only APPLIED corrections change published values. Report applied vs non-applied event
   id lists (sorted ascending).
3. **Anomalies.** Flag unresolved scale-break cells (an apparent scale discontinuity with
   no APPLIED correction) as `ISO3|YEAR|indicator_id`, sorted ascending; these cells are
   excluded before imputation. Report raw-missing, anomaly, and imputed cell counts and the
   usable country/indicator matrix dimensions, per the template's field definitions.

Then feed the completed cross-section matrix to the PCA / clustering / panel primitives in
`references/methods.md`.
