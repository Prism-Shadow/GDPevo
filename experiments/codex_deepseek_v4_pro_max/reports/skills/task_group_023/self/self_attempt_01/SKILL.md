## When to Use This Skill

Use this skill whenever a task is framed as a Public Health Observatory (PHO) algorithmic audit. Indicators include:
- A task directory containing `prompt.txt`, `analysis_request.json`, and `answer_template.json`.
- Reference to a read-only Observatory portal at a base URL provided via the prompt as `<TASK_ENV_BASE_URL>` or an equivalent environment variable.
- Instructions to complete one or more "audit modules" and return a single JSON object.

## Core Protocol

Every PHO audit task follows the same invariant workflow:

1. Read `prompt.txt` for the business-level task description and the portal base URL.
2. Read `analysis_request.json` for the full technical specification including cohort rules, statistical methods, evidence requirements, and decision gates.
3. Read `answer_template.json` to understand the exact output contract — required keys, array lengths, cardinality rules, numeric precision, and enum values.
4. Query the portal for all required evidence, following the declared `release_method` and `publication_selection` filters.
5. Apply each declared audit module's `standard_method` to produce the required statistics.
6. Format results exactly to the answer template contract and return a single JSON object with no narrative outside it.

## Portal Interaction Rules

### Discovery and Catalog

Before querying data endpoints, explore the portal's structure:
- `GET /` — portal root and navigation.
- `GET /catalog` — list of available datasets and their descriptions.
- `GET /geographies/states`, `GET /geographies/counties`, `GET /geographies/countries` — geographic reference data.
- `GET /methodology` — methodological documentation including measure definitions.

### Data Endpoints

- `GET /data/state-health` — State-level health measures. Supports `?page=` and `?page_size=` pagination.
- `GET /data/state-socioeconomic` — State-level socioeconomic data. Supports `?page=` and `?page_size=`.
- `GET /data/county-health` — County-level health measures. Supports `?page=` and `?page_size=`.
- `GET /data/county-socioeconomic` — County-level socioeconomic data. Supports `?page=` and `?page_size=`.
- `GET /data/country-indicators` — Country-level indicators. Supports `?page=` and `?page_size=`.
- `GET /data/revisions` — Revision event history with status, timestamps, and related metadata.
- `GET /download?dataset=<dataset>&format=csv` — CSV export of a full dataset, plus supported filter query parameters.

### Filtering Convention

Data endpoints accept query parameters matching the analysis request's filter vocabulary. Common filters include `measure_id`, `value_type`, `source_type`, `release_status`, `year`, and geography keys. Use exact filter names from the portal's JSON response field names; do not guess parameter names.

### Data Resolution Rules

When an analysis request declares `REGISTERED_FINAL_RELEASE_RESOLUTION` or similar release methods:
- Filter by `release_status`: `FINAL` (exclude `PRELIMINARY`, `ARCHIVED`, or other statuses).
- When multiple final records exist for the same measure/year/geography, apply the declared `health_revision_priority` or `socioeconomic_revision_priority` (typically: highest `revision` number first, then latest `released_at`, then highest `observation_id`/`record_id`).
- Treat quality flags declared in `invalid_quality_flags` (e.g., `INVALID_SCALE`, `INVALID`, `WITHDRAWN`) as unavailable.
- Suppressed, invalid, or blank values are never zero-filled; they are treated as missing (`null`/unavailable).
- Health measures may have multiple `value_type`/`source_type` combinations; filter to the declared combination only.

## How to Read an Analysis Request

### Publication/Cohort Section

The request defines one or more data cohorts. Key concepts:
- **Release resolution**: How to select among multiple publication revisions for each observation.
- **Filter specification**: The `value_type`, `source_type`, `release_status`, and other criteria for selecting health and socioeconomic records.
- **Complete case definition**: Which variables must be non-null and valid for a geography-year to qualify.
- **Cohort types** (may appear under `evidence_specification`, `publication_selection`, or `evidence_and_cohorts`):
  - **Primary/Reference cohort**: Complete cases in the reference year for the outcome and adjustments.
  - **Balanced panel cohort**: Complete cases in every analysis year (intersection of complete-case geographies across all years).
  - **Machine-learning/strict cohort**: Additional completeness requirements beyond the primary cohort.

### Audit Modules

Each module declares:
- A `standard_method` identifier (e.g., `STANDARD_TWO_WAY_FIXED_EFFECTS_OLS_DELETE_ONE_STATE_JACKKNIFE`). This is the registered statistical procedure to implement.
- A `cohort` reference (which cohort definition to apply).
- Model specification: outcome variable, predictors/features (in declared order), clustering unit, grouping keys.
- Tuning grids: `lambda_grid`, `alpha_grid`, `l1_ratio_grid` — always preserve the declared order.
- Randomization metadata: `seed`, `stream`, `replicate_count` — never alter these.
- `required_evidence` / `required_audit_outputs`: The exact statistics that must appear in the answer.

### Statistical Method Patterns

Common module families you may encounter:

**Delete-one/Jackknife** — Fit the full model, then iteratively delete one cluster unit (state, census division) and refit. Report: full coefficient, all delete-one coefficients, jackknife bias-corrected coefficient, jackknife standard error, t-statistic, p-value, and extreme deletion summaries.

**Nested Cross-Validation** — Outer folds by group (state, division), inner folds for hyperparameter selection. Report: outer fold sizes, inner grid RMSE, selected parameters per outer fold, outer RMSE per fold, pooled metrics.

**Wild Cluster Bootstrap** — Restricted-null or Webb wild bootstrap with declared PRNG (PCG32 or XORShift32), seed, and stream. Report: observed fit, checkpoint PRNG states and bootstrap-t values at declared replicates, exceedance counts, plus-one p-value, quantiles.

**Grouped Conformal Prediction** — Split the data by group, fit on training folds, calibrate thresholds on calibration folds, evaluate on test folds. Report: fold-level and aggregate coverage, mean width, worst-performing group.

**Trajectory PCA Clustering** — PCA on longitudinal features, deterministic k-means with fixed initialization, leave-unit-out or leave-year-out stability via Adjusted Rand Index. Report: spectrum, loadings, scores, centroids, cluster assignments, and all stability ARI values.

**Source Perturbation** — Systematic replacement or deletion of data sources/groups. Report: all scenario results, worst-case shifts, and attribution statistics (e.g., Shapley values).

**Difference/System GMM Mediation** — Instrumented change models with clustered standard errors. Report: coefficient summaries for each structural equation, first-stage partial F statistics, indirect effect with cross-equation delta-method inference, and deletion diagnostics.

### Decision Rules

Every task ends with a controlled decision. The decision section declares:
- **Gates/Flags**: Named conditions with numeric thresholds (e.g., `FULL_EXPOSURE_COEFFICIENT_IS_NEGATIVE_AND_JACKKNIFE_P_VALUE_IS_AT_MOST_0_05`).
- **Precedence**: Ordered decision outcomes from best to worst case (e.g., `PRIMARY_TRANSPORTABLE` → `ASSOCIATED_WITH_LIMITED` → `NO_TRANSPORTABLE`).
- Each gate evaluates to a boolean. Count passing gates. Apply the precedence rule exactly as written.

## How to Fulfill an Answer Template

### Global Rules (apply to every task)

1. **JSON only**: Return exactly one JSON object. Do not include markdown fences, narrative, or commentary outside the JSON.
2. **Required keys**: Every key listed in the template's `required_top_level_keys` must be present. Every `required_keys` within each sub-object must be present. Do not add extra keys.
3. **Numeric precision**: Report non-integer values at the declared number of decimal places (typically 4 or 6) as actual JSON numbers. Integer fields (counts, seeds, fold numbers, PRNG states, replicate numbers, ranks) are encoded as JSON integers without decimals.
4. **Identifiers**: Use exact case from the portal data. State codes are uppercase two-letter strings. ISO3 codes are uppercase three-letter strings. Division/cluster names match portal values exactly.
5. **Ordering**: Every array must preserve the declared order from the analysis request. Do not sort alphabetically or numerically unless the template explicitly requires it. Alignment between arrays (e.g., state order matching across modules) is required when cardinality rules declare it.
6. **Missing values**: Use JSON `null` only when a requested statistic is mathematically unavailable or a geography is excluded from a cohort. Never use `NaN`, `Infinity`, or string placeholders like `"N/A"`.
7. **Enum values**: When the template restricts a field to an allowed list, use exactly one of the declared values — do not paraphrase, abbreviate, or invent new values.
8. **Array lengths**: Verify every list's length matches the template's declared expectations before submitting.

### Template-Driven Field Construction

When the answer template specifies `required_keys` for an object, construct every key with a value of the declared type. When the template specifies `array_lengths` or `cardinality_rules`, enforce those constraints:
- Positional alignment: if `state_order` in module B must match `state_order` in module A, copy the order.
- Nested alignment: `inner_rmse_grid` dimensions like `[9, 5]` mean 9 rows (one per outer fold), each row a 5-element array aligned to the lambda grid.

### Precision Rules

The analysis request or answer template will declare precision rules. Apply them consistently:
- Computed real-valued statistics → declared decimal places (e.g., 4 or 6).
- Grid values, thresholds, and literal parameters → may have a separate precision rule (often 4 decimal places).
- Do not round intermediate values; only round the final reported number. Use standard rounding (half-up or half-even as appropriate to match the portal's likely output).

## Evidence Collection Strategy

1. Start by enumerating all required measures, years, and geographies from the analysis request.
2. Paginate through data endpoints to collect complete datasets. Use `page_size` to maximize throughput within any portal limits.
3. Apply release resolution, filter criteria, and quality exclusions to build the required cohorts.
4. Cross-reference revision history (via `/data/revisions`) when the request requires tracking applied/non-applied revision events.
5. Verify cohort sizes and state/county/country lists before proceeding to statistical modules.

## Error Handling and Verification

- If a required endpoint returns no data for a valid query, re-check filter parameters against the portal's actual field names.
- If a geography has no eligible record after applying all filters, it is excluded from the relevant cohort (not zero-filled).
- If a statistical computation is mathematically impossible (e.g., division by zero, singular matrix, empty cohort), report `null` for the affected statistic and document in any required diagnostic field.
- Before submission, validate that every template-required key exists, every array has the correct length, and every enum/Boolean field contains a valid value.

## Checklist Before Submitting

- [ ] All portal data collected and cohorts resolved per the declared filters.
- [ ] Every audit module executed with the declared `standard_method`.
- [ ] Output conforms exactly to `answer_template.json` — no missing keys, no extra keys.
- [ ] Every array preserves declared order; aligned arrays match positionally where required.
- [ ] Numeric precision matches the declared rules (counts as integers, statistics at the declared decimal places).
- [ ] All enum and Boolean fields use only the declared allowed values.
- [ ] No narrative, markdown, or commentary outside the single JSON object.
- [ ] `null` used only for mathematically unavailable or excluded values; never `NaN` or `Infinity`.
