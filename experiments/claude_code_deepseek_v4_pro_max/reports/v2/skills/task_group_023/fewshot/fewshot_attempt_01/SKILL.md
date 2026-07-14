# Public Health Evidence Portal — Audit Skill

Transferable SOPs for state, county, and country statistical data audits using the
shared Public Health Evidence Portal at `GDPEVO_ENV_BASE_URL`.

## 1. Data Acquisition Workflow

1. **Always start from the portal home page** (`GET /`) to confirm the available
   pages and CSV downloads. The portal is a static HTML site with linked `.csv`
   files served from `/data/`.
2. **Download CSVs directly** — every table in the portal has a corresponding
   downloadable CSV. Never scrape rendered HTML tables; use the CSV files.
3. **CSV encoding**: standard comma-separated with quoted fields. Use a proper
   CSV parser (Python `csv.DictReader`, R `read.csv`, pandas `read_csv`).
4. **CSV row counts** (as documented in `/pages/methodology.html`):
   - `state_health_long.csv`: 29,161 rows
   - `state_life_expectancy.csv`: 4,859 rows
   - `state_ses_long.csv`: 972 rows
   - `state_regions.csv`: 54 rows (50 states + DC + 3 territories)
   - `county_health_long.csv`: 40,108 rows
   - `county_ses_long.csv`: 7,536 rows
   - `county_metadata.csv`: 631 rows
   - `state_neighbors.csv`: 51 rows
   - `country_health_panel.csv`: 1,090 rows
   - `country_metadata.csv`: 109 rows
   - `country_name_variants.csv`: 14 rows

## 2. State-Level Analysis Conventions

### 2.1 Territory Exclusion

Three entities are territories, NOT states, and must be excluded from all
state-level analyses unless the task explicitly asks for them:

| Abbrev | Name | FIPS |
|--------|------|------|
| PR | Puerto Rico | 72 |
| GU | Guam | 66 |
| VI | U.S. Virgin Islands | 78 |

**How to detect**: filter `state_level_analysis_flag = 'Y'` in `state_regions.csv`,
or filter `territory_flag = 'N'` in `state_health_long.csv`. In `state_ses_long.csv`,
filter `geo_level = 'state'` (excludes `territory` and `county-like distractor`).

### 2.2 Valid States

After excluding territories, the valid analysis set consists of **50 states
plus DC** (51 entities). DC (District of Columbia) is NOT a territory; it is
included in state-level analyses with `state_level_analysis_flag = 'Y'`.

### 2.3 Strata Filtering — The "Total" Rule

Every health measure in `state_health_long.csv` has rows for multiple strata:

| stratum_type | Example stratum values |
|---|---|
| Total | Total |
| Age | 18-44, 45-64, 65+ |
| Sex | Female, Male |
| Income quartile | Q1 lowest, Q2, Q3, Q4 highest |
| Race/ethnicity | American Indian or Alaska Native, Asian, Black, Hispanic, White |

**For between-state comparisons or regressions**, always filter to
`stratum_type = 'Total'` AND `stratum = 'Total'`. These rows represent the
whole-population estimate. Using non-Total strata without justification
introduces demographic confounding.

### 2.4 Known Missing Data

- **California 2024 Total OBESITY** is intentionally absent from
  `state_health_long.csv`. When this measure-year is needed, CA must be
  excluded from the analytic sample.
- **Texas 2024 Total LIFE_EXP** is similarly absent.
- One Ohio stratified row is duplicated — deduplicate before summarizing.
- **Stale 2023 Total rows** may remain alongside 2024 rows. Always filter by
  the requested analysis year; do not average across years without explicit
  instruction.

### 2.5 SES Table Filtering

`state_ses_long.csv` is a long-format Attribute-Value table with mixed geo_levels:

| geo_level | FIPS pattern | Purpose |
|---|---|---|
| state | Ends in `000` (e.g., `01000`) | True state rows |
| county-like distractor | Does NOT end in `000` | Ignore for state analyses |
| territory | Separate rows | Ignore for state analyses |

**How to filter**: `geo_level = 'state'` (most reliable) AND optionally
`geo_fips` ending in `000`.

State SES attributes available:
- `PCTPOVALL_2023` — Percent in poverty, all ages (percent)
- `MEDHHINC_2023` — Median household income, 2023 (dollars)
- `Unemployment_rate_2023` — Unemployment rate (percent)
- `Percent_bachelors_or_higher_2019_23` — Educational attainment (percent)
- `POP_ESTIMATE_2023` — Population estimate (persons)
- `R_NET_MIG_2023` — Net migration rate (per 1,000)

### 2.6 Region Lookup

`state_regions.csv` provides census-like region and division for each state:

| Column | Description |
|---|---|
| state_fips | 2-digit state FIPS |
| state | 2-letter abbreviation |
| state_name | Full name |
| region | Census region (Northeast, Midwest, South, West) |
| division | Census division (9 total) |
| state_level_analysis_flag | Y for valid states, N for territories |

Use `state_regions.csv` for:
- Regional clustering ICC computation (random-intercept by division or region)
- Identifying regional confounders
- Grouping states for residual diagnostics

## 3. County-Level Analysis Conventions

### 3.1 Available States

County data is NOT available for all 50 states. `county_health_long.csv`
covers 27 states: AK, AL, AZ, CA, CO, FL, GA, HI, IL, KY, LA, MA, MI, MN,
MS, NC, NY, OH, OR, PA, SD, TN, TX, VA, WA, WI, WV.

When a task requests counties from specific states, verify those states exist
in the county files before proceeding.

### 3.2 County Health Measures

All county health measures are in long format in `county_health_long.csv`:

| Column | Description |
|---|---|
| year | 2021–2024 |
| fips | 5-digit county FIPS (string, zero-padded) |
| state | 2-letter abbreviation |
| county | County name |
| measure_id | Short code (CASTHMA, OBESITY, DIABETES, etc.) |
| measure | Human-readable label |
| category | Health outcomes / Health risk behaviors / Health status / Prevention |
| data_value_type | Age-adjusted prevalence |
| data_value | The estimate |
| low_confidence_limit / high_confidence_limit | CI bounds |
| population | County population (may be blank for some rows) |

Measure IDs:
- `CASTHMA` — Current asthma among adults
- `OBESITY` — Obesity among adults
- `DIABETES` — Diagnosed diabetes among adults
- `DEPRESSION` — Depression among adults
- `CHD` — Coronary heart disease among adults
- `LPA` — No leisure-time physical activity
- `GHLTH` — Fair or poor self-rated health
- `CSMOKING` — Current smoking among adults
- `SLEEP` — Short sleep duration among adults
- `BINGE` — Binge drinking among adults
- `MAMMOUSE` — Mammography use among eligible women
- `BPMED` — Taking blood pressure medication
- `CHECKUP` — Annual checkup
- `COREM` / `COREW` — Core preventive services (men/women)
- `DENTAL` — Dental visit

### 3.3 County SES Data

`county_ses_long.csv` — long-format Attribute-Value table keyed by 5-digit FIPS:

Attributes include:
- `PCTPOVALL_2023` — Percent poverty
- `MEDHHINC_2023` — Median household income 2023
- `Median_Household_Income_2022` — Prior year income
- `Unemployment_rate_2010` — Long-ago unemployment
- `Unemployment_rate_2023` — Recent unemployment
- `Percent_bachelors_or_higher_2019_23` — Education
- `POP_ESTIMATE_2023` — Population
- `CENSUS_2020_POP` — Decennial census population
- `R_NET_MIG_2023` — Net migration
- `R_NATURAL_CHG_2023` — Natural population change
- `RUCC_2023` — Rural-Urban Continuum Code
- `Economic_typology_2015` — Economic typology category

### 3.4 County Metadata

`county_metadata.csv` provides:
- `rucc_code` — RUCC code (1–9)
- `economic_typology` — Category string
- `census_division` — Census division name (9 divisions)
- `metadata_note` — Flags invalid FIPS, old county names

### 3.5 County Exclusion Rules

Apply in this order when constructing a county analytic dataset:

1. **Invalid FIPS**: `fips = '00000'` (state `ZZ`). Always exclude.
2. **Outside requested states**: Keep only counties whose `state` abbreviation
   appears in the prompt's requested-state list.
3. **Missing SES data**: A county FIPS present in `county_health_long.csv` but
   missing one or more required SES attributes after the pivot/join.
4. **Missing health data**: A county FIPS with no value for the outcome
   measure_id in the analysis year.

Track counts for each exclusion reason separately.

### 3.6 SES Pivot (Attribute-Value → Wide)

County SES starts in long format. Pivot so each attribute becomes a column,
keyed by `fips`. This produces one row per county.

### 3.7 RUCC Handling

RUCC codes (1–9) are always treated as **categorical dummies**, not as a
continuous numeric variable. Do not include RUCC as a linear predictor.

### 3.8 Income Change Variable

When the analysis calls for a "dynamic" or change specification, compute:

```
income_change = MEDHHINC_2023 − Median_Household_Income_2022
```

This is always computed as `MEDHHINC_2023` minus `Median_Household_Income_2022`
(never the reverse).

For unemployment change (when used):
```
unemp_change = Unemployment_rate_2023 − Unemployment_rate_2010
```

A "static" model uses only concurrent (2023) values. A "dynamic" model adds
the change variables on top of the static specification.

### 3.9 FIPS Format

Always use 5-digit zero-padded strings for county FIPS codes (e.g., `"01001"`,
not `1001` or `"1001"`).

### 3.10 Spatial Neighbors and Isolates

`state_neighbors.csv` lists each state's contiguous neighbors. Alaska (AK) and
Hawaii (HI) are isolates (`isolate_flag = 'Y'`, `neighbor_count = 0`).

For county-level spatial analysis (Moran's I on residuals):
- Build a spatial weights matrix from shared-border adjacency within the
  universe of counties in the analytic sample.
- Isolate states contain counties with no within-sample neighbors from other
  states. Count isolate states separately.
- Census division labels come from `county_metadata.csv` (`census_division`
  field).

## 4. Country-Level Analysis Conventions

### 4.1 Country Health Panel

`country_health_panel.csv` covers 109 unique ISO3 codes across 2015–2024
(10 years, 1,090 rows). Columns:

| Column | Description |
|---|---|
| country | Canonical country name |
| iso3 | ISO 3166-1 alpha-3 code |
| year | 2015–2024 |
| life_expectancy | Years |
| adult_mortality | Per 100,000 (or scaled proxy) |
| bmi | Mean BMI |
| alcohol | Alcohol consumption |
| health_expenditure | % of GDP |
| immunization | Coverage % |
| schooling | Years |
| income_composition | Index (0–1 scale) |
| gdp | Per capita (USD or proxy) |
| population | Total persons |
| infant_mortality | Per 1,000 live births |
| missingness_note | Flags for known data gaps |

### 4.2 Country Metadata

`country_metadata.csv` (109 rows) provides:

| Column | Description |
|---|---|
| country | Canonical name (joins to panel) |
| iso3 | ISO3 code (joins to panel) |
| region | World Bank-like region name |
| income_group | Low income / Lower middle income / Upper middle income / High income |
| lending_category | IDA / IBRD / Blend / Not classified — a distractor field |

**Important**: `lending_category` is explicitly a distractor. Do not use it
in place of `income_group`. The four `income_group` values are the grouping
variable for mixed-model random intercepts.

### 4.3 Name Reconciliation

`country_name_variants.csv` (14 rows) maps alternate names to canonical names:

| Column | Description |
|---|---|
| canonical_country | Name as it appears in the panel and metadata |
| variant_name | Alternate name seen in external sources |
| iso3 | ISO3 code |
| reconciliation_note | Description of the variant |

Key variants include: United States ↔ United States of America, Cote d'Ivoire
↔ Ivory Coast, Bolivia ↔ Bolivia (Plurinational State of), Czechia ↔ Czech
Republic, Eswatini ↔ Swaziland, Turkiye ↔ Turkey, Korea Rep. ↔ South Korea,
Viet Nam ↔ Vietnam, etc.

**Workflow**: When joining external country data to the panel, try direct
name match first, then resolve unmatched rows through this crosswalk. Count
resolved vs. unresolved variant rows.

### 4.4 Known Anomalies

The portal documents known anomalies that must be detected and logged:

- **Scaled BMI**: Namibia (NAM) 2018–2021 — BMI values are on a different
  scale from the rest of the series.
- **Adult mortality scale drop**: Eswatini/Swaziland (SWZ) 2021–2024 — a
  ≈10× drop in adult_mortality values.
- **Complete GDP gap**: Japan (JPN) — all GDP values are missing across all
  years in the panel.

**Detection approach**: For each variable, compute country-level z-scores or
look for discrete jumps in the series. A scale anomaly is a sustained shift
across multiple years (not a single-year outlier).

### 4.5 PCA — Burden Score Construction

PCA is run on the country-year panel after centering/scaling variables. The
retained variable set is typically:

```
adult_mortality, bmi, alcohol, health_expenditure, immunization,
schooling, income_composition, gdp, population, infant_mortality
```

(10 variables; `life_expectancy` is excluded as it is the outcome being
predicted by the burden score.)

**Pre-PCA prep**:
1. Filter to the analysis year range (e.g., 2015–2024).
2. Drop rows where any retained variable is missing (complete-case PCA).
3. Standardize each variable (z-score: subtract mean, divide by SD).
4. Fit PCA, extract PC1 loadings and variance share.

**Post-PCA**:
- Cluster rows into 3 equal-frequency terciles by PC1 score: low_burden,
  middle_burden, high_burden.
- Report PC1 variance share, variable count, rows_used, missing rates per
  variable.

### 4.6 Mixed Model vs. Pooled OLS

To decide whether income-group structure matters:
- Fit a mixed-effects model with a random intercept for `income_group`.
- Compare to pooled OLS via a likelihood-ratio test or compare
  random-intercept variance to residual variance.
- **random_intercept_variance_ratio**: the ratio of random-intercept variance
  to residual variance. High ratios (>0.5) support mixed models.
- **lr_decision**: `mixed_model_supported` if the grouped structure improves
  fit; `pooled_ols_sufficient` otherwise.

## 5. Statistical Conventions

### 5.1 Rounding Rules

| Statistic | Decimal places | Example |
|---|---|---|
| Standardized beta | 3 | 0.778 |
| VIF | 2 | 2.66 |
| Regional ICC | 3 | 0.173 |
| Attenuation % | 1 | 3.6 |
| Spearman ρ | 3 | 0.350 |
| AIC | 2 | 252.13 |
| PC1 variance share | 3 | 0.717 |
| Missing rate | 3 | 0.009 |
| Bootstrap CI bounds | 3 | -0.068 |
| Indirect effect | 3 | -0.010 |
| Moran's I | 3 | -0.170 |
| Tercile means | 2 | 12.16 |
| Join/metadata coverage | 3 | 1.000 |

### 5.2 p-value Buckets

Always report p-values as a bucket, never as a raw number:

| Bucket | Meaning |
|---|---|
| `lt_0_001` | p < 0.001 |
| `lt_0_01` | 0.001 ≤ p < 0.01 |
| `lt_0_05` | 0.01 ≤ p < 0.05 |
| `ge_0_05` | p ≥ 0.05 |
| `not_computed` | No test was run |

### 5.3 VIF Buckets

| Bucket | Range |
|---|---|
| `lt_5` | VIF < 5 |
| `5_to_10` | 5 ≤ VIF < 10 |
| `ge_10` | VIF ≥ 10 |

### 5.4 ICC / Moran's I Buckets

| Bucket | Range |
|---|---|
| `lt_0_05` | Value < 0.05 |
| `0_05_to_0_15` | 0.05 ≤ value < 0.15 |
| `ge_0_15` | Value ≥ 0.15 |

For Moran's I, note that the value can be negative; negative values fall into
`lt_0_05`.

### 5.5 Coefficient Signs

Report coefficient signs as one of: `positive`, `negative`, `near_zero`.

"near_zero" is used when the coefficient magnitude is very small relative to
its standard error (typically |t| < ~0.5 or when the sign is ambiguous).

### 5.6 Conclusion / Verdict Enums

**Confounding conclusions** (state-level regression):
- `supported_after_adjustment` — exposure remains significant with meaningful
  effect after SES adjustment
- `partly_confounded` — effect attenuates substantially but remains
  significant
- `not_primary_after_adjustment` — exposure is no longer the dominant
  predictor after adjustment

**Sensitivity verdicts**:
- `stable` — effect direction and significance unchanged
- `sign_flip` — coefficient sign changes
- `significance_changed` — crosses a significance threshold
- `magnitude_shift_gt_20` — standardized beta changes by >20%

**Ranking action labels**:
- `review_income_adjusted_rank_shifts` — rankings change meaningfully after
  income adjustment
- `crude_ranking_stable` — rankings are robust to adjustment

**County model reconciliation**:
- `static_wins` — static (concurrent-only) model is preferred by AIC
- `dynamic_wins` — dynamic (change-variable) model is preferred
- `dynamic_changes_mixed_by_outcome` — winner varies by outcome

**Spatial action labels**:
- `review_spatial_context` — residual spatial structure warrants investigation
- `socioeconomic_model_sufficient` — no residual spatial pattern beyond what
  SES captures

**Country readiness**:
- `ready_with_anomaly_log` — data can be used with anomalies documented
- `ready_without_flags` — no material anomalies detected

### 5.7 Attenuation Calculation

```
attenuation_pct = ((bivariate_beta − adjusted_beta) / bivariate_beta) × 100
```

Use absolute values if both betas have the same sign; if signs differ, report
the direction explicitly.

### 5.8 Bootstrap Indirect Effect

For mediation: bootstrap the indirect effect (exposure → mediator × mediator →
outcome) with N replications (e.g., 1000). Report:
- Point estimate (indirect_effect) rounded to 3 decimals
- CI low and high rounded to 3 decimals
- CI enum: `positive_excludes_zero`, `negative_excludes_zero`, `includes_zero`

### 5.9 Moran's I on Residuals

- Extract residuals from the fitted county-level model.
- Build a spatial weights matrix (row-standardized contiguity).
- Compute Moran's I.
- Identify the census division with the most extreme positive residual cluster
  (hotspot division name from `county_metadata.csv`).

## 6. Identifier and List Ordering Rules

### 6.1 State Abbreviations

- Always use 2-letter uppercase postal abbreviations (AL, AK, …, WY).
- DC is included as a "state" in state-level analyses.
- **Sort states in ascending alphabetical order** by abbreviation when
  producing `included_states` and `excluded_states` arrays.
- **Exception**: `requested_states` lists must preserve the **exact order**
  given in the task prompt.

### 6.2 Territory Abbreviations

Sorted ascending: GU, PR, VI.

### 6.3 County FIPS

- 5-digit zero-padded strings, sorted numerically (as strings "01001" <
  "01002").
- When reporting top residual outlier FIPS, order by residual magnitude
  (largest positive residual first), not by FIPS.

### 6.4 Predictor IDs

- Sorted ascending alphabetically when listed together (e.g., culprit pairs,
  variable lists).
- For PCA loadings: report top N by absolute loading descending for
  `top_absolute_loadings`, and by loading descending (signed) for
  `top_positive_loadings`.

### 6.5 Rank Shift Ordering

- `top_upward_shift_states`: order by rank_shift **descending** (states whose
  rank improved most after adjustment first).
- `top_downward_shift_states`: order by rank_shift **ascending** (states whose
  rank dropped most after adjustment first).
- `priority_review_states`: order by adjusted priority (worst adjusted value
  first when lower_value_worse, best adjusted value first when
  higher_value_worse).

### 6.6 High-Leverage States

Report **3 state abbreviations in leverage order** (highest leverage first).

## 7. Priority Direction Conventions

For health measures, know which direction is "worse":

| Measure | Worse direction | Rationale |
|---|---|---|
| OBESITY | higher_value_worse | Higher prevalence |
| DIAB_MORT | higher_value_worse | Higher mortality |
| SCREEN | lower_value_worse | Lower screening uptake is worse |
| CASTHMA | higher_value_worse | Higher asthma prevalence |
| LPA | higher_value_worse | More inactivity is worse |
| LIFE_EXP | lower_value_worse | Lower life expectancy is worse |

When a new measure appears, determine direction from context: prevalence and
mortality measures are typically `higher_value_worse`; screening, vaccination,
and life expectancy are typically `lower_value_worse`.

## 8. Common Pitfalls and Traps

### Portal Traps

1. **Territories in state data**: PR, GU, VI appear in state CSV files with
   valid-looking data. Always filter them out for state-level analyses unless
   the task explicitly includes them.

2. **County-like distractors in state_ses_long.csv**: Rows with `geo_level =
   'county-like distractor'` have FIPS codes that do NOT end in `000`. They
   look like real county data but belong to no actual county. Filter by
   `geo_level = 'state'`.

3. **Stale year rows**: `state_health_long.csv` may contain rows for multiple
   years. Always filter to the analysis year specified in the prompt. Do not
   average across years without instruction.

4. **Blank demographic strata**: Some rows in `state_health_long.csv` may have
   blank `stratum` or `stratum_type` values. These are NOT valid
   demographic-stratified estimates and indicate that direct standardization
   is not feasible.

5. **Invalid FIPS in county data**: `fips = '00000'` with `state = 'ZZ'` is
   an intentional invalid row. Always exclude it.

6. **Old county names**: Some `county_metadata.csv` rows have notes about old
   county names. Join by FIPS, not by county name.

7. **Duplicate rows**: One Ohio stratified row in `state_health_long.csv` is
   duplicated. Deduplicate before computing aggregates.

8. **Lending category vs. income group**: `country_metadata.csv` has both
   `income_group` and `lending_category`. The latter is a distractor. Always
   use `income_group` for grouped models.

### Statistical Traps

9. **Collinearity**: SES predictors (especially `MEDHHINC_2023` and
   `PCTPOVALL_2023`) are often highly correlated. Always compute VIF after
   fitting the full model. The culprit pair is the two predictors with the
   highest pairwise correlation.

10. **Regional ICC**: When computing ICC from a random-intercept model by
    census division or region, the ICC is `var_intercept / (var_intercept +
    var_residual)`, NOT `var_intercept / var_residual`.

11. **Sensitivity check**: Re-fit the model excluding high-leverage states
    (top 3 by Cook's distance or leverage). Compare the exposure standardized
    beta before and after exclusion. If the sign flips or the beta changes
    substantially, the result is sensitive.

12. **Attenuation direction**: Attenuation = bivariate beta minus adjusted
    beta, expressed as a percentage of the bivariate beta. If the adjusted
    beta is larger than the bivariate beta, attenuation is negative (a
    suppression effect, not attenuation).

13. **Moran's I can be negative**: A negative Moran's I (e.g., −0.17) means
    spatial dispersion (checkerboard pattern). It correctly buckets into
    `lt_0_05`.

14. **Bootstrap CI crossing zero**: When the indirect effect bootstrap CI
    includes zero, the mediation is not statistically supported, regardless
    of the point estimate's sign.

15. **Sample size weighted rows**: When counting income-bracket coverage,
    count the number of state-level rows (one per state per bracket), not
    the underlying survey sample sizes.

### Join Traps

16. **State SES join**: Join `state_health_long.csv` to `state_ses_long.csv`
    by `state` abbreviation (both files have this column). Validate that
    exactly 51 rows result for a Total-stratum single-year extract.

17. **County join chain**: health (fips) → SES (fips) → metadata (fips). The
    health CSV and SES CSV use the same 5-digit FIPS codes. Metadata may
    include rows not in the health or SES files.

18. **Country join**: Health panel joins to metadata by `iso3` (preferred) or
    by `country` (canonical name). The name variants table maps non-canonical
    names to canonical names and ISO3 codes. Always resolve names before
    computing join coverage.

## 9. Debug Checklist

When a result seems wrong, verify:

- [ ] Territories (PR, GU, VI) excluded
- [ ] Correct analysis year filtered
- [ ] Total stratum only (stratum_type=Total, stratum=Total)
- [ ] SES geo_level=state (not county-like distractor or territory)
- [ ] Invalid FIPS (00000) excluded
- [ ] Missing health data flagged and counted
- [ ] Missing SES data flagged and counted
- [ ] RUCC treated as categorical, not continuous
- [ ] Income change computed as 2023 minus 2022 (never reversed)
- [ ] Rounding matches the convention table
- [ ] p-values reported as buckets, not raw numbers
- [ ] State lists sorted ascending unless prompt order is required
- [ ] FIPS codes are 5-digit zero-padded strings
- [ ] Lending category not confused with income group
- [ ] Country name variants resolved before join coverage calculation
