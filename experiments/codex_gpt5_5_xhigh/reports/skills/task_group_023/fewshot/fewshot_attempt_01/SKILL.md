---
name: public-health-statistical-data-audits
description: Use for public-health statistical data audit tasks that rely on a browser-accessible evidence portal and linked CSV downloads, especially state, county, and country health/SES joins with strict JSON templates, model diagnostics, rank audits, PCA summaries, mediation, spatial residual checks, and reconciliation flags.
---

# Public Health Statistical Data Audits

## Operating Boundaries

- Work only in the staged attempt directory. Read the task prompt, `input/payloads/source_request.txt`, `input/payloads/answer_template.json`, and `environment_access.md`.
- Replace `<TASK_ENV_BASE_URL>` with the base URL from `environment_access.md`. Use only browser-visible portal pages and linked CSV downloads as evidence.
- Do not inspect environment implementation files, evaluator files, task notes, parent directories, or unstaged answers.
- Return exactly one JSON object matching the template. Do not add prose, comments, markdown, or extra keys.

## Source-First Workflow

1. Parse the answer template before modeling. Treat it as the contract for keys, enum values, rounding, ordering, and whether arrays are sorted or ranked.
2. Identify the required portal pages from the prompt: state health, county health, country indicators, socioeconomic pages, region/neighbor/reference pages, metadata, or reconciliation pages.
3. Download the linked CSVs. Inspect column names, units, years, measure IDs, geography fields, strata fields, and any Attribute-Value layout before joining.
4. Build a local reproducible analysis from the downloaded CSVs. Prefer structured data operations over manual copying from page tables.
5. Keep an audit trail of row counts at each filter and join step so sample sizes and exclusion counts can be filled from data, not guessed.

## Field And Filter Conventions

- Use exact `measure_id`, labels, `iso3`, state abbreviations, and FIPS values from the portal. Do not substitute display labels for IDs when the template asks for IDs.
- Preserve long-format health measure identities. Filter to the requested measure(s), geography level, year, and strata; do not pivot measures in a way that loses the original IDs.
- For state "Total" analyses, require `stratum_type == Total` and `stratum == Total` when those fields exist. Blank demographic labels are not valid strata for demographic standardization.
- Keep U.S. states and territories separate. Exclude territories from state-only models when the template asks for state counts and territory exclusions.
- Preserve county FIPS as zero-padded 5-character strings. Count invalid FIPS separately from counties outside requested states, missing SES, and missing health data.
- If the template says requested states are "in prompt order," preserve prompt order. If it says "sorted ascending," sort alphabetically.
- County socioeconomic downloads may be long Attribute-Value tables. Pivot by stable keys such as FIPS, state, county, and year, with attributes as columns.
- Treat RUCC as categorical dummies when requested. Do not model RUCC as a numeric linear scale unless the template explicitly says so.
- For country panels, reconcile name variants through the portal's metadata/reconciliation pages, report join coverage, and keep ISO3 codes uppercase. Flag scale anomalies by country-year instead of silently ignoring them.

## Modeling Checks

- Use complete cases after all required filters and joins. Report complete-case counts and exclusion reasons from the final analysis frame.
- Standardized betas require standardizing the modeled continuous variables, not just rescaling the outcome after fitting.
- For bivariate versus adjusted claims, compute attenuation as the percent reduction in absolute standardized beta after adjustment. Bucket p-values from raw p-values, not rounded display values.
- For collinearity, compute VIFs on the adjusted predictor set. When asked for a culprit pair, report the most collinear predictor pair in the template's required order.
- For regional clustering or country income-group structure, compare the grouped/random-intercept model with the pooled model using the requested LR, ICC, or variance-ratio diagnostic.
- For influential states or counties, use formal influence/leverage or residual diagnostics from the fitted model. Preserve the requested order: leverage order, absolute residual order, positive residual order, or rank-shift order.
- For rank audits, define priority direction first (`higher_value_worse` or `lower_value_worse`), compute crude and adjusted ranks consistently, then compute Spearman rank correlation and upward/downward shifts from those ranks.
- For mediation, use the portal's exact mediator and outcome measure IDs, fit the poverty-to-mediator and mediator-to-outcome paths on the same complete-case frame, and compute the indirect effect as the product of the two path coefficients. Use bootstrap CI enums based on whether the interval excludes zero.
- For spatial residual checks, compute residuals from the specified socioeconomic model, then use the portal neighbor reference to calculate Moran's I. Track isolates and do not invent neighbors.
- For PCA burden summaries, standardize retained variables, orient PC1 so higher burden indicators load in the expected direction, report missing rates separately from PCA rows used, and label burden clusters consistently with the task's low/middle/high convention.

## Rounding, Buckets, And Enumeration

- Round only at output time, to the decimals specified in the template. Keep numbers as JSON numbers, not strings.
- Apply buckets to unrounded raw values:
  - p-value buckets: `lt_0_001`, `lt_0_01`, `lt_0_05`, `ge_0_05`, or `not_computed`.
  - VIF buckets: `lt_5`, `5_to_10`, `ge_10`.
  - ICC, Moran's I, variance, and CI buckets: use the exact threshold labels in the template.
- Use enum strings exactly as written in `answer_template.json`; do not paraphrase.
- Arrays named "top" are usually ranked arrays, not sorted arrays. Arrays explicitly labeled "sorted ascending" must be sorted even if the analysis naturally produced a different order.
- FIPS values must remain strings. State abbreviations and ISO3 codes should be uppercase strings.
- Validate the final JSON with a parser and compare every key against the template before submitting.

## Common Pitfalls

- Mixing territories with state rows, or county rows with state rows.
- Treating blank demographic fields as valid age/sex strata.
- Losing leading zeros in FIPS by reading them as integers.
- Joining SES Attribute-Value data before pivoting it into one row per geography/year.
- Using the wrong year for dynamic variables or income-change rules.
- Reporting rounded values that were also used to decide buckets.
- Sorting arrays that the template wants in model, residual, leverage, rank-shift, or prompt order.
- Ignoring metadata/name-reconciliation rows in country panels.
- Letting PCA sign ambiguity invert "high burden" and "low burden."
- Hard-coding values from prior examples instead of recomputing from the current portal downloads.
