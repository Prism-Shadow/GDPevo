# Atlas Commerce Operations — Conventions & Value Enums

## Timestamps, dates, booleans
- All timestamps are ISO-8601 UTC text ending in `Z` (lexically sortable). Calendar dates are `YYYY-MM-DD`.
- Boolean fields are `INTEGER`: `1` = true, `0` = false (accounts.is_internal, accounts.is_test, products.is_active).
- Time math in the SQLite-like dialect: `datetime(col, '+24 hours')`, `datetime(col, '-2 hours')`, etc.

## Raw vs canonical (the central dual-axis)
- `raw_*` fields preserve source-supplied values exactly; `canonical_*` fields hold normalized operational values.
- **Operational analytics read `canonical_*`.** Deliveries use `carrier_scans.canonical_status='DELIVERED'` at `canonical_event_at`; inventory quantities use `canonical_quantity_each`. Snapshot columns (`current_status`) lag and must be re-derived from event/scan history when a definition says "effective" or "by the cutoff."
- The controlled correction fixes a `canonical_*` field that contradicts its `raw_*` source (see SKILL.md).

## Production accounts
`accounts.is_internal=0 AND accounts.is_test=0`. Strict — confirmed by scoring (loosening to `is_test=0` only dropped a refund task from 0.81 to 0.31). Apply both flags whenever a cohort says "production."

## Money & FX
- `*_minor` monetary fields are the smallest unit of the row currency (cents for USD).
- `fx_rates.usd_per_unit` = USD per one *unit* (one unit = 100 minor) of the named currency, keyed by `(rate_date, currency)`. A USD row exists and is not exactly 1.0.
- USD amount = `(amount_minor / 100.0) * usd_per_unit`, joining on the money-policy date (often the refund/reversal `service_date`) and currency. Apply the literal policy even to USD rows.
- Round only final reported amounts (`ROUND(x, 2)`).

## Duplicate rows (import retries)
Append-only event/scan tables contain deliberate duplicate rows (a parallel high-numbered row echoing a low-numbered one at identical timestamp/value). Always dedup by the natural key before counting/summing:
- `case_events` → `(case_id, event_at, event_type)` (also dedup by `(source_system, external_event_id, ingested_at)`).
- `carrier_scans` → `(shipment_id, canonical_event_at, canonical_status)`.
- `order_events`, `payment_events`, `refund_attempts`, `warehouse_task_events` → by `(source_system, external_event_id, ingested_at)`.
- Verify duplicates are value-identical (`COUNT(DISTINCT amount)=1` or `MIN=MAX`) before folding them with `MAX`/`MIN`. If they are not identical, keep the appropriate copy (usually latest `ingested_at`).

## Known value enums

Status / risk ladders are evaluated top-down per the request's explicit conditions; "otherwise" is the fallback. Compute inputs with the exact denominators named in the request (often "eligible," which includes incomplete/active cases).

- **account.segment** — CONSUMER, SMB, ENTERPRISE, STRATEGIC
- **account.tier** — STANDARD, SILVER, GOLD, PLATINUM
- **warehouse_tasks.work_class** — PRODUCTION, TRAINING (TRAINING excluded from production productivity cohorts)
- **order_events.event_type** — CREATED, PAYMENT_CONFIRMED, ALLOCATED, PACKED, SHIPPED, DELIVERED, CANCELLED
- **carrier canonical_status** — includes CREATED, LABEL_PRINTED, IN_TRANSIT, OUT_FOR_DELIVERY, DELIVERED, EXCEPTION, RETURNED (effective delivery = DELIVERED)
- **case_events.event_type** — OPENED, AGENT_RESPONDED, CUSTOMER_REPLIED, WAITING_CUSTOMER, RESOLVED, REOPENED (+ others)
- **support_cases.priority** — URGENT, HIGH, MEDIUM, LOW (thresholds below)

Facility / risk status families and their ladder shape (always read the exact thresholds and field conditions from the per-request `*_rules` array — copy them verbatim; never assume constants from another task):
- Warehouse facility (ladder on completion_rate and rework_rate): STABLE → PRESSURED → AT_RISK ("otherwise"). Typical cuts are around completion 0.70/0.82 and rework 0.05/0.10.
- Support risk (ladder on severe_rate and first-response-breach_rate): CONTROLLED → ELEVATED → SEVERE. Typical cuts are around severe 0.03/0.08 and fr-breach 0.08/0.15.
- Refund / cohort risk (ladder on a risk rate computed over the eligible cohort): LOW/MODERATE/HIGH (or similar), HIGH when the rate exceeds the named threshold.
- Correction outcome: APPLIED / NOT_APPLIED.
Evaluate top-down; the first matching condition wins and the trailing "otherwise" is the fallback.

## Support priority thresholds (read from the request when present)
First-response and resolution SLAs are keyed by priority (URGENT/HIGH/MEDIUM/LOW). When the request supplies SLA hours, use those exactly. A representative shape (breach if active-time exceeds):
- First-response: URGENT 2h, HIGH 4h, MEDIUM 8h, LOW 24h.
- Resolution: URGENT 16h, HIGH 24h, MEDIUM 48h, LOW 96h.
- "Severe" active case: open/reopened at cutoff AND priority in the named high-priority set (e.g. URGENT/HIGH) AND resolution active-time beyond its threshold (uses elapsed for still-open cases).

## Dedup-safe "latest row per group" patterns
- Latest scan per shipment ≤ cutoff: `ORDER BY canonical_event_at DESC, scan_row_id DESC LIMIT 1` via a correlated `NOT EXISTS` (a later scan would defeat it), to stay under the complexity threshold.
- Latest case event of a type per case: same `NOT EXISTS` form, or compute `MIN`/`MAX(event_at)` grouped.
- One row per task for COMPLETED units when duplicate COMPLETED events exist: group by task, take `MAX(units)` / one effective row.

## Result-set & complexity limits
- `POST /api/sql` caps results at **5000 rows silently** — aggregate/order server-side. Confirm `COUNT(*)` separately when you need a per-entity list.
- Complex multi-CTE + multi-join queries are rejected ("query rejected") past a threshold. Mitigations: merge sibling CTEs; replace a final eligibility CTE+JOIN with `IN (SELECT …)` / scalar subquery; compute intermediates in one query then feed IDs into a second; prefer `NOT EXISTS` correlated subqueries over window functions.

## Answer-template obedience
- Match the template *exactly*: field names, JSON types, `multipleOf`/precision, array `minItems`/`maxItems`, required ordering, enum casing. No extra keys, no commentary, no trailing fields.
- Round only as specified; sort by the *unrounded* underlying value first, then the stated tie-break (usually id ascending), then round for display.
- Self-check identities where they exist (e.g. complete + incomplete = eligible; pre − delta = post; rates in [0,1]).
