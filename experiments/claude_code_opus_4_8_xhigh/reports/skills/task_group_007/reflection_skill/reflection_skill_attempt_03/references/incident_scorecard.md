# SOP: Supplier incident scorecard

Build a supplier-quality scorecard over a date-windowed incident population. The request payload supplies
the window, precision rules, severity set, ordering, and the recommendation policy — **follow the payload
policy verbatim; the codes/thresholds below are the validated structure but the payload is authoritative.**

This family was solved correctly in the blind phase; the rules here are confirmed.

## Data to pull
- `GET /incidents` (all), filter locally to the window, or use `start`/`end` query params.
- `GET /suppliers` (quality_status, name).

## Filter population
`start_date <= open_date <= end_date` (inclusive, ISO string compare on `open_date`). This filtered set is
the denominator for shares and the population for every per-supplier metric.

## Per-supplier metrics (suppliers with >= 1 filtered incident)
- `incident_count` = filtered incidents for the supplier.
- `incident_percentage = incident_count / filtered_total * 100`, rounded to the policy precision (1 dp).
- `total_resolution_cost` = sum of `resolution_cost`, 2 dp.
- `avg_duration_days` = mean of per-incident durations, 2 dp, where duration in calendar days is:
  - closed incident: `close_date - open_date`.
  - open incident (no close_date): `analysis_date - open_date`.
- `rma_count` = incidents with `incident_type == RMA`; `work_order_count` = `WORK_ORDER`.
- `open_incident_count` = `status == open`.
- `severe_incident_count` = `severity in {high, critical}` (use the payload's `severe_severity_values`).

## Recommendation code (precedence, first match wins)
Apply in the payload's precedence order. The validated policy is:
1. **ESCALATE_SUPPLIER** if `(quality_status == quality_hold AND incident_count >= 3)` OR
   `(any critical RMA, i.e. incident_type == RMA AND severity == critical)` OR
   `(rma_count >= 3 AND total_resolution_cost >= the policy cost threshold)`.
2. **PROCESS_REVIEW** if `work_order_count >= 3 AND work_order_count > rma_count`.
3. **WATCHLIST** if `quality_status in {watch, quality_hold}` OR `incident_count >= the policy count`
   OR `total_resolution_cost >= the policy cost` OR `severe_incident_count >= 2`.
4. **MONITOR** otherwise.

Read the exact numeric thresholds from the payload's `recommendation_policy` — do not hardcode numbers;
they are given per task. The quality_hold escalation clause requires the incident-count condition too, so
a quality_hold supplier with too few incidents lands on WATCHLIST, not ESCALATE.

## Derived outputs
- `supplier_scorecard` sorted by `supplier_id` asc.
- `top_escalation_suppliers` = supplier_ids whose code is ESCALATE_SUPPLIER, ordered by the payload's
  `top_escalation_order` (incident_count desc, then total_resolution_cost desc, then supplier_id asc).
- `highest_cost_supplier_id` = max `total_resolution_cost` (tie-break supplier_id asc).
- `highest_share_supplier_id` = max incident share = max `incident_count` (tie-break per policy).

## Summary
- `filtered_incident_count`, `supplier_count` (suppliers with >=1 filtered incident),
  `total_resolution_cost` (2 dp), `overall_rma_count`, `overall_work_order_count` — all over the filtered
  population.
