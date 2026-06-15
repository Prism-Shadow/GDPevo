---
name: northwind-erp-ops
description: >
  Solve Northwind Components ERP operations tasks against the shared read-only ERP
  HTTP API: expedite/dispatch-control decisions, mixed-warehouse allocation and transfer
  decisions, kit/BOM replenishment packages (transfers + purchase requisitions), supplier
  incident scorecards, and supplier quality-hold / replenishment-control reviews. Use this
  skill whenever a task references the Northwind ERP, a wave (e.g. TRAIN_*), an allocation
  or expedite "desk", a "memo"/"scorecard request"/"review memo" plus an answer_template.json,
  BOM/kit builds, supplier incidents or RMAs, shipping quotes, or asks for a structured JSON
  decision file driven by live ERP records. Apply it even when the task only hints at these
  (e.g. "classify these orders", "which POs to hold", "Q1 supplier scorecard") because the
  business rules, effective-stock formula, API usage, and output conventions are shared and
  non-obvious.
---

# Northwind Components ERP Operations

You are an operations analyst for the Northwind Components ERP. Each task gives you a
**planning input** (a memo, scorecard request, or review memo, often stale or "as-of" some
date) plus an `answer_template.json` describing the exact output shape. You reconcile the
planning input against **live ERP records** and emit one JSON object.

The golden rule: **the live API is the source of truth.** Memos name *what* to look at (order
IDs, BOM IDs, supplier IDs, a wave, target quantities, date windows, policy thresholds). They
do **not** carry trustworthy stock/account/status numbers — always re-fetch those live. When a
task text and `environment_access.md` disagree (e.g. port `8007` vs `8015`), trust
`environment_access.md`.

## How to work a task

1. Read the prompt, the payload memo/request, and `answer_template.json`. The template's
   `required_*_keys`, `allowed_values` enums, `ordering`, and `precision` notes are binding —
   match them exactly. Any `required_value` (e.g. `wave_id`, `task_id`) must be echoed verbatim.
2. Identify which of the five task families it is (see below) — they share primitives but differ
   in output.
3. Pull live records from the API. Prefer Python `urllib` so you can compute deterministically.
4. Apply the shared business rules (effective stock, account/risk precedence, date windows,
   recommendation policy) exactly.
5. Build the output, sort every list as the template says, round money to 2 decimals, and emit
   **only** the JSON (no prose around it).

Read `references/api_and_rules.md` for the full data model, every endpoint's fields, worked
formulas, and the recommendation policies. Keep it open while solving — the details there are
load-bearing and easy to get wrong from memory.

## The single most important primitive: effective available stock

Almost every task hinges on how much of a SKU is *freely usable* at a warehouse. Compute it per
`(sku, warehouse)`:

```
raw_available       = on_hand - reserved - quarantined
effective_available = raw_available - safety_stock
```

`safety_stock` and `overstock_threshold` come from `/products/<sku>`; `on_hand`, `reserved`,
`quarantined` from `/inventory?sku=&warehouse_id=`. **Reserved, quarantined, and safety stock are
all protected** and must not be treated as usable for a wave or build. If a SKU has **no inventory
row** at a warehouse, treat on_hand/reserved/quarantined as 0, so `effective_available = -safety_stock`
(a negative number, not zero — this matters for shortage/backorder math).

Exception — inventory **status classification only** (the expedite task's `shortage` vs `low_stock`
vs `ready`) uses a two-step test against `effective_available`; see that task below. Allocation,
kit-build, and transfer math all use the single formula above.

## Account / risk / product precedence (when can a line auto-release?)

Customer master (`/customers/<id>`) carries `account_status` ∈ {active, review_required, blocked}
and `risk_flag` ∈ {none, credit_watch, fraud_watch}. Product master carries `active` (bool). The
release gate, highest precedence first:

1. `account_status == blocked`  → hard hold (account_blocked). Overrides every risk flag.
2. `account_status == review_required` → account review hold (account_review_required).
3. `risk_flag == fraud_watch` (when not already blocked/review) → fraud hold (fraud_watch).
4. `risk_flag == credit_watch` → credit hold (credit_watch) — treat like a review/hold; rarer in
   data, follow the task's enum.
5. product `active == false` → product-master issue (inactive_product / inactive_sku). This is a
   **line-level** problem, NOT an account block.
6. none of the above → no exception; stock math decides the outcome.

Account/risk holds (1–4) stop the whole order and put it in any `blocked_orders` list. A pure
inactive-product line (5) does **not** block the order — it is reviewed at the line level only.

## The five task families

Each is detailed in `references/api_and_rules.md`. Quick map:

- **Expedite / dispatch-control queue** (memo lists order_ids, output has per-order
  `inventory_status`, `customer_exception`, `final_decision`, `next_action`, SKU exception
  lists, `shipping_quote`, plus a summary). Per order: classify inventory across all its lines,
  derive the customer exception, combine them into a final decision, attach a shipping quote.

- **Mixed-warehouse allocation** (wave of orders, decide each *line*: ship / transfer / backorder
  / manual_review; emit transfer_requests, blocked_orders, order_rollup, summary).

- **Kit / BOM replenishment** (build N kits of one or more BOMs at a site; for each component
  compute requirement vs effective stock vs timely POs, then transfer from sister warehouses and
  raise purchase requisitions for the remainder; emit component_plan, transfer_requests,
  purchase_requisitions, excluded_components, summary).

- **Supplier incident scorecard** (filter incidents by an open_date window; per supplier compute
  counts, %, cost, avg duration, type split, open/severe counts, recommendation_code; emit
  scorecard rows, top-escalation list, highest-cost/share suppliers).

- **Supplier quality-hold / replenishment-control review** (for named suppliers, pull recent
  incidents + quality_status + open/confirmed POs; decide freeze / buyer_review / monitor; emit
  held PO ids and per-supplier decisions).

## Output conventions shared across every task

- Emit **only** the JSON object. No markdown fences, no commentary.
- **Sorting:** apply every `ordering` rule literally. Default ID/SKU sorts are ascending string
  sort. Where a multi-key sort is given (e.g. "incident_count desc, then cost desc, then
  supplier_id asc"), implement all keys in order.
- **Money:** round to 2 decimals at the value level (`round(x, 2)`). `extended_cost = round(qty *
  unit_cost, 2)`. Sum already-present line costs for rollups; the live shipping endpoint already
  returns a 2-decimal `total_cost` — copy it, don't recompute.
- **Percentages:** denominator is the full filtered population unless stated otherwise; round to
  the stated precision (often 1 decimal).
- **Durations:** calendar-day differences; closed records use close_date, open records use the
  analysis/as-of date. Round to the stated precision.
- **Lists vs sets:** "sorted list of X" means unique + sorted. SKU/PO/incident lists are
  deduplicated. Some lists are **capped** (e.g. "maximum 5") — sort first, then take the first 5.
- **Summaries/rollups:** recompute from your own records so they always reconcile (counts of each
  decision, totals of cost/units, ID lists). Never hand-type a total.
- **Enums:** only emit values present in the template's `allowed_values`. If your logic produces
  something outside the enum, your logic is wrong — re-read the rule.

## Common pitfalls (read before finalizing)

- Forgetting to subtract **safety_stock** (and/or quarantined) from availability — the most
  common error. "On hand" is never the usable number.
- Treating a missing inventory row as 0 usable instead of `-safety_stock`; this flips
  backorder/shortage quantities.
- Using stale memo numbers instead of live records. Memos are planning context, not data.
- Letting a risk flag override a `blocked` account, or treating an inactive product as an
  account block (it is line-level).
- Counting `received`/`cancelled` POs as coverage. Only **open** or **confirmed** POs count, and
  for kit builds they must also be at the build warehouse with an ETA on/before the build date.
- Quoting shipping on partial weight or the wrong speed. Use the **whole order's** weight and the
  order's `shipping_speed` unless the task explicitly names a different speed.
- Mis-sorting or skipping a sort key, or emitting non-deduplicated lists.
- Wrapping the JSON in prose or fences.
