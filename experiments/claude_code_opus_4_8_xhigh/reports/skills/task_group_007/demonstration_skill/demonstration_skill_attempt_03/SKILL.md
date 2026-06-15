---
name: northwind-erp-ops
description: >-
  Solve Northwind Components ERP operations tasks against the shared read-only ERP API:
  expedite/dispatch decisions, mixed-warehouse allocation and transfer waves, kit-build
  replenishment (BOM coverage, transfers, purchase requisitions), supplier incident
  scorecards, and supplier quality-hold / replenishment-control reviews. Use this skill
  whenever a task references the Northwind Components ERP, a "wave", an expedite/allocation/
  dispatch queue, a BOM/kit build, a supplier incident scorecard, a quality-hold review,
  effective inventory availability, shipping quotes, or asks for a structured JSON decision
  file built from /orders, /products, /inventory, /customers, /suppliers, /warehouses,
  /boms, /purchase_orders, /incidents, or /shipping/quote — even if the task only mentions
  a memo, planning extract, or answer_template.json. The local memo/extract is planning
  context only; the live API is the source of truth.
---

# Northwind Components ERP Operations

You build structured JSON decision files for an operations desk by reconciling a local
planning input (a memo, request payload, or stale extract) against the **live read-only
ERP API**. The local input tells you *what to decide and how to format the answer*; the
**API records are the source of truth** for every quantity, status, price, and date.

## Golden rules (apply to every task)

1. **Live API over local text.** Memos, notes, and extracts may be stale, partial, or
   contain distractors. Pull the real record from the API and decide from it. The memo's
   job is to give you scope (which orders/suppliers/BOMs), the policy, and the output shape.
2. **Read `answer_template.json` first and obey it exactly.** It defines the required top-level
   keys, every item key, the allowed enum values, the sort order of each list, and the
   rounding rules. Emit *only* the JSON object — no prose, no markdown fences around it.
3. **Effective availability is the universal stock formula.** See below. Reserved,
   quarantined, and safety stock are protected and never freely available.
4. **Money rounds to 2 decimals; percentages to 1 decimal; durations to 2 decimals.**
   Round only at output, compute on full precision. Do not strip trailing zeros that the
   schema implies (e.g. `58.0` is a valid 2-decimal duration).
5. **Sort every list exactly as the template says** (usually by id/sku ascending; some have
   multi-key sorts). Sets of ids/skus must be **deduplicated and sorted**.
6. **Operator notes are usually distractors.** "Customer asked for overnight", "expedite
   today", "high priority" do not change the computed decision or the shipping speed — the
   order's own `shipping_speed` field and the policy rules govern. Honor a note only when it
   asks for an *additional* output the schema already has a slot for.

## The base URL

Use `http://127.0.0.1:8015`. **Ignore any other port** a memo or prompt mentions (e.g.
8007). Confirm with `GET /health`, which also returns record counts and a
`generation_timestamp` (the "as-of" / clock for the dataset).

See `references/api_reference.md` for the full endpoint list, query params, and field
shapes. Read it before your first API call on a task.

## The effective-availability formula (memorize this)

For a SKU at a warehouse, using the live `/inventory` row:

```
effective_available = on_hand - reserved - quarantined - product.safety_stock
```

- `on_hand`, `reserved`, `quarantined` come from `/inventory?warehouse_id=&sku=`.
- `safety_stock` comes from `/products/<sku>`.
- The result **can be negative** — keep the negative value; do not clamp it for reporting
  fields like `target_effective_available` or `requested_effective_available`.
- If a warehouse has no inventory row for a SKU (rare here — coverage is complete), treat
  effective_available as `0 - safety_stock` only if a row truly does not exist; otherwise
  always use the row.

A line/component is:
- **shortage** when `effective_available < required_quantity`,
- **low_stock** when it is coverable (`effective_available >= required_quantity`) but
  `effective_available < product.safety_stock`,
- **ready** otherwise.
(Check `product.active` separately — an inactive product is flagged as inactive regardless
of stock, and may be *both* inactive and short.)

## Status precedence (shared vocabulary)

**Customer / account exception** (derive from `/customers/<id>`; first match wins):
1. `account_status == "blocked"` → account blocked (hardest stop)
2. `risk_flag == "fraud_watch"` → fraud watch
3. `risk_flag == "credit_watch"` → credit watch
4. `account_status == "review_required"` → review required
5. otherwise → none

Account/risk exceptions **outrank inventory and product issues**: if an order is blocked or
under account review, that decision wins even when lines are short or a product is inactive.
Product-master (inactive SKU) problems are *line-level* and do **not** block the whole order
when the account is clean.

**Quality status** lives on `/suppliers/<id>.quality_status` ∈ {`approved`, `watch`,
`quality_hold`}. **Severe** incidents are `severity ∈ {high, critical}`.

## PO and incident conventions

- **Eligible / "timely" / "held" POs** are `status ∈ {open, confirmed}`. `received` and
  `cancelled` POs are ignored.
- **Incident date window**: `GET /incidents?start=&end=` filters on `open_date` with an
  **inclusive string compare** on ISO dates. Always pass the policy's start/end verbatim.
- **Incident duration (calendar days)**: closed = `close_date - open_date`; open (or null
  close_date) = `analysis_date - open_date`. Average over the supplier's filtered incidents.
- **Percentage share** = `100 * supplier_incidents / total_filtered_incidents`, 1 decimal.

## Shipping quotes — let the API do the math

Do **not** recompute freight. Call `GET /shipping/quote` and read its result.
- **Weight** = `sum(line.quantity * product.weight_lb)` over all order lines.
- **Speed** = the **order's own `shipping_speed`** field ∈ {ground, two_day, overnight}.
  Ignore notes asking for a different speed unless the schema clearly wants an alternate quote.
- Pass `warehouse_id` (the order's warehouse), `destination_zip` (the order's zip), `weight_lb`,
  `speed`. Read back `zone_distance`, `service_days`, and `total_cost` (round to 2 dp as
  `total_cost_usd`).

## Pick the right SOP

Match the task to one of the playbooks below and follow that reference file. They share the
formulas above; each adds its own decision table, output assembly, and pitfalls.

| If the task is about… | Use |
|---|---|
| An expedite/dispatch queue: per-order release/hold/review/backorder + shipping quote | `references/sop_expedite_queue.md` |
| A mixed-warehouse allocation wave: per-line ship/transfer/backorder/manual_review | `references/sop_allocation_wave.md` |
| A kit/BOM build replenishment: coverage, transfers, purchase requisitions, exclusions | `references/sop_kit_replenishment.md` |
| A supplier incident scorecard with recommendation codes | `references/sop_incident_scorecard.md` |
| A supplier quality-hold / replenishment-control review (hold POs) | `references/sop_quality_hold_review.md` |

If a new task blends these, take the relevant pieces from each SOP — the building blocks
(effective availability, exception precedence, transfer sourcing, PO eligibility) are shared.

## General workflow

1. `GET /health`; read `answer_template.json` and the local memo/request payload.
2. Determine scope: the set of orders (often via `GET /orders?wave=<WAVE>`), suppliers, or
   BOMs to process. Prefer the live wave membership over a hand-typed list when both exist.
3. For each item, pull every record you need (order, customer, each line's product and
   inventory row, POs, incidents) and compute the shared quantities.
4. Apply the SOP's decision table to get statuses, actions, reason/recommendation codes.
5. Build the lists in the required sort order; dedupe id/sku sets.
6. Compute the summary/rollup (counts, totals, id lists) **from your own records** so they
   are internally consistent.
7. Validate against the template: all keys present, enums valid, money/percent/duration
   rounded, lists sorted. Output the JSON object only.

## Common pitfalls (these cause most misses)

- Forgetting to subtract **safety_stock** (and/or quarantined) from availability.
- **Clamping negative** effective availability to 0 in report fields.
- Using a memo/extract quantity, price, status, or speed instead of the **live** value.
- Quoting shipping at the speed a *note* requested instead of the order's `shipping_speed`.
- Counting `received`/`cancelled` POs as eligible coverage.
- Letting a product-inactive line **block the whole order** (it shouldn't) or, conversely,
  shipping an account-blocked order line (account stop wins everywhere).
- Wrong incident window: off-by-one on inclusive ends, or filtering on the wrong date field
  (`open_date` is the filter field).
- Summary lists/counts that disagree with the per-record decisions — always roll up from the
  records you actually produced.
- Emitting extra prose, omitting required keys, or mis-sorting a list.
