---
name: pho-algorithmic-audit
description: Complete registered algorithmic audits against the Public Health Observatory (PHO) data portal. Use when the user presents an analysis_request.json and answer_template.json against a PHO portal, needs to resolve publication records into analytic cohorts, run a sequence of registered statistical audit modules, and return one JSON object conforming to an answer template. Trigger on PHO, Public Health Observatory, algorithmic audit, analysis_request, answer_template, protocol_id, or any mention of a read-only health-data portal with registered audit protocols.
---

# PHO Algorithmic Audit

Completes registered algorithmic audits using the Public Health Observatory portal — a read-only web portal that serves health, socioeconomic, geography, and revision data as browsable HTML tables and CSV downloads.

## Core workflow

Every audit follows the same sequence. Never skip a step or reorder modules.

1. **Read the request.** Ingest `analysis_request.json` and `answer_template.json`. The request binds entities, measures, time windows, filters, hyperparameters, random seeds, reporting precision, business gate predicates, and the controlled decision mapping. The template fixes the output contract.

2. **Access the portal.** Use the provided base URL. Preferred access is through CSV downloads (`/download?dataset=<name>&format=csv`) because they return the full dataset in one call. Fall back to HTML browsing with query parameters when filtering before download is useful, but always prefer the CSV route for analytic work. Never silently substitute rollup for direct estimates, or provisional for final releases.

3. **Resolve publications and build cohorts.** For each requested dataset, filter by the effective status, source type, value type, validity, and geography from the request. Within each entity-time-measure key select one record by the declared priority chain (highest revision, then latest release timestamp, then lowest record ID). Suppressed, invalid, withdrawn, blank, or null analytic values are unavailable and are never zero-filled. Join resolved series by stable entity-time keys, then apply completeness predicates to construct primary, balanced-panel, broad, or dual-source analytic sets. Preserve declared entity, time, feature, and group ordering everywhere.

4. **Execute every audit module in declared order.** For each module: read its bound method, parameters, cohort, and evidence requirements from the effective request. Implement the algorithm exactly as specified. Do not skip evidence fields. Do not reorder or substitute algorithms. When a protocol profile is available for the request's `protocol_id`, prefer its canonical method descriptions over general heuristics — see `references/protocols.md`.

5. **Apply decision rules and return one JSON object.** After completing all modules, evaluate every bound business predicate on **unrounded** values, count and order gates as declared, select the applicable controlled decision class, and populate every template field. Use the declared numeric precision only for final reporting — compute everything at full machine precision. Encode integers and booleans as their natural JSON types.

## Data resolution rules

These rules hold across all datasets, geographies, and protocols.

- **Release precedence.** For each entity-time-measure key choose the greatest FINAL revision, then the latest `released_at` timestamp, and when both tie choose the lowest observation/record identifier. Ignore PROVISIONAL records when a FINAL record exists for the same key.

- **Suppression and missing values.** A row with `suppression_flag=1`, a suppressed value (em dash), a `quality_flag` among the request's invalid set, or a null/blank analytic value is incomplete. Never treat an unavailable value as zero. A suppressed record still counts as a selected publication when the request asks for selected-row counts before completeness filtering.

- **Source types.** DIRECT_SURVEY is the primary publication series. COUNTY_ROLLUP estimates are parallel diagnostics. Never substitute one for the other unless the request explicitly binds a replacement source in a perturbation module.

- **Revision events.** APPLIED revision notices describe corrections already reflected in later FINAL revisions. Use them for audit trail reporting but not for changing already-resolved values. PENDING and WITHDRAWN notices do not authorize replacement.

## Portal data reference

All portal structure is documented in `references/portal.md`. Read it before accessing endpoints.

## Protocol profiles

When a train answer for the exact `protocol_id` includes a `protocol_registry_record.portable_protocol_profile` labeled `REUSABLE_METHOD_ONLY`, the profile's `modules` section carries canonical method descriptions. Use those as the authoritative algorithm specification, with the future request overriding only the task-local bindings listed in the profile's `instance_boundary`. Profiles for known protocols are cataloged in `references/protocols.md`.

When no matching protocol profile exists, implement the algorithms from the request's own module descriptions, applying the general data resolution rules above and the algorithm reference in `references/algorithms.md`.

## Algorithm reference

Detailed specifications for the statistical methods that appear across protocols — double-demeaned fixed effects, ridge regression, nested cross-validation, delete-cluster jackknife, wild cluster bootstrap, grouped split conformal, PCA trajectory clustering, k-means, elastic net, GMM, mediation sensitivity, Shapley attribution, and more — are in `references/algorithms.md`. Read it when implementing a module whose method is not fully described in a protocol profile.

## Reporting

- Compute everything at full machine (unrounded) precision.
- Apply the declared decimal-place rounding only when writing final JSON values.
- Report integers (counts, ranks, fold numbers, seeds, PRNG states, replicates) as JSON integers.
- Report booleans as JSON booleans.
- Preserve every declared array order. Do not sort results independently.
- Use JSON `null` only when a statistic is mathematically unavailable — never for `NaN` or `Infinity`.
- Use uppercase for state codes, ISO3 identifiers, and division names as they appear in the portal.
- When the request or template declares a fixed vocabulary (gate values, classification labels, decision enums), use exactly those strings.
