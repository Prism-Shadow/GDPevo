# Public Health Evidence Portal — Statistical Audit Skill

## Portal Overview

The Public Health Evidence Portal is a browser-accessible web application serving
state, county, and country health/statistical CSV downloads. All data are synthetic
(seed `20260707`) but shaped like real public-health evidence sources. The portal
is the **only source of record** for every audit — stale memos, older spreadsheets,
and external assumptions must be discarded in favor of live portal data.

**Base URL pattern:** `{BASE_URL}` — substituted from the task environment.
All page and data paths below are relative to this base.

---

## Data Download Workflow

### 1. Always fetch these key pages before analysis
Each page documents known cautions, column meanings, and intentional anomalies:

| Page | Path |
|---|---|
| Home / download index | `/` or `/index.html` |
| State Health Indicators | `/pages/state-health.html` |
| State SES Indicators | `/pages/state-ses.html` |
| State Region/Division Lookup | `/pages/state-regions.html` |
| County Health Measure Catalog | `/pages/county-health.html` |
| County SES Attribute-Value Tables | `/pages/county-ses.html` |
| State Neighbor/Isolate Reference | `/pages/county-neighbors.html` |
| Country Health Indicator Panel | `/pages/country-indicators.html` |
| Country Metadata & Income Groups | `/pages/country-metadata.html` |
| Country Name Reconciliation | `/pages/name-reconciliation.html` |
| Methodology | `/pages/methodology.html` |

Read the **hero/lede** text and **`.note`** paragraphs on each page; they flag
missing data, duplicates, distractor rows, and known anomalies that affect every
downstream computation.

### 2. Download all relevant CSVs

| CSV | Rows (approx.) | Used for |
|---|---|---|
| `/data/state_health_long.csv` | 29,161 | State health measures (all tasks) |
| `/data/state_ses_long.csv` | 972 | State SES attributes |
| `/data/state_regions.csv` | 54 | Region/division lookup, territory flags |
| `/data/state_life_expectancy.csv` | 4,859 | Life expectancy by stratum |
| `/data/state_neighbors.csv` | 51 | Spatial neighbor/isolate reference |
| `/data/county_health_long.csv` | 40,108 | County health measures |
| `/data/county_ses_long.csv` | 7,536 | County SES attribute-value table |
| `/data/county_metadata.csv` | 631 | County RUCC, typology, division, flags |
| `/data/country_health_panel.csv` | 1,090 | Country-year indicators (2015–2024) |
| `/data/country_metadata.csv` | 109 | Country income groups, regions |
| `/data/country_name_variants.csv` | 14 | Crosswalk of systematic name variants |

### 3. CSV Parsing Warnings

- **Use a proper CSV parser** (e.g., Python `csv.DictReader`). Do NOT split on
  commas with awk/cut — the column `data_value_type` contains the value
  `"Deaths per 100,000"` (with an embedded comma inside quotes) for measure
  `DIAB_MORT`. Simple comma-splitting will misalign all columns to the right.

- Columns vary across datasets. Always read `fieldnames` from the header before
  assuming column positions.

---

## State-Level Conventions

### Measure IDs (state_health_long.csv)

| measure_id | measure | category | data_value_type |
|---|---|---|---|
| `DIAB_MORT` | Diabetes mortality rate | Mortality | Deaths per 100,000 |
| `INACTIVE` | Physical inactivity prevalence | Risk factor | Percent |
| `LIFE_EXP` | Life expectancy | Outcome | Years |
| `OBESITY` | Adult obesity prevalence | Risk factor | Percent |
| `SCREEN` | Preventive screening prevalence | Prevention | Percent |
| `VACC_COMP` | Vaccination completion | Prevention | Percent |

### Stratum Types and Values

Every measure has rows for these `stratum_type` values:

| stratum_type | stratum values |
|---|---|
| `Total` | `Total` |
| `Age` | `18-44`, `45-64`, `65+` |
| `Sex` | `Female`, `Male` |
| `Income quartile` | `Q1 lowest`, `Q2`, `Q3`, `Q4 highest` |
| `Race/ethnicity` | `American Indian or Alaska Native`, `Asian`, `Black`, `Hispanic`, `White` |

`SCREEN` also has rows with **empty** `stratum_type` and `stratum` (both `""`).
For SCREEN 2022, these 270 empty-label rows (54 states × 5 per state) correspond
to the Age (3 strata) and Sex (2 strata) demographic breakdowns — an older
spreadsheet treated blank demographic labels as valid strata. Check other SCREEN
years as well. **Always exclude these rows** from demographic-adjustment checks
and from any analysis requiring identifiable strata.

### State SES Attributes (state_ses_long.csv)

| attribute | attribute_label | unit |
|---|---|---|
| `PCTPOVALL_2023` | Percent in poverty, all ages | percent |
| `MEDHHINC_2023` | Median household income, 2023 | dollars |
| `Unemployment_rate_2023` | Unemployment rate, 2023 | percent |
| `Percent_bachelors_or_higher_2019_23` | Bachelor degree or higher, 2019-23 | percent |
| `POP_ESTIMATE_2023` | Population estimate, 2023 | persons |
| `R_NET_MIG_2023` | Net migration rate, 2023 | per 1,000 |

### Extracting True State Rows from SES

The `state_ses_long.csv` has three `geo_level` values:
- `state` — 306 rows (51 states/DC × 6 attributes)
- `territory` — 18 rows (GU, PR, VI × 6 attributes)
- `county-like distractor` — 648 rows (synthetic county records injected as distractors)

**Rule:** Filter `geo_level == "state"` to get true state rows. These have
`geo_fips` ending in `000` (e.g., `01000` for Alabama). Rows with non-zero
suffixes (e.g., `01001`) are county-like distractors regardless of `geo_level`.
The extraction_note column identifies them.

### Territories

Three territories appear across state datasets: **GU** (Guam), **PR** (Puerto
Rico), **VI** (U.S. Virgin Islands). They are flagged:
- `territory_flag = "Y"` in state health and life expectancy CSVs
- `state_level_analysis_flag = "N"` in `state_regions.csv`
- `geo_level = "territory"` in `state_ses_long.csv`

**Always exclude territories from state-level analysis.** They have their own
rows in every measure and year; they will inflate N and distort regression
results if not removed.

### Known Missing Data (State)

| Gap | Detail |
|---|---|
| CA 2024 OBESITY Total | Intentionally missing (documented on state-health page) |
| TX 2024 LIFE_EXP Total | Intentionally missing |
| CA 2023 OBESITY Total | **Duplicated row** (source_note: "Stale 2023 Total retained beside missing 2024 Total") — deduplicate |
| TX 2023 LIFE_EXP Total | **Duplicated row** (same stale-retained pattern) — deduplicate |
| OH 2021 INACTIVE Black | **Duplicated stratum row** (source_note: "Intentional duplicate stratified row from overlapping extract") — deduplicate |

### SCREEN Empty-Strata Contamination (Critical)

For **SCREEN 2022** (and possibly other SCREEN years), the 5 rows per state
corresponding to **Age strata** (18-44, 45-64, 65+) and **Sex strata** (Female,
Male) have **blank `stratum_type` and `stratum` fields**. The data values are
present but the demographic labels are missing. This affects 270 rows (54 states
× 5 strata). These rows are contaminated — an older spreadsheet treated blank
demographic labels as valid.

When checking **demographic adjustment feasibility**, this means Age and Sex
strata cannot be reliably identified for SCREEN → report
`not_feasible_blank_demographic_strata`. When computing income-bracket counts,
exclude these empty-label rows (they do NOT represent income strata).

### State Regions and Divisions

`state_regions.csv` provides census-like region/division for all 50 states + DC:
- Regions: Midwest, Northeast, South, West
- Divisions: East North Central, East South Central, Middle Atlantic, Mountain,
  New England, Pacific, South Atlantic, West North Central, West South Central

Territories have region=`Territory`, division=`Caribbean` or `Pacific Island Areas`,
and `state_level_analysis_flag = "N"`.

### State Neighbors and Isolates

`state_neighbors.csv` defines neighbor relationships for spatial analysis.
- **Non-isolate states** (21): neighbors in pipe-delimited format (`FL|GA|MS|TN`)
- **Isolate states** (30): `isolate_flag = "Y"`, empty `neighbors` column,
  `neighbor_count = 0`. These states have no contiguous neighbors in the
  reference — used for spatial residual summaries.

The 21 non-isolate states are: AL, AZ, AR, CA, CO, CT, DE, DC, FL, GA, IL,
KY, MA, NY, NC, OH, OR, PA, TX, WA, WV. The remaining 30 states are isolates.
Note: although the portal page mentions only Alaska and Hawaii as true geographic
isolates, the **CSV (source of record)** marks 30 states as isolates for spatial
analysis purposes. Always use the CSV, not the page summary.

When computing Moran's I or spatial clustering, only non-isolate states
contribute to the spatial weight matrix. Isolates are excluded from
spatial-lag computation but included in residual analysis.

### State Health Data Subsetting Rules

1. Filter `territory_flag == "N"` (exclude GU, PR, VI)
2. Filter `stratum_type == "Total"` and `stratum == "Total"` for bivariate/adjusted models
3. For income-adjusted rankings: use Total/Total for crude ranking, Income quartile
   strata for income-proxy adjustment
4. Deduplicate: check for duplicate (year, state, measure_id, stratum_type, stratum)
   rows — CA 2023 OBESITY and TX 2023 LIFE_EXP are known duplicates
5. Handle missing: exclude state-years with missing outcome or exposure

### Sample Size and Weighting

- `DIAB_MORT` and `LIFE_EXP`: `sample_size` column is **empty/NULL for all rows**
  (mortality/vital statistics, not survey data). These two measures have NO
  survey sample size — use unweighted regression for these measures. The
  total affected rows: DIAB_MORT (4,860 rows), LIFE_EXP (4,859 rows; one
  stale duplicate row may have a sample_size value — ignore it).
- All other measures (`OBESITY`, `INACTIVE`, `SCREEN`, `VACC_COMP`): `sample_size`
  is populated for all rows. Use sample-size-weighted regression when comparing
  estimates across states with varying sample sizes.

---

## County-Level Conventions

### County Measure IDs (county_health_long.csv)

16 measures modeled after CDC PLACES:

| measure_id | measure | category |
|---|---|---|
| `CASTHMA` | Current asthma among adults | Health outcomes |
| `OBESITY` | Obesity among adults | Health risk behaviors |
| `DIABETES` | Diagnosed diabetes among adults | Health outcomes |
| `DEPRESSION` | Depression among adults | Health outcomes |
| `CHD` | Coronary heart disease among adults | Health outcomes |
| `GHLTH` | Fair or poor self-rated health | Health status |
| `LPA` | No leisure-time physical activity | Health risk behaviors |
| `CSMOKING` | Current smoking among adults | Health risk behaviors |
| `BINGE` | Binge drinking among adults | Health risk behaviors |
| `SLEEP` | Short sleep duration among adults | Health risk behaviors |
| `MAMMOUSE` | Mammography use among eligible women | Prevention |
| `BPMED` | Taking blood pressure medication | Prevention |
| `CHECKUP` | Annual checkup among adults | Prevention |
| `COREM` | Core preventive services for older men | Prevention |
| `COREW` | Core preventive services for older women | Prevention |
| `DENTAL` | Dental visit among adults | Prevention |

Years: 2021, 2022, 2023, 2024. Data are at county level (5-digit FIPS).

### County SES Attributes (county_ses_long.csv)

12 attributes, all keyed by 5-digit FIPS:

| attribute | Description |
|---|---|
| `PCTPOVALL_2023` | Percent poverty, all ages |
| `MEDHHINC_2023` | Median household income, 2023 |
| `Unemployment_rate_2010` | Unemployment rate, 2010 |
| `Unemployment_rate_2023` | Unemployment rate, 2023 |
| `Median_Household_Income_2022` | Median household income, 2022 |
| `Percent_bachelors_or_higher_2019_23` | Bachelor degree or higher, 2019-23 |
| `POP_ESTIMATE_2023` | Population estimate, 2023 |
| `CENSUS_2020_POP` | Census population, 2020 |
| `R_NET_MIG_2023` | Net migration rate, 2023 |
| `R_NATURAL_CHG_2023` | Natural change rate, 2023 |
| `RUCC_2023` | Rural-urban continuum code, 2023 |
| `Economic_typology_2015` | Economic typology, 2015 |

### County Metadata (county_metadata.csv)

631 rows: 630 real counties + 1 invalid FIPS distractor (00000/ZZ).
Additional columns per county:
- `rucc_code`: 1–9 (RUCC classification; 9 distinct codes)
- `economic_typology`: 7 real categories (Farming, Federal/State government,
  Manufacturing, Mining, Nonspecialized, Persistent poverty, Recreation) +
  2 distractor values ("Invalid FIPS distractor" for 00000, "Old name" for 46113)
- `census_division`: 9 Census division names (plus 1 blank for the ZZ invalid row)
- `metadata_note`: Flags invalid FIPS and old county names

**County health CSV** has 630 counties (does NOT include the ZZ/00000 distractor
row). **County SES CSV** has 631 rows (includes ZZ/00000). Always left-join
county health → county SES → county metadata by FIPS, and exclude the ZZ row.

### Invalid and Problematic FIPS Rows

| FIPS | Issue | Action |
|---|---|---|
| `00000` | State `ZZ`, county `Unknown County` — invalid FIPS distractor | **Exclude** from all merges |
| `46113` | Shannon County, SD — old county name; modern name is Oglala Lakota County | **Exclude** or map to modern name; metadata_note flags it |

The invalid FIPS row `00000` has missing `CENSUS_2020_POP`, blank `RUCC_2023`,
and blank `Economic_typology_2015`.

### Partial Missing SES Attributes

18 counties (all named "Pine County" with FIPS ending in `*019` across 18
different states: CA, CO, FL, GA, IL, KY, LA, MI, MN, MS, NC, NY, OH, PA, TN,
TX, VA, WI) are missing `POP_ESTIMATE_2023` and `Percent_bachelors_or_higher_2019_23`.
These counties should be excluded from complete-case analysis when those
attributes are needed (count them under `missing_ses` exclusions).

### Missing County Health Measures (Systematic)

Two measures are **systematically absent** for specific counties:

| Pattern | Detail |
|---|---|
| Franklin County (*007) — DENTAL + COREM | All 25 "Franklin County" rows (FIPS `*007` across 25 states) lack DENTAL and COREM for all 4 years. 200 missing rows (25 counties × 2 measures × 4 years). |
| Alaska — MAMMOUSE 2024 | All 12 Alaska counties (FIPS `02001`–`02012`) lack MAMMOUSE for 2024. 12 missing rows. |

County `02007` (AK Franklin County) is affected by both patterns and has only
55 health rows instead of the standard 64.

All 14 other measures are fully complete (2,520 rows each) across all 630 counties
and all 4 years.

### Blank Population in County Health

23 rows have blank `population`: all are "Madison County" (FIPS `*013`),
measure `SLEEP`, year 2023, across 23 states. These counties have valid
health data but missing population weights — exclude from population-weighted
analyses of SLEEP in 2023.

### Static vs. Dynamic SES Specifications

**Static specification:** Use only current-value SES attributes:
- `PCTPOVALL_2023`, `MEDHHINC_2023`, `Unemployment_rate_2023`,
  `Percent_bachelors_or_higher_2019_23`

**Dynamic specification:** Add change variables:
- **Unemployment change:** `Unemployment_rate_2023` − `Unemployment_rate_2010`
- **Income change:** `MEDHHINC_2023` − `Median_Household_Income_2022`

When computing the income change, the exact rule is `MEDHHINC_2023` **minus**
`Median_Household_Income_2022`.

Compare static vs. dynamic models using AIC (lower is better). The winner is
the specification with lower AIC.

### RUCC Handling

RUCC codes (1–9) are categorical. **Always model RUCC as categorical dummies**
(not continuous). Omit one category as reference.

### County Data Subsetting Rules

1. Filter to requested states (from task prompt — maintain prompt order for
   `requested_states` arrays)
2. Remove FIPS `00000` (invalid FIPS distractor) — count under `invalid_fips`
3. Remove `46113` (old county name) — count under `invalid_fips`
4. Remove counties outside requested states — count under `outside_requested_states`
5. Remove counties missing SES attributes needed for the model — count under `missing_ses`
6. Remove counties missing health data for the outcome measure — count under
   `missing_health_data`
7. Report remaining count as `complete_case_count`

---

## Country-Level Conventions

### Country Health Panel (country_health_panel.csv)

109 countries × 10 years (2015–2024) = 1,090 rows (balanced panel).

11 indicators (column names in the CSV):

| Column | Description |
|---|---|
| `life_expectancy` | Life expectancy at birth (years) |
| `adult_mortality` | Adult mortality rate (per 100,000) |
| `bmi` | Average body mass index |
| `alcohol` | Alcohol consumption (liters per capita) |
| `health_expenditure` | Health expenditure (% of GDP) |
| `immunization` | Immunization coverage (%) |
| `schooling` | Years of schooling |
| `income_composition` | Income composition index (0–1) |
| `gdp` | GDP per capita (current USD) |
| `population` | Total population |
| `infant_mortality` | Infant mortality rate (per 1,000 live births) |

All columns except `country`, `iso3`, `year`, and `missingness_note` are numeric.

### Missingness Pattern

| Column | Missing | Pattern |
|---|---|---|
| `health_expenditure` | 13 rows (1.2%) | Scattered across 9 countries, random years |
| `schooling` | 20 rows (1.8%) | Scattered across 17 countries, mostly early years |
| `gdp` | 10 rows (0.9%) | **Japan only** — all 10 years, intentional |
| All others | 0 | Fully populated |

### Known Anomalies (Documented on Country Indicators Page)

| Anomaly | Detail | Detection |
|---|---|---|
| **Namibia BMI scaling** | BMI values ~2,600 for years 2018–2021 (100× scale error). Normal range for Namibia is 25–27. | Values > 1,000 are scale anomalies |
| **Eswatini adult mortality drop** | Drops from ~200 to ~20 for 2021–2024 (factor of 10 shift). Life expectancy remains stable — confirms it's a scaling error. | Check for > 5× year-over-year change |
| **Japan GDP blank** | All 10 years have empty `gdp`. Documented in `missingness_note` column as "Japan GDP blank by design." | `missingness_note` column |

These anomalies should be logged but do not necessarily disqualify rows from all
analyses. For PCA, exclude the anomalous country-years from the affected variable
but consider whether the country can be retained with column-wise imputation.

### Country Name Reconciliation

The `country_name_variants.csv` file lists 14 canonical-to-variant mappings.
**The health panel and metadata exclusively use canonical names.** All 14
canonical names appear directly in the panel; variant names do not.

Variant types include: WHO-style formal names (`Bolivia (Plurinational State of)`),
World Bank variants (`Egypt, Arab Rep.`), former names (`Swaziland` → Eswatini,
`Czech Republic` → Czechia), English exonyms (`Ivory Coast` → Cote d'Ivoire),
and short/press names (`South Korea` → Korea, Rep.).

**Reconciliation workflow:**
1. Count `variant_rows` — total rows in the variants crosswalk (14)
2. Count `resolved_variant_rows` — rows where the canonical name matches a
   country in both the health panel and metadata (all 14 are resolvable)
3. Count `unresolved_variant_rows` — rows where the variant name is in the panel
   but the canonical isn't (should be 0; all panel data uses canonical names)
4. Compute `metadata_join_coverage` — proportion of health-panel ISO3 codes
   with a metadata match (should be 1.0; the datasets are aligned by ISO3)

### Income Groups and Regions (country_metadata.csv)

- **Income groups:** `Low income`, `Lower middle income`, `Upper middle income`, `High income`
- **Regions:** East Asia & Pacific, Europe & Central Asia, Latin America &
  Caribbean, Middle East & North Africa, North America, South Asia,
  Sub-Saharan Africa
- **Lending category:** Present as a distractor — do NOT confuse with income group

### PCA Workflow for Country Burden Score

1. **Year selection:** Choose a single year (or year range). The task will
   specify `year_start` and `year_end`.
2. **Variable retention:** Start with candidate indicators. Exclude variables
   with > threshold missing rate. Document `missing_rate_by_variable` for all
   retained candidates.
3. **Row filtering:** Use only complete cases (rows with no missing values in
   retained variables). Report `rows_used`.
4. **Scale anomaly handling:** Flag Namibia BMI and Eswatini adult_mortality
   in the anomaly log. Decide whether to exclude or winsorize.
5. **PCA:** Run on standardized variables. Report:
   - `pc1_variance_share` — proportion of variance explained by PC1
   - `top_absolute_loadings` — top 3 variables by absolute loading (descending)
   - `top_positive_loadings` — top 3 variables by signed loading (descending)
   - `cluster_counts` — k-means clusters (typically 3: low/middle/high burden)
6. **Mixed model assessment:** Join income group metadata. Check whether
   `income_group` explains significant between-group variance (random intercept
   variance ratio). If the random-intercept variance is substantial
   (`random_intercept_variance_bucket` = `moderate` or `high`), report
   `lr_decision = "mixed_model_supported"`; otherwise `"pooled_ols_sufficient"`.

---

## Statistical Conventions

### Rounding Rules

| Precision | Applied to |
|---|---|
| **1 decimal** | Attenuation percentage |
| **2 decimals** | AIC, unemployment change tercile means, max VIF |
| **3 decimals** | Standardized betas, regional ICC, Spearman's ρ, Moran's I, bootstrap CI bounds, missing rates, variance ratios, indirect effects, mediation path betas, PC1 variance share |

Always round to the specified precision **after** computation, not before.

### Bucket (Categorization) Rules

**p-value buckets** (used for bivariate_p_bucket, adjusted_p_bucket,
sensitivity_p_bucket, income_p_bucket, poverty_p_bucket):
- `lt_0_001`: p < 0.001
- `lt_0_01`: 0.001 ≤ p < 0.01
- `lt_0_05`: 0.01 ≤ p < 0.05
- `ge_0_05`: p ≥ 0.05
- `not_computed`: model could not be fit

**VIF buckets** (max_vif_bucket):
- `lt_5`: VIF < 5
- `5_to_10`: 5 ≤ VIF < 10
- `ge_10`: VIF ≥ 10

**Regional ICC buckets** (regional_icc_bucket):
- `lt_0_05`: ICC < 0.05
- `0_05_to_0_15`: 0.05 ≤ ICC < 0.15
- `ge_0_15`: ICC ≥ 0.15

**Moran's I buckets** (moran_i_bucket):
- `lt_0_05`: I < 0.05
- `0_05_to_0_20`: 0.05 ≤ I < 0.20
- `ge_0_20`: I ≥ 0.20

**Random intercept variance buckets** (random_intercept_variance_bucket):
- `low`: variance ratio < 0.10
- `moderate`: 0.10 ≤ variance ratio < 0.30
- `high`: variance ratio ≥ 0.30

### Priority Direction

For ranking tasks: determine whether `higher_value_worse` or `lower_value_worse`
based on the measure. Higher screening rates are better (`lower_value_worse` —
lower rank means worse/needs more attention). Higher mortality rates are worse
(`higher_value_worse`).

### Income-Bracket Coverage

Count states with valid (non-missing) data in each income quartile stratum:
`Q1 lowest`, `Q2`, `Q3`, `Q4 highest`. Report counts as an object with integer
keys `{"Q1": N1, "Q2": N2, "Q3": N3, "Q4": N4}`.

### Ranking Conventions

- **Crude ranking:** Rank states by Total/Total data_value for the analysis year
- **Adjusted ranking:** Rank by income-proxy-adjusted values
- **Rank shift:** `rank_shift = crude_rank − adjusted_rank` (positive = upward
  shift in priority, negative = downward shift)
- **Top upward shift:** States where adjusted rank is worse (higher priority)
  than crude — ordered by `rank_shift` **descending**
- **Top downward shift:** States where adjusted rank is better (lower priority)
  than crude — ordered by `rank_shift` **ascending**
- **Spearman:** `spearman_crude_vs_adjusted` — rank correlation between crude
  and adjusted rankings

### Demographic Adjustment Feasibility

Check whether the state health data contains **non-empty, non-blank** Age and
Sex strata for the analysis measure and year. If demographic strata are fully
populated (no blank labels treated as valid), report `direct_strata_available`.
If blank/empty demographic labels exist (as with SCREEN's empty-strata rows),
report `not_feasible_blank_demographic_strata`.

### Bootstrap CI Convention

For mediation: bootstrap the indirect effect (e.g., 1,000 resamples).
Report `bootstrap_ci_low` and `bootstrap_ci_high`. The `bootstrap_ci_enum`:
- `positive_excludes_zero`: CI entirely above 0
- `negative_excludes_zero`: CI entirely below 0
- `includes_zero`: CI straddles 0

---

## Filtering and Exclusion Rules Summary

### State-Level Exclusions
1. **Territories:** Always exclude GU, PR, VI (`territory_flag == "Y"` or
   `state_level_analysis_flag == "N"`)
2. **Non-Total strata:** For bivariate/adjusted models, keep only
   `stratum_type == "Total"` and `stratum == "Total"`
3. **Empty-strata SCREEN rows:** Exclude rows where `stratum_type == ""` and
   `stratum == ""` (contaminated duplicates from older spreadsheet)
4. **Missing outcome:** Exclude state-years where the outcome measure is missing
5. **Missing exposure:** Exclude state-years where the exposure measure is missing
6. **California 2024 OBESITY Total** and **Texas 2024 LIFE_EXP Total** are
   intentionally absent — exclude from models using those measures in 2024

### County-Level Exclusions
1. **Invalid FIPS:** Exclude `00000` (ZZ, Unknown County)
2. **Old county names:** Exclude `46113` (Shannon County, SD) or resolve to
   Oglala Lakota County
3. **Outside requested states:** Count counties whose state abbreviation is not
   in the task's requested_states list
4. **Missing SES:** Exclude counties lacking any attribute needed for the model.
   Known patterns: 18 "Pine County" (*019) rows missing POP_ESTIMATE_2023 and
   Percent_bachelors_or_higher_2019_23
5. **Missing health data:** Exclude counties with missing data_value for the
   outcome measure_id. Known patterns: Franklin County (*007) missing DENTAL
   and COREM; Alaska counties missing MAMMOUSE 2024
6. **Blank population:** Exclude Madison County (*013) SLEEP 2023 rows from
   population-weighted analyses

### Country-Level Exclusions
1. **Missing indicators for PCA:** Exclude rows with any missing value in
   retained variables (complete-case PCA)
2. **Scale anomalies:** Log Namibia BMI 2018–2021 and Eswatini adult_mortality
   2021–2024; decide per analysis whether to winsorize or exclude
3. **Japan GDP:** Japan's rows are excluded from any analysis requiring GDP

---

## Identifier and List Ordering Rules

### State Abbreviations
- Use **uppercase 2-letter postal abbreviations** (AL, AK, AZ, ..., WY)
- DC is included as a state-level unit
- For `excluded_states` and `included_states`: sort alphabetically **ascending**
- For `territories_excluded`: sort alphabetically ascending (GU, PR, VI)
- For `requested_states`: preserve the **exact order from the task prompt**

### FIPS Codes
- State FIPS: 2-digit string with leading zero (e.g., `"01"` for AL)
- County FIPS: 5-digit string with leading zeros (e.g., `"01001"`)
- State SES geo_fips: 5-digit with `000` suffix (e.g., `"01000"`)

### ISO3 Codes
- Uppercase 3-letter codes (e.g., `"USA"`, `"AFG"`, `"JPN"`)
- Sort alphabetically ascending when listing

### Predictor Pairs
- When returning `culprit_pair`: two predictor IDs sorted **ascending**
  (alphabetically)

### Residual Ordering
- `top_residual_outlier_fips`: counties ordered by residual magnitude
  **descending** (largest |residual| first)
- `top_positive_residual_fips`: counties with largest positive residuals
  (observed > predicted), ordered **descending**

### Top-N Arrays
- Unless specified otherwise, top-N lists are ordered by the ranking criterion
  (not alphabetically)
- For `priority_review_states`: ordered by adjusted priority (worst first)
- For `high_leverage_states`: ordered by leverage descending (most influential first)

---

## Common Pitfalls

1. **Not reading portal page notes.** The `.note` paragraphs on each page
   flag critical issues (duplicates, missing data, anomalies). Skipping them
   causes downstream errors that are hard to diagnose.

2. **Including territories in state models.** GU, PR, VI have flag columns in
   every dataset. Forgetting to filter them inflates N by 3 and biases
   regression estimates.

3. **Not deduplicating.** CA 2023 OBESITY Total and TX 2023 LIFE_EXP Total
   are exact duplicates. Including both rows doubles the weight of those
   observations.

4. **Including SCREEN empty-strata rows.** These 270 rows with blank
   `stratum_type` are from an older spreadsheet that treated blank labels as
   valid demographic strata. They contaminate income-bracket counts and
   demographic adjustment feasibility checks.

5. **Using simple comma splitting on CSVs.** The `data_value_type` column
   contains `"Deaths per 100,000"` — an embedded comma inside quotes. Use
   a proper CSV parser.

6. **Treating RUCC as continuous.** RUCC codes are ordinal categories, not
   a continuous scale. Model them as categorical dummies.

7. **Assuming all states have neighbors.** 30 of 51 states are marked as
   isolates (`isolate_flag = "Y"`). Computing Moran's I requires building
   a spatial weight matrix from non-isolate states only.

8. **Confusing lending_category with income_group.** The country metadata
   includes `lending_category` (IDA, IBRD, Blend, Not classified) as a
   distractor. Mixed-model grouping should use `income_group`, not
   `lending_category`.

9. **Ignoring scale anomalies in country data.** Namibia BMI values of
   ~2,600 and Eswatini adult mortality of ~20 will dominate PCA loadings
   if not addressed. Check variable distributions before running PCA.

10. **Not handling the Japan GDP gap.** Japan is the only country with all 10
    years of GDP missing. Any analysis using GDP must exclude Japan or handle
    the missingness explicitly.

11. **Wrong ordering of change variables.** The income change rule is
    `MEDHHINC_2023` **minus** `Median_Household_Income_2022`, not the reverse.
    The unemployment change is `Unemployment_rate_2023` **minus**
    `Unemployment_rate_2010`.

12. **Counting county-level distractors in state SES.** The state SES CSV
    contains 648 county-like distractor rows. Always filter
    `geo_level == "state"` before extracting state SES values.

---

## Task-Type Quick Reference

### State Confounding Audit (train_001 pattern)
```
1. Identify exposure (predictor) and outcome measure_ids from task text
2. Extract Total/Total rows for analysis year, exclude territories
3. Compute bivariate model: outcome ~ exposure
4. Merge state SES (state rows only: geo_level="state"), add socioeconomic covariates
5. Compute adjusted model: outcome ~ exposure + SES covariates
6. Report attenuation: 100*(bivariate_beta - adjusted_beta)/bivariate_beta
7. Merge region/division, compute regional ICC (random intercept by division)
8. Check collinearity: VIF for all predictors, identify max VIF and culprit pair
9. Identify high-leverage states (top 3 by Cook's D or leverage)
10. Sensitivity check: re-estimate excluding top-leverage states, compare
```

### Income-Adjusted Ranking Audit (train_002 pattern)
```
1. Extract Total/Total SCREEN rows for analysis year, exclude territories
2. Generate crude ranking (higher screening rate = better = lower priority)
3. Extract Income quartile rows, count non-empty brackets per state
4. Check demographic adjustment feasibility (blank strata check)
5. Build sample-size-weighted model: SCREEN ~ income_proxy + poverty_proxy
6. Generate adjusted predictions, rank by adjusted values
7. Compute rank shifts and Spearman correlation
8. Identify top upward/downward shift states
```

### County Reconciliation Audit (train_003 pattern)
```
1. Filter county health to requested states and outcome measure
2. Merge county SES (static spec) by FIPS
3. Compute static model AIC
4. Add dynamic change variables, compute dynamic model AIC
5. Compare AIC: determine static_wins or dynamic_wins per outcome
6. For the winning model, compute residuals, identify top outliers
7. For dynamic model, compute unemployment change tercile means
```

### Country Burden PCA Audit (train_004 pattern)
```
1. Verify name reconciliation coverage
2. Identify anomalies (Namibia BMI, Eswatini mortality, Japan GDP)
3. Select analysis year(s), retain variables with acceptable missing rate
4. Run PCA on complete cases, extract PC1 loadings and variance
5. k-means cluster on PC scores, count per burden cluster
6. Join income group metadata, fit mixed model with random intercept
7. Report variance ratio and LR test decision
```

### County Mediation Audit (train_005 pattern)
```
1. Filter county health to requested states, extract outcome (OBESITY) and mediator (LPA)
2. Merge county SES (static + RUCC dummies)
3. Run mediation: poverty → mediator → outcome
4. Compute indirect effect (poverty→mediator × mediator→outcome)
5. Bootstrap indirect effect CI (≥1000 resamples)
6. Compute residuals, build spatial weight matrix from neighbors
7. Compute Moran's I on residuals, identify hotspot division
8. Flag top positive residual counties
```
