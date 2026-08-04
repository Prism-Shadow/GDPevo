 # PHO Methodology Quick Reference

 Extracted from the portal methodology pages. Consult `/methodology` for full documents.

 ## Release Lifecycle
 - **Provisional**: Timely review only. Not for publication.
 - **Final**: Replaces provisional for publication.
 - **Revisions**: When multiple final revisions exist, the highest applied final revision governs.

 ## Value Types
 - **AGE_ADJUSTED**: Supports state comparisons. Preferred for cross-state analysis.
 - **CRUDE**: Describes observed burden, retains county population structure. Used for county-level analysis.

 ## Source Types
 - **DIRECT_SURVEY**: Primary state publication series.
 - **COUNTY_ROLLUP**: Parallel estimate for coverage review. Do not silently substitute for direct records.

 ## Suppression
 - Suppressed observations (`suppression_flag = 1`) retain metadata but publish no value.
 - Never treat suppressed or missing values as zero.

 ## Quality Flags
 - `REVIEWED`, `REVISED`, `PROVISIONAL`, `SUPPRESSED`, `PARALLEL_ESTIMATE`, `STALE`, `CAUTION`
 - `INVALID_SCALE`, `INVALID`, `WITHDRAWN`: Exclude these from analysis.

 ## Rural-Urban Continuum Codes (RUCC)
 - 1–3: Metropolitan counties.
 - 4–9: Nonmetropolitan counties.
 - RUCC 1 is the reference category in models using RUCC dummies.

 ## Country Label Reconciliation
 - Portal labels may differ from canonical names.
 - Use `alternate_labels` (semicolon-separated) and ISO3 identifiers for stable reconciliation.
 - A resolved label that differs from the canonical country name counts as an alias resolution.

 ## Socioeconomic Fields
 - Fields are revised independently after late responses.
 - Sparse null fields do not invalidate other published fields in the same record.

 ## County FIPS
 - Text type. Leading zeros are meaningful.
 - Format: two-character state code + three-character county suffix.

 ## Measure Dictionary (Selected)
 | measure_id | display_name | direction |
 |---|---|---|
 | life_expectancy | Life Expectancy | HIGHER_BETTER |
 | adult_obesity | Adult Obesity | HIGHER_WORSE |
 | adult_smoking | Adult Smoking | HIGHER_WORSE |
 | diagnosed_diabetes | Diagnosed Diabetes | HIGHER_WORSE |
 | physical_inactivity | Physical Inactivity | HIGHER_WORSE |
 | food_insecurity | Food Insecurity | HIGHER_WORSE |
 | frequent_mental_distress | Frequent Mental Distress | HIGHER_WORSE |
 | premature_mortality_rate | Premature Mortality Rate | HIGHER_WORSE |
 | poverty_rate | Poverty Rate | HIGHER_WORSE |
 | bmi_burden | Bmi Burden | HIGHER_WORSE |
 | health_spending_gap | Health Spending Gap | HIGHER_WORSE |
 | hiv_burden | Hiv Burden | HIGHER_WORSE |
 | immunization_gap | Immunization Gap | HIGHER_WORSE |
 | infant_mortality | Infant Mortality | HIGHER_WORSE |
 | adult_mortality | Adult Mortality | HIGHER_WORSE |
 | schooling_gap | Schooling Gap | HIGHER_WORSE |

 ## Census Divisions
 Nine divisions: New England, Middle Atlantic, East North Central, West North Central, South Atlantic, East South Central, West South Central, Mountain, Pacific.
 DC belongs to South Atlantic.

 ## Regions
 Four regions: Northeast, Midwest, South, West.
 DC belongs to South.
