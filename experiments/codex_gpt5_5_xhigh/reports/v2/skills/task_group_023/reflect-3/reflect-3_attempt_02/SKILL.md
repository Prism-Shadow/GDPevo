---
name: public-health-evidence-audit
description: Use when auditing public-health statistical claims from a browser-accessible evidence portal with linked CSV downloads, especially state, county, or country health panels joined to socioeconomic, region, neighbor, metadata, or name-reconciliation tables for regression, ranking, mediation, PCA, residual, and data-quality audits.
---

# Public Health Evidence Audit

## Core Workflow

1. Read the staged task prompt and any staged answer template before computing. Return the exact requested JSON shape, field names, scalar/list types, and no prose outside JSON.
2. Use only browser-visible portal pages and their linked CSV downloads. Read the relevant portal pages first because they often disclose missing rows, distractors, stale rows, invalid geographies, and scale anomalies.
3. Keep the analytic unit explicit: state or DC, county, country-year, or country mean. State the year, geography set, included/excluded units, complete-case count, and why rows were dropped.
4. Preserve long-format identifiers until the last possible step. Filter on stable IDs such as `measure_id`, `attribute`, `iso3`, `fips`, `state`, `year`, `stratum_type`, and `stratum`; do not infer from display labels alone.
5. Build a small reconciliation table before modeling: source row counts, unique units, join keys, matched/unmatched counts, missingness by required field, and distractor rows removed.

## Field Conventions

- State health rows are long format. For crude state measures, usually require `year`, `territory_flag == N`, `stratum_type == Total`, `stratum == Total`, and the exact `measure_id`.
- State SES rows are attribute-value records. True state rows use `geo_level == state` and FIPS-like codes ending in `000`; county-like and territory rows can be distractors.
- State regions and neighbor files contain explicit analysis flags and adjacency metadata. Use those flags rather than assuming the 50 states only; DC may be valid if flagged.
- County FIPS must remain a zero-padded 5-character string. Join county health, SES, and metadata by FIPS, not county name.
- County health rows are long format by `measure_id`. Typical outcome/mediator IDs include disease or behavior codes; keep the code in outputs so labels cannot be confused.
- County SES rows are attribute-value records. Pivot only after filtering the target states/counties, then convert numeric attributes with a parser that safely leaves categorical fields intact.
- Country panels should join metadata by `iso3`. Use name-variant tables as reconciliation hints, not as primary keys when ISO3 is available.
- Distinguish `income_group` from lending-category or other metadata distractors.

## Filtering Habits

- Check every requested measure for duplicate rows, blank strata, stale years, and missing values before pivoting.
- For stratified health data, verify that every requested stratum exists for every analytic unit. Do not claim direct standardization is supported unless the required strata and usable weights are present.
- For complete-case models, report both the pre-filter matched count and the final model count. Enumerate dropped geographies by stable code when the list is short.
- Treat portal notes as data-quality constraints. Examples of reusable checks: scaled indicators, complete-country gaps, missing state-year totals, invalid FIPS rows, old county names, and territory distractors.

## Modeling Checks

- Regression audits: fit the crude model first, then the controlled model. Report coefficient direction, attenuation, R2 or adjusted R2 change, and whether controls change the substantive conclusion.
- Use standardized coefficients or correlations when the prompt asks for "dominant" predictors across variables with different units.
- Check collinearity with a correlation matrix and VIFs when multiple SES controls enter the same model. Do not overstate coefficients from highly collinear controls.
- Ranking audits: define whether low or high values imply priority, then compare crude ranks to adjusted ranks or residual ranks. Name states/counties that move materially.
- Weighted models: state the weight source, usually survey sample size or population. Confirm the sign of the weighted slope because the sign drives the policy interpretation.
- Mediation audits: name exposure, mediator, and outcome IDs. Estimate `a`, `b`, total effect `c`, direct effect `c_prime`, and indirect effect `a*b`. Bootstrap the indirect effect direction and interval; if controls reverse `c`, avoid claiming a stable mediated share.
- Residual audits: report the model used to generate residuals, then list most positive and most negative residual units with stable IDs. Use neighbor files for spatial summaries and report the denominator of neighbor pairs considered.
- PCA burden audits: clean or exclude anomalous indicators before standardizing. Drop variables with structural gaps or variables that are not burden rates unless the prompt asks for them. Orient PC1 so a higher score means the stated burden direction, and report retained variables, explained variance, loadings direction, cluster counts, and grouping structure.
- Grouped interpretation: compare pooled results with region or income-group summaries when metadata groups explain large score or residual differences. Do not present pooled-only conclusions when groups dominate the structure.

## Rounding And Enumeration

- Keep internal calculations at full precision; round final coefficients, correlations, residuals, R2, and cluster centers to 3 decimals unless the template implies otherwise.
- Round percentages to 1 decimal point when they summarize attenuation, bootstrap positivity, or mediated share.
- For short exclusion/outlier lists, enumerate stable IDs and names. For longer lists, give counts by reason and include representative or top-ranked records.
- Always include denominators for coverage claims: matched rows out of total rows, countries out of countries, strata per state, neighbor pairs with same sign out of all neighbor pairs.

## Common Pitfalls

- Ignoring the answer template or changing its schema.
- Joining on names when FIPS or ISO3 keys exist.
- Letting pandas or another parser strip leading zeros from FIPS codes.
- Mixing county-like rows into state SES extracts or territories into state analyses.
- Pivoting all measures before filtering, which can silently merge unrelated long-format indicators.
- Treating marginal strata as joint demographic cells for direct standardization.
- Using stale or blank-stratum rows as if they were valid current-year totals.
- Confusing negative residuals with high priority when the priority direction depends on the outcome definition.
- Reporting a mediated proportion when the total effect is near zero or changes sign after controls.
- Running PCA before fixing scale anomalies or deciding whether the unit is country-year or country mean.
