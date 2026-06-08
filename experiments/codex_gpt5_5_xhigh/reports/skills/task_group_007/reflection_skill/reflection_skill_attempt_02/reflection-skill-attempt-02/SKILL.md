---
name: reflection-skill-attempt-02
description: Use for PanofyBench Northwind Components ERP tasks that require API-backed order dispatch, warehouse allocation, BOM replenishment, supplier incident scorecards, or procurement quality controls. The skill emphasizes a blind API-first workflow, JSON-template fidelity, protected-stock math, policy precedence, and common pitfalls found by reflection.
---

# Northwind ERP Reflection

## Workflow

1. Read the task prompt, visible memo/request payloads, and answer template first.
2. Use only the API base URL allowed by the user or runner. If the prompt mentions a default port but the user gives another base URL, the user boundary wins.
3. Query public endpoints rather than local environment files. Useful endpoints are usually exposed at `/`: products, customers, warehouses, inventory, purchase orders, orders, shipping quotes, incidents, suppliers, and BOMs.
4. Build the answer blind from API records, then validate the shape against the template: required keys, enum values, ordering, rounding, and exact field names.
5. Return only JSON for task answers. Keep records sorted exactly as the template requires.

Use `curl --noproxy '*'` or a proxy-disabled HTTP client for local API calls. Do not inspect env files, evaluator code, test tasks, hidden notes, or answer files while solving.

## Output Rules

- Preserve the template's top-level keys and nested item keys.
- Sort IDs lexicographically unless the template gives a different sort.
- Currency and costs: round to 2 decimals.
- Percentages: round to 1 decimal when requested.
- Average durations: use calendar-day differences and round to 2 decimals.
- Do not clamp numeric availability fields unless the field specifically asks for shippable quantity. Report raw effective availability when the template asks for it, even when negative.

## Inventory Math

Use protected-stock math consistently:

```text
free_before_buffer = on_hand - reserved - quarantined
effective_available = on_hand - reserved - quarantined - product.safety_stock
```

Important consequences:

- `effective_available` may be negative and should stay negative in reported availability fields.
- Safety stock is protected. If `effective_available < requested_quantity`, classify the line/component as short even when physical free stock exists.
- Shippable quantities cannot be negative: use `max(0, min(quantity, effective_available))`.
- For source warehouses, transfer only positive effective availability and never consume protected stock.
- If choosing one transfer source, prefer a warehouse that can cover the uncovered quantity; break ties by greater effective availability, then warehouse ID ascending. For replenishment plans, allocate multiple sources by quantity descending, then warehouse ID ascending if needed.

For expedite queue exception lists:

- `shortage_skus`: active or inactive SKUs whose effective availability is below the ordered quantity.
- `inactive_skus`: SKUs whose product master has `active: false`.
- `low_stock_skus`: coverable active SKUs with scarce effective availability after the protected buffer is respected. Include low-stock exceptions even when another SKU on the same order drives the final shortage decision.
- Inventory status precedence is inactive plus shortage, inactive only, shortage, low stock, ready.

## Customer And Product Precedence

Account and risk status can stop a release even when inventory is available.

- `account_status: blocked` -> account-blocked/manual-hold behavior.
- `risk_flag: fraud_watch` or `credit_watch` -> risk hold behavior.
- `account_status: review_required` -> manual account review.
- Product inactive -> manual product review when no account/risk condition already controls the line.

For order-level expedite decisions, account review takes precedence for the next action when the customer is review-required. Account blocked or fraud/credit watch maps to a hold/reject decision. With no customer stop, shortage maps to backorder, low stock to delayed monitoring if the template supports it, and ready stock to release.

For transfer-wave line decisions, apply account/risk review to every line on the order before product or stock actions. `blocked_orders` means orders stopped by account or customer risk, not product-only manual reviews.

## Dispatch And Shipping

For expedite or release-control tasks:

1. Fetch each order, customer, product, warehouse inventory, and shipping quote.
2. Compute line exceptions with protected-stock math.
3. Compute shipping quote from the order warehouse, destination ZIP, total order weight, and requested speed. Use API quote fields for zone distance, service days, and total cost.
4. Summary lists should be derived from final decisions, not from raw statuses.

## Transfer Allocation

For mixed-warehouse order waves:

- `requested_effective_available` is the raw protected-stock value and may be negative.
- `ship`: requested warehouse effective availability covers the full line.
- `transfer`: requested warehouse cannot cover the full line, but one source warehouse can cover the uncovered quantity from positive effective availability. Put any positive requested-warehouse coverage in `ship_quantity`.
- `backorder`: no source can clear the remaining quantity. Backorder only the unfilled quantity after positive requested-warehouse coverage.
- `manual_review`: account, risk, or inactive-product status prevents automatic release; quantities should be zero.
- Roll up orders from line actions: all ship -> ready to ship; only ship/transfer -> needs transfer; ship/backorder -> has backorder; all manual -> manual review; otherwise mixed actions.

## BOM Replenishment

For kit-build replenishment:

1. Expand each BOM by requested build quantity and aggregate required units by SKU.
2. Compute target warehouse effective availability with the raw formula, allowing negative values.
3. Eligible timely POs are same-warehouse, `open` or `confirmed`, and ETA on or before the component's needed build date. Count them even if the ETA is before the planning date and the status is still open/confirmed.
4. If target on-hand or effective stock exceeds the product overstock threshold, exclude the component as `target_overstock` and do not transfer or buy more.
5. If timely POs cover the gap, mark `timely_po_covered`, record coverage PO IDs, and exclude as `timely_po_covers_gap`.
6. Otherwise use positive effective stock from other warehouses for transfers, then create purchase requisitions for the remaining gap.

When a component appears in multiple builds, compute purchase `needed_by` from cumulative demand: existing target stock and transfers can cover earlier builds, while any purchase residual may be due by the later build date where the cumulative gap appears. Transfer `needed_by` is the first build date where transferred stock is needed.

Summary totals:

- `total_purchase_units`: sum purchase requisition quantities.
- `total_purchase_cost`: sum rounded extended costs.
- `total_transfer_units`: sum transfer quantities.
- `timely_po_covered_units`: units of the gap covered by timely POs, using `total_required - target_effective_available`, not a zero-clamped gap.

## Supplier Incident Scorecards

Filter incidents by the requested incident date field, usually `open_date`, with inclusive start and end dates. Include only suppliers with at least one filtered incident.

Metrics:

- Severe incidents are severity `high` or `critical`.
- Open incident count uses `status: open`.
- RMA/work-order counts use `incident_type`.
- Closed duration is `close_date - open_date`; open duration is `analysis_date - open_date`.
- Percent denominator is the full filtered incident population.

Recommendation precedence matters:

1. `ESCALATE_SUPPLIER`: quality-hold supplier with at least 3 filtered incidents, any critical RMA, or at least 3 RMAs with total filtered resolution cost at or above the policy threshold.
2. `PROCESS_REVIEW`: work-order incidents are at least 3 and exceed RMA incidents.
3. `WATCHLIST`: supplier status is watch/quality-hold, incident count/cost/severe counts meet policy thresholds.
4. `MONITOR`: no higher rule applies.

Because precedence is strict, a supplier can be `PROCESS_REVIEW` even if watchlist-style conditions are also true.

## Procurement Quality Controls

For supplier replenishment-control reviews:

- Build each supplier row from recent incidents in the requested window, supplier quality status, and purchase orders.
- `affected_skus` is the sorted unique SKU set from recent incidents.
- `sample_incident_ids` is the sorted incident ID list, capped at 5.
- A practical decision policy is: quality-hold suppliers freeze new replenishment; watched suppliers with multiple severe/critical recent incidents require buyer review; otherwise monitor only.
- Hold PO IDs only for suppliers with freeze or buyer-review decisions. Use `open` or `confirmed` POs, sorted ascending, and cap the list at 5 when many POs qualify. Monitor-only suppliers have no held POs and belong in `release_supplier_ids`.

## Common Pitfalls

- Do not use `on_hand - reserved - quarantined` as availability for decisions; subtract safety stock too.
- Do not clamp effective availability to zero in fields named effective availability.
- Do not treat every watch-status supplier as buyer review; apply the task policy and severity thresholds.
- Do not hold every open PO for a supplier when the expected control file caps actionable PO IDs.
- Do not let inactive product review override an account-level hold on an already stopped order line.
- Do not infer answers from train examples or hard-code task IDs, SKUs, suppliers, or PO IDs. Recompute from the live API and the visible payload every time.
