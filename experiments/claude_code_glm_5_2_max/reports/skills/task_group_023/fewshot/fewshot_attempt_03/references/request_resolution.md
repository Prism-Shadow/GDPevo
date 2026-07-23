# Effective Request Resolution, Release Priority, and Cohorts

The `analysis_request.json` is a *registered protocol instance*. Before touching any data,
resolve it to one frozen **effective request**, then use that contract consistently in every
module. This file defines the override semantics, the publication release priority, the
cohort construction rules, and the ordering conventions.

## 1. Activation and protocol identity

- A protocol-specific profile activates **only** when the future request's `protocol_id` is
  the exact, case-sensitive string. Family membership, a similar name, or similar subject
  matter is **not** a match.
- The method (numerics) is portable across the family; the task-local bindings are not. Bind
  entities, measures, fields, time coordinates, sources, random initialization, parameter
  grids, reporting cutoffs, output names, and business predicates exclusively from the
  effective request.
- **Never carry solved analytical values across invocations.** Recompute all evidence and
  outputs for the current request.

## 2. Override resolution (build one effective request)

Start from the registered method profile and any inherited canonical defaults for the exact
protocol version, then fold the request's explicit bindings in **document order**:

- **Direct keys.** A direct request key `k` targets the canonical root key of the identical
  name. Inside a named section or module, a direct child key targets only the identical child
  path.
- **Suffix aliases.** A root key named `<section>_overrides` targets canonical `<section>`;
  `module_overrides.<module_name>` targets the canonical top-level module of that exact name;
  `reporting_overrides` targets `reporting`. Strip only the terminal `_overrides` suffix
  during target resolution.
- **Merge rules.**
  - Objects merge recursively by exact key.
  - Arrays replace the inherited array **whole** — never concatenate, union, or patch by
    position.
  - Explicit scalars / strings / booleans / null replace only their exact path.
  - Absent paths inherit unchanged.
- **Validation (reject before computing).** No array concatenation, positional patch, inferred
  alias, key renaming, or type coercion. Reject unknown targets and incompatible types.
- **Precedence.** Task-local direct bindings and resolved overrides take precedence over
  inherited values at the same path.
- **Freeze.** Resolve exactly one effective request before any data access, folding, random
  draw, fit, aggregation, or decision, and use it in every module.

## 3. Release resolution (select one record per key)

For each requested publication key (entity + time + measure/field + value_type + source_type,
as the dataset requires), filter by the effective bindings (release status, source, value
type, validity, geography), then select **one** surviving record using the request's declared
ordered release priority. The canonical default priority, unless the request overrides it:

1. **Greatest `revision`** among FINAL records (highest applied final revision governs).
2. Then **latest `released_at`** timestamp.
3. Then **greatest** (or, where the request declares, lowest) record identifier
   (`observation_id` / `record_id`) — follow the request's exact tie-break string.

Rules that always hold:

- **Final replaces provisional** for publication. Provisional records support timely review
  but are not the publication series when a FINAL exists.
- Only **APPLIED** revision events are reflected in later final revisions. `PENDING` and
  `WITHDRAWN` notices do **not** authorize replacing a published value.
- Direct survey estimates are the primary state series; county rollups are parallel coverage
  estimates and must not silently replace direct records (use rollups only where the request
  explicitly swaps the outcome source — e.g. an exhaustive source-perturbation module).
- Suppressed, invalid, withdrawn, blank, or null analytic values are **unavailable** and are
  **never zero-filled**.
- When a module asks to count "selected publications," count the selected records **before**
  analytic completeness exclusions. A selected-but-suppressed record still counts as a
  publication; it just fails the analytic completeness predicate.

### Revision / anomaly handling (when a module requests it)

Some protocols (notably country-burden audits) require reconciling `revisions` events:

- Partition applicable revision events into **APPLIED** and **non-APPLIED** (PENDING /
  WITHDRAWN) by `revision_event_id`, sorted ascending.
- An unresolved **scale-break** cell (an observation whose unit/scale is inconsistent and not
  corrected by an APPLIED revision) is an **anomaly**. Report anomaly observation keys as
  `ISO3|YEAR|indicator_id` (or the dataset's equivalent), sorted ascending. Exclude anomaly
  cells from the analytic matrix; impute remaining missing requested cells per the module's
  declared rule (e.g. column mean / PCA-appropriate completion) and report the imputed count.
- `raw_missing` counts missing requested indicator cells **before** anomaly exclusions;
  `anomaly` counts unresolved scale-break cells in the cross-section; `imputed` counts total
  cells imputed **after** quality exclusions.

## 4. Cohort construction

Build each analytic set from the effective completeness predicates. Common cohort types
(names vary by protocol — bind from the request):

- **Primary / reference-year complete cases** — entities complete (nonsuppressed, nonmissing)
  on the outcome, focal exposure, adjustments, and any reliability weight in the reference
  year, drawn from the declared jurisdiction universe.
- **Balanced / core panel cohort** — the intersection of complete-case entities across **every**
  requested analysis year (entities complete in all years).
- **Broad reference cohort** — reference-year complete cases for the outcome and all ordered
  ridge/elastic-net features.
- **Strict dual-source cohort** — complete for outcome, primary exposure, parallel exposure,
  and adjustments in **every** analysis year.
- **Machine-learning cohort** — primary-cohort members also complete on the extra ML features
  (e.g. unemployment, net_migration, uninsured).

Construction rules:

- Join independently resolved series by the effective **stable entity** and **time** keys.
- Apply the effective completeness predicates per field. Socioeconomic sparse nulls do not
  invalidate other published fields in the same record unless that field is itself required.
- **Reliability weight** (when declared): use the selected outcome direct-record
  `sample_size` as the fixed positive weight, including in source-perturbation refits, unless
  overridden.
- Preserve **entity-code then time** order, and preserve every declared feature and group
  order. Do not re-sort aligned arrays.

Report the cohort audit the template asks for: selected release counts by year, annual
complete counts, primary / balanced / ML cohort counts, excluded entity codes (complete
exclusion set — every universe entity absent from the cohort, and no others), and state/entity
counts.

## 5. Ordering conventions (apply everywhere)

- **Entity order:** ascending entity code (uppercase 2-letter state code; uppercase ISO3;
  county FIPS as text). When a module says "registered division order" or "registered group
  order," use the order the request declares (often the portal's division list in catalog
  order, or the request's explicit `division_order` / `group` list).
- **Time order:** ascending year / end-period.
- **Feature / coefficient order:** exactly as declared in the request (e.g.
  `feature_order`, `coefficient_order`, `primary_design_order`, `instrument_order`).
- **Grid order:** exactly as declared (`lambda_grid`, `alpha_grid_in_order`,
  `l1_ratio_grid_in_order`, `r2_*_values`).
- **Checkpoint / replicate order:** exactly the request's `checkpoint_replicates` /
  `quantile_probabilities` / replicate schedule.
- **Source / subset enumeration order:** increasing subset size then lexicographic tuple
  order; or registered disagreement order; or `ordered_groups` / `ordered_rollup_state_codes`
  as declared.
- **Tie-breaks** follow each method's documented rule (see [`methods.md`](methods.md)):
  smaller penalty / smaller grid value / earlier entity code / smaller bitmask / lexicographically
  smallest permutation, as applicable.

## 6. Single contract

Resolve one effective request, then run modules in the order the request lists them. Modules
are not independent silos: bootstrap reuses the fixed-effects / weighted fit; conformal reuses
nested-CV outer predictions; sensitivity reuses the primary mediation fits; source perturbation
reuses the primary design and reliability weights. Bind every reuse from the same effective
request and the same resolved evidence.
