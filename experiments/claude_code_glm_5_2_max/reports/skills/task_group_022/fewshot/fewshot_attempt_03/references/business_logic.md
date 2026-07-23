# Recurring Business-Logic Patterns & Pitfalls

The five request families repeat a handful of definitional traps. Each section states the generic shape and the SQL discipline that resolves it. **No task-specific numbers or ID lists appear here** — these are the reusable interpretation patterns.

## 1. "Eligible cohort" is always stated exactly — implement the conjunction literally

Every request defines its in-scope population as a conjunction of conditions (production exclusion + named scope + a time/window/campaign boundary + a status/relationship predicate). Build the cohort in one CTE and reference it everywhere downstream so every metric shares the *same denominator*.

Example shape (generic):
```sql
WITH eligible AS (
  SELECT o.order_id
  FROM orders o
  JOIN accounts a USING (account_id)
  JOIN campaigns c ON c.campaign_id = o.campaign_id
  WHERE a.is_test = 0
    AND a.tier = :tier        -- named scope
    AND o.order_created_at >= c.starts_at
    AND o.order_created_at <= c.ends_at   -- campaign active window
    AND o.order_created_at <= :cutoff
)
```
Pitfalls:
- Forgetting the production exclusion (`is_test = 0`, and `is_internal = 0` where "production" excludes internal).
- Using `orders.promised_at` when the request says *created* window, or vice versa.
- Half-open vs inclusive windows. The request states `inclusive`/`boundary` explicitly — translate `inclusive` end boundary to `<= end_at` (the timestamps already end in `23:59:59Z` so `<=` is usually right), and a "strictly before" rule (`due_at strictly before the cutoff`) to `< cutoff`.
- Multi-table membership predicates like "has an effective scan in the named batch at or before cutoff" must be applied *inside* the cohort CTE (e.g. `WHERE EXISTS (SELECT 1 FROM carrier_scans s WHERE s.shipment_id IN (... ) AND s.import_batch_id = :batch AND s.canonical_event_at <= :cutoff)`), not assumed by joining shipments afterward.

## 2. "Complete" / "on-time" / "breach" rollups need a per-entity status first

Status-family rules (fulfillment completion, support SLA breaches) reduce to: **classify each eligible entity, then aggregate**. Compute a per-entity flag set in a CTE, then `SUM(CASE WHEN …)` over the cohort.

Generic completion pattern:
```sql
WITH order_ship AS (
  SELECT o.order_id,
         /* has >=1 physical shipment */
         COUNT(s.shipment_id) AS ship_count,
         /* every physical shipment effectively DELIVERED by cutoff */
         MIN(CASE WHEN s.current_status = 'DELIVERED' THEN 1 ELSE 0 END) AS all_delivered,
         /* every delivered shipment on or before its promised_delivery_at */
         MIN(CASE WHEN s.current_status = 'DELIVERED'
                    AND s.shipped_at <= s.promised_delivery_at THEN 1 ELSE 0 END) AS all_on_time
  FROM eligible o
  LEFT JOIN shipments s ON s.order_id = o.order_id
  GROUP BY o.order_id
)
SELECT
  COUNT(*)                                   AS eligible,
  SUM(CASE WHEN ship_count > 0 AND all_delivered = 1 THEN 1 ELSE 0 END) AS complete,
  SUM(CASE WHEN ship_count > 0 AND all_on_time = 1 THEN 1 ELSE 0 END)   AS on_time_complete
FROM order_ship;
```
Pitfalls:
- "Complete requires at least one physical shipment" — an eligible order with **no** shipment is incomplete (not complete, not on-time), but **stays in the denominator**.
- "Every shipment delivered by the cutoff" is an `AND` over the order's shipments, i.e. `MIN(flag)=1` only when *all* shipments pass; a single non-delivered shipment fails completion.
- "On time" only applies among complete orders; the on-time rate's numerator is on-time-complete, denominator is all eligible (incomplete orders count against you).

## 3. "Severe exception" / "breach" conditions have an AND/OR structure with a NULL guard

Severe/breach definitions combine a duration threshold with a promise/threshold reference, and explicitly note the NULL case ("an incomplete order with no shipment promise does not satisfy the first condition"). Encode the NULL guard with `case when promise is not null then … else 0 end`.

Generic severe-exception shape (two OR'd branches, one guarded against NULL promise):
```
severe = (incomplete AND cutoff > latest_promise + 24h  /* only when a promise exists */)
      OR (complete AND any shipment delivered > its_promise + 24h)
```
Use `julianday(string_ts)` or equivalent datetime arithmetic for the `+24h` comparison, or compare against `datetime(promise, '+24 hours')`. Always: emit the *exact* severe ID list sorted ascending, and verify it is a strict subset of the incomplete/metric population you already computed.

SLA breach analog: a case is "breached" if active-elapsed time (or time-to-first-agent-response) exceeds the *priority-specific* threshold. Join the case's `priority` to the request's `sla_thresholds_hours[priority]` map. An **unresponded**/active case uses elapsed active time *at the cutoff* as its clock value (not a NULL/skip).

## 4. Per-group rate rollups and worst/best-N

When a request ranks regions/teams/accounts/employees by a rate:
- Compute the group rate as `SUM(numerator_flag)/COUNT(*)` over that group's eligible members, **without rounding**.
- Order by the unrounded rate (asc or desc per the request), then by the stable secondary key (region/team/account/employee id) asc.
- Slice the first N. Because the secondary sort is on a string id, ties are deterministic.

Verify the slice boundary: query the row at rank N+1 and confirm its unrounded rate is strictly worse (or, if tied, its id is strictly greater) so it would not belong in the slice. Output the **rounded** rate alongside each returned region/account but keep ordering on the **unrounded** value.

## 5. Money, FX, and "net/refund after reversals" with linked rows

Refund/payment families chain linked rows (`linked_refund_id`, `linked_event_id`) to net reversals against their originals. The disciplined approach:
- Identify the *effective settled* logical refund rows (`.status = SETTLED`).
- Identify reversals/voids that link back (`.status = REVERSED` / linked to a settled refund) as offsets.
- For each order, sum settled refund amounts − reversed amounts, in **minor units per currency**, then convert each refund to USD at its own `service_date` fx rate, then sum to USD. Keying FX by the row's own service date (not the order date) is the rule that most often changes the answer.
- "Gross order value in USD" for the leakage comparison: value the order `gross_amount_minor` at the **settled refund service_date** rate used for the candidate comparison (the request specifies this basis explicitly).
- "Eligible *refunded* order" denominator is distinct orders with ≥1 effective settled refund — distinct, not refund-row count.

Leakage candidate = (effective settled refund USD after reversals > gross order USD) **OR** (≥2 unreversed effective settled refunds sharing the same normalized reason_code). Output leakage ids ascending. Cohort risk bands compare the leakage count as a *rate of eligible refunded orders* against fixed thresholds, ANDed with an absolute net-refund-USD threshold — evaluate bands top-down (LOW first, then MODERATE, else HIGH).

## 6. Productivity metrics: "units per hour" basis and the rework denominator

- `eligible production-task count` = `warehouse_tasks` where `work_class = 'PRODUCTION'` (and in the named warehouse, created in the window). This is the denominator for `completion_rate` and `rework_rate`.
- `completed production units` and the matching `productive minutes` come from `warehouse_task_events` joined to the eligible tasks on `task_id`. The denominator minutes are those **attached to completed units** — sum `units` and `productive_minutes` over completed-task events; units-per-hour = `SUM(units) / SUM(productive_minutes) * 60`.
- `rework_task_count` = eligible production tasks whose status is `REWORK` (or rework events). `rework_rate = rework_task_count / eligible_production_task_count`.
- "Delayed high priority": `priority IN ('URGENT','HIGH')` AND `due_at < state_cutoff` AND not `COMPLETED` at the cutoff. Sort ascending.
- `lowest_performing_team_id`: rank teams by `completion_rate` ascending, then `team_id` ascending; return the first.

## 7. The controlled-correction transaction (mutating family)

Sequence within **one** `/api/sql/transaction` call, with `expected_total_changes` = exactly the number of mutated rows (one business UPDATE + one audit INSERT = 2):
1. Pre-correction `SELECT` (read the target row: confirm raw vs canonical contradiction, capture `old_value`). Costs zero changes.
2. Guarded `UPDATE carrier_scans SET canonical_status = ?, corrected_at = ?, correction_reason = ? WHERE scan_row_id = ?` — `WHERE` scoped to the single `scan_row_id`. One change.
3. `INSERT INTO correction_audit (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor) VALUES (…)` — all 11 columns. One change.
4. Post-correction `SELECT` (confirm canonical value now equals `new_value`). Zero changes.

Rules re-emphasized:
- The one contradiction is **raw_status vs canonical_status** (raw says delivered, canonical says in-transit, or similar). Correct the **canonical** field to match the truth; never touch raw.
- "Minimal canonical" = the single field on the single row, nothing else.
- `entity_type = 'carrier_scan'`, `entity_id = <shipment_id>` (the business entity), `source_row_id = <scan_row_id>`.
- Backlog metric (`EFFECTIVE_FINAL_CARRIER_STATUS_IS_NOT_DELIVERED`) recomputes pre vs post: the corrected shipment leaves the backlog, so `backlog_delta = post − pre` reflects that single shipment flipping to DELIVERED. `post_correction_delivered_shipment_count` is the delivered subset at/under cutoff in the cohort.
- Declare `APPLIED` only when the transaction reports `total_changes` == expected and the post-change `SELECT` confirms the new canonical value. After commit, `GET /api/correction-audit` should show the new row.

## 8. Common output-formatting rules across families

- **Round only the final reported value** to the precision the template demands (`multipleOf`).
- **Sort by the unrounded value**, then the request's secondary key, before slicing/rounding.
- **Fixed-length arrays** (`exactly two regions`, `exactly three accounts/employees`) must meet `minItems` = `maxItems` = N; verify length and identity.
- **ID lists**: unique, sorted ascending lexicographically (IDs are zero-padded so string order == numeric order), each matching the template `pattern`.
- **Enums**: statuses/risk levels must be one of the template's enum members — derive the label by evaluating the request's band rules against the computed metrics, do not guess.
- **No arrays where the template forbids them** (some correction outputs are scalar/object only) — re-read `additionalProperties: false` and the `x-list-ordering`/`ordering` hints.

## 9. Decompose when a single query is rejected or truncated

If `/api/sql` returns `"error": "query rejected"` or `"truncated": true`:
- **Rejected:** split the statement. Materialize the cohort IDs first (one query), then compute each metric against that set in smaller queries. Avoid deeply-nested 16-way unions in one call.
- **Truncated:** page through the result with bounded `LIMIT`/`OFFSET` (or a key-range predicate on the zero-padded id) until a page is short. Never treat a truncated page as complete. Counts and aggregates (`COUNT`, `SUM`) are never truncated — use them for denominators/totals directly.
