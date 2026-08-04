 # Country Burden Revision Audit

 Country-level burden-stratification audit using cross-sectional PCA, clustering,
 and panel modeling of life-expectancy against a PC1 burden score.  Activated
 when the task requests a country burden audit with reconciliation of country
 labels, revision history, and scale breaks.

 ## Module execution order

 1. `label_reconciliation`
 2. `quality_audit`
 3. `pca`
 4. `clustering`
 5. `panel_model`
 6. `advisory`

 ## Module methods

 ### label_reconciliation

 For every requested country label, query the portal's country catalog and
 resolve to a canonical ISO3 code.  Count labels that differ from the canonical
 country name (alias resolutions).  Produce the sorted set of all uniquely
 resolved ISO3 codes.

 ### quality_audit

 Query the revisions endpoint for all revision events applicable to the resolved
 countries and requested indicators.  Classify each by its status (APPLIED or
 otherwise).  Record all observation keys (ISO3|YEAR|indicator_id) flagged with
 unresolved scale breaks.

 For the cross-section year, count raw missing indicator cells, unresolved
 scale-break cells, and total cells requiring imputation.  After exclusions and
 imputation, record the usable country count and indicator count for the PCA
 matrix.  Use the declared imputation method (typically median by indicator
 across available countries).

 ### pca

 Center and scale the completed country-by-indicator matrix (standardize to unit
 variance).  Run PCA via covariance of the standardized matrix.  Retain
 components as indicated by the eigenvalue spectrum.  Report PC1 variance
 fraction and the top absolute loadings in descending order; break exact ties by
 indicator_id ascending.

 ### clustering

 Use the PC1 scores (or first K PC scores as appropriate) to cluster countries
 with k-means.  Compute silhouette coefficients for the candidate cluster counts
 (typically 2 through 5) and select the count with the highest silhouette.

 For the requested three-cluster solution, label clusters LOW_BURDEN,
 MIDDLE_BURDEN, HIGH_BURDEN by increasing mean PC1 score (PC1 is oriented so
 higher scores mean higher burden).  Report cluster sizes and the sorted ISO3
 list for the high-burden cluster.

 ### panel_model

 Build a panel dataset with the PC1 burden score and life expectancy for every
 country-year in the declared panel range.  Fit an OLS model of life expectancy
 on PC1 burden score with region fixed effects (if declared).  Use
 cluster-robust standard errors by country.  Report n, coefficient, standard
 error, p-value, R-squared, and whether region fixed effects were applied.

 ### advisory

 Classify the high-burden cluster priority:

 | Advisory | Condition |
 |---|---|
 | `PRIORITIZE_HIGH_BURDEN_CLUSTER` | Panel PC1 coefficient is negative and statistically significant, confirming an adverse burden gradient |
 | `MONITOR_GRADIENT` | Evidence of a gradient exists but is not conclusive |
 | `NO_ADVERSE_GRADIENT` | No evidence of an adverse burden gradient |

 ## Reporting

 - Scores and statistics: 4 decimal places.
 - Counts: integers.
 - ISO3 values: uppercase.
 - Set-like identifier lists: unique and sorted ascending.
 - Return one JSON object conforming to the effective template, with no
   surrounding narrative.
