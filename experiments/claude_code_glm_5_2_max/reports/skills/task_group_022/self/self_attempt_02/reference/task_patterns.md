# Recurring Task Patterns (value-free checklists)

Each pattern is a checklist derived from the train tasks. Specific thresholds, windows, IDs, result sizes, and final values are **read from the request payload at runtime** — never hardcoded.

## Pattern A — Cohort rate scorecard (e.g. fulfillment on-time-complete)

A cutoff-based scorecard over an eligible order/shipment cohort.

- [ ] Define eligible cohort: named campaign + production orders created within the campaign's active window (`order_created_at` between `campaigns.starts_at` and `ends_at`).
- [ ] Complete order: has ≥1 physical shipment **and** every shipment effectively DELIVERED by the cutoff. No shipment ⇒ incomplete.
- [ ] On-time complete: complete **and** every shipment delivered ≤ its `promised_delivery_at`.
- [ ] Severe exception: incomplete with cutoff >24h past latest shipment promise, OR completed with any shipment delivered >24h past its promise. Incomplete with no promise ⇒ not severe via the first condition.
- [ ] Rates: on-time-complete / all eligible (incomplete stay in denominator). Regional rate = same formula within `warehouses.region`. Rank worst regions on **unrounded** rate ascending, then region ascending; take top N.
- [ ] Overall status: ordered rules (e.g. HEALTHY → WATCH → CRITICAL) on rate + severe-exception rate; first match wins.
- [ ] Round only final reported rates to the stated decimals; ranks use unrounded values.
- [ ] Output: counts, the overall rate, worst regions array, severe exception ID list (sorted ascending), status.

## Pattern B — Settlement reconciliation (e.g. refund leakage)

Net settled exposure over an in-scope population within a service-date window.

- [ ] Scope: account tier + production accounts + effective refund service_date window (inclusive).
- [ ] Effective settled logical refund: refund rows minus their linked reversals (via `linked_refund_id`), where status/effectiveness rules hold.
- [ ] USD conversion: each refund/reversal at its `service_date` × row currency via `fx_rates.usd_per_unit`; order gross compared at the same settled-refund service_date FX basis.
- [ ] Net refund amount USD: sum of effective refunds (display to stated decimals).
- [ ] Reason ranking: group by **normalized** reason code, rank by effective net refund USD desc, tie-break reason code asc; return top N.
- [ ] Leakage candidates: order qualifies if any condition holds (e.g. effective settled refund > gross order value in USD; OR ≥2 unreversed effective settled logical refunds with the same normalized reason code). Output order_id ascending.
- [ ] Cohort risk: ordered rules (LOW → MODERATE → HIGH) on candidate-rate (denominator = eligible refunded orders) and net refund USD thresholds.
- [ ] Output: distinct eligible order count, logical refund count, linked reversal count, net USD, top reason codes, leakage IDs, risk.

## Pattern C — Carrier/source quality correction (the one write variant)

Identify one raw/canonical contradiction, apply minimal canonical correction + audit, report pre/post backlog.

- [ ] Confirm payload declares **exactly one** contradiction and supplies `approved_correction` (audit_id, correction_key, reason_code, actor, corrected_at).
- [ ] Cohort: production shipments with an effective scan in the named `import_batch_id` at/before cutoff.
- [ ] Backlog definition: effective final canonical carrier status is NOT DELIVERED (compute pre-correction count).
- [ ] Find the single `carrier_scans` row whose raw vs canonical contradicts per the payload; identify its `shipment_id`.
- [ ] Transaction (Phase 4): guarded `UPDATE` one `carrier_scans` canonical field (+corrected_at, correction_reason) → `INSERT correction_audit` with all columns → `expected_total_changes` per the rule (one business row + one audit row).
- [ ] Post-change verify: query confirms corrected canonical value.
- [ ] `correction_status` = APPLIED only if both the row-count rule and post-change verification hold; else NOT_APPLIED with observed counts.
- [ ] Report pre/post backlog shipment counts, delta (= post − pre), and post-correction delivered count.
- [ ] Output: correction_target (scan_row_id, shipment_id, field_name, old/new), mutation_result (1 business row, 1 audit row), audit_record (all columns), backlog_analysis, correction_status. (Some contracts forbid arrays.)

## Pattern D — Warehouse productivity review

A cutoff-consistent review of production tasks created in a window.

- [ ] Scope: named warehouse + tasks created in the stated window (inclusive UTC boundaries); state evaluated at `state_cutoff_at`.
- [ ] Units per hour (per employee): total completed production units / total productive minutes on those units × 60.
- [ ] Completion rate: completed eligible tasks / eligible tasks. Rework rate: rework tasks / eligible tasks.
- [ ] Delayed high-priority task: HIGH/URGENT with `due_at` strictly before cutoff and not completed by cutoff.
- [ ] Employee ranking: units-per-hour desc, then employee_id asc; take top N.
- [ ] Lowest-performing team: completion_rate asc, then team_id asc; take 1.
- [ ] Facility status: ordered rules (e.g. STABLE → PRESSURED → AT_RISK) on completion_rate + rework_rate; first match wins.
- [ ] Output: eligible task count, completed units, top employee IDs, top employee UPH, rework count + rate, delayed task IDs (asc), lowest team ID, status.

## Pattern E — Support health review

Month-end support SLA/risk review over a case-opened window.

- [ ] Scope: production accounts + named segment + named regions; cases opened in the window (inclusive).
- [ ] Clock basis = SUPPORT_ACTIVE_TIME (not wall-clock). SLA thresholds per priority: first_response hours and resolution active-time hours (read from payload).
- [ ] First-response breach: active time to first agent response exceeds priority threshold; unresponded case uses active elapsed time at cutoff.
- [ ] Active-clock resolution breach: active time to resolution exceeds threshold; active case uses active elapsed time at cutoff.
- [ ] Case state at cutoff: open_at_cutoff = open OR reopened; reopened_at_cutoff = reopened subset.
- [ ] Severe active case: open/reopened at cutoff AND priority URGENT/HIGH AND beyond active-time resolution threshold.
- [ ] Worst accounts: rank by severe active case count desc, then active-clock breach count desc, then account_id asc; take top N.
- [ ] Resolved-case median: median active resolution hours across cases resolved at cutoff; even count ⇒ average two central values; round to stated decimals.
- [ ] Support risk: ordered rules (e.g. CONTROLLED → ELEVATED → SEVERE) on active-severe-case-rate and first-response-breach-rate (denominator = eligible case count).
- [ ] Output: eligible case count, case_state_summary {open, reopened}, first-response breach count, active-clock resolution breach count, worst_accounts array, severe active case IDs (asc), median hours, risk.

## Cross-pattern final checks

- [ ] Every count/rate shares one eligible-cohort CTE (no silent population drift).
- [ ] Decompositions add up (e.g. complete + incomplete = eligible) and status uses the same reported rate.
- [ ] Ranks use unrounded values when "rank by rate"; reported values rounded to template grid.
- [ ] Arrays: exact sizes, exact ordering, unique, ascending ID lists where required.
- [ ] `additionalProperties: false` honored — output only required keys; write pure JSON to `answer.json`.
