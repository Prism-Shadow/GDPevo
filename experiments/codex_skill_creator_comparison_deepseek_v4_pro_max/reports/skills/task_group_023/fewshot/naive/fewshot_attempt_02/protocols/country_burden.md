## Country Burden Audit

Country-level burden-stratification briefing for international portfolios.
Tasks provide a list of country labels (which may be aliases), burden indicator
identifiers, a reference year for cross-section, and a panel range. The audit
reconciles country labels, quality-checks indicator data, performs burden PCA,
clusters countries, fits a panel model, and issues a burden advisory.

### Module execution order

1. reconciliation
2. quality_audit
3. pca
4. clusters
5. panel_model
6. advisory

### 1. Reconciliation

Compare requested country labels against the `/geographies/countries` registry.
Each label resolves to a single canonical country with an uppercase ISO3 code.
A label is an alias if the label string differs from the canonical country name.
Report the set of all uniquely resolved ISO3 identifiers, sorted ascending.

### 2. Quality audit

From `/data/revisions`, identify all revision_event_id values applicable to the
requested indicators. Separate into APPLIED and non-APPLIED sets, each sorted
ascending.

From `/data/country-indicators`, fetch requested indicators for the resolved
countries across the panel years. Identify anomaly (scale-break) observation
keys as ISO3|YEAR|indicator_id strings, sorted ascending.

Count raw missing 2022 cells: the number of requested indicator cells absent
before anomaly exclusions. Count anomaly 2022 cells: unresolved scale-break
cells specifically in the 2022 cross-section. Count imputed 2022 cells: total
2022 cells imputed after quality exclusions (raw missing plus anomaly 2022).

The usable PCA matrix has one row per country with complete 2022 data after
imputation and one column per usable indicator.

### 3. PCA

Impute missing 2022 cells using the mean of non-missing values for that
indicator across countries. Standardize each column by sample standard
deviation. Form covariance C = Z'Z/(n-1).

Perform eigendecomposition. Retain one component (PC1 is the burden axis). The
PC1 variance fraction is PC1 eigenvalue divided by the sum of all eigenvalues.

Report the top three absolute loadings on PC1, ordered by descending absolute
loading value. On exact ties, order by indicator_id ascending. Loadings retain
their signed values.

### 4. Clusters

Run k-means (k=2,3,4,5) on the PC1 scores (one-dimensional). Compute Euclidean
silhouette scores for each k (singleton silhouette = 0). Report the silhouette
coefficient for each k to 4 decimal places.

The silhouette-selected k is the best candidate among {2,3,4,5} by largest
unrounded mean silhouette, then smaller k.

For the requested three-cluster solution, label clusters by ascending PC1
centroid as LOW_BURDEN, MIDDLE_BURDEN, HIGH_BURDEN. Report each cluster's
size and the HIGH_BURDEN membership as sorted ISO3 codes.

### 5. Panel model

Construct a country-year panel for the resolved countries over the declared
panel period (typically 2017-2022). For each country-year, attach the country's
PC1 score as a fixed burden measure and the life_expectancy indicator as the
outcome.

Fit an OLS regression: life_expectancy ~ pc1_score + region_fixed_effects.
Region fixed effects are indicator variables for each distinct country region
from the geography registry, omitting one reference category.

Report n_observations (country-years used), the pc1 coefficient, its standard
error, two-sided p-value, R-squared, and whether region fixed effects were
included (always true).

### 6. Advisory

If the panel model's pc1 coefficient is negative and pc1 p-value is at most
0.05, the advisory is PRIORITIZE_HIGH_BURDEN_CLUSTER. If the coefficient is
negative but p-value exceeds 0.05, the advisory is MONITOR_GRADIENT.
Otherwise, return NO_ADVERSE_GRADIENT.

### Output formatting

- Decimal values to 4 decimal places. Counts are integers.
- ISO3 values are uppercase. Set-like identifier lists are sorted ascending.
- Silhouette_by_k keys are strings "2", "3", "4", "5".
- High_burden_iso3 is sorted ascending.
- Panel model p-value: report 0.0 (not 0) when p < 0.00005.
