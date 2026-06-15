# SOP: Supplier incident scorecard

**Shape of task:** filter incidents to a date window, then per supplier compute counts,
percentages, cost, average duration, type split, open/severe counts, and a controlled
recommendation code. Output is `{analysis_window, summary, supplier_scorecard[],
top_escalation_suppliers[], highest_cost_supplier_id, highest_share_supplier_id}`.

The request payload carries the window, the `analysis_date`, the severe-severity set, the
precedence list, and the exact recommendation-code thresholds. **Use the payload's policy
verbatim** — the rules below are the structure; the thresholds come from the request.

## Filter the population

`GET /incidents?start=<start_date>&end=<end_date>` — this filters on `open_date`, inclusive
ISO string compare. That filtered list is *the* population; every percentage denominator is
its size. Group by `supplier_id`. Get supplier names/quality_status from `/suppliers`.

## analysis_window

`{start_date, end_date, analysis_date}` copied from the request.

## summary

- `filtered_incident_count` = size of the filtered population.
- `supplier_count` = number of suppliers with ≥ 1 filtered incident.
- `total_resolution_cost` = sum of `resolution_cost` over the population (2dp).
- `overall_rma_count` / `overall_work_order_count` = counts by `incident_type` over the
  population.

## Per supplier row (only suppliers with ≥1 filtered incident)

- `incident_count` = supplier's filtered incidents.
- `incident_percentage` = `100 * incident_count / filtered_incident_count`, **1 decimal**.
- `total_resolution_cost` = sum of that supplier's `resolution_cost` (2dp).
- `avg_duration_days` (2dp): for each incident, duration = `close_date - open_date` if
  closed (and close_date present), else `analysis_date - open_date`; average over the
  supplier's filtered incidents. Use calendar days.
- `rma_count` / `work_order_count` = by `incident_type`.
- `open_incident_count` = incidents with `status == open`.
- `severe_incident_count` = incidents with `severity` in the policy's severe set
  (high, critical).
- `recommendation_code` — see below.

Sort `supplier_scorecard` by `supplier_id` ascending.

## recommendation_code (apply precedence top-down; first match wins)

Use the request's `recommendation_policy.precedence` and `codes`. The training policy was:

1. **ESCALATE_SUPPLIER** if any of:
   - supplier `quality_status == quality_hold` **and** `incident_count >= 3`, **or**
   - the supplier has **any critical RMA** (an incident with `incident_type == RMA` and
     `severity == critical`), **or**
   - `rma_count >= 3` **and** `total_resolution_cost >= 15000.00`.
2. **PROCESS_REVIEW** if `work_order_count >= 3` **and** `work_order_count > rma_count`.
3. **WATCHLIST** if any of: `quality_status in {watch, quality_hold}`, **or**
   `incident_count >= 4`, **or** `total_resolution_cost >= 12000.00`, **or**
   `severe_incident_count >= 2`.
4. **MONITOR** otherwise.

Always read the live thresholds from the request payload — if a future task changes a number
or adds a clause, follow the payload, not these defaults. The "any critical RMA" clause is
easy to miss and can escalate a low-volume supplier (e.g. 2 incidents) — check it explicitly.

## Derived fields

- `top_escalation_suppliers` = ids of suppliers whose code is `ESCALATE_SUPPLIER`, sorted by
  `incident_count` desc, then `total_resolution_cost` desc, then `supplier_id` asc.
- `highest_cost_supplier_id` = supplier with the greatest `total_resolution_cost` (break ties
  per the request, else by supplier_id asc).
- `highest_share_supplier_id` = supplier with the greatest `incident_count` (equivalently
  greatest percentage; same ranking as cost ties — by supplier_id asc).

## Pitfalls
- Filtering on the wrong date field or being exclusive at the window ends.
- Counting only closed incidents for duration (open incidents use `analysis_date`).
- Percentage denominator being a supplier subtotal instead of the full filtered population.
- Missing the critical-RMA escalation clause.
- Rounding percentages to 2 dp (they are 1 dp) or cost/duration to the wrong precision.
