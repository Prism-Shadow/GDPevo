# Public Health Evidence Portal — Audit Skill

## Overview

This skill covers statistical data audits using a Public Health Evidence Portal that
serves static HTML pages and downloadable CSV files for **state**, **county**, and
**country** health/statistical analyses. The portal is synthetic but follows patterns
found in CDC PLACES, WHO, and World Bank data sources. All CSVs are generated with a
fixed seed and combine geographic profiles, year trends, and random noise.

### Portal Access

All data is accessed via HTTP at a base URL (set by `GDPEVO_ENV_BASE_URL` or
`<TASK_ENV_BASE_URL>`). The portal serves:

- **Pages** at `/pages/<name>.html` — documentation, schema reference, known caveats
- **Data** at `/data/<name>.csv` — downloadable CSV files
- **Homepage** at `/` — navigation and download index

Always read the portal pages first to understand schema and documented caveats before
downloading CSVs. The methodology page at `/pages/methodology.html` lists row counts
and generation notes.

---

## Data Download Workflow

```
1. Fetch /pages/methodology.html → get row counts, generation notes
2. Fetch the relevant /pages/<topic>.html → get schema, known caveats, sample rows
3. Fetch /data/<target>.csv → download the full CSV
4. Parse CSV with proper quoting (fields may contain commas in quoted strings)
5. Validate against documented caveats and row counts
```

### CSV Parsing Notes

- All CSVs use standard comma separation with double-quote escaping
- Field values may contain commas (e.g. `"Korea, Rep."`, `"Egypt, Arab Rep."`)
- Use a proper CSV parser (Python `csv.DictReader`, R `read.csv`); do not split on raw commas
- FIPS codes are strings, not integers — always preserve leading zeros
- Empty cells represent missing data (not zero); treat as `NA`/`None`

---

## State-Level Data

### state_health_long.csv

**Columns:** `year, state_fips, state, state_name, territory_flag, measure_id, measure,
category, stratum_type, stratum, sample_size, data_value_type, data_value,
low_confidence_limit, high_confidence_limit, source_note`

**Years:** 2019–2024 (6 years)

**Measures (6):**
| measure_id | measure | category |
|---|---|---|
| OBESITY | Adult obesity prevalence | Risk factor |
| DIAB_MORT | Diabetes mortality rate | Mortality |
| LIFE_EXP | Life expectancy | Outcome |
| INACTIVE | Physical inactivity prevalence | Risk factor |
| SCREEN | Preventive screening prevalence | Prevention |
| VACC_COMP | Vaccination completion | Prevention |

**Entities:** 50 states + DC + 3 territories (PR=Puerto Rico, GU=Guam, VI=U.S. Virgin Islands)
— total 54 state-level rows per measure-year.

**Stratum types (5):** Total, Age, Sex, Income quartile, Race/ethnicity

**Critical filter for state-level analysis:**
- `territory_flag = N` — exclude territories (PR, GU, VI)
- `stratum_type = Total` AND `stratum = Total` — use only Total estimates
- This yields 51 rows per measure-year (50 states + DC), minus intentional missing data

**Known missing data (documented on portal):**
- **CA 2024 OBESITY Total** — missing; a stale 2023 row is retained with source_note
  `"Stale 2023 Total retained beside missing 2024 Total"`
- **TX 2024 LIFE_EXP Total** — missing; a stale 2023 row is retained with same note
- Always check `source_note` column for these stale-row markers
- When stale rows exist, the 2024 count of valid states drops below 51 for that measure

**Known duplicate:**
- **OH 2021 INACTIVE Black** — intentional duplicate row from overlapping extract
  (source_note: `"Intentional duplicate stratified row from overlapping extract"`)
- Deduplicate before counting or model fitting

**Territory exclusion:**
- Territories are PR, GU, VI — flag `territory_flag=Y`
- Territory rows are excluded from all state-level analyses
- List excluded territories in output sorted ascending by abbreviation

### state_life_expectancy.csv

Separate CSV for life expectancy with different granularity.
**Columns:** `year, state, state_name, territory_flag, stratum_type, stratum,
life_expectancy, low_confidence_limit, high_confidence_limit, note`
- Also subject to TX 2024 Total missing / stale 2023 retention

### state_ses_long.csv

**Columns:** `geo_fips, state, state_name, geo_name, geo_level, attribute,
attribute_label, value, unit, extraction_note`

**Critical filtering rule — the "000 suffix" pattern:**
- State-level rows: `geo_level = "state"` AND `geo_fips` ends in `000`
  (e.g. `01000` for Alabama, `02000` for Alaska)
- County-like distractors: `geo_fips` does NOT end in `000` (e.g. `01001`, `01002`)
  with `geo_level = "county-like distractor"`
- **Always apply both conditions together** to isolate true state rows

**State SES attributes (6):**
| attribute | label | unit |
|---|---|---|
| PCTPOVALL_2023 | Percent in poverty, all ages | percent |
| MEDHHINC_2023 | Median household income, 2023 | dollars |
| Unemployment_rate_2023 | Unemployment rate, 2023 | percent |
| Percent_bachelors_or_higher_2019_23 | Bachelor degree or higher, 2019-23 | percent |
| POP_ESTIMATE_2023 | Population estimate, 2023 | persons |
| R_NET_MIG_2023 | Net migration rate, 2023 | per 1,000 |

### state_regions.csv

**Columns:** `state_fips, state, state_name, region, division, state_level_analysis_flag, note`

- `state_level_analysis_flag = "Y"` for 50 states + DC — these are valid for analysis
- `state_level_analysis_flag = "N"` for territories (PR, GU, VI) — exclude
- **Regions (4):** South, West, Northeast, Midwest
- **Divisions (9):** East South Central, West South Central, South Atlantic, Pacific,
  Mountain, New England, Middle Atlantic, East North Central, West North Central
- Join to state health data on `state` (2-letter abbreviation)

### state_neighbors.csv

**Columns:** `state, state_name, region, division, neighbors, neighbor_count,
isolate_flag, neighbor_names, note`

- `neighbors` is pipe-delimited: `"FL|GA|MS|TN"`
- `isolate_flag = "Y"` for states with no contiguous neighbors
- **Isolates (many):** AK, HI, ID, IN, IA, KS, LA, ME, MD, MI, MN, MS, MO, MT, NE,
  NV, NH, NJ, NM, ND, OK, RI, SC, SD, TN, UT, VT, VA, WI, WY
- In spatial analysis (Moran's I), isolate states need special handling — they have
  no spatial weights

---

## County-Level Data

### county_health_long.csv

**Columns:** `year, fips, state, county, measure_id, measure, category,
data_value_type, data_value, low_confidence_limit, high_confidence_limit, population`

**Years:** 2021–2024 (4 years)

**Measures (16):**
| measure_id | measure | category |
|---|---|---|
| CASTHMA | Current asthma among adults | Health outcomes |
| DIABETES | Diagnosed diabetes among adults | Health outcomes |
| DEPRESSION | Depression among adults | Health outcomes |
| CHD | Coronary heart disease among adults | Health outcomes |
| GHLTH | Fair or poor self-rated health | Health status |
| OBESITY | Obesity among adults | Health risk behaviors |
| LPA | No leisure-time physical activity | Health risk behaviors |
| CSMOKING | Current smoking among adults | Health risk behaviors |
| SLEEP | Short sleep duration among adults | Health risk behaviors |
| BINGE | Binge drinking among adults | Health risk behaviors |
| MAMMOUSE | Mammography use among eligible women | Prevention |
| BPMED | Taking blood pressure medication | Prevention |
| CHECKUP | Annual checkup among adults | Prevention |
| COREM | Core preventive services for older men | Prevention |
| COREW | Core preventive services for older women | Prevention |
| DENTAL | Dental visit among adults | Prevention |

- `population` may be blank for some county-year rows — treat as missing
- Some counties intentionally lack selected measures (not all 16 appear for every county)
- `fips` is 5-digit zero-padded string — use as join key, not integer

### county_ses_long.csv

**Columns:** `fips, state, county, attribute, attribute_label, value, unit, join_note`

**Attributes (12):**
| attribute | label | unit |
|---|---|---|
| PCTPOVALL_2023 | Percent poverty, all ages | percent |
| MEDHHINC_2023 | Median household income, 2023 | dollars |
| Unemployment_rate_2010 | Unemployment rate, 2010 | percent |
| Unemployment_rate_2023 | Unemployment rate, 2023 | percent |
| Median_Household_Income_2022 | Median household income, 2022 | dollars |
| Percent_bachelors_or_higher_2019_23 | Bachelor degree or higher, 2019-23 | percent |
| POP_ESTIMATE_2023 | Population estimate, 2023 | persons |
| CENSUS_2020_POP | Census population, 2020 | persons |
| R_NET_MIG_2023 | Net migration rate, 2023 | per 1,000 |
| R_NATURAL_CHG_2023 | Natural change rate, 2023 | per 1,000 |
| RUCC_2023 | Rural-urban continuum code, 2023 | code |
| Economic_typology_2015 | Economic typology, 2015 | category |

### county_metadata.csv

**Columns:** `fips, state, state_name, county, rucc_code, economic_typology,
census_division, metadata_note`

- `rucc_code`: integer 1–9 (RUCC 2023 classification)
- `economic_typology`: categorical (Mining, Recreation, Federal/State government,
  Farming, Nonspecialized, Persistent poverty, Manufacturing, Old name)
- `census_division`: matches state_regions divisions

### County Data Cleaning — Required Steps

1. **Remove invalid FIPS:** `fips = "00000"` with `state = "ZZ"`, `county = "Unknown County"`
   - Present in both `county_ses_long.csv` and `county_metadata.csv`
   - These are intentional data-quality traps — always filter out

2. **Remove old-name counties:** County name contains a number suffix pattern
   (e.g. `"Adams 27 County"`, `"Benton 28 County"` — 22 such patterns)
   - These are intentional join-breakers: the health data uses the canonical name
     (`"Adams County"`) while the SES data has the old-name variant (`"Adams 27 County"`)
   - **Detection:** county name matches regex `\d+ County` (a digit followed by "County")
   - Also check `county_metadata.csv` for `metadata_note` containing "Old county name"
     (e.g. Shannon County SD → Oglala Lakota County)
   - When joining county health ↔ county SES, rows with old-name counties in SES won't
     match health data → they become missing-SES exclusions

3. **Complete-case assembly:**
   - Join county health + county SES on `fips`
   - Pivot SES from long to wide (each attribute becomes a column)
   - Track exclusions by reason:
     - `invalid_fips`: count of rows with FIPS 00000
     - `outside_requested_states`: rows with state not in the requested state list
     - `missing_ses`: rows where SES join fails (old-name counties, missing attributes)
     - `missing_health_data`: rows where health measure is missing for the outcome

4. **Requested states ordering:** When a task specifies a list of states (e.g.
   "AL, GA, MS, TN, KY, WV"), preserve that order in the `requested_states` output
   array — do not sort alphabetically

### County Derived Variables

**Income change (static):**
```
income_change = MEDHHINC_2023 - Median_Household_Income_2022
```
Rule name: `MEDHHINC_2023_minus_Median_Household_Income_2022`

**Dynamic specification (difference-in-differences style):**
```
unemployment_change = Unemployment_rate_2023 - Unemployment_rate_2010
income_change = MEDHHINC_2023 - Median_Household_Income_2022
```
Rule name: `unemployment_2023_minus_2010_and_income_2023_minus_2022`

**RUCC handling:** Always `categorical_dummies` — RUCC codes (1–9) are treated as
categorical factor levels, not as a continuous numeric variable.

---

## Country-Level Data

### country_health_panel.csv

**Columns:** `country, iso3, year, life_expectancy, adult_mortality, bmi, alcohol,
health_expenditure, immunization, schooling, income_composition, gdp, population,
infant_mortality, missingness_note`

**Years:** 2015–2024 (10 years), ~109 countries

**Variables:**
| column | description | missingness |
|---|---|---|
| life_expectancy | Life expectancy at birth (years) | Complete |
| adult_mortality | Adult mortality rate (per 1,000) | Complete |
| bmi | Mean BMI | Complete |
| alcohol | Alcohol consumption (liters/capita) | Complete |
| health_expenditure | Health expenditure (% GDP) | Complete |
| immunization | Immunization coverage (%) | Complete |
| schooling | Mean years of schooling | Sparse |
| income_composition | Income composition of HDI | Sparse |
| gdp | GDP per capita (USD) | Mostly complete |
| population | Total population | Complete |
| infant_mortality | Infant mortality rate (per 1,000) | Complete |

**Known anomalies (documented on portal page):**
- **Namibia (NAM) BMI scaled 2018–2021:** BMI values ~9–12 (normal ~21–27) — scale error
- **Eswatini (SWZ) adult_mortality 10× drop:** Dramatic drop in adult_mortality —
  possible unit change or data error
- **Japan (JPN) complete GDP gaps:** GDP values are all missing — complete gap
- **Missingness note column:** `missingness_note` field in the CSV flags rows with
  known issues

**Anomaly detection approach:**
- Compute country-level means and variances for each variable
- Flag country-years where values deviate beyond expected bounds
- For the `adult_mortality_scaled_country_years` field: return list of
  `{iso3, years[]}` objects where adult mortality shows anomalous scaling
- For the `bmi_scaled_country_years` field: return list of
  `{iso3, years[]}` objects where BMI shows anomalous scaling
- For `complete_gdp_gap_iso3`: list ISO3 codes where GDP is entirely missing
  — sorted ascending

### country_metadata.csv

**Columns:** `country, iso3, region, income_group, lending_category, metadata_note`

- `income_group` values: Low income, Lower middle income, Upper middle income, High income
- **CRITICAL:** `lending_category` is a **distractor** — do NOT confuse with `income_group`
  - lending_category values: IDA, IBRD, Blend, Not classified
  - Only `income_group` is used for grouped/hierarchical models
- Join health panel to metadata on `iso3`

### country_name_variants.csv

**Columns:** `canonical_country, variant_name, iso3, reconciliation_note`

- 14 variant pairs (e.g. "Korea, Rep." ↔ "South Korea", "Turkiye" ↔ "Turkey")
- The health panel uses the **canonical** country names
- If joining external data, match on `iso3` (not country name) first
- Variant lookups are for resolving externally-sourced country names to canonical form

### Name Reconciliation for Country Joins

```
1. Join country_health_panel ↔ country_metadata on iso3 (preferred)
2. For external names: look up in country_name_variants.csv variant_name → iso3
3. Track coverage:
   - metadata_join_coverage: fraction of panel country-years that join to metadata
   - variant_rows: total variant entries (14)
   - resolved_variant_rows: variants that successfully map to panel countries
   - unresolved_variant_rows: variants that don't map
```

---

## Statistical Conventions

### Rounding Rules

| precision | applies to |
|---|---|
| **3 decimals** | std_beta, p-values, ICC, Spearman ρ, PC1 variance share, Moran's I, missing rates, bootstrap CI bounds (low/high), regression betas, indirect effects, random intercept variance ratio, join coverage ratios |
| **2 decimals** | AIC, VIF, tercile means (T1/T2/T3) |
| **1 decimal** | attenuation_pct (percentage of beta reduction) |
| **Integer** | analysis_year, state counts, cluster counts, rows_used, variable_count, complete_case_count, exclusions_by_reason values |

### Bucket / Enum Rules

**p-value buckets:**
- `lt_0_001` — p < 0.001
- `lt_0_01` — 0.001 ≤ p < 0.01
- `lt_0_05` — 0.01 ≤ p < 0.05
- `ge_0_05` — p ≥ 0.05
- `not_computed` — value not computed (e.g. due to missing data)

**VIF buckets:**
- `lt_5` — VIF < 5
- `5_to_10` — 5 ≤ VIF < 10
- `ge_10` — VIF ≥ 10

**ICC buckets:**
- `lt_0_05` — ICC < 0.05
- `0_05_to_0_15` — 0.05 ≤ ICC < 0.15
- `ge_0_15` — ICC ≥ 0.15

**Moran's I buckets:**
- `lt_0_05` — I < 0.05
- `0_05_to_0_20` — 0.05 ≤ I < 0.20
- `ge_0_20` — I ≥ 0.20

**Random intercept variance bucket:**
- `low` — variance ratio < 0.10
- `moderate` — 0.10 ≤ variance ratio < 0.30
- `high` — variance ratio ≥ 0.30

**Bootstrap CI enumeration:**
- `positive_excludes_zero` — CI entirely above zero (CI low > 0)
- `negative_excludes_zero` — CI entirely below zero (CI high < 0)
- `includes_zero` — CI spans zero (CI low < 0 < CI high)

**Sensitivity verdict:**
- `stable` — adjusted estimate within 20% of original
- `sign_flip` — coefficient sign changed
- `significance_changed` — crossed a significance threshold
- `magnitude_shift_gt_20` — magnitude changed >20% but sign same

**Model conclusion (confounding audit):**
- `supported_after_adjustment` — exposure remains significant with meaningful effect after adjustment
- `partly_confounded` — effect substantially attenuated but still present
- `not_primary_after_adjustment` — effect no longer significant after adjustment

**Coefficient sign:**
- `positive` — coefficient > 0 and meaningfully different from zero
- `negative` — coefficient < 0 and meaningfully different from zero
- `near_zero` — coefficient approximately 0

**Priority direction (for rankings):**
- `higher_value_worse` — larger data_value = worse outcome (e.g. mortality, obesity)
- `lower_value_worse` — smaller data_value = worse outcome (e.g. screening, vaccination)

### PCA Conventions (Country Burden Score)

**Retained variable candidates (10):**
`adult_mortality, bmi, alcohol, health_expenditure, immunization, schooling,
income_composition, gdp, population, infant_mortality`
- Note: `life_expectancy` is excluded — it's the complementary outcome, not a burden indicator
- Variables with excessive missingness (>50%) should be excluded from PCA
- Report `missing_rate_by_variable` for each candidate
- Center and scale variables before PCA
- Report `pc1_variance_share` (fraction of total variance explained by PC1)
- Report `top_absolute_loadings`: top 3 variable ids by absolute loading value descending
- Report `top_positive_loadings`: top 3 variable ids by positive loading value descending
- Cluster on PC1 scores into 3 equal-count (tercile) groups: low_burden, middle_burden, high_burden

### Model Specification for Grouped/Hierarchical Models

**Country model:**
- Fit a random-intercept model with `income_group` as the grouping variable
- Compare to pooled OLS
- Decision:
  - `mixed_model_supported` — random intercept variance ratio ≥ ~0.05 and model fit improved
  - `pooled_ols_sufficient` — negligible group-level variance

**County static vs dynamic specification:**
- **Static model:** contemporaneous SES variables (MEDHHINC_2023, Unemployment_rate_2023,
  Percent_bachelors_or_higher_2019_23, PCTPOVALL_2023)
- **Dynamic model:** replace static unemployment with unemployment_change, add income_change
- Compare AIC between static and dynamic specifications per outcome measure
- `static_wins` — static model has lower AIC
- `dynamic_wins` — dynamic model has lower AIC
- RUCC dummies included in both specifications

---

## Ordering and Identifier Conventions

### State Abbreviations
- **Included states:** sorted ascending alphabetically by 2-letter abbreviation:
  AK, AL, AR, AZ, CA, CO, CT, DC, DE, FL, GA, HI, IA, ID, IL, IN, KS, KY, LA, MA,
  MD, ME, MI, MN, MO, MS, MT, NC, ND, NE, NH, NJ, NM, NV, NY, OH, OK, OR, PA, RI,
  SC, SD, TN, TX, UT, VA, VT, WA, WI, WV, WY
- **Excluded states / territories:** sorted ascending alphabetically
- **Requested states:** preserved in prompt order (do not sort)

### FIPS Codes
- Always 5-digit zero-padded strings (e.g. `"01001"`, not `1001`)
- **Top residual outliers:** ordered by residual value descending (most positive first)
- **Shared residual outliers:** list the 5 FIPS codes (as strings) that appear across
  outcomes, ordered by their average residual

### Measure IDs
- Always use the exact measure_id from the portal (e.g. `"CASTHMA"`, `"OBESITY"`)
- Measure IDs are uppercase alphanumeric
- When listing requested measure IDs in output, use prompt order

### ISO3 Codes
- Always sorted ascending alphabetically (e.g. for GDP-gap countries)

### Predictor IDs (for culprit pair)
- Array of two predictor IDs sorted ascending (alphabetically)

### Priority Review States (rank shift)
- Array of state abbreviations in **adjusted priority order** (best rank first for
  `higher_value_worse` measures, worst rank first for `lower_value_worse`)

### Top Shift States
- `top_upward_shift_states`: 5 states where adjusted rank improved most vs crude,
  ordered by rank_shift descending (largest improvement first)
- `top_downward_shift_states`: 5 states where adjusted rank worsened most vs crude,
  ordered by rank_shift ascending (most negative shift first)

---

## Filtering and Exclusion Checklist

### State-Level Analysis
- [ ] Exclude territories: `territory_flag != "Y"` (remove PR, GU, VI)
- [ ] Restrict to Total stratum: `stratum_type == "Total"` AND `stratum == "Total"`
- [ ] Filter to requested year (e.g. 2024)
- [ ] Check `source_note` for stale rows — CA 2024 OBESITY, TX 2024 LIFE_EXP
- [ ] For SES join: `geo_level == "state"` AND `geo_fips` ends in `"000"`
- [ ] For region join: `state_level_analysis_flag == "Y"`
- [ ] Deduplicate: check for OH 2021 INACTIVE duplicate pattern
- [ ] Exclude blank demographic strata — they are NOT valid for direct standardization

### County-Level Analysis
- [ ] Remove invalid FIPS: `fips != "00000"` (state ZZ)
- [ ] Filter to requested states only
- [ ] Remove old-name county records (county name matches `\d+ County` pattern)
- [ ] Remove Shannon County (46113, SD) — old name for Oglala Lakota County
- [ ] Handle missing population: some county-year rows have blank population
- [ ] Join on FIPS (not county name) — county names repeat across states
- [ ] Account for counties that lack specific health measures
- [ ] Handle log-transformation carefully: zero or negative values cannot be log-transformed

### Country-Level Analysis
- [ ] Join health panel to metadata on `iso3` (not country name)
- [ ] Use `income_group`, not `lending_category`
- [ ] Flag known anomalies: Namibia BMI (2018–2021), Eswatini adult_mortality, Japan GDP
- [ ] Handle sparse variables: `schooling`, `income_composition` have high missingness
- [ ] Use `country_name_variants.csv` for external name resolution

---

## Common Pitfalls

1. **County-like distractors in state_ses_long.csv:** Rows where geo_fips doesn't end in
   000 look like states but are distractors. Always check geo_level AND geo_fips suffix.

2. **Territories in state counts:** The portal includes PR, GU, VI. If you count rows
   without filtering territory_flag, you get 54, not 51.

3. **Stale rows ≠ valid data:** CA 2024 OBESITY Total and TX 2024 LIFE_EXP Total have
   stale 2023 rows with a `source_note`. These are NOT valid 2024 data — they inflate
   the row count while providing incorrect values for 2024.

4. **Duplicate rows:** OH 2021 INACTIVE Black stratum has two rows. Deduplicate before
   any counting or regression.

5. **FIPS as integer:** FIPS 01001 becomes 1001 if parsed as integer — loses the
   leading zero. Always treat FIPS as string.

6. **Old-name county joins:** County names with number suffixes ("Adams 27 County")
   won't join to health data (where it's "Adams County"). These are intentional
   join-breakers in the SES table.

7. **Lending category ≠ income group:** `country_metadata.csv` has both `income_group`
   and `lending_category`. Only `income_group` is used for hierarchical modeling.

8. **Name variants:** Country names differ between sources. Always reconcile via ISO3.

9. **Scale anomalies:** Namibia BMI and Eswatini adult_mortality have scaling issues
   that distort PCA if not flagged. Always check for out-of-range values.

10. **Blank demographic strata:** Blank `stratum_type` fields are not valid
    demographic strata for direct standardization. `direct_strata_available` only
    when all required age/sex strata are non-blank.

11. **Isolate states in spatial analysis:** Many states have no contiguous neighbors
    per `state_neighbors.csv`. Moran's I should handle isolates appropriately
    (they don't contribute to the spatial weight matrix).

12. **Population blanks in county health:** Some county-year rows have blank
    `population` — these cannot be used for population-weighted analyses.

13. **Exclusion reason counts must sum correctly:** `invalid_fips + outside_requested_states
    + missing_ses + missing_health_data + complete_case_count` should reconcile with
    the total county count in the raw data.

14. **Income quartile strata are state-level, not individual:** The `Income quartile`
    stratum in state_health groups states into Q1–Q4 based on state-level income,
    not individual-level income.

15. **SES attributes for static vs dynamic models:** The static model uses
    Unemployment_rate_2023 directly. The dynamic model uses the difference
    (Unemployment_rate_2023 - Unemployment_rate_2010). Both use MEDHHINC_2023
    directly, and the dynamic model also includes (MEDHHINC_2023 - Median_Household_Income_2022).

---

## Typical Audit Pattern

### State Confounding Audit
```
1. Load state_health_long.csv → filter territory_flag=N, stratum=Total, year=2024
2. Extract exposure (e.g. OBESITY) and outcome (e.g. DIAB_MORT) Total values
3. Load state_ses_long.csv → filter geo_level=state, geo_fips ending in 000
4. Pivot SES to wide format
5. Load state_regions.csv → filter state_level_analysis_flag=Y → join region/division
6. Merge health + SES + regions on state abbreviation
7. Identify excluded states (those missing from the merge after filtering)
8. Fit bivariate model: outcome ~ exposure
9. Fit adjusted model: outcome ~ exposure + SES covariates
10. Compute attenuation_pct = (bivariate_beta - adjusted_beta) / bivariate_beta * 100
11. Fit mixed model with region random intercept → extract ICC
12. Check collinearity → report max VIF and its predictor
13. Identify high-leverage/influential states
14. Sensitivity check: remove top influential states, re-fit
```

### County Mediation Audit
```
1. Load county_health_long.csv → filter to requested states, target year
2. Filter to outcome measure (e.g. OBESITY) and mediator measure (e.g. LPA)
3. Load county_ses_long.csv → filter out FIPS 00000, filter to requested states
4. Pivot SES to wide; remove old-name counties (name matches \d+ County)
5. Compute derived variables: income_change, unemployment_change
6. Join health + SES on FIPS → track exclusions by reason
7. Mediation: poverty → mediator → outcome
   - Path a: poverty → mediator (poverty_to_mediator_beta)
   - Path b: mediator → outcome (mediator_to_outcome_beta)
   - Indirect effect = a × b
8. Bootstrap indirect effect → report CI and enumeration
9. Compute residuals; fit spatial model (Moran's I) on residuals
10. Report top positive residual counties and hotspot division
```

### Country PCA Audit
```
1. Load country_health_panel.csv → aggregate to country means (2015–2024)
2. Load country_metadata.csv → join on iso3
3. Load country_name_variants.csv → note reconciliation coverage
4. Check each candidate variable for missing rate
5. Retain variables with acceptable missingness
6. Impute remaining missing values (mean/mode per income group)
7. Center and scale → run PCA
8. Report PC1 variance share, top loadings
9. Cluster on PC1 scores (terciles) → report cluster counts
10. Compare mixed model (income_group) vs pooled OLS for burden score
11. Log all anomalies found
```
