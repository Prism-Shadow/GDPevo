---
name: northwind-erp
description: Build strict JSON decision files for Northwind Components ERP tasks from a local memo/template pair and the live public API. Use this whenever the user needs a dispatch-control answer, transfer or allocation review, replenishment or BOM plan, supplier quality scorecard, or any other Northwind ERP output that must be assembled from live records, even if the request only says "fill the template" or names a wave/task id.
---

# Northwind ERP

Use the live ERP API. Do not infer values from the memo alone. Work from the answer template, fetch the needed records, and fill only the required JSON keys.

## Workflow

1. Read the task prompt, payload files, and answer template first.
2. Use `environment_access.md` for the base URL and allowed endpoints.
3. Use [`scripts/northwind_erp.py`](scripts/northwind_erp.py) for lookups and arithmetic.
4. Build the JSON exactly to the template:
   - preserve required key order
   - sort lists as requested
   - round currency to 2 decimals
   - round percentages to 1 decimal only when the template asks for it
   - return JSON only, with no prose

## Shared rules

- Use the live API, not the staged answers.
- Treat missing fields as a signal to inspect the record type directly.
- Do not depend on `/manifest`; use the endpoints listed in `environment_access.md`.
- Use product data for `active`, `safety_stock`, `overstock_threshold`, `supplier_id`, `unit_cost`, and `weight_lb`.
- Use inventory records as warehouse-level snapshots.
- Use customer account status and risk flags to determine release blockers.
- Use PO `status` and `eta` to decide whether coverage is timely.
- Use BOM target quantities and build dates exactly as provided in the memo.
- When calling `/shipping/quote`, pass the order's `shipping_speed` as `speed`.

## Core math

Use this baseline for planning stock unless the template defines a different projection:

```text
effective_available = on_hand - reserved - quarantined - safety_stock
```

Use the same inventory snapshot to derive source-warehouse surplus, target-warehouse gaps, and line-level release decisions.

For transfers, the movable source-side surplus is the same inventory baseline on the sending warehouse:

```text
transferable_surplus = on_hand - reserved - quarantined - safety_stock
```

## Dispatch / expedite tasks

- Classify the customer first.
  - `blocked` or `credit_watch` means an account-level hold.
  - `review_required` means manual review.
  - `fraud_watch` is also a hard stop.
- Then classify each line from the requested warehouse inventory.
  - `ready`: enough effective stock and not a thin buffer.
  - `low_stock`: releasable, but the remaining buffer is thin.
  - `shortage`: not enough effective stock.
  - `inactive_sku`: the SKU is inactive.
  - `inactive_and_shortage`: both conditions appear.
- If a line is blocked by customer status, do not try to fix it with inventory.
- If another warehouse can cover the uncovered quantity without stripping that warehouse too far, use a transfer.
- Otherwise backorder the unmet units.
- If the template asks for a blocked-order list, include every order stopped by account or risk logic, including review-required holds, and leave out product-only issues.
- Roll up the order by the strongest blocker:
  - `ready_to_ship`
  - `needs_transfer`
  - `has_backorder`
  - `manual_review`
  - `mixed_actions`

## Replenishment / kit build tasks

- Expand every target BOM into component demand.
- Compute `total_required` as `quantity_per_kit * build_quantity` across the requested BOMs.
- Compute target-warehouse effective availability from the live inventory snapshot.
- Count only same-warehouse `open` or `confirmed` POs whose ETA is on or before the needed date as timely coverage.
- If timely coverage closes the gap, mark the component as covered and exclude it.
- If stock already covers the gap, mark it as overstocked or stocked-no-gap, depending on the template wording.
- Otherwise:
  - use transfers from other warehouses for the portion that is realistically movable
  - purchase the remainder from the product's supplier
- Do not invent supplier IDs or unit costs; take them from the product master.
- When several sources can move the same SKU, prefer the fewest sources that satisfy the gap and keep a sensible buffer on the sending side.

## Supplier quality scorecards

- Filter incidents to the requested date window.
- Group by `supplier_id`.
- Count incidents, RMAs, work orders, open incidents, and severe incidents.
- Compute average duration from open-to-close for closed incidents, or open-to-analysis date for open incidents.
- Sum resolution cost with currency precision.
- Apply recommendation precedence exactly as stated in the task memo.
- Build `top_escalation_suppliers` only from suppliers whose recommendation is `ESCALATE_SUPPLIER`, sorted by the task's rule.

## Final check

Before you finish, compare the output against the template one more time:

- required keys present
- lists sorted correctly
- enums only from the template
- numbers rounded correctly
- no extra prose or wrapper text
