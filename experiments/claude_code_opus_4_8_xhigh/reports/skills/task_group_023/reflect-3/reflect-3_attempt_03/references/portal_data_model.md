# PHO portal data model

The portal is read-only and self-consistent across tasks in this family. It exposes a
**catalog**, three **geography references**, several **domain data tables**, a
**revisions** table, and a **methodology library**, plus a bulk table/CSV export. Load
whole tables and compute locally. Column names below are stable; confirm against the
catalog in the current environment.

## Geography references

- **states** — one row per jurisdiction: `state_fips`, `state_abbr`, `state_name`,
  `region`, `division`, `is_state`. There are **51** rows: 50 states + DC. DC has
  `is_state = 0`. Use uppercase two-letter `state_abbr` as the identifier.
- **counties** — `county_fips` (5-char text = 2-char state + 3-char county),
  `state_abbr`, `county_name`, `region`, `rucc` (integer 1–9), `metro_class`,
  `population_base`, `latitude`, `longitude`. **RUCC lives here**, not in the health
  tables. RUCC 1–3 = metropolitan, 4–9 = nonmetropolitan.
- **countries** — `iso3` (uppercase), `canonical_name`, `portal_label`,
  `alternate_labels` (a single string of **pipe-separated** aliases), `region`,
  `income_group`.

### Regions and the 9 census divisions (fixed)

Regions: **Northeast, Midwest, South, West**. Each state maps to exactly one of the 9
census divisions, and each division sits in exactly one region:

| division | region |
|---|---|
| New England | Northeast |
| Middle Atlantic | Northeast |
| East North Central | Midwest |
| West North Central | Midwest |
| South Atlantic | South |
| East South Central | South |
| West South Central | South |
| Mountain | West |
| Pacific | West |

Jurisdiction counts by region (incl. DC): Northeast 9, Midwest 12, South 17, West 13.
Modules that "cluster by census division" therefore have **9** groups.

## Domain data tables

All domain tables carry release metadata: `release_status` (`FINAL` / `PROVISIONAL`),
`revision` (integer), `released_at` (date), and usually a `quality_flag`.

- **state_health** — `observation_id`, `state_fips`, `state_abbr`, `year`, `measure_id`,
  `value_type` (`CRUDE` / `AGE_ADJUSTED`), `source_type` (`DIRECT_SURVEY` /
  `COUNTY_ROLLUP`), `release_status`, `revision`, `value`, `standard_error`,
  `sample_size`, `suppression_flag` (0/1), `quality_flag`, `released_at`.
  Measures include life_expectancy, adult_obesity, adult_smoking, diagnosed_diabetes,
  physical_inactivity, frequent_mental_distress, food_insecurity,
  premature_mortality_rate.
- **county_health** — like state_health but **no `source_type`/`sample_size`**; adds
  `region`, `low_ci`, `high_ci`, `population`. Measures include adult_obesity,
  adult_smoking, copd, depression, diagnosed_diabetes, physical_inactivity,
  severe_housing_cost_burden, short_sleep.
- **state_socioeconomic** — `record_id`, fips/abbr, `year`, release metadata, then
  `poverty`, `bachelors`, `median_income`, `unemployment`, `uninsured`,
  `food_insecurity`, `population`, `quality_flag`.
- **county_socioeconomic** — `record_id`, fips/abbr, `region`, `year`, release
  metadata, then `poverty`, `median_income`, `bachelors`, `unemployment`,
  `net_migration`, `uninsured`, `population`, `quality_flag`. (Note: county SES carries
  `net_migration`; state SES carries `food_insecurity`. Socioeconomic fields are
  revised independently — a null in one field does **not** invalidate the record.)
- **country_indicators** — `observation_id`, `country_label`, `iso3`, `year`,
  `indicator_id`, `release_status`, `revision`, `released_at`, `value`, `unit`,
  `quality_flag`. Indicators carry different **units** (percent, deaths per 100,000,
  deaths per 1,000, years) — never combine incommensurable units without
  standardising. Burden-type indicators include adult_mortality, bmi_burden,
  health_spending_gap, hiv_burden, immunization_gap, infant_mortality, poverty_rate,
  schooling_gap; life_expectancy is a favourable outcome.

## Revisions table

`revision_event_id`, `domain` (COUNTRY / STATE_HEALTH / STATE_SES / COUNTY_HEALTH /
COUNTY_SES), `entity_id` (a state/county/ISO3 code), `field_id` (a measure/field),
`effective_year`, `old_value`, `new_value`, `status` (**APPLIED / PENDING /
WITHDRAWN**), `issued_at`, `reason_code` (**SOURCE_RESTATE / GEOGRAPHY_RECODE /
LATE_RESPONSE / SCALE_CORRECTION**), `note`.

Key fact: the domain data already reflects **APPLIED** revisions — an applied
correction appears as a *higher final revision* of the cell (e.g. a later
`CORRECTED` record), so ordinary highest-final-revision resolution picks it up. The
revisions table is used to (a) enumerate which events are APPLIED vs not for audit
outputs and (b) flag **unresolved scale breaks** (a `SCALE_CORRECTION` whose status is
PENDING/WITHDRAWN — the corrected value was *not* substituted). See
`resolution_and_cohorts.md`.

## Methodology library (rules that bind your computation)

The portal's methodology documents encode the conventions the reference implementation
uses. The load-bearing ones:

- **Release lifecycle** — provisional records support timely review; final records
  replace provisional; **the highest applied final revision governs** when several
  final revisions exist.
- **Small-number suppression** — suppressed observations keep metadata but publish no
  value; **never treat suppressed or missing as zero**.
- **Direct vs rollup** — direct-survey estimates are the primary state series; county
  rollups are parallel coverage estimates and must not silently replace direct records.
- **Crude vs age-adjusted** — age-adjusted for cross-jurisdiction comparison; crude for
  observed local burden. Filter to exactly what the request's evidence spec names.
- **Quality flags** — describe review state and do **not** change release precedence,
  with the scale-break exception noted above.
- **Geographic identifiers** — FIPS are text; leading zeros meaningful; county_fips =
  state(2) + county(3).
- **Country label reconciliation** — portal labels can differ from canonical names;
  reconcile through canonical/alternate labels to stable ISO3 identifiers.
