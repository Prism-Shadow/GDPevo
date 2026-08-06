# PHO portal data model

The Public Health Observatory portal is a **read-only** web app. Orient yourself first
by fetching two self-describing pages (relative to the base URL your task provides):

- `/catalog` — lists every dataset with its **columns**, **filters**, row counts, coverage
  years, a **measure dictionary** (domain, measure_id, display_name, unit, direction), and
  a CSV export link per dataset.
- `/methodology` — the governing publication rules (release lifecycle, suppression,
  direct-vs-rollup, crude-vs-age-adjusted, RUCC, country-label reconciliation, revisions).

Every dataset can be pulled whole as CSV (`/download?dataset=<name>&format=csv`); the
HTML browse pages accept the filters listed in the catalog. **Always confirm the schema
against the live `/catalog`** — treat the tables below as the expected shape, not gospel.

## Datasets (typical schema)

| dataset | grain | key columns |
|---|---|---|
| `states` | 51 rows (50 states + DC) | `state_fips`,`state_abbr`,`state_name`,`region`,`division`,`is_state` |
| `counties` | counties | `county_fips`,`state_abbr`,`county_name`,`region`,`rucc`,`metro_class`,`population_base`,`latitude`,`longitude` |
| `countries` | countries | `iso3`,`canonical_name`,`portal_label`,`alternate_labels`,`region`,`income_group` |
| `state_health` | observation | `observation_id`,`state_fips`,`state_abbr`,`year`,`measure_id`,`value_type`,`source_type`,`release_status`,`revision`,`value`,`standard_error`,`sample_size`,`suppression_flag`,`quality_flag`,`released_at` |
| `state_socioeconomic` | record | `record_id`,`state_fips`,`state_abbr`,`year`,`release_status`,`revision`,`released_at`,`poverty`,`bachelors`,`median_income`,`unemployment`,`uninsured`,`food_insecurity`,`population`,`quality_flag` |
| `county_health` | observation | `observation_id`,`county_fips`,`state_abbr`,`region`,`year`,`measure_id`,`value_type`,`release_status`,`revision`,`released_at`,`value`,`low_ci`,`high_ci`,`population`,`suppression_flag`,`quality_flag` |
| `county_socioeconomic` | record | `record_id`,`county_fips`,`state_abbr`,`region`,`year`,`release_status`,`revision`,`released_at`,`poverty`,`median_income`,`bachelors`,`unemployment`,`net_migration`,`uninsured`,`population`,`quality_flag` |
| `country_indicators` | observation | `observation_id`,`country_label`,`iso3`,`year`,`indicator_id`,`release_status`,`revision`,`released_at`,`value`,`unit`,`quality_flag` |
| `revisions` | revision notice | `revision_event_id`,`domain`,`entity_id`,`field_id`,`effective_year`,`old_value`,`new_value`,`status`,`issued_at`,`reason_code`,`note` |

## Publication semantics (from `/methodology`)

- **Release lifecycle.** Records are `PROVISIONAL` (revision 0) or `FINAL` (revision ≥ 1).
  *Final replaces provisional; the highest applied final revision governs when several
  final revisions exist.* → resolve each cell to its FINAL max-revision record.
- **Identifiers are TEXT.** `state_fips`/`county_fips`/`iso3` keep leading zeros. A
  county FIPS is 2-char state code + 3-char county suffix.
- **Suppression.** A suppressed cell (`suppression_flag == 1`) keeps its metadata but has
  no value. **Never treat suppressed or missing as zero** — it is *unavailable*.
- **Direct vs rollup.** `source_type` is `DIRECT_SURVEY` (primary state series) or
  `COUNTY_ROLLUP` (parallel coverage-review series). Rollups must not silently replace
  direct records; some tasks perturb one against the other.
- **Crude vs age-adjusted.** `value_type` is `AGE_ADJUSTED` (state comparisons) or
  `CRUDE` (observed county burden). Tasks specify exactly which to select.
- **Quality flags describe review state, not precedence.** Retain `STALE`/`REVISED`/
  caution flags in extracts *unless* the task declares specific flags invalid (e.g.
  `INVALID_SCALE`, `INVALID`, `WITHDRAWN`) — those mark a cell unavailable.
- **RUCC** lives on `counties` (integer 1–9; 1–3 metro, 4–9 nonmetro). Validate range.
- **Units matter.** Percentages and mortality rates are not interchangeable; check the
  measure dictionary `direction` (HIGHER_WORSE / HIGHER_BETTER / NEUTRAL) before signing
  a coefficient claim.

## Revisions dataset (scale breaks / restatements)

Each `revisions` row is a notice keyed by `(domain, entity_id, field_id, effective_year)`
mapping onto an observation series, with `old_value`→`new_value`, a `reason_code`
(`SCALE_CORRECTION`, `SOURCE_RESTATE`, `GEOGRAPHY_RECODE`, `LATE_RESPONSE`) and a `status`:

- `APPLIED` — the correction **is** reflected in a later final revision; use the corrected
  series.
- `PENDING` / `WITHDRAWN` — the notice does **not** authorize replacement. If it flags a
  scale discontinuity (`SCALE_CORRECTION` / quality `SCALE_REVIEW`) that is unresolved,
  the cell is an **anomaly / unresolved scale break** → exclude it from the analysis
  cross-section (and report it if the template asks for anomaly keys).

`domain` values map to datasets: `STATE_HEALTH`, `STATE_SES`, `COUNTY_HEALTH`,
`COUNTY_SES`, `COUNTRY`. `entity_id` is the state/county/iso3 code; `field_id` is the
measure/socio field.

## Country label reconciliation

Requested country **labels** may be a `portal_label`, a `canonical_name`, or one of the
pipe-delimited `alternate_labels` (`"Alder Republic|Alder|Republic of Alder"`). Build one
index from all three onto `iso3`. `alias_resolution_count` counts labels whose text
differs from the resolved `canonical_name`. Resolve to stable `iso3` before any join.
Beware collisions: a short alias like `"Alder"` may belong to a *different* country than
`"Republic of Alder"`.
