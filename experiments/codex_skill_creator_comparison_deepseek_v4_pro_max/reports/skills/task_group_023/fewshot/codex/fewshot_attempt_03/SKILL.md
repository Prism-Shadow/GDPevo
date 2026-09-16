---
name: pho-audit-protocols
description: Complete multi-module algorithmic audit protocols for the Public Health Observatory data portal. Use when a task requires running registered PHO protocol modules (fixed-effects jackknife, nested ridge/elastic-net CV, wild cluster bootstrap, grouped conformal, trajectory PCA+k-means, source perturbation, or controlled decision gates) against the read-only PHO web portal at the task environment base URL. Covers state, county, and country-level analyses with deterministic PRNGs, release resolution, and audit-grade reproducibility requirements.
---

# PHO Audit Protocols

Execute multi-module algorithmic audits using the Public Health Observatory (PHO) read-only data portal.

## Workflow

1. Read the task prompt and the attached analysis_request.json and answer_template.json.
2. Download all required datasets from the portal as CSV via `GET /download?dataset={name}&format=csv`.
   Base URL is `<TASK_ENV_BASE_URL>` from the prompt.
3. Resolve releases: for each (entity, year, measure, filter) combination, select greatest
   revision, then latest released_at, then lowest record id. See [references/release_resolution.md](references/release_resolution.md).
4. Build the cohort(s) specified by the request (balanced, broad, dual-source, primary, etc.).
5. Execute every audit module in the order declared by the request.
6. Apply the controlled decision gate evaluation.
7. Return exactly one JSON object conforming to the answer template. No narrative outside the JSON.

## Portal reference

See [references/portal_api.md](references/portal_api.md) for complete endpoint, column, and filter details.

## Module catalog

See [references/module_catalog.md](references/module_catalog.md) for every registered module method name,
algorithmic contract, and script reference.

## Key portal methodology rules

- Direct survey estimates are primary for state publications; county rollups are parallel.
- Age-adjusted values for state comparisons; crude values for county burden.
- Final releases supersede provisional; highest final revision governs.
- Suppressed, invalid, or blank values are never zero-filled.
- Country labels resolve via portal_label and alternate_labels to stable iso3 identifiers.
- RUCC 1-3 = metropolitan; 4-9 = nonmetropolitan.
- Leading zeros in FIPS codes are meaningful.

## Scripts

Import from or adapt these bundled implementations:

| Script | Contents |
|--------|----------|
| [scripts/prng.py](scripts/prng.py) | PCG32 and XORSHIFT32 with Webb six-point weight mapping |
| [scripts/ols.py](scripts/ols.py) | OLS, two-way FE, CR1/HC3 variance, delete-one-cluster jackknife |
| [scripts/ridge.py](scripts/ridge.py) | Ridge coordinate descent, training-only standardization, nested group CV |
| [scripts/pca.py](scripts/pca.py) | Symmetric Jacobi PCA, standardized scores, loading orientation |
| [scripts/cluster.py](scripts/cluster.py) | Deterministic k-means, silhouette, adjusted Rand index |
| [scripts/conformal.py](scripts/conformal.py) | Grouped split conformal, cross-fold conformal, per-state coverage |

## Reporting rules

- Round all non-integer reported statistics to the precision declared in the request (typically 4 or 6 decimal places).
- Use uppercase two-letter state codes and exact portal division/region names.
- Preserve every declared order (entity-code, time, feature, group); never independently sort aligned arrays.
- Use JSON null only when a requested statistic is mathematically unavailable; never use NaN or Infinity.
- Counts, ranks, seeds, PRNG states, and replicate numbers are integers.

## Protocols observed in evidence

The following protocol_ids appear in the training evidence. Each follows the module
execution pattern above with different module compositions:

- PHO_STATE_TRANSPORT_AUDIT_V1: six-module state transportability audit (FE jackknife, ridge CV, wild bootstrap, conformal, trajectory PCA, source-year perturbation).
- PHO_COUNTY_MEDIATION_TRANSPORT_V1: county mediation audit (GMM mediation, nested ridge, wild bootstrap, state conformal, sensitivity surface, trajectory PCA).
- PHO_STATE_ROBUSTNESS_TRANSPORT_V1: weighted state robustness audit (weighted FE jackknife, elastic net CV, wild bootstrap, cross-fold conformal, trajectory PCA, source perturbation with Shapley).
- PHO_COUNTY_PANEL_TRANSPORT_V1: county panel dynamics audit (two-step GMM, elastic net CV, wild bootstrap, cross-fold conformal, trajectory PCA, source group deletion).

When a task protocol_id matches one of these, apply the corresponding module composition.
When a protocol_id is novel, construct the audit from the module names declared in
analysis_request.json, using the algorithmic contracts in the module catalog.
