# Public Health Statistical Data Audit — Transferable Workflow

This skill covers state-level, county-level, and country-level public-health
statistical audits using the Public Health Evidence Portal.  The portal serves
long-format CSV downloads for health measures, socioeconomic covariates,
regional metadata, and reference lookups.

---

## 1. Data-Download and Assembly Workflow

1. **Fetch all CSVs needed for a task** from the portal's `/data/` directory.
   Use the `environment_access.md`-supplied base URL.  Never assume localhost
   or `env/setup.sh`.

2. **State-level health** → `/data/state_health_long.csv`.  Long-format;
   columns include `year`, `state_fips`, `state`, `territory_flag`,
   `measure_id`, `stratum_type`, `stratum`, `sample_size`, `data_value`.

3. **State-level SES** → `/data/state_ses_long.csv`.  Also long-format.
   **Critical**: state rows have `geo_fips` ending in `000` and
   `geo_level = "state"`.  County-like distractor rows (`geo_fips` not
   ending in `000`) are mixed into the same file.  Filter strictly to
   `geo_level == "state"` before joining.

4. **County-level health** → `/data/county_health_long.csv`.  Contains FIPS,
   measure IDs, data values, populations, and confidence limits.

5. **County-level SES** → `/data/county_ses_long.csv`.  Attributes include
   `PCTPOVALL_2023`, `MEDHHINC_2023`, `Median_Household_Income_2022`,
   `Unemployment_rate_2023`, `Unemployment_rate_2010`,
   `Percent_bachelors_or_higher_2019_23`, `RUCC_2023`, and others.
   `Economic_typology_2015` is a string field — guard against float coercion.

6. **County metadata** → `/data/county_metadata.csv`.  Contains `rucc_code`,
   `economic_typology`, `census_division`.

7. **Country health panel** → `/data/country_health_panel.csv`.  2015–2024
   annual panel with 10 core indicators per country.

8. **Country metadata** → `/data/country_metadata.csv`.  Contains
   `income_group`, `region`, `lending_category`.

9. **Country name variants** → `/data/country_name_variants.csv`.  Maps
   variant names to canonical `iso3` codes.

10. **State regions** → `/data/state_regions.csv`.  Census region and
    division for each state; includes a `state_level_analysis_flag`.

11. **State neighbors** → `/data/state_neighbors.csv`.  Neighbor lists,
    `neighbor_count`, and `isolate_flag` (Y/N).  Use `isolate_flag == "Y"`
    to count isolate states in spatial summaries.

---

## 2. State-Level Analysis Conventions

### Stratum Filtering

- For a **Total estimate**, filter to `stratum_type == "Total"` AND
  `stratum == "Total"` (both conditions).
- Do NOT mix Total rows with age, sex, income-quartile, or race/ethnicity
  strata unless the task explicitly requests stratified estimates.

### Territory Handling

- Rows with `territory_flag == "Y"` represent territories (GU, PR, VI).
  Exclude them from state-level models.  List them in
  `territories_excluded`, sorted ascending by abbreviation.
- **Include DC**: DC has `territory_flag == "N"` and
  `state_level_analysis_flag == "Y"`.  It is a valid state-level unit.

### Measure IDs from the Portal

Common state-level measure IDs (use exactly as found in the CSV):
- `OBESITY` — Adult obesity prevalence (Risk factor)
- `DIAB_MORT` — Diabetes mortality rate (Mortality)
- `SCREEN` — Preventive screening prevalence (Prevention)
- `INACTIVE` — Physical inactivity prevalence (Risk factor)
- `LIFE_EXP` — Life expectancy

### SES Attribute IDs

State SES attributes to use as covariates (exact names):
- `PCTPOVALL_2023` — Percent in poverty, all ages
- `MEDHHINC_2023` — Median household income, 2023
- `Unemployment_rate_2023` — Unemployment rate, 2023
- `Percent_bachelors_or_higher_2019_23` — Bachelor's degree or higher
- `POP_ESTIMATE_2023` — Population estimate, 2023
- `R_NET_MIG_2023` — Net migration rate, 2023

### Analysis Year

Use the most recent available year (2024 for state-level tasks, unless the
task text specifies a different year).  The data span 2019–2024 for state
measures.

### Rank-Shift Conventions

- **Priority direction**: for screening/prevention measures, **lower value =
  worse** (`lower_value_worse`).  States with the lowest adjusted values get
  priority review.
- **Rank shift sign**: `crude_rank - adjusted_rank`.  Positive = state was
  ranked worse in crude (needs more priority after adjustment).  Negative =
  state was ranked worse in the adjusted measure (needs less priority).
- **Spearman rank correlation** between crude and adjusted rankings helps
  determine whether rank shifts are substantial.

### Demographic Standardisation Feasibility

When checking whether direct demographic standardisation is supported, inspect
the available `stratum_type` values for the target measure/year.  If age and
sex strata exist but have blank/empty labels in BOTH `stratum_type` and
`stratum` columns, the feasibility is **`not_feasible_blank_demographic_strata`**
— treat blank demographic labels as invalid, not as usable strata.

### Model Diagnostics

- **VIF** is computed from the correlation matrix of predictors (excluding
  intercept).  Bucket boundaries: `< 5` (`lt_5`), `5–10` (`5_to_10`),
  `≥ 10` (`ge_10`).
- **Culprit pair**: the two predictors with the highest absolute Pearson
  correlation, sorted ascending alphabetically.
- **High-leverage states**: top 3 states by hat-matrix diagonal, ordered by
  leverage descending.  Report as state abbreviations (e.g. `["WV","RI","OR"]`).
- **Regional ICC**: compute from model residuals grouped by census division.
  Use `(MSB − MSW) / (MSB + (k_avg − 1) × MSW)`.  Bucket boundaries:
  `< 0.05` (`lt_0_05`), `0.05–0.15` (`0_05_to_0_15`), `≥ 0.15` (`ge_0_15`).

### Sensitivity Analysis

- Re-fit the adjusted model after removing the top-3 leverage states.
- **Verdict logic** (checked in order):
  1. If sign flips → `sign_flip`
  2. If original p < 0.05 and sensitivity p ≥ 0.05 → `significance_changed`
  3. If `|sensitivity beta − original beta| / |original beta| > 0.20` → `magnitude_shift_gt_20`
  4. Otherwise → `stable`

### Attenuation

- `attenuation_pct = ((bivariate_std_beta − adjusted_std_beta) / bivariate_std_beta) × 100`, rounded to 1 decimal.
- **Conclusion logic**:
  - `supported_after_adjustment`: adjusted p < 0.01 and attenuation < 25%
  - `partly_confounded`: adjusted p < 0.05 and attenuation < 50%
  - `not_primary_after_adjustment`: otherwise

### Income-Proxy Adjusted Rankings

1. Extract the **Total** stratum value for each state (crude rate).
2. Extract the **Income quartile** strata (`Q1 lowest`, `Q2`, `Q3`,
   `Q4 highest`) with their sample sizes.
3. Compute the **sample-size-weighted average** across the four income
   brackets: `Σ(w_i × v_i) / Σ(w_i)`.
4. Rank states by crude and adjusted values separately.
5. `income_proxy_bracket_counts` reports the number of states with valid
   data for each bracket (Q1, Q2, Q3, Q4).
6. `sample_size_weighted_rows` is the total number of income-quartile rows
   used (typically `4 × N_states`).

---

## 3. County-Level Analysis Conventions

### FIPS Validation

- Valid county FIPS are exactly 5 digits (`len == 5` and `.isdigit()`).
  Rows with other formats are counted in `invalid_fips` exclusions and
  discarded.

### County-State Filtering

- Extract health rows whose `state` abbreviation is in the requested list.
- Join to SES data and metadata by 5-digit FIPS.

### Exclusion Categories (count every record, not just unique counties)

- `invalid_fips`: rows where `len(fips) != 5` or non-numeric
- `outside_requested_states`: rows with valid FIPS whose state is not in the
  requested list
- `missing_ses`: counties in requested states with health data but incomplete
  or missing SES attributes
- `missing_health_data`: counties in requested states with SES data but
  missing the target health measure

### Static vs Dynamic SES Models

- **Static model**: intercept + poverty + income_2023 + unemployment_2023 +
  bachelors + RUCC dummies (excluding first category as reference)
- **Dynamic model**: static covariates + `income_change` +
  `unemployment_change`
  - `income_change = MEDHHINC_2023 − Median_Household_Income_2022`
  - `unemployment_change = Unemployment_rate_2023 − Unemployment_rate_2010`
  - Answer template rule: `MEDHHINC_2023_minus_Median_Household_Income_2022`
  - Combined rule: `unemployment_2023_minus_2010_and_income_2023_minus_2022`
- **RUCC handling**: always `categorical_dummies` — include dummy variables
  for all RUCC codes except the lowest as the reference category
- **Winner selection**: compare AIC (`n × ln(RSS/n) + 2k`).  Lower AIC wins.
  If within 2 units, still report the lower one.

### Residual Outliers

- `top_residual_outlier_fips`: 5 FIPS strings with the largest **absolute**
  residual values, ordered by absolute residual descending (most extreme first)
- `shared_residual_outlier_fips`: when only one outcome exists, identical to
  the single-outcome top residuals.  When multiple outcomes, use the FIPS
  appearing in all outcome-specific top-5 sets.

### Unemployment Change Tercile Means

- Split counties into three equal-sized groups by `unemployment_change`;
  report the mean outcome value (CASTHMA/OBESITY) within each tercile,
  rounded to 2 decimals.

### Mediation Models (County-Level)

**Model specification** (include RUCC dummies in all equations):
- **Path A** (poverty → mediator):
  `LPA ~ poverty + income2023 + unemp2023 + bachelors + income_change + unemp_change + RUCC_dummies`
- **Path B** (mediator → outcome, controlling for poverty):
  `OBESITY ~ LPA + poverty + income2023 + unemp2023 + bachelors + income_change + unemp_change + RUCC_dummies`
- **Indirect effect** = `β_poverty(A) × β_LPA(B)`

**Bootstrap** (1 000 resamples with replacement, fixed seed):
- Extract 2.5th and 97.5th percentiles for the 95% CI
- `positive_excludes_zero`: CI entirely above 0
- `negative_excludes_zero`: CI entirely below 0
- `includes_zero`: CI crosses 0

**Action label**:
- `socioeconomic_model_sufficient` if the indirect effect is near zero or the
  bootstrap CI includes zero
- `review_spatial_context` if the mediation pathway is non-zero

### Spatial Diagnostics

- **Moran's I** on the residuals of the full outcome model.  Use a
  state-based spatial weights matrix (counties in the same state are
  neighbours).  Buckets: `< 0.05` (`lt_0_05`), `0.05–0.20`
  (`0_05_to_0_20`), `≥ 0.20` (`ge_0_20`).
- **Top residual hotspot division**: the census division with the highest
  mean residual across its counties.
- **Isolate state count**: count states in the dataset whose
  `isolate_flag == "Y"` in `state_neighbors.csv`.
- **Top positive residual FIPS**: 5 FIPS with the largest positive residuals,
  ordered descending.

### Mediator Labels

- `LPA` → label `"No leisure-time physical activity"`
- Verify against the portal's `measure` column in the health CSV.

---

## 4. Country-Level Analysis Conventions

### Name Reconciliation

- Read `country_name_variants.csv`.  Count `variant_rows` (total variants).
- Variant rows whose `iso3` appears in the health panel are **resolved**;
  others are **unresolved**.

### Metadata Join Coverage

- `metadata_join_coverage = |health_iso3s ∩ metadata_iso3s| / |health_iso3s|`
- `income_group_join_coverage`: same formula restricted to rows where
  income_group is not null.

### Anomaly Detection

- **Scale anomalies**: for each indicator (adult_mortality, bmi), compute
  the year-specific mean and standard deviation.  Flag country-years where
  `|value − mean| > 3 × std`.  Report as `[{iso3, years: [...]}]`.

- **Complete GDP gap**: country `iso3` codes where one or more years
  (2015–2024) lack GDP data.

### PCA Conventions

- Use the full panel (all country-years with complete data for all 10
  retained variables).
- **Variables retained** (in this exact order):
  `adult_mortality`, `bmi`, `alcohol`, `health_expenditure`,
  `immunization`, `schooling`, `income_composition`, `gdp`,
  `population`, `infant_mortality`
- Standardise each variable (z-score).  Impute missing values with 0
  (the mean after standardisation) for complete-case analysis.
- Compute `pc1_variance_share` = first eigenvalue / k (where k = 10).
- **Top positive loadings**: 3 variable IDs with largest (most positive)
  loading on PC1.
- **Top absolute loadings**: 3 variable IDs with largest absolute loading.
- **Cluster counts**: split PC1 scores into three equal-sized terciles and
  label them `low_burden`, `middle_burden`, `high_burden` (by increasing
  score).  `high_burden_cluster_count` = size of the highest tercile.
- `rows_used` = count of panel rows with complete data for all 10 variables.
- `year_start` = 2015, `year_end` = 2024.
- `missing_rate_by_variable`: for each variable, `missing_rows / total_panel_rows`,
  rounded to 3 decimals.  Use the full metadata-matched panel as the
  denominator.

### Income-Group Model

- Group PC1 scores by `income_group` from metadata.
- Compute the random-intercept variance ratio (ICC-like):
  `(MSB − MSW) / (MSB + (k_avg − 1) × MSW)`.
- RI variance bucket: `< 0.05` = `low`, `0.05–0.15` = `moderate`,
  `≥ 0.15` = `high`.
- `lr_decision`: `mixed_model_supported` if RI variance ≥ 0.05, else
  `pooled_ols_sufficient`.

### Final Readiness

- `ready_with_anomaly_log` if any anomalies were detected (non-empty
  anomaly arrays); `ready_without_flags` otherwise.

---

## 5. General Rounding and Enum Rules

| Field Type | Rule | Example |
|---|---|---|
| Standardised betas | Round to 3 decimals | `0.750`, `-0.034` |
| AIC | Round to 2 decimals | `252.13` |
| Attenuation / percentages | Round to 1 decimal | `3.6` |
| Proportions / coverage | Round to 3 decimals | `1.000`, `0.012` |
| VIF | Round to 2 decimals | `2.66` |
| Moran's I / ICC | Round to 3 decimals | `0.028` |
| Tercile means | Round to 2 decimals | `12.26` |
| Bootstrap CI bounds | Round to 3 decimals | `0.043` |
| p-buckets | `lt_0_001`, `lt_0_01`, `lt_0_05`, `ge_0_05`, `not_computed` |
| Enum values | Use exact strings from answer templates |

---

## 6. Identifier and List Ordering Rules

- **FIPS codes**: 5-digit strings, zero-padded (e.g. `"01001"`).
- **State abbreviations**: 2-letter codes, sorted ascending in lists
  (`["AK","AL",...]`).
- **ISO3 codes**: 3-letter strings, sorted ascending.
- **Requested states**: listed in the same order as the task prompt.
- **Measure/attribute IDs**: use exact strings from the portal CSV headers —
  do not invent or abbreviate.

---

## 7. Common Pitfalls

1. **Treating state SES county distractors as states**: the
   `state_ses_long.csv` contains county-like rows (`geo_fips` not ending in
   `000`).  Always filter `geo_level == "state"` before joining to
   state health data.

2. **Mixing strata**: when a task asks for Total estimates, filter both
   `stratum_type == "Total"` AND `stratum == "Total"`.  Blank-stratum rows
   (both fields empty) are NOT valid demographic strata — flag them as
   `not_feasible_blank_demographic_strata`.

3. **Unbalanced bracket maps**: income-quartile brackets use inconsistent
   naming (`Q1 lowest`, `Q2`, `Q3`, `Q4 highest`).  Map them explicitly.

4. **FIPS precision**: validate `len(fips) == 5 and fips.isdigit()` before
   joining.  County data can contain rows with non-standard FIPS lengths.

5. **RUCC as continuous**: RUCC codes are categorical, NOT continuous.
   Always use dummy-variable encoding (`categorical_dummies`).

6. **DC exclusion**: DC is NOT a territory.  It has `territory_flag == "N"`
   and should be included in state-level analyses unless a task explicitly
   says otherwise.

7. **Country-GDP masking**: one country (Japan, JPN) has zero GDP rows in
   the health panel.  List it as the `complete_gdp_gap_iso3`.

8. **BMI scale anomaly**: Namibia (NAM) has BMI values ~2 600 for
   2018–2021 — a scaling error (likely multiplied by 100).  Flag in
   `bmi_scaled_country_years`.

9. **Missing SES attributes**: not all counties have
   `Percent_bachelors_or_higher_2019_23` or `POP_ESTIMATE_2023` — include
   them in `missing_ses` counts.

10. **Bootstrap seeding**: use a fixed seed for reproducibility.  Borderline
    CIs (just crossing or just excluding zero) may be sensitive — verify
    with the exact seed used in the task environment.

11. **Analysis year selection**: use the most recent year for which both the
    exposure and outcome are available.  For state-level tasks this is
    typically 2024; for county-level tasks check data availability.

12. **Country PCA aggregation**: use the full panel (all years), not
    country-level means, for PCA.  The `rows_used` should reflect panel rows,
    not unique countries.
