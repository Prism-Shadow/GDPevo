# Public Health Evidence Portal — Audit Skill

## Overview

This skill covers statistical audit tasks against a public-health evidence portal. The portal
serves static HTML pages and linked CSV downloads for state, county, and country health and
socioeconomic data. All data are synthetic but shaped like real public-health sources.

**Base URL:** use the remote URL provided in the task environment (not localhost or 127.0.0.1).

---

## 1. Data Download Workflow

Every audit starts by downloading the relevant CSVs from the portal's `/data/` directory.
The portal home page (`GET /`) lists all available pages and downloadable files.

### 1.1 Essential CSVs

| CSV | Description |
|-----|-------------|
| `state_health_long.csv` | Long-format state-year health measures with strata |
| `state_life_expectancy.csv` | State life expectancy by stratum |
| `state_ses_long.csv` | State socioeconomic attribute-value records |
| `state_regions.csv` | Census-like region/division lookup |
| `state_neighbors.csv` | State contiguity neighbors for spatial summaries |
| `county_health_long.csv` | County-year health measures |
| `county_ses_long.csv` | County socioeconomic attribute-value records |
| `county_metadata.csv` | County RUCC, economic typology, census division |
| `country_health_panel.csv` | 2015–2024 WHO-like country-year indicators |
| `country_metadata.csv` | ISO3, region, income group |
| `country_name_variants.csv` | Crosswalk for resolving variant country names |

### 1.2 Portal Pages

Key pages (for column descriptions, data cautions, reference lookups):

- `pages/state-health.html` — state health measure catalog and known cautions
- `pages/state-ses.html` — state SES with geo_fips conventions
- `pages/state-regions.html` — region/division lookup with territory flags
- `pages/county-health.html` — county health measures and categories
- `pages/county-ses.html` — county SES attributes and join notes
- `pages/county-neighbors.html` — spatial neighbor reference (isolates)
- `pages/country-indicators.html` — country panel with anomaly descriptions
- `pages/country-metadata.html` — income groups (do not confuse with lending category)
- `pages/name-reconciliation.html` — variant-to-canonical name crosswalk
- `pages/methodology.html` — row counts and general notes

---

## 2. State-Level Data Conventions

### 2.1 State Health (`state_health_long.csv`)

**Columns:** `year, state_fips, state, state_name, territory_flag, measure_id, measure,
category, stratum_type, stratum, sample_size, data_value_type, data_value,
low_confidence_limit, high_confidence_limit, source_note`

**Measure IDs:**

| measure_id | Description | Category |
|------------|-------------|----------|
| `OBESITY` | Adult obesity prevalence | Risk factor |
| `DIAB_MORT` | Diabetes mortality | — |
| `INACTIVE` | Physical inactivity | — |
| `LIFE_EXP` | Life expectancy | — |
| `SCREEN` | Preventive screening | Prevention |
| `VACC_COMP` | Vaccination completion | Prevention |

**Stratum types:** `Total`, `Age`, `Sex`, `Income quartile`, `Race/ethnicity`, and blank (`""`).

**Territories:** `GU` (Guam), `PR` (Puerto Rico), `VI` (U.S. Virgin Islands) appear with
`territory_flag = "Y"`. Exclude them for state-level analysis unless the task explicitly
requires them.

**Filtering for state-level "Total" estimates:**

- `stratum_type = "Total"` AND `stratum = "Total"` AND `territory_flag = "N"`
- The Total rows include 50 states + DC + 3 territories = 54 rows per measure per year.

**Known data issues (always check for these):**

1. **Missing 2024 Total rows:** California (`CA`) `OBESITY` 2024 Total is intentionally
   missing. Texas (`TX`) `LIFE_EXP` 2024 Total is intentionally missing. These states
   must be excluded from analyses that require those measures for 2024.

2. **Stale 2023 rows:** When a 2024 Total is missing, a stale 2023 Total row is retained
   with `source_note = "Stale 2023 Total retained beside missing 2024 Total"`. Filter
   these out — use the analysis year, not the stale row. The stale rows are:
   - CA OBESITY 2023 Total (stale, alongside missing 2024)
   - TX LIFE_EXP 2023 Total (stale, alongside missing 2024)

3. **Ohio intentional duplicates:** One `INACTIVE` row for Ohio 2021 (Race/ethnicity,
   Black) is duplicated with `source_note = "Intentional duplicate stratified row from
   overlapping extract"`. One duplicate should be dropped. Also, Ohio `SCREEN` 2022 has
   5 rows with blank `stratum_type` and blank `stratum` (a design artifact); use only
   the SCREEN 2022 Total row, not these 5 blank-stratum rows.

4. **Blank demographic strata (SCREEN 2022):** The `SCREEN` measure for 2022 has Age and
   Sex strata where `stratum_type = ""` and `stratum = ""`. These 270 rows (54 entities ×
   5 blanks) are not usable for direct demographic standardization — income quartile
   strata are available instead.

**Sample size:** Available on Total rows . Use when weighting regressions by sample size.

### 2.2 State SES (`state_ses_long.csv`)

**Columns:** `geo_fips, state, state_name, geo_name, geo_level, attribute, attribute_label,
value, unit, extraction_note`

**Critical filtering rule:** State-level rows have `geo_fips` ending in `000` (e.g.,
`01000` for Alabama). County-like rows (non-000 suffix) are distractors with
`geo_level = "county-like distractor"`. **Always filter `geo_fips` to those ending in `000`
before use.**

Territory rows also end in 000 and appear with `geo_level = "territory"`. Exclude them
for state-level analysis.

**Attributes (6 per state):**

| Attribute | Description | Unit |
|-----------|-------------|------|
| `PCTPOVALL_2023` | Percent in poverty, all ages | percent |
| `MEDHHINC_2023` | Median household income, 2023 | dollars |
| `Unemployment_rate_2023` | Unemployment rate, 2023 | percent |
| `Percent_bachelors_or_higher_2019_23` | Bachelor's or higher, 2019–23 | percent |
| `POP_ESTIMATE_2023` | Population estimate, 2023 | persons |
| `R_NET_MIG_2023` | Net migration rate, 2023 | per 1,000 |

**Pivot pattern:** Convert from long (attribute-value) to wide (one column per attribute)
by pivoting on `attribute` using `geo_fips`/`state` as the key.

### 2.3 State Regions (`state_regions.csv`)

**Columns:** `state_fips, state, state_name, region, division, state_level_analysis_flag, note`

**Territories:** PR, GU, VI have `state_level_analysis_flag = "N"`. Filter to `"Y"`
for state-level analyses.

**Regions:** `Northeast`, `Midwest`, `South`, `West`

**Divisions:** `New England`, `Middle Atlantic`, `East North Central`, `West North Central`,
`South Atlantic`, `East South Central`, `West South Central`, `Mountain`, `Pacific`,
plus territory divisions (`Caribbean`, `Pacific Island Areas`) which should be excluded.

### 2.4 State Neighbors (`state_neighbors.csv`)

**Columns:** `state, state_name, region, division, neighbors, neighbor_count,
isolate_flag, neighbor_names, note`

**Isolates:** Alaska (`AK`) and Hawaii (`HI`) always have `isolate_flag = "Y"` with 0
contiguous neighbors. Many other states are also marked as isolates in the portal's
spatial reference (`isolate_flag = "Y"`) — check the CSV directly.

Use this table for spatial residual summaries (regional ICC, Moran's I clustering).

---

## 3. County-Level Data Conventions

### 3.1 County Health (`county_health_long.csv`)

**Columns:** `year, fips, state, county, measure_id, measure, category, data_value_type,
data_value, low_confidence_limit, high_confidence_limit, population`

**Measure IDs (16 total):** `CASTHMA`, `OBESITY`, `DIABETES`, `DEPRESSION`, `CHD`, `GHLTH`,
`LPA` (No leisure-time physical activity), `CSMOKING`, `SLEEP`, `BINGE`, `MAMMOUSE`,
`BPMED`, `CHECKUP`, `DENTAL`, `COREM`, `COREW`

**Years:** 2021–2024

**FIPS:** 5-digit string, zero-padded (e.g., `01001`). **Always treat FIPS as a string,
not an integer.** When sorting FIPS, sort lexicographically.

**Important filtering rules:**

1. **Invalid FIPS (`00000`):** Rows with FIPS `00000` (state `ZZ`, county `Unknown County`)
   are distractor rows. Exclude from all analysis.

2. **Population blanks:** ~23 rows have blank `population` — handle these in
   population-weighted analyses.

3. **Missing measures:** Some counties intentionally lack certain measures. Check
   completeness for each measure separately.

### 3.2 County SES (`county_ses_long.csv`)

**Columns:** `fips, state, county, attribute, attribute_label, value, unit, join_note`

**Attributes (12 per county):**

| Attribute | Description |
|-----------|-------------|
| `PCTPOVALL_2023` | Percent poverty, all ages, 2023 |
| `MEDHHINC_2023` | Median household income, 2023 |
| `Unemployment_rate_2010` | Unemployment rate, 2010 |
| `Unemployment_rate_2023` | Unemployment rate, 2023 |
| `Median_Household_Income_2022` | Median household income, 2022 |
| `Percent_bachelors_or_higher_2019_23` | Bachelor's or higher, 2019–23 |
| `POP_ESTIMATE_2023` | Population estimate, 2023 |
| `CENSUS_2020_POP` | Census 2020 population |
| `R_NET_MIG_2023` | Net migration rate, 2023 |
| `R_NATURAL_CHG_2023` | Natural change rate, 2023 |
| `RUCC_2023` | Rural-Urban Continuum Code |
| `Economic_typology_2015` | Economic typology category |

**Known issues:**
- `POP_ESTIMATE_2023` and `Percent_bachelors_or_higher_2019_23` are missing for some
  counties — these counties become incomplete cases.
- FIPS `00000` rows are invalid distractors.

**Pivot pattern:** Convert from long to wide by pivoting on `attribute`, using `fips`
as the key. Each county becomes one row with all 12 attributes as columns.

**Dynamic variables (for dynamic model specifications):**
- `unemployment_change = Unemployment_rate_2023 - Unemployment_rate_2010`
- `income_change = MEDHHINC_2023 - Median_Household_Income_2022`
  (rule name: `MEDHHINC_2023_minus_Median_Household_Income_2022`)

### 3.3 County Metadata (`county_metadata.csv`)

**Columns:** `fips, state, state_name, county, rucc_code, economic_typology,
census_division, metadata_note`

**Key fields:**
- `rucc_code`: Integer 1–9. Treat as **categorical dummies** in models (not continuous).
  RUCC 00000 has a blank code — exclude.
- `economic_typology`: Categories like `Farming`, `Manufacturing`, `Mining`,
  `Federal/State government`, `Recreation`, `Nonspecialized`, `Persistent poverty`,
  `Invalid FIPS distractor`, `Old name`.
- `census_division`: Used for spatial hotspot identification.

**Distractors:**
- FIPS `00000` with `economic_typology = "Invalid FIPS distractor"` — exclude.
- FIPS `46113` with `economic_typology = "Old name"` — Shannon County, SD (current:
  Oglala Lakota County).

### 3.4 County SES Join and Completeness

To build a complete analysis dataset:
1. Start with county health rows for the target measure, year, and requested states.
2. Exclude `fips = "00000"` and FIPS outside the requested states.
3. Left-join county SES (pivoted wide) on `fips`.
4. Left-join county metadata on `fips`.
5. Count **complete cases** (no missing outcome, no missing SES predictors, no missing
   metadata fields needed for the model).
6. Track exclusions by reason:
   - `invalid_fips`: FIPS 00000
   - `outside_requested_states`: state not in task's requested list
   - `missing_ses`: any required SES attribute or RUCC/typology is blank
   - `missing_health_data`: outcome or predictor health measure is blank

---

## 4. Country-Level Data Conventions

### 4.1 Country Health Panel (`country_health_panel.csv`)

**Columns:** `country, iso3, year, life_expectancy, adult_mortality, bmi, alcohol,
health_expenditure, immunization, schooling, income_composition, gdp, population,
infant_mortality, missingness_note`

**Years:** 2015–2024. **109 countries**, each with 10 years = 1090 rows.

**Variable missingness rates (approximate):**
- `schooling`: ~1.8% missing
- `health_expenditure`: ~1.2% missing
- `gdp`: ~0.9% missing (Japan: all 10 years blank by design)
- Other variables have full coverage in raw data.

**Known anomalies (always screen for these):**

1. **Namibia (NAM) BMI scale anomaly:** 2018–2021 BMI values are ~2600 (scaled ~100×).
   Exclude or flag these country-years. BMI values in the 20–30 range are normal.

2. **Eswatini (SWZ) adult_mortality 10× drop:** 2021–2024 values drop to ~20 from
   ~200. Exclude or flag these country-years.

3. **Japan (JPN) complete GDP gap:** All 10 years have blank `gdp`.

**Detection approach:** For each variable, compute z-scores or simple range checks per
country. Values that deviate by >10× within-country are anomalies.

### 4.2 Country Metadata (`country_metadata.csv`)

**Columns:** `country, iso3, region, income_group, lending_category, metadata_note`

**Income groups:** `Low income`, `Lower middle income`, `Upper middle income`, `High income`

**IMPORTANT:** `lending_category` is a distractor column. Do NOT confuse it with
`income_group`. The lending category includes values like `IDA`, `IBRD`, `Blend`,
`Not classified`.

**Join pattern:** Join health panel to metadata on `iso3`. Track join coverage =
(matched health rows) / (total health rows).

### 4.3 Country Name Reconciliation (`country_name_variants.csv`)

**Columns:** `canonical_country, variant_name, iso3, reconciliation_note`

14 variant-to-canonical mappings. Key pairs:
- `United States` ← `United States of America`
- `Cote d'Ivoire` ← `Ivory Coast`
- `Bolivia` ← `Bolivia (Plurinational State of)`
- `Czechia` ← `Czech Republic`
- `Eswatini` ← `Swaziland`
- `Korea, Rep.` ← `South Korea`
- `Turkiye` ← `Turkey`
- `Viet Nam` ← `Vietnam`
- `Lao PDR` ← `Laos`
- `Kyrgyz Republic` ← `Kyrgyzstan`
- `Slovak Republic` ← `Slovakia`
- `Egypt` ← `Egypt, Arab Rep.`
- `Iran` ← `Iran, Islamic Rep.`
- `Yemen` ← `Yemen, Rep.`

The crosswalk is a hint table, not a complete authority. Use `iso3` as the primary join
key whenever possible. For name-based joins, resolve variants against the canonical
column first, then join on `canonical_country`.

---

## 5. Statistical Conventions

### 5.1 Rounding Rules

| Precision | Applied to |
|-----------|------------|
| 0 decimals | Counts (states, counties, complete cases), cluster counts, analysis year |
| 1 decimal | Attenuation percentage |
| 2 decimals | VIF, AIC, tercile/category means |
| 3 decimals | Standardized betas, ICC, p-values, correlations (Spearman, Pearson), Moran's I, bootstrap CI bounds, indirect effects, PC1 variance share, loading scores, missing rates, join coverage, random intercept variance ratio |

### 5.2 Bucket Rules

**VIF:**
- `lt_5`: max VIF < 5.0
- `5_to_10`: 5.0 ≤ max VIF < 10.0
- `ge_10`: max VIF ≥ 10.0

**Regional ICC:**
- `lt_0_05`: ICC < 0.05
- `0_05_to_0_15`: 0.05 ≤ ICC < 0.15
- `ge_0_15`: ICC ≥ 0.15

**P-value buckets (for coefficients and sensitivity tests):**
- `lt_0_001`: p < 0.001
- `lt_0_01`: 0.001 ≤ p < 0.01
- `lt_0_05`: 0.01 ≤ p < 0.05
- `ge_0_05`: p ≥ 0.05
- `not_computed`: test not run or not applicable

**Moran's I:**
- `lt_0_05`: I < 0.05
- `0_05_to_0_20`: 0.05 ≤ I < 0.20
- `ge_0_20`: I ≥ 0.20

**Random intercept variance ratio (for mixed models):**
- `low`: variance ratio < 0.1
- `moderate`: 0.1 ≤ variance ratio < 0.3
- `high`: variance ratio ≥ 0.3

**Bootstrap CI enumeration:**
- `positive_excludes_zero`: CI low > 0
- `negative_excludes_zero`: CI high < 0
- `includes_zero`: CI low ≤ 0 ≤ CI high

### 5.3 Model Direction and Standardization

- **Standardized betas:** Report all regression coefficients as standardized betas
  (both predictor and outcome standardized to mean 0, variance 1) unless otherwise
  instructed.
- **Attenuation:** `attenuation_pct = ((bivariate_beta - adjusted_beta) / bivariate_beta) × 100`,
  rounded to 1 decimal.
- **AIC:** Report AIC from comparable OLS models (not mixed models). Lower AIC wins.
  The `winning_model` is `static_wins` when static AIC is lower, `dynamic_wins` otherwise.
- **Weighted regression:** When `sample_size` is available (state data), use it as
  regression weights. For county data with `population`, use population as weights.
- **Priority direction:** `higher_value_worse` means higher measure values indicate worse
  outcomes (e.g., obesity, diabetes mortality). `lower_value_worse` means lower values
  indicate worse outcomes (e.g., screening rates, vaccination coverage).

### 5.4 PCA Conventions

For country burden-score PCA:
1. Standardize all variables (mean 0, variance 1) before PCA.
2. Use complete cases only (listwise deletion of rows with any missing value).
3. Report `pc1_variance_share` (proportion of variance explained by PC1).
4. Report loadings as the raw component scores (correlation between variable and PC1).
5. Report `top_absolute_loadings`: 3 variables with largest |loading|, descending by
   absolute value.
6. Report `top_positive_loadings`: 3 variables with most positive loading, descending.
7. Variable retention: exclude variables with >50% missing or those that are not
   conceptually part of a health burden index (e.g., population, GDP may be scale
   variables, not burden indicators).
8. Cluster assignment: compute a burden score (PC1 score) per country (averaged across
   years), then use k-means (k=3) or tertile-based clustering into `low_burden`,
   `middle_burden`, `high_burden`.

### 5.5 Regression Diagnostics

**Sensitivity analysis for influential cases:**
- Identify high-leverage states by Cook's distance or leverage values. Report top 3
  in descending leverage order.
- Refit the model excluding the most influential states and check if:
  - `stable`: coefficient magnitude changes <20%, significance unchanged
  - `sign_flip`: coefficient sign reverses
  - `significance_changed`: coefficient remains same sign but p crosses 0.05
  - `magnitude_shift_gt_20`: coefficient magnitude changes >20% without sign flip
- Report `sensitivity_adjusted_std_beta` and `sensitivity_p_bucket` for the refit model.

**Collinearity (VIF):**
- Compute VIF for all predictors in the fully adjusted model.
- Report `max_vif`, `max_vif_bucket`, and `max_vif_predictor` (the predictor ID with
  the highest VIF).
- The `culprit_pair`: the two predictors with the highest pairwise correlation.

**Regional clustering (ICC):**
- Fit a random-intercept model with `region` or `division` as the grouping variable.
- Report ICC = `random_intercept_variance / (random_intercept_variance + residual_variance)`.

### 5.6 Rank-Shift Analysis

For comparing crude vs. adjusted rankings:
1. Compute crude ranking: rank states by raw outcome measure.
2. Compute adjusted ranking: rank states by residuals from an income-proxy weighted
   regression (e.g., outcome regressed on income quartile means, weighted by sample size).
3. Report Spearman rank correlation between crude and adjusted rankings (3 decimal places).
4. Rank shift = crude_rank − adjusted_rank. Positive shift means the state moved up
   in the adjusted ranking (lower rank number = higher priority).
   - `top_upward_shift`: largest positive shifts (biggest rank improvement after adjustment).
   - `top_downward_shift`: largest negative shifts (biggest rank drop after adjustment).
5. Order states with equal shift values by state abbreviation ascending as tiebreaker.

### 5.7 Mediation Analysis

For the poverty → mediator → outcome pathway:
1. Path A: poverty → mediator (standardized beta, `poverty_to_mediator_beta`).
2. Path B: mediator → outcome, controlling for poverty (standardized beta,
   `mediator_to_outcome_beta`).
3. Indirect effect: Path A × Path B (A × B).
4. Bootstrap the indirect effect (e.g., 1000 resamples). Report CI bounds and
   `bootstrap_ci_enum`.
5. `indirect_effect` = the point estimate of A × B.

### 5.8 Spatial Diagnostics

- **Moran's I:** Compute on model residuals using a spatial weights matrix from
  state contiguity (neighbors table). Use row-standardized weights.
- **Isolates:** Alaska and Hawaii are spatial isolates (no contiguous neighbors).
  Assign them weight 0 in the spatial weights matrix.
- **Hotspot division:** After computing residuals, aggregate by census division.
  The division with the highest mean residual is the top residual hotspot.

---

## 6. Identifier and List Ordering Rules

### 6.1 State Abbreviations
- **Sort ascending** (alphabetically, A→Z) unless task specifies a different order.
- **`requested_states`** arrays: preserve the order given in the prompt/source_request.

### 6.2 FIPS Codes
- Always 5-digit zero-padded strings.
- Sort **lexicographically** (as strings, not numerically).
- Invalid FIPS `00000` is excluded before sorting.

### 6.3 Territory Abbreviations
- Sort ascending: `GU` < `PR` < `VI`.

### 6.4 Measure IDs
- Sort ascending (lexicographic).

### 6.5 Country Identifiers
- ISO3 codes: sort ascending (lexicographic).
- Country names: use the canonical name from the metadata table, sorted ascending.

### 6.6 Ordered Lists in Output

| Field | Ordering |
|-------|----------|
| `high_leverage_states` | Descending leverage/Cook's D |
| `culprit_pair` | Sorted ascending by predictor ID |
| `top_residual_outlier_fips` | Largest absolute residual first |
| `top_positive_residual_fips` | Largest positive residual first |
| `top_absolute_loadings` | Descending by absolute loading |
| `top_positive_loadings` | Descending by loading value |
| `priority_review_states` | Adjusted priority order (most needing review first) |
| `top_upward_shift_states` | Descending rank_shift |
| `top_downward_shift_states` | Ascending rank_shift |
| `adult_mortality_scaled_country_years` / `bmi_scaled_country_years` | Sorted ascending by iso3, then years ascending within each iso3 |
| `complete_gdp_gap_iso3` | Sorted ascending |

---

## 7. Filtering and Exclusion Habits

### 7.1 State Analysis Preprocessing Checklist

1. Download `state_health_long.csv`, `state_ses_long.csv`, `state_regions.csv`,
   `state_neighbors.csv`.
2. **Territories:** Exclude PR, GU, VI using `territory_flag = "N"` or
   `state_level_analysis_flag = "Y"`.
3. **Total strata only:** `stratum_type = "Total"` AND `stratum = "Total"`.
4. **Year:** Pick the analysis year from the task prompt (usually the latest available).
5. **Missing values:** Check for states with missing outcome or exposure in the
   analysis year (CA 2024 OBESITY, TX 2024 LIFE_EXP). List them in `excluded_states`.
6. **Stale rows:** Filter out rows with `source_note` containing "Stale". These are
   prior-year rows left in as traps.
7. **Duplicates:** Deduplicate by (year, state, measure_id, stratum_type, stratum).
   For Ohio's intentional duplicate, keep the first occurrence.
8. **State SES:** Filter `geo_fips` ending in `000`, exclude territory geo_fips.
9. **Join:** Merge health, SES, and region tables on `state` abbreviation.

### 7.2 County Analysis Preprocessing Checklist

1. Download `county_health_long.csv`, `county_ses_long.csv`, `county_metadata.csv`.
2. **Invalid FIPS:** Exclude `fips = "00000"`.
3. **State filter:** Keep only rows where `state` is in the task's requested list.
4. **Year filter:** Use the specified analysis year.
5. **Measure filter:** Select the requested measure(s) (e.g., CASTHMA, OBESITY, LPA).
6. **Pivot SES:** Convert county SES from long to wide (one row per FIPS).
7. **Join:** Health ← SES on `fips`, then ← metadata on `fips`.
8. **Complete cases:** Drop rows with any missing value in outcome, exposure, or
   SES predictors. Track exclusion counts by reason.
9. **Economic_typology:** Drop rows with `Invalid FIPS distractor` or `Old name`.
   For the old-name county (46113), if it is in the analysis and has data, use it
   under its current FIPS/name.

### 7.3 Country Analysis Preprocessing Checklist

1. Download `country_health_panel.csv`, `country_metadata.csv`,
   `country_name_variants.csv`.
2. **Name reconciliation:** Resolve variant names against the crosswalk. Use `iso3`
   as the primary join key.
3. **Metadata join:** Merge health panel with metadata on `iso3`.
4. **Scale anomaly detection:** For each indicator, flag country-years where the
   within-country value deviates >10× from its median. Specifically screen:
   - `bmi`: values in 20–30 range are normal; values >2000 are scaled (Namibia).
   - `adult_mortality`: values in 100–300 range are normal; values <30 after being
     previously >100 are anomalous (Eswatini).
   - `gdp`: all-blank for a country is a data gap (Japan), not an anomaly.
5. **Missingness:** Track missing rates per variable for the analysis window.
6. **Income group model:** Fit a random-intercept model with `income_group` as the
   grouping variable. Compare variance components to decide `mixed_model_supported`
   vs. `pooled_ols_sufficient`.
7. **PCA:** Standardize, use complete cases, report PC1 variance and loadings.

---

## 8. Model Specification Patterns

### 8.1 State-Level Bivariate → Adjusted with Diagnostics

```
Bivariate: OUTCOME ~ EXPOSURE                     (weighted by sample_size)
Adjusted:  OUTCOME ~ EXPOSURE + SES_covariates     (weighted by sample_size)
```

SES covariates: SES_measures (PCTPOVALL_2023, MEDHHINC_2023, Unemployment_rate_2023,
Percent_bachelors_or_higher_2019_23).

Diagnostics: VIF, regional ICC (region as grouping), sensitivity (remove top-3 leverage
states), attenuation calculation.

### 8.2 State-Level Income-Proxied Ranking Adjustment

```
Crude rank:    rank(OUTCOME_measure_value)
Adjusted:      OUTCOME ~ Q1 + Q2 + Q3 + Q4_income_quartile_values (weighted)
Adjusted rank: rank(residuals from adjusted model)
```

Income bracket counts: count states with non-missing values for each income quartile
(Q1, Q2, Q3, Q4). These come from `stratum_type = "Income quartile"` rows.

### 8.3 County-Level Static vs. Dynamic Model Comparison

```
Static:  OUTCOME ~ PCTPOVALL_2023 + MEDHHINC_2023 + Unemployment_rate_2023
                  + Percent_bachelors_or_higher_2019_23 + RUCC_dummies (weighted)

Dynamic: OUTCOME ~ PCTPOVALL_2023 + MEDHHINC_2023 + unemployment_change
                  + income_change + Percent_bachelors_or_higher_2019_23
                  + RUCC_dummies (weighted)
```

where:
- `unemployment_change = Unemployment_rate_2023 - Unemployment_rate_2010`
- `income_change = MEDHHINC_2023 - Median_Household_Income_2022`
- RUCC_dummies = dummy variables for RUCC codes 1–9 (reference category = 1, or use
  all 9 with intercept suppressed)

Winner selection: Compare AIC. If static AIC < dynamic AIC → `static_wins`.
If dynamic AIC < static AIC → `dynamic_wins`.

### 8.4 County Mediation Model

```
Path A: LPA ~ PCTPOVALL_2023 + SES_covariates + RUCC_dummies (dynamic spec)
Path B: OBESITY ~ LPA + PCTPOVALL_2023 + SES_covariates + RUCC_dummies (dynamic spec)
Indirect: A_poverty × B_mediator
```

Bootstrap: 1000 resamples. CI: percentile method.

### 8.5 Country Burden PCA + Mixed Model

```
PCA on: adult_mortality, bmi, alcohol, health_expenditure, immunization,
        schooling, income_composition, gdp, population, infant_mortality
(standardized, complete cases, 2015-2024)

Mixed model: burden_score ~ 1 + (1 | income_group)
Random intercept variance ratio: var(income_group) / (var(income_group) + var(residual))
```

---

## 9. Common Pitfalls

### 9.1 Territory Contamination
- **Pitfall:** Including PR, GU, VI in state-level analyses.
- **Fix:** Filter `territory_flag = "N"` or `state_level_analysis_flag = "Y"`.
  Also exclude territory rows from state SES (`geo_level = "territory"` matches).

### 9.2 Stale and Missing Rows
- **Pitfall:** Using CA 2023 OBESITY Total when 2024 is the analysis year
  (2024 is intentionally missing for CA).
- **Fix:** Always check for missing values in the target year. If missing, exclude
  the state from analysis. Do NOT substitute stale rows from prior years.

### 9.3 State SES County Distractors
- **Pitfall:** Using county-like rows (non-000 geo_fips) from `state_ses_long.csv`
  as if they were state-level values.
- **Fix:** Filter `geo_fips` to end in `000` AND `geo_level = "state"`.

### 9.4 Ohio Duplicates
- **Pitfall:** Counting duplicate rows as multiple independent observations.
- **Fix:** Deduplicate, keeping one occurrence. For INACTIVE duplicate (2021),
  drop the one marked "Intentional duplicate." For SCREEN blank-strata rows (2022),
  use only the Total row.

### 9.5 FIPS Handling
- **Pitfall:** Converting FIPS to integer (losing leading zeros) or including `00000`.
- **Fix:** Always treat FIPS as 5-digit strings. Zero-pad when necessary.
  Exclude `00000`.

### 9.6 Lending Category vs. Income Group
- **Pitfall:** Using `lending_category` as the income group for country analyses.
- **Fix:** Use `income_group` column from country metadata. `lending_category` is
  a deliberate distractor.

### 9.7 Country Name Joins
- **Pitfall:** Joining on raw country names without resolving variant forms.
- **Fix:** Match against `canonical_country` in the name variants table first, or
  use `iso3` as the join key.

### 9.8 Blank Demographic Strata
- **Pitfall:** Treating SCREEN 2022 blank `stratum_type` rows as valid age/sex strata
  for direct demographic standardization.
- **Fix:** Blank strata are not valid demographic strata. Use income quartile strata
  instead for income-proxy adjustment.

### 9.9 Missing Data in PCA/Regressions
- **Pitfall:** Including rows with partial missingness in PCA or regressions.
- **Fix:** Use listwise deletion (complete cases only). Report `rows_used` and
  `missing_rate_by_variable`.

### 9.10 Scale Anomalies in Country Data
- **Pitfall:** Namibia BMI ~2600 or Eswatini adult_mortality ~20 contaminating
  regressions and PCA.
- **Fix:** Screen each variable for within-country scale anomalies. Flag anomalous
  country-years in the anomaly log. Exclude or flag in `final_readiness`.

### 9.11 Standardized vs. Raw Coefficients
- **Pitfall:** Reporting raw/unstandardized betas when the template expects
  standardized betas.
- **Fix:** Always standardize (z-score) both outcome and predictors before fitting,
  or compute standardized betas from raw coefficients: β_std = β_raw × (σ_x / σ_y).

### 9.12 Weighting
- **Pitfall:** Running unweighted regressions when sample_size or population weights
  are available.
- **Fix:** Use `sample_size` as weights for state models, `population` for county models.

---

## 10. Quick-Reference: Common Task Patterns

### Pattern A: Confounding Audit (State)
Analyze whether an exposure-outcome relationship survives SES adjustment:
1. Select `Total` strata for both measures, analysis year, exclude territories.
2. Exclude states with missing exposure or outcome in analysis year.
3. Fit bivariate model (exposure → outcome), get standardized beta and p-value.
4. Fit adjusted model (exposure + SES → outcome), get standardized beta and p-value.
5. Compute attenuation = (biv − adj) / biv × 100.
6. Run VIF on adjusted model, identify max VIF predictor and culprit pair.
7. Fit random-intercept model by region/division, compute ICC.
8. Remove top-3 leverage states, refit adjusted model, classify sensitivity.

### Pattern B: Ranking Adjustment (State)
Audit whether crude rankings are distorted by income:
1. Get crude outcome values for Total strata, analysis year, 50 states + DC.
2. Get income quartile values (Q1–Q4) for each state from health data.
3. Fit weighted regression: outcome ~ Q1 + Q2 + Q3 + Q4 (or income proxy).
4. Rank residuals (adjusted rank) vs. crude rank.
5. Report Spearman correlation, top shift states, weighted model direction.

### Pattern C: County Model Selection
Compare static and dynamic SES specifications by AIC:
1. Filter to requested states, analysis year, target measure.
2. Pivot SES to wide, join with health and metadata.
3. Exclude invalid FIPS, incomplete cases.
4. Fit static model, record AIC.
5. Fit dynamic model (with change variables), record AIC.
6. Compare, report residual outliers, unemployment-change tercile means.

### Pattern D: County Mediation
Audit a mediation pathway with bootstrap CI:
1. Same data prep as Pattern C for requested states, add NC.
2. Fit Path A and Path B, compute indirect effect.
3. Bootstrap (1000 draws) the indirect effect.
4. Compute Moran's I on residuals.
5. Flag top positive residual counties.

### Pattern E: Country Burden Audit
Audit a multi-country panel for PCA burden scores and anomalies:
1. Screen each variable for scale anomalies per country.
2. Resolve name variants, join metadata.
3. Select retained variables, exclude rows with missing values.
4. Standardize, run PCA, report PC1 stats.
5. Compute burden score (PC1), cluster into 3 groups.
6. Test random-intercept model by income_group, classify variance.

---

## 11. Task Execution Order

When given an audit task:
1. Read `environment_access.md` for the base URL.
2. Read `answer_template.json` to understand the expected output schema.
3. Read `source_request.txt` for task-specific hints (requested states, measures, issues).
4. Download all relevant CSVs from the portal's `/data/` directory.
5. Apply the preprocessing checklist for the data level (state/county/country).
6. Execute the model/analysis pattern that matches the task.
7. Format output to exactly match the answer template JSON structure.
8. Double-check rounding, bucket rules, and sort order.
