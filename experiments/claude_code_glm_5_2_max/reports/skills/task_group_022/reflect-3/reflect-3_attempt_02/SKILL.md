---
name: atlas-commerce-ops-scorecard
description: Solve Atlas Commerce Operations analytical scorecard, reconciliation, and data-correction requests against the authenticated workplace SQL service. Use when a task gives a business request JSON + an answer-template JSON and asks you to compute fulfillment, refund, carrier-quality, warehouse-productivity, or support-health metrics from the Atlas Operations database. Covers cohort scoping, snapshot-vs-event-history authority, raw/canonical fields, minor-unit money + FX, the controlled correction transaction, and the support active-time clock.
---

# Atlas Commerce Operations Scorecard & Reconciliation

## When to use

A request provides a **business request object** (scope, definitions, rules) and an **answer template JSON** (a schema with required fields, units, rounding, and ordering). The job is to compute the requested metrics from the Atlas Commerce Operations database and write one JSON object that conforms to the template *exactly* (no extra fields, no commentary). Requests are analytical (read-only) unless an approved data correction is explicitly requested.

## Environment

- Authenticated HTTP service (base URL and bearer token are given per environment in the access doc).
- `GET /api/schema` — table DDL.
- `GET /api/data-dictionary` — column descriptions and conventions.
- `GET /api/correction-audit` — public audit rows for applied corrections.
- `POST /api/sql` — read-only `SELECT`/`WITH` queries. Body `{"sql": "...", "params": [...]}`.
- `POST /api/sql/transaction` — controlled multi-statement transaction (only when a correction is requested). Body `{"statements": [{"sql","params"}], "expected_total_changes": N}`.

Always send `Authorization: Bearer <token>` and `Content-Type: application/json`.

## Hard-won environment constraints (respect these)

1. **Results are capped at 5000 rows silently.** Do all aggregation/ordering server-side. Never page large row sets into the client and merge — you will silently miss rows. If you need a per-entity list that could exceed 5000, compute it as a single server-side `SELECT ... ORDER BY ...` and confirm the returned row count matches a separate `COUNT(*)`.
2. **Complex queries are rejected ("query rejected")** past a threshold — roughly when a heavy `GROUP BY` CTE over a large event/scan table is combined with several more CTEs and multi-table joins. Mitigations that work:
   - Merge sibling CTEs (e.g. one `delivered` CTE with conditional `MIN`/`MAX` instead of separate `del` + `delany`).
   - Replace a final eligibility CTE+`JOIN` with an `IN (SELECT ...)` membership subquery, or a scalar subquery in the `SELECT`.
   - Compute intermediates server-side in one query, then feed IDs into a second query.
   - Prefer `NOT EXISTS` correlated subqueries over window functions when finding "latest row per group" inside a constrained query.
3. **Dialect is SQLite-like:** `datetime(col, '+24 hours')` for time math; `?` params; `GROUP_CONCAT`; window functions (`ROW_NUMBER() OVER`) work but add cost.
4. **Deliberate duplicate rows exist** in event/scan tables (a parallel high-numbered row echoing a low-numbered one, identical timestamps/values). Always dedup by the natural key (e.g. `(event_at, event_type)` for case events, `(canonical_event_at, canonical_status)` for scans, or by business id) before counting/summing. Verify duplicates are truly identical (`COUNT(DISTINCT amount)=1`) before assuming `MAX`/`MIN` collapse them.

## Core analytical principles

### A. Read the contract before querying
Open the answer template first. It pins: required field names, types, units, `multipleOf`/decimal precision, array `minItems`/`maxItems`, ordering rules, and enum values. Then open the request for the business definitions, scope windows, cutoffs, thresholds, and status/risk rules. The template is the source of truth for *shape*; the request is the source of truth for *semantics*.

### B. "Production" = strict
`accounts` has two production-exclusion flags: `is_internal` and `is_test`. **Production accounts = `is_internal=0 AND is_test=0`.** Do not relax to `is_test=0` only — internal accounts are non-production and excluding them is required. When a cohort says "production orders/accounts/shipments/cases," join to `accounts` and apply both flags.

### C. Snapshot columns lag; event/scan history is authoritative
The dictionary warns that `current_status` on `orders`, `shipments`, `support_cases`, `warehouse_tasks` "may lag append-only event history." Derive effective state/time from the append-only event or scan table, not the snapshot:
- **Shipment delivery** → `carrier_scans` with `canonical_status='DELIVERED'` (the `canonical_*` columns are the normalized "effective" values; `raw_*` are source-as-supplied). Effective delivery time = the `canonical_event_at` of the DELIVERED scan.
- **Order lifecycle** → `order_events` (`CREATED/PAYMENT_CONFIRMED/ALLOCATED/PACKED/SHIPPED/DELIVERED/CANCELLED`).
- **Warehouse task completion/rework** → `warehouse_task_events` (`COMPLETED`/`REWORK` rows carry the real `units` and `productive_minutes`).
- **Support case state & clocks** → `case_events` (see Active-time clock below).

When a definition says "effectively" or "by the cutoff," derive from events/scans with a time bound (`event_at <= cutoff` / `canonical_event_at <= cutoff`), and dedup.

### D. Cohort scoping is the highest-leverage, highest-risk step
Most failures come from the cohort, not the math. Nail every scope clause: campaign attribution **and** creation-window, account tier/segment/region **and** production flags, service-date / opened / created windows (inclusive boundaries unless stated), warehouse id, and named import batch. Check whether a request-level `warehouse_id` further restricts a batch-defined cohort (it does — apply it). Re-derive the window start/end from the reference table (e.g. `campaigns.starts_at/ends_at`) rather than guessing, then confirm the cohort size with a `COUNT(*)` before computing metrics.

### E. Money: minor units + daily FX
Monetary `*_minor` fields are the smallest unit of the row's currency (e.g. cents). `fx_rates.usd_per_unit` is USD per one *unit* (one unit = 100 minor) of the named currency, keyed by `(rate_date, currency)`, and it exists for USD too (it is not exactly 1.0). To convert an amount to USD: `(amount_minor / 100.0) * usd_per_unit`, joining on the row's `service_date`/event date and currency. Follow the request's money policy literally for which date's rate to use (often the refund/reversal `service_date`), even for USD rows. Round only final reported amounts (`ROUND(..., 2)`).

### F. Status / risk rules are ordered ladders
Status enums (HEALTHY/WATCH/CRITICAL, STABLE/PRESSURED/AT_RISK, LOW/MODERATE/HIGH, CONTROLLED/ELEVATED/SEVERE, APPLIED/NOT_APPLIED) come from ordered threshold ladders. Evaluate top-down per the request's explicit conditions; "otherwise"/"all other outcomes" is the fallback. Compute the inputs (rates, counts) with the exact denominators the request names (often "eligible" count, which includes incomplete/active cases in the denominator — do not drop them).

### G. Ordering and tie-breaks
For ordered lists (worst regions, top employees, worst accounts, id lists), sort by the *unrounded* underlying value first, then apply the stated tie-break (usually id ascending), and only round for display. Read ordering rules verbatim — e.g. "rate ascending, then region ascending" or "severe count desc, breach count desc, account id asc."

## The controlled correction (only when explicitly requested)

A correction request names one raw/canonical contradiction and an approved minimal canonical fix. Workflow:

1. **Find the contradiction.** Within the named `import_batch_id` (and warehouse scope), `GROUP BY raw_status, canonical_status` and find the single pairing where they diverge (e.g. `raw_status='DELIVERED'` but `canonical_status='IN_TRANSIT'`). Exactly one such contradiction exists; all other rows map cleanly. Capture `scan_row_id`, `shipment_id`, the `field_name` (`canonical_status`), `old_value`, `new_value`.
2. **Apply via one transaction** with `expected_total_changes = 2` and two statements:
   - Guarded UPDATE on `carrier_scans`:
     `UPDATE carrier_scans SET canonical_status=? WHERE scan_row_id=? AND canonical_status=?`
     with params `[new_value, scan_row_id, old_value]`. The guard **requires** the primary-key `scan_row_id` *and* the old `canonical_status` in the `WHERE`, and the `SET` may contain **only** `canonical_status` (do not set `corrected_at`/`correction_reason` — including them is rejected; those columns stay NULL).
   - Audit INSERT with all 11 columns:
     `INSERT INTO correction_audit (audit_id, correction_key, entity_type, entity_id, source_row_id, field_name, old_value, new_value, reason_code, corrected_at, actor) VALUES (?,?,?,?,?,?,?,?,?,?,?)`.
     `correction_key` is UNIQUE (a retry with the same key is rejected). Use `entity_type='carrier_scan'`, `entity_id` = the shipment business id, `source_row_id` = the scan row id.
3. **Verify** with a post-change `SELECT` confirming the corrected `canonical_status`, and confirm exactly one business row changed and one audit row exists.
4. `correction_status = APPLIED` only when exactly one business row + one audit row committed and the post-change value is confirmed; otherwise `NOT_APPLIED` with the observed results.

### Backlog / post-correction metrics
Define the cohort (warehouse-scoped + production + has an effective scan in the named batch at/before the cutoff). **Effective final carrier status** = `canonical_status` of the shipment's *latest* scan by `canonical_event_at <= cutoff` (tie-break `scan_row_id` desc), across **all** the shipment's scans (not only the named batch). Backlog = final status `<> 'DELIVERED'`. Report pre- and post-correction counts and the delta (post − pre); the corrected scan must be the shipment's latest scan ≤ cutoff for the correction to change the backlog.

## The support active-time clock

For support-health requests, `SUPPORT_ACTIVE_TIME` is wall-clock time the case is actively being worked, **excluding** waiting-on-customer intervals. Reconstruct each case's dedup'd, time-sorted `case_events`:

- Clock starts at `OPENED`. **Paused intervals** = each span from a `WAITING_CUSTOMER` event to the next `CUSTOMER_REPLIED` event. `active_time(start, end) = (end - start) - sum(paused intervals overlapping [start,end])`.
- **First-response active time** = `active_time(OPENED, first AGENT_RESPONDED <= cutoff)`; if no agent response by cutoff, use `active_time(OPENED, cutoff)`. Breach if it exceeds the priority first-response SLA from the request (a representative shape: URGENT 2 / HIGH 4 / MEDIUM 8 / LOW 24 hours — always read the actual values from the request).
- **Resolution active time** = `active_time(OPENED, final RESOLVED <= cutoff)`; for active (unresolved) cases use `active_time(OPENED, cutoff)`. Breach if it exceeds the resolution SLA from the request (representative shape: URGENT 16 / HIGH 24 / MEDIUM 48 / LOW 96 hours — read actual values from the request).
- **State at cutoff** is derived from events, not `current_status` (which lags). Resolved by cutoff = a `RESOLVED` event <= cutoff exists with no later reopen. `open_at_cutoff` = not resolved by cutoff (includes open + reopened). `reopened_at_cutoff` = open cases with a `REOPENED` event after their last `RESOLVED` (or no RESOLVED).
- **severe_active_case** = open/reopened at cutoff AND priority in the request's high-priority set (typically URGENT/HIGH) AND resolution active time beyond the threshold (uses elapsed for active cases). Return ids sorted ascending.
- **median_active_resolution_hours** = median of resolution active-time over cases *resolved* at cutoff; for an even count average the two central values; round to 2 decimals.
- **worst_accounts** = top N (usually 3) by severe-active-case-count desc, active-clock-breach-count desc, account_id asc.

## Workflow checklist per task

1. Read template → request → schema/data-dictionary. List every required field with its unit/precision/ordering.
2. Pin the cohort: write a `COUNT(*)` for the eligible set and sanity-check it against scope clauses. Apply production flags, windows, region/segment/tier/warehouse/batch filters.
3. Decide authoritative source per metric (events/scans, not snapshots). Dedup deliberate duplicate rows.
4. Compute counts/rates/amounts server-side; keep intermediates under the complexity threshold (merge CTEs, use `IN`/`NOT EXISTS`/scalar subqueries).
5. Apply status/risk ladders with the exact denominators and ordered conditions.
6. Build the JSON object to match the template *exactly* (field names, types, rounding, array sizes, ordering, enums). No extra keys, no commentary.
7. Self-check identities: e.g. `complete + incomplete = eligible`; `pre - delta = post`; rates in `[0,1]`.

## Reference files

- `references/schema.md` — concise table/column map for the Atlas schema.
- `references/conventions.md` — value enums, money/FX, and the duplicate-row/active-time conventions.
