Cohort Building Patterns
========================

After publication resolution, build analytic cohorts from resolved records.
All cohorts respect the missing-value rule: suppressed, invalid, withdrawn,
blank, or null analytic values are unavailable and never zero-filled.

Core Balanced Cohort
--------------------

Definition: Entities that have non-null, non-suppressed values for every
required core_panel_variable (or equivalent) in every analysis year.

Algorithm:
1. From resolved records, for each entity and year, check that every
   required variable has a valid (non-null, non-suppressed) value.
2. An entity is core-complete in a year if all required variables are
   present in that year.
3. The core balanced cohort is the set of entities that are core-complete
   in every analysis year.
4. Report the yearly core-complete counts and the balanced cohort count.

Entity ordering: sort by entity code (state_abbr, county_fips, iso3)
ascending (ASCII order: A-Z before a-z, digits before letters).

Broad / Reference-Year Cohort
------------------------------

Definition: Entities that are complete for the outcome and every ordered
feature/term in a single reference year.

Algorithm:
1. For the reference year, identify entities where the outcome and all
   ordered features have valid (non-null, non-suppressed) values.
2. Features come from both health and socioeconomic sources; each field
   is independently validated.
3. An RUCC/region field counts as "present" if the geography reference
   supplies the value (RUCC is always available for counties; division
   and region are always available from the states reference).

Entity ordering: sort by entity code ascending.

Strict Dual-Source Cohort
--------------------------

Definition: Entities complete for outcome, primary exposure, parallel
exposure, and all adjustments in every analysis year.

Algorithm:
1. For each entity-year, verify the outcome, primary exposure, parallel
   exposure, and all adjustments have valid (non-null) values.
2. The primary and parallel exposures may come from different value_type
   or source_type filters (e.g., AGE_ADJUSTED+DIRECT_SURVEY vs
   CRUDE+DIRECT_SURVEY). Resolve each independently.
3. Balance across all requested years.

Panel Cohort
------------

Definition: Entities complete for all required variables in every panel year.

Algorithm:
1. For each entity-year in the panel range, verify all required variables
   are present and valid.
2. The panel cohort is the intersection of complete entities across all
   panel years.

Machine-Learning Cohort
------------------------

Definition: Primary-cohort members also complete for additional specified
fields in the reference year.

Algorithm:
1. Start with the primary cohort (reference-year complete for core set).
2. Additionally require non-null values for the extra ML fields.
3. Report the ML-complete count.

Ordered Exclusion Lists
-----------------------

When reporting excluded entities:
- core_balanced_excluded_state_codes: all entities not in the balanced
  cohort, sorted ascending (ASCII).
- strict_excluded_state_codes: all entities not in the strict cohort,
  sorted ascending.

Counts
------

Report resolved_health_observations: count of state_health records that
survive resolution steps 1-4 (before completeness exclusions).

Report resolved_socioeconomic_records similarly for state_socioeconomic.

Report yearly_core_complete_n: for each analysis year, count entities
that are core-complete in that year.
