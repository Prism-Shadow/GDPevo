# Cohort Construction Rules

## General Principles

1. **Cohorts are defined by completeness**: A jurisdiction-year is "complete" when all required values are present, nonsuppressed, and non-missing.
2. **Intersection, not union**: Balanced/strict cohorts are the intersection of complete jurisdictions across all required years.
3. **Never zero-fill**: Missing values remain missing; they do not become zeros.
4. **Report exclusions**: Always list jurisdiction codes excluded from each cohort.

## Common Cohort Types

### Primary Cohort (Reference-Year Complete Cases)
- Scope: All jurisdictions in the declared universe (e.g., 51 for states, or region-filtered counties).
- Requirement: In the reference year, all declared health measures AND socioeconomic fields must be non-null and non-suppressed.
- For weighted audits: Also require `sample_size` to be non-null.

### Balanced Panel Cohort
- Requirement: Must be primary-cohort-complete in *every* analysis year.
- Procedure: Compute primary-cohort-complete set for each year, then intersect all sets.
- Key metric: `core_balanced_state_n` / `balanced_four_year_count`.

### Machine Learning Cohort
- Base: Primary cohort.
- Additional: Also require completeness for extra socioeconomic fields (e.g., unemployment, net_migration, uninsured) in the reference year.

### Strict Dual-Source Cohort
- Requirement: Complete for outcome, primary exposure, parallel exposure, AND all adjustment variables in *every* analysis year.
- Used for: Source-year perturbation where both AGE_ADJUSTED and CRUDE values must exist.

### Broad Reference Cohort
- Requirement: Reference-year complete for outcome AND all ordered features (health + socioeconomic).
- Used for: Ridge regression, conformal prediction modules that need a broad feature set.

## State-Level Health Filter Patterns

| Task Component | value_type | source_type | release_status |
|---|---|---|---|
| Primary exposure (AGE_ADJUSTED) | AGE_ADJUSTED | DIRECT_SURVEY | FINAL |
| Parallel exposure (CRUDE) | CRUDE | DIRECT_SURVEY | FINAL |
| County rollup replacement | CRUDE | COUNTY_ROLLUP | FINAL |
| Socioeconomic | N/A | N/A | FINAL |

## County-Level Health Filter Patterns

County health has **no source_type column**. Filter on value_type and release_status only.

| Task Component | value_type | release_status |
|---|---|---|
| Standard county health | CRUDE | FINAL |
| Revision priority | N/A | HIGHEST_FINAL_REVISION_THEN_LATEST_RELEASE |

## Quality Flags

Always exclude records with these quality flags:
- `INVALID_SCALE` — Scale break, not comparable
- `INVALID` — Data marked invalid
- `WITHDRAWN` — Withdrawn publication

Other quality flags (REVIEWED, PARALLEL_ESTIMATE, PROVISIONAL, REVISED, SUPPRESSED) have specific meanings:
- `SUPPRESSED` in quality_flag or `suppression_flag == 1` → treat value as unavailable
- `REVISED` → this is a revised record; may supersede the original if revision number is higher
- `PARALLEL_ESTIMATE` → a county-rollup parallel estimate; not a direct survey value

## Revision Priority for Resolution

When multiple records match the same (geography, year, measure, value_type, source_type, release_status):

1. **Highest revision number** wins
2. If tied, **latest released_at** timestamp wins

This applies to both health and socioeconomic data.

## Region and Division Mapping

States reference table provides:
- **Region**: Midwest, Northeast, South, West (4 regions)
- **Division**: East North Central, East South Central, Middle Atlantic, Mountain, New England, Pacific, South Atlantic, West North Central, West South Central (9 divisions)

County reference table provides `region` and `rucc` (1-9 Rural-Urban Continuum Code).

## Country Label Reconciliation Priority

1. Match against `canonical_name` first
2. Then `portal_label`
3. Then each label in `alternate_labels` (pipe-delimited `|`)
4. Each match resolves to one `iso3` code
5. Count as "alias resolution" when the requested label differs from the canonical name
