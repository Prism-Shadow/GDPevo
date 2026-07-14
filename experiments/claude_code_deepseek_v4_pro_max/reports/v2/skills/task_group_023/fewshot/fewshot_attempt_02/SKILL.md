# Public Health Evidence Portal — Statistical Audit Skill

## Environment

All tasks use the shared Public Health Evidence Portal at:

```
http://34.46.77.124:9023
```

The portal is a static web application with linked CSV downloads served from `/data/`.
Do **not** use localhost, 127.0.0.1, API_BASE_URL, BASE_URL, `<TASK_ENV_BASE_URL>`, or
any `env/setup.sh` references. Use the remote URL above as the only entrypoint.

## Portal Pages and Corresponding CSV Downloads

| Portal Page                          | CSV Endpoint                          |
|--------------------------------------|---------------------------------------|
| `/pages/state-health.html`           | `/data/state_health_long.csv`         |
| `/pages/state-health.html`           | `/data/state_life_expectancy.csv`     |
| `/pages/state-ses.html`              | `/data/state_ses_long.csv`            |
| `/pages/state-regions.html`          | `/data/state_regions.csv`             |
| `/pages/county-health.html`          | `/data/county_health_long.csv`        |
| `/pages/county-ses.html`             | `/data/county_ses_long.csv`           |
| `/pages/county-ses.html`             | `/data/county_metadata.csv`           |
| `/pages/county-neighbors.html`       | `/data/state_neighbors.csv`           |
| `/pages/country-indicators.html`     | `/data/country_health_panel.csv`      |
| `/pages/country-metadata.html`       | `/data/country_metadata.csv`          |
| `/pages/name-reconciliation.html`    | `/data/country_name_variants.csv`     |
| `/` (home)                           | —                                     |
| `/pages/methodology.html`            | —                                     |

Also fetch the HTML pages themselves — they sometimes contain table-level metadata,
descriptions, and filter hints not present in the CSVs.

---

## Part 1 — Data Download and Ingestion Workflow

### 1.1 Fetching Data

All portal data is publicly accessible. Download CSVs via HTTP GET to the base URL:

```bash
curl -s "http://34.46.77.124:9023/data/state_health_long.csv"
```

Important column notes:
- **Quoted fields**: Some fields contain commas inside double quotes (e.g.,
  `"Percent in poverty, all ages"`). Always use a CSV parser that respects quoting.
- **Encoding**: UTF-8.
- **Header row**: Every CSV includes a header row. Row counts in methodology
  exclude the header.

### 1.2 State Health Long Schema (`state_health_long.csv`)

| Column                 | Description                                            |
|------------------------|--------------------------------------------------------|
| `year`                 | Integer year                                           |
| `state_fips`           | 2-digit state FIPS (zero-padded, e.g. `"01"`)          |
| `state`                | 2-letter USPS abbreviation                             |
| `state_name`           | Full state name                                        |
| `territory_flag`       | `"Y"` for territories, `"N"` for states/DC             |
| `measure_id`           | Short measure identifier (see §2.1)                     |
| `measure`              | Human-readable measure name                            |
| `category`             | e.g. `"Risk factor"`, `"Health outcomes"`              |
| `stratum_type`         | `"Total"`, `"Age"`, `"Sex"`, `"Race/ethnicity"`        |
| `stratum`              | `"Total"`, `"18-44"`, `"Male"`, etc.                   |
| `sample_size`          | Integer, survey sample size (can be null/blank)        |
| `data_value_type`      | Usually `"Percent"`                                     |
| `data_value`           | Float, the primary value                               |
| `low_confidence_limit` | Float                                                    |
| `high_confidence_limit`| Float                                                    |
| `source_note`          | Often blank                                             |

### 1.3 State Life Expectancy Schema (`state_life_expectancy.csv`)

| Column                 | Description                                   |
|------------------------|-----------------------------------------------|
| `year`                 | Integer                                       |
| `state`                | 2-letter USPS abbreviation                    |
| `state_name`           | Full state name                               |
| `territory_flag`       | `"Y"` / `"N"`                                 |
| `stratum_type`         | `"Total"`, `"Age"`, `"Sex"`                   |
| `stratum`              | `"Total"`, `"18-44"`, `"Male"`, etc.          |
| `life_expectancy`      | Float, years                                  |
| `low_confidence_limit` | Float                                         |
| `high_confidence_limit`| Float                                         |
| `note`                 | Often blank                                   |

### 1.4 State SES Long Schema (`state_ses_long.csv`)

| Column            | Description                                                      |
|-------------------|------------------------------------------------------------------|
| `geo_fips`        | 5-digit geo FIPS; state rows end in `000` (e.g. `01000`)         |
| `state`           | 2-letter USPS abbreviation                                       |
| `state_name`      | Full state name                                                  |
| `geo_name`        | Geography name                                                   |
| `geo_level`       | `"state"`, `"county-like distractor"`, `"territory"`              |
| `attribute`       | Attribute identifier (see §2.3)                                  |
| `attribute_label` | Human-readable label                                             |
| `value`           | Float                                                            |
| `unit`            | `"percent"`, `"dollars"`, `"persons"`, `"per 1,000"`             |
| `extraction_note` | Metadata hint                                                    |

**Critical**: Only rows with `geo_level == "state"` contain state-level SES data.
Rows with `geo_level == "county-like distractor"` are synthetic county-level
records embedded in the same table. Rows with `geo_level == "territory"` are
territory records.

### 1.5 State Regions Schema (`state_regions.csv`)

| Column                      | Description                                           |
|-----------------------------|-------------------------------------------------------|
| `state_fips`                | 2-digit state FIPS                                    |
| `state`                     | 2-letter USPS abbreviation                            |
| `state_name`                | Full state name                                       |
| `region`                    | Census region (`"South"`, `"Midwest"`, etc.)          |
| `division`                  | Census division (`"East South Central"`, etc.)        |
| `state_level_analysis_flag` | `"Y"` for states/DC, `"N"` for territories             |
| `note`                      | Territory distractor annotation                       |

### 1.6 County Health Long Schema (`county_health_long.csv`)

| Column                 | Description                                         |
|------------------------|-----------------------------------------------------|
| `year`                 | Integer year                                        |
| `fips`                 | 5-digit county FIPS string                          |
| `state`                | 2-letter USPS abbreviation                          |
| `county`               | County name (may contain distractor artifacts)       |
| `measure_id`           | Short measure identifier (see §2.1)                  |
| `measure`              | Human-readable measure name                         |
| `category`             | e.g. `"Health outcomes"`, `"Health risk behaviors"`  |
| `data_value_type`      | Usually `"Age-adjusted prevalence"`                  |
| `data_value`           | Float, primary value                                |
| `low_confidence_limit` | Float                                               |
| `high_confidence_limit`| Float                                               |
| `population`           | Integer, county population estimate                 |

### 1.7 County SES Long Schema (`county_ses_long.csv`)

| Column            | Description                                                   |
|-------------------|---------------------------------------------------------------|
| `fips`            | 5-digit county FIPS string                                    |
| `state`           | 2-letter USPS abbreviation                                    |
| `county`          | County name                                                   |
| `attribute`       | Attribute identifier (see §2.4)                                |
| `attribute_label` | Human-readable label                                          |
| `value`           | Float                                                         |
| `unit`            | `"percent"`, `"dollars"`, `"persons"`, `"per 1,000"`          |
| `join_note`       | Metadata hint                                                 |

### 1.8 County Metadata Schema (`county_metadata.csv`)

| Column              | Description                                                   |
|---------------------|---------------------------------------------------------------|
| `fips`              | 5-digit county FIPS string (includes invalid `"00000"`)        |
| `state`             | 2-letter USPS abbreviation (`"ZZ"` for invalid)               |
| `state_name`        | Full state name                                               |
| `county`            | County name                                                   |
| `rucc_code`         | Integer 1–9; 1=metro core, 9=most rural; null for invalid     |
| `economic_typology` | `"Mining"`, `"Recreation"`, `"Federal/State government"`, etc.|
| `census_division`   | Census division name                                          |
| `metadata_note`     | Annotation for distractors                                    |

### 1.9 State Neighbors Schema (`state_neighbors.csv`)

| Column           | Description                                             |
|------------------|---------------------------------------------------------|
| `state`          | 2-letter USPS abbreviation                              |
| `state_name`     | Full state name                                         |
| `region`         | Census region                                           |
| `division`       | Census division                                         |
| `neighbors`      | Pipe-delimited neighbor abbreviations (`"FL\|GA\|..."`)   |
| `neighbor_count` | Integer count of neighbors                              |
| `isolate_flag`   | `"Y"` for isolates (AK, HI), `"N"` otherwise             |
| `neighbor_names` | Pipe-delimited full names                               |
| `note`           | Annotation                                              |

### 1.10 Country Health Panel Schema (`country_health_panel.csv`)

| Column                | Description                              |
|-----------------------|------------------------------------------|
| `country`             | Country name (canonical)                 |
| `iso3`                | 3-letter ISO3 code                       |
| `year`                | Integer 2015–2024                        |
| `life_expectancy`     | Float                                    |
| `adult_mortality`     | Float (per 1,000, scaled)                |
| `bmi`                 | Float (mean BMI, scaled)                 |
| `alcohol`             | Float (liters per capita)                |
| `health_expenditure`  | Float (% of GDP)                         |
| `immunization`        | Float (% coverage)                       |
| `schooling`           | Float (mean years, may be blank)         |
| `income_composition`  | Float (HDI component, 0–1)               |
| `gdp`                 | Float (per capita, scaled)               |
| `population`          | Float (scaled)                           |
| `infant_mortality`    | Float (per 1,000 live births)            |
| `missingness_note`    | Annotation for missing values            |

109 unique countries, 10 years each = 1,090 rows (some may be incomplete).

### 1.11 Country Metadata Schema (`country_metadata.csv`)

| Column           | Description                                       |
|------------------|---------------------------------------------------|
| `country`        | Country name (canonical)                          |
| `iso3`           | 3-letter ISO3 code                                |
| `region`         | World Bank region                                 |
| `income_group`   | `"Low income"`, `"Lower middle income"`, `"Upper middle income"`, `"High income"` |
| `lending_category`| `"IDA"`, `"IBRD"`, `"Blend"`                     |
| `metadata_note`  | Annotation                                        |

### 1.12 Country Name Variants Schema (`country_name_variants.csv`)

| Column               | Description                                 |
|----------------------|---------------------------------------------|
| `canonical_country`  | Canonical name used in health panel          |
| `variant_name`       | Alternate name found in the panel or sources |
| `iso3`               | 3-letter ISO3 code                          |
| `reconciliation_note`| Description of the variant                   |

14 variant rows (e.g. "Swaziland" → "Eswatini", "Czech Republic" → "Czechia",
"Turkey" → "Turkiye", "Ivory Coast" → "Cote d'Ivoire").

---

## Part 2 — Identifiers and Naming Conventions

### 2.1 State Health Measure IDs

| measure_id    | Measure                              |
|---------------|--------------------------------------|
| `OBESITY`     | Adult obesity prevalence             |
| `DIAB_MORT`   | Diabetes mortality                   |
| `SCREEN`      | Preventive screening                 |
| `INACTIVE`    | Physical inactivity                  |
| `LIFE_EXP`    | Life expectancy                      |
| `VACC_COMP`   | Vaccination completion               |

### 2.2 County Health Measure IDs

| measure_id   | Measure                                |
|--------------|----------------------------------------|
| `CASTHMA`    | Current asthma among adults            |
| `OBESITY`    | Obesity among adults                   |
| `DIABETES`   | Diagnosed diabetes among adults        |
| `DEPRESSION` | Depression among adults                |
| `DIAB_MORT`  | Diabetes mortality                     |
| `INACTIVE`   | Physical inactivity                    |
| `LIFE_EXP`   | Life expectancy                        |
| `SCREEN`     | Preventive screening                   |
| `VACC_COMP`  | Vaccination completion                 |

### 2.3 State SES Attribute IDs

| Attribute                        | Label                                  |
|----------------------------------|----------------------------------------|
| `PCTPOVALL_2023`                 | Percent in poverty, all ages           |
| `MEDHHINC_2023`                  | Median household income, 2023          |
| `Unemployment_rate_2023`         | Unemployment rate, 2023                |
| `Percent_bachelors_or_higher_2019_23` | Bachelor degree or higher, 2019–23 |
| `POP_ESTIMATE_2023`              | Population estimate, 2023              |
| `R_NET_MIG_2023`                 | Net migration rate, 2023               |

### 2.4 County SES Attribute IDs

All state SES attributes above, plus:

| Attribute                        | Label                                  |
|----------------------------------|----------------------------------------|
| `Unemployment_rate_2010`         | Unemployment rate, 2010                |
| `Median_Household_Income_2022`   | Median household income, 2022          |
| `CENSUS_2020_POP`                | Census 2020 population                 |
| `Economic_typology_2015`         | Economic typology, 2015                |
| `POP_ESTIMATE_2023`              | Population estimate, 2023              |
| `RUCC_2023`                      | Rural-Urban Continuum Code, 2023       |
| `R_NATURAL_CHG_2023`             | Natural change rate, 2023              |
| `R_NET_MIG_2023`                 | Net migration rate, 2023               |

### 2.5 Country Indicator IDs

| Variable              | Description                                  |
|-----------------------|----------------------------------------------|
| `adult_mortality`     | Adult mortality rate (per 1,000, scaled)     |
| `bmi`                 | Mean BMI (scaled)                            |
| `alcohol`             | Alcohol consumption (liters per capita)      |
| `health_expenditure`  | Health expenditure (% of GDP)                |
| `immunization`        | Immunization coverage (%)                    |
| `schooling`           | Mean years of schooling                      |
| `income_composition`  | Income composition (HDI component, 0–1)      |
| `gdp`                 | GDP per capita (scaled)                      |
| `population`          | Population (scaled)                          |
| `infant_mortality`    | Infant mortality (per 1,000 live births)     |

### 2.6 Income Bracket Keys (Q1–Q4)

- `Q1`: Lowest quartile of MEDHHINC_2023 across valid state-level entities
- `Q4`: Highest quartile of MEDHHINC_2023

Partition 51 valid states (50 states + DC) into quartiles. Since 51 does not
divide evenly by 4, the top or bottom group will have one fewer. The portal
uses equal-frequency bins.

### 2.7 RUCC Codes

RUCC is a 9-level categorical variable (codes 1–9). In regression models treat
RUCC as categorical dummy variables (k-1 dummies), never as a continuous
numeric predictor. The convention is `rucc_handling: "categorical_dummies"`.

---

## Part 3 — Filtering and Exclusion Rules

### 3.1 State-Level Analysis: Stratum Filtering

Always filter `stratum_type == "Total"` AND `stratum == "Total"` for aggregate
state-level analyses. This excludes Age, Sex, and Race/ethnicity demographic
subgroups.

### 3.2 Territory Exclusion

Three territories appear as distractors in state-level data: **GU** (Guam),
**PR** (Puerto Rico), **VI** (U.S. Virgin Islands). Exclude them for all
state-level analyses:

- In `state_regions.csv`: filter `state_level_analysis_flag == "Y"`
- In `state_health_long.csv` and `state_life_expectancy.csv`: filter `territory_flag == "N"`
- In `state_ses_long.csv`: filter `geo_level == "state"`

### 3.3 DC Handling

DC (District of Columbia) has `state_level_analysis_flag == "Y"` and
`territory_flag == "N"`. **Include DC in all state-level analyses** as a valid
analytic unit. It counts toward state totals (e.g., 50 states + DC = 51 valid
state-level entities).

### 3.4 State SES: Geo-Level Filtering

In `state_ses_long.csv`, use `geo_level == "state"` to select only state-level
rows (geo_fips ending in `000`). Rows with `geo_level == "county-like
distractor"` are synthetic county records embedded in the state SES table — do
not use them for state-level analyses.

### 3.5 County-Level: FIPS Validation

- Valid FIPS: 5-digit numeric string (`00001`–`56999` ish).
- **FIPS `"00000"` is always invalid**. It appears in `county_metadata.csv`
  (state `"ZZ"`, `"Invalid state"`) and `county_ses_long.csv` but NOT in
  `county_health_long.csv`. Count it under `invalid_fips` in exclusions.
- County names containing numeric artifacts (e.g. `"Adams 27 County"`) are
  synthetic distractors but may have valid FIPS codes — validate by FIPS, not
  by name.

### 3.6 County-Level: State Filtering

When a task specifies a list of requested states, filter county records to
only those states. The `state` column uses 2-letter USPS abbreviations.
Counties in non-requested states go under `outside_requested_states` in
exclusions.

### 3.7 Missing Data Exclusions (County)

After FIPS validation and state filtering:
- `missing_ses`: FIPS present in health data but missing from SES data after
  the join.
- `missing_health_data`: FIPS present in SES data but missing the target health
  outcome measure for the analysis year.
- Complete cases: records with both health outcome AND all required SES
  attributes for the model.

### 3.8 Missing Data (Country)

Country-level data has structured missingness. The `missingness_note` column
indicates blanks. Variables most likely to have gaps: `schooling`, `gdp`,
`health_expenditure`. Missing rates are computed as the proportion of NA values
per variable across the analysis panel.

### 3.9 Name Variant Resolution (Country)

The health panel uses canonical country names. When joining with metadata or
external references, resolve variants using `country_name_variants.csv`:
- Match variant names to their canonical form.
- Join by `iso3` when canonical names differ.
- 14 variant rows should be resolved; unresolved rows indicate variants in the
  panel not covered by the variants table.

---

## Part 4 — Statistical Conventions

### 4.1 Regression Modeling

**Bivariate model**: outcome ~ exposure (single predictor, no covariates).

**Adjusted model**: outcome ~ exposure + SES covariates (multivariable ordinary
least squares or weighted least squares).

**Weighted regression**: When `sample_size` is available, use sample-size
weights (observations with larger surveys get more weight).

**Standardized betas**: Use standardized coefficients (outcome and predictors
z-scored before regression) for comparing effect magnitudes across predictors
measured on different scales.

**Attenuation percent**: `((bivariate_std_beta - adjusted_std_beta) /
bivariate_std_beta) × 100`. Measures how much the exposure-outcome association
weakens after adjusting for confounders.

### 4.2 Sensitivity Analysis

After fitting the primary adjusted model:
1. Identify high-leverage states (via hat-values / leverage diagnostic).
2. Drop the top-N most influential states and refit the adjusted model.
3. Compare the sensitivity adjusted std beta for the exposure to the original.
4. Classify sensitivity verdict:
   - `stable`: coefficient sign and significance unchanged, magnitude change ≤ 20%
   - `sign_flip`: coefficient sign changes
   - `significance_changed`: crosses a significance threshold
   - `magnitude_shift_gt_20`: magnitude changes > 20% but sign/significance stable

### 4.3 Multicollinearity (VIF)

Compute Variance Inflation Factors for all predictors in the adjusted model.
- `max_vif`: maximum VIF across all predictors, rounded to 2 decimal places.
- `max_vif_predictor`: the predictor ID with the highest VIF.
- `culprit_pair`: the two most collinear predictors (the pair with the highest
  pairwise correlation or that jointly drive the VIF), sorted alphabetically by
  predictor ID.

### 4.4 Regional Clustering (ICC)

Compute the Intraclass Correlation Coefficient using Census region or division
as the grouping variable:
1. Fit a random-intercept (mixed-effects) model with region/division as the
   grouping factor.
2. ICC = between-group variance / (between-group variance + within-group variance).

### 4.5 Bootstrap Confidence Intervals (Mediation)

For indirect effects in mediation analysis:
1. Bootstrap the indirect effect (poverty → mediator → outcome) with many
   resamples (e.g., 1,000+).
2. Extract the CI at the desired level (typically 95%).
3. Classify:
   - `positive_excludes_zero`: CI lower > 0
   - `negative_excludes_zero`: CI upper < 0
   - `includes_zero`: CI spans zero

### 4.6 PCA (Country Burden Score)

1. **Variable retention**: Keep all 10 candidate indicators: `adult_mortality`,
   `bmi`, `alcohol`, `health_expenditure`, `immunization`, `schooling`,
   `income_composition`, `gdp`, `population`, `infant_mortality`.
2. **Standardization**: Z-score all variables before PCA.
3. **Imputation**: Use mean imputation or complete-case analysis depending on
   the missing rate. For country PCA, impute missing values (typically with
   variable means) so the full panel is used.
4. **PC1**: First principal component. Report variance share of PC1.
5. **Loadings**: Use the loading vector of PC1. `top_absolute_loadings`:
   variables with highest |loading|. `top_positive_loadings`: variables with
   highest loading (signed). These two lists often differ — a variable with a
   large negative loading appears in absolute but not positive.
6. **Burden clustering**: Apply k-means (k=3) on the PC1 scores. Label clusters
   `low_burden`, `middle_burden`, `high_burden` by ascending mean value of a
   mortality/health-burden indicator (high positive PC1 = high burden).

### 4.7 Spatial Autocorrelation (Moran's I)

Compute Moran's I on regression residuals using a spatial weights matrix:
- Neighbor definitions from `state_neighbors.csv` (pipe-delimited `neighbors`
  column).
- Isolates (AK, HI; `isolate_flag == "Y"`) are excluded from the spatial
  weights matrix but counted separately.
- Use row-standardized weights (each neighbor gets 1/k weight).

### 4.8 Mixed-Effects Model (Country Income Groups)

For the country analysis, test whether income-group-level random intercepts
improve model fit over pooled OLS:
1. Fit a random-intercept model with `income_group` as the grouping variable.
2. Report the ratio: random-intercept variance / residual variance.
3. Compare to pooled OLS via likelihood ratio or AIC.

### 4.9 Dynamic vs. Static SES Specification (County)

For county models, compare two specifications:

**Static**: Uses current-year (snapshot) SES variables:
- `PCTPOVALL_2023`
- `MEDHHINC_2023`
- `Unemployment_rate_2023`
- `Percent_bachelors_or_higher_2019_23`
- RUCC dummies
- Economic typology dummies (optional)

**Dynamic**: Replaces income and unemployment snapshots with change variables:
- Income change = `MEDHHINC_2023 - Median_Household_Income_2022`
- Unemployment change = `Unemployment_rate_2023 - Unemployment_rate_2010`
- Keeps other static controls

Model selection: Compare AIC (lower = better). Report the winning model per
outcome.

### 4.10 Rank-Shift Analysis

For income-adjusted preventive screening audit:
1. **Crude ranking**: Rank states by the raw health measure value.
2. **Adjusted ranking**: Regress the health measure on income proxy (MEDHHINC_2023)
   and poverty (PCTPOVALL_2023), extract residuals, then rank by residuals.
3. **Rank shift**: adjusted_rank - crude_rank for each state.
   - Positive shift: state ranks worse after adjustment (crude ranking flattered it).
   - Negative shift: state ranks better after adjustment (crude ranking penalized it).
4. **Spearman correlation**: Spearman's ρ between crude and adjusted rankings.
5. **Priority direction**: `lower_value_worse` means low values = bad (e.g.,
   screening). `higher_value_worse` means high values = bad (e.g., mortality).
   This determines whether the poorest-performing states have lowest or highest
   values.

### 4.11 Income and Poverty Coefficient Signs

In weighted regression with income and poverty as predictors:
- A `positive` income coefficient: higher income → higher outcome value.
- A `positive` poverty coefficient: higher poverty → higher outcome value.
- `near_zero`: coefficient magnitude < some very small threshold (e.g.,
  |std_beta| < 0.01 or p > 0.10).

---

## Part 5 — Rounding Rules

| Quantity                        | Decimal Places | Example      |
|---------------------------------|----------------|--------------|
| Standardized betas              | 3              | `0.778`       |
| Attenuation percent             | 1              | `3.6`         |
| VIF                             | 2              | `2.66`        |
| ICC                             | 3              | `0.173`       |
| Spearman ρ                      | 3              | `0.350`       |
| AIC                             | 2              | `252.13`      |
| Bootstrap CI bounds             | 3              | `0.051`       |
| Indirect effect                 | 3              | `-0.010`      |
| Moran's I                       | 3              | `-0.170`      |
| Coverage rates (proportions)    | 3              | `1.000`       |
| PC1 variance share              | 3              | `0.717`       |
| Missing rates                   | 3              | `0.009`       |
| Tercile means                   | 2              | `12.16`       |
| Random intercept variance ratio | 3              | `1.170`       |

---

## Part 6 — Bucket (Enum) Rules

### VIF
- `lt_5`: VIF < 5
- `5_to_10`: 5 ≤ VIF < 10
- `ge_10`: VIF ≥ 10

### ICC
- `lt_0_05`: ICC < 0.05
- `0_05_to_0_15`: 0.05 ≤ ICC < 0.15
- `ge_0_15`: ICC ≥ 0.15

### p-value
- `lt_0_001`: p < 0.001
- `lt_0_01`: 0.001 ≤ p < 0.01
- `lt_0_05`: 0.01 ≤ p < 0.05
- `ge_0_05`: p ≥ 0.05
- `not_computed`: model not fit or p-value not computed

### Moran's I
- `lt_0_05`: |I| < 0.05 (effectively no spatial autocorrelation)
- `0_05_to_0_20`: 0.05 ≤ |I| < 0.20
- `ge_0_20`: |I| ≥ 0.20

### Random Intercept Variance
- `low`: variance ratio < 0.5
- `moderate`: 0.5 ≤ variance ratio < 1.0
- `high`: variance ratio ≥ 1.0

### Bootstrap CI
- `positive_excludes_zero`: CI entirely above zero
- `negative_excludes_zero`: CI entirely below zero
- `includes_zero`: CI spans zero

---

## Part 7 — Ordering and Sorting Rules

### States
- When listed explicitly in the prompt (e.g., "AL, GA, MS, TN, KY, WV"): output
  in **prompt order** for the `requested_states` field.
- When in a plain sorted list (e.g., `included_states`, `excluded_states`,
  `territories_excluded`): **ascending USPS alphabetical order** (AK, AL, AR, …).
- When in priority/review lists: order by the relevant metric, not alphabetically.

### FIPS Codes
- `top_residual_outlier_fips`: order by residual magnitude (most positive
  residual first, i.e., descending residual).
- `top_positive_residual_fips`: same — most positive residual first.

### Predictor IDs
- `culprit_pair`: sorted ascending alphabetically by predictor ID string.

### Country ISO3
- `complete_gdp_gap_iso3`: sorted ascending alphabetically by ISO3.

### Rank Shifts
- `top_upward_shift_states`: order by rank_shift **descending** (biggest
  positive shift first — state that improved most in ranking).
- `top_downward_shift_states`: order by rank_shift **ascending** (most negative
  shift first — state that dropped most in ranking).
- `priority_review_states`: order by adjusted priority (worst performers first,
  taking `priority_direction` into account).

### PCA Loadings
- `top_absolute_loadings`: order by absolute loading **descending**.
- `top_positive_loadings`: order by signed loading **descending**.

### Variables Retained (Country PCA)
- List in the canonical analysis order: `adult_mortality`, `bmi`, `alcohol`,
  `health_expenditure`, `immunization`, `schooling`, `income_composition`,
  `gdp`, `population`, `infant_mortality`.

### Census Divisions
- Use the division name exactly as it appears in `state_regions.csv` (e.g.,
  `"East South Central"`, not abbreviated).

---

## Part 8 — Common Pitfalls

1. **Forgetting stratum filtering**: The state health table includes demographic
   strata (Age, Sex, Race/ethnicity). Using unfiltered data double- or
   triple-counts each state. Always filter to `stratum_type == "Total"` and
   `stratum == "Total"`.

2. **Mixing county-like distractors with state SES rows**: `state_ses_long.csv`
   embeds county-level distractors. If you fail to filter `geo_level ==
   "state"`, your state SES summaries will be contaminated with hundreds of
   non-state rows.

3. **Counting territories as states**: Territories (GU, PR, VI) appear in state
   tables. Always exclude them using `territory_flag == "N"` or
   `state_level_analysis_flag == "Y"`.

4. **FIPS 00000**: This is a planted invalid FIPS in county data. It appears in
   `county_metadata.csv` and `county_ses_long.csv` but NOT in
   `county_health_long.csv`. It will appear as a missing-SES row if you
   left-join from health to SES; it will appear as an unmatched row if you
   inner-join. Always check for it and count it as `invalid_fips`.

5. **Name-variant join misses**: The country health panel may use variant names
   that differ from the metadata table. Always resolve through
   `country_name_variants.csv` before joining on country name. Use `iso3` as
   the definitive join key when available.

6. **RUCC as numeric**: RUCC is categorical (1–9). Using it as a continuous
   predictor produces wrong results and invalid model selection. Always use
   `rucc_handling: "categorical_dummies"`.

7. **Dynamic variable order**: When computing changes, always subtract the older
   value from the newer: `MEDHHINC_2023 - Median_Household_Income_2022`,
   `Unemployment_rate_2023 - Unemployment_rate_2010`.

8. **Income quartile unevenness**: With 51 valid state-level entities, one
   quartile will have 12 states instead of 13. This is expected — do not pad.

9. **Mixing measure IDs across levels**: County health uses `CASTHMA` and
   `DIABETES` which do not exist in state health. State health uses
   `DIAB_MORT`. Verify the measure ID exists at the level you are working at.

10. **Weighted vs. unweighted regression**: When `sample_size` is available
    (state health data), use weighted regression. The population column in
    county data is an estimate, not a survey sample size — follow the task's
    specification for whether to weight county models.

11. **Bootstrap CI direction**: The bootstrap CI for the indirect effect may
    not be symmetric around the point estimate. Report the CI bounds as computed,
    not derived from the point estimate ± SE.

12. **Spatial isolate handling**: AK and HI have `isolate_flag == "Y"` — they
    have no neighbors. They do not contribute to Moran's I computation but
    count toward `isolate_state_count`.

---

## Part 9 — Task-Specific Analysis Recipes

### 9.1 State Confounding Audit (like train_001)

1. Load `state_health_long.csv` — filter to analysis year, `stratum_type ==
   "Total"`, `stratum == "Total"`, `territory_flag == "N"`.
2. Pivot exposure (e.g., `OBESITY`) and outcome (e.g., `DIAB_MORT`) to wide
   format, keyed by state.
3. Load `state_ses_long.csv` — filter `geo_level == "state"`, pivot SES
   attributes to wide format.
4. Load `state_regions.csv` — filter `state_level_analysis_flag == "Y"`.
5. Merge all three by state abbreviation.
6. Fit bivariate model: outcome ~ exposure.
7. Fit adjusted model: outcome ~ exposure + SES covariates.
8. Compute attenuation percent.
9. Compute VIF, identify culprit pair and max VIF predictor.
10. Compute regional ICC using the `region` or `division` column.
11. Compute leverage, drop top-3 high-leverage states, refit, classify
    sensitivity verdict.

### 9.2 Income-Adjusted Screening Audit (like train_002)

1. Load state health, filter to analysis year and Total strata.
2. Extract the target measure (e.g., `SCREEN`) and sample sizes.
3. Load state SES, filter to `geo_level == "state"`.
4. Merge by state.
5. Check demographic strata coverage: if any stratum labels (e.g., age/sex) are
   blank, declare `not_feasible_blank_demographic_strata`.
6. Bin states into Q1–Q4 by MEDHHINC_2023.
7. Compute crude ranking (by data_value, respecting priority_direction).
8. Fit weighted regression: outcome ~ MEDHHINC_2023 + PCTPOVALL_2023.
9. Extract income and poverty coefficient signs and p-buckets.
10. Compute adjusted ranking (by residuals, respecting direction).
11. Compute Spearman ρ between rankings.
12. Compute rank shifts, identify top upward/downward shift states and priority
    review states.

### 9.3 County Reconciliation Audit (like train_003)

1. Load `county_health_long.csv` — filter to analysis year and target measure
   (e.g., `CASTHMA`).
2. Load `county_ses_long.csv` — pivot to wide format keyed by FIPS.
3. Load `county_metadata.csv` — for RUCC, economic typology.
4. Identify and exclude FIPS `"00000"` (invalid_fips).
5. Filter to requested states only; count excluded as `outside_requested_states`.
6. Merge health, SES, and metadata on FIPS.
7. Identify missing SES and missing health data rows.
8. For complete cases, fit static model (current-year SES + RUCC dummies +
   economic typology dummies).
9. Compute dynamic variables: income change and unemployment change.
10. Fit dynamic model; compare AICs; declare winner per outcome and overall
    reconciliation label.
11. Extract residuals from winning model, identify top-5 positive residual FIPS.
12. Compute tercile means of unemployment change.

### 9.4 Country Burden PCA Audit (like train_004)

1. Load `country_health_panel.csv`.
2. Load `country_name_variants.csv` — resolve all variants.
3. Load `country_metadata.csv` — join on ISO3. Compute metadata join coverage.
4. Report reconciliation stats (variant rows, resolved, unresolved).
5. Restrict to analysis year range (e.g., 2015–2024).
6. Compute country-year averages or use latest year per country depending on
   task specification.
7. Standardize the 10 retained variables.
8. Impute missing values (mean or median).
9. Run PCA. Extract PC1 variance share, loadings, variables retained.
10. Apply k-means (k=3) on PC1 scores. Label clusters. Count per cluster.
11. Compute missing rates per variable.
12. Detect anomalies: flag scaled adult_mortality or bmi values that are
    suspiciously patterned (e.g., all values ≥ some threshold for a country).
13. Identify countries with complete GDP across all years (no gaps).
14. Fit mixed-effects model with income_group random intercepts. Compute
    variance ratio, bucket it, decide `mixed_model_supported` vs.
    `pooled_ols_sufficient` via likelihood ratio test.

### 9.5 County Mediation-Spatial Audit (like train_005)

1. Load county health for target outcomes and mediator at analysis year.
2. Load county SES and metadata.
3. Exclude invalid FIPS and filter to requested states.
4. Compute complete case counts and exclusion breakdowns.
5. Fit mediation model:
   - Path a: poverty → mediator
   - Path b: mediator → outcome (controlling for poverty + SES controls)
   - Indirect effect: a × b
6. Bootstrap the indirect effect. Report CI and classification.
7. Extract residuals from outcome model.
8. Load `state_neighbors.csv` for spatial weights.
9. Compute Moran's I on residuals. Bucket.
10. Count isolate states.
11. Identify hot-spot census division (division with highest mean positive
    residual).
12. Identify top-5 positive residual FIPS.

---

## Part 10 — Template Compliance

Every task provides an `answer_template.json` in `input/payloads/`. Read it
carefully — it defines the exact JSON schema, including enum values, array
lengths, and key names. Fill every field. Array fields must be in the order
specified by the conventions above. Enum fields must use exactly the string
values defined in the template.
