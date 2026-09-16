Publication Resolution Algorithm
================================

The publication resolution algorithm selects authoritative records from the
portal for each entity-year-measure combination. Apply these rules exactly
in the order given.

Step 1: Filter
--------------

Filter the downloaded dataset by the effective request specification:

- release_status: typically "FINAL" (exclude "PROVISIONAL" unless specified)
- value_type: as specified (e.g. "AGE_ADJUSTED", "CRUDE")
- source_type: as specified (e.g. "DIRECT_SURVEY", "COUNTY_ROLLUP")
- quality_flag: exclude records with quality_flag in the effective
  invalid_quality_flags list (typically "INVALID_SCALE", "INVALID",
  "WITHDRAWN")
- suppression_flag: exclude records with suppression_flag=1 (or non-zero)
- For state_health: value must be non-null; for state_socioeconomic: each
  field is independently valid; a null poverty does not invalidate a
  non-null bachelors in the same record

Step 2: Select Greatest Revision
---------------------------------

For each unique (entity_id, year, measure_id) tuple among the filtered
records, select the record(s) with the greatest revision number. The
entity_id is state_abbr for states, county_fips for counties, iso3 for
countries.

Step 3: Select Latest Release Timestamp
----------------------------------------

If multiple records tie on revision, select the one with the latest
(maximum) released_at timestamp. For state_health this is the released_at
column; for state_socioeconomic the same; for counties and countries the
same.

Step 4: Select Lowest Record Identifier
---------------------------------------

If multiple records still tie, select the one with the lowest (minimum)
record identifier string: observation_id for health data, record_id for
socioeconomic data.

Count Before Completeness Exclusions
--------------------------------------

When the request asks for resolved observation/record counts, count all
records that survive steps 1-4 before applying analytic completeness
exclusions (i.e. before checking whether required analytic values are
present/non-null).

Missing Value Rule
------------------

Suppressed, invalid, withdrawn, blank, or null analytic values are
unavailable and are never zero-filled. A record that resolves through
steps 1-4 but has a null/suppressed analytic value cannot contribute to
a cohort that requires that value.

Country-Specific Rules
----------------------

For country indicators, first reconcile analyst-provided labels to iso3
using the countries reference:

1. Match each requested label against the portal_label column (exact
   case-sensitive match) OR against any pipe-delimited token in the
   alternate_labels column (exact match).
2. Resolve to the iso3 for that match.
3. If multiple labels map to the same iso3, de-duplicate and report the
   unique iso3 set.
4. The alias_resolution_count is the count of resolved labels whose
   matched text (portal_label or alternate) differs from the canonical_name
   for that iso3.

For revision events on country indicators:

- APPLIED revision_event_id values: list all revision_event_id values where
  status is "APPLIED" and the domain/dataset matches the task scope.
  Sort ascending.
- Non-APPLIED: list all revision_event_id values where status is "PENDING"
  or "WITHDRAWN" (not "APPLIED"). Sort ascending.
- Anomaly cells: ISO3|YEAR|indicator_id cells where quality_flag indicates
  an unresolved scale break. The exact quality flag for scale breaks is
  "SCALE_BREAK". Sort these cells ascending.
