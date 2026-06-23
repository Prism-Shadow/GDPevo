---
name: northwind-erp-decision-sop
description: Use this skill for Northwind Components ERP tasks that require structured JSON decisions from orders, inventory, products, customers, suppliers, incidents, BOMs, purchase orders, transfers, shipping quotes, allocation waves, expedite queues, replenishment plans, or supplier quality scorecards. It gives the reusable API workflow, field conventions, calculation habits, decision precedence, sorting, rounding, and validation checks needed for these tasks.
---

# Northwind ERP Decision SOP

Use this playbook when a task asks for a JSON answer based on the Northwind Components ERP API. These tasks usually provide a prompt, one or more memo/policy payloads, and an `answer_template.json`. The job is to combine those local instructions with live ERP records, then return only the requested JSON.

## Source Discipline

Read only the visible task prompt, visible payloads, and public API records. Do not inspect environment source files, previous answers, hidden outputs, judge endpoints, or unrelated attempts. Treat the answer template as the contract: required keys, enum values, ordering, and rounding in the template override any default habit below.

Start from the API base URL provided in the task or environment access file. If several URLs appear, use the runner-provided or environment-access URL first. Check `GET /` to confirm the available public endpoints before querying records.

Useful public endpoints observed for this ERP:

- `GET /products` and `GET /products/<sku>`
- `GET /customers` and `GET /customers/<customer_id>`
- `GET /warehouses`
- `GET /inventory?warehouse_id=&sku=`
- `GET /purchase_orders?supplier_id=&sku=&status=`
- `GET /orders?wave=&required_date=&customer_id=` and `GET /orders/<order_id>`
- `GET /shipping/quote?warehouse_id=&destination_zip=&weight_lb=&speed=`
- `GET /incidents?start=&end=&supplier_id=&sku=&incident_type=&status=`
- `GET /suppliers`
- `GET /boms` and `GET /boms/<bom_id>`

When an endpoint returns more records than expected, filter locally after the API call. Always keep a small local working table keyed by IDs so every output field can be traced back to a record or a stated policy.

## Standard Workflow

1. Extract the requested entity set from the prompt and payloads: wave IDs, order IDs, supplier IDs, BOM IDs, analysis dates, build quantities, required windows, and output sort order.
2. Read the answer template and list the exact enum values, required keys, precision rules, and summary fields.
3. Query the API for the needed live records. Join orders to customers, order lines to products and inventory, products to suppliers, BOM components to products and inventory, and incidents to suppliers.
4. Normalize numeric conventions before making decisions. Keep integer quantities as integers. Use currency rounding only at final output.
5. Apply the task's policy first. If the policy is incomplete, use the conservative precedence rules below and keep them consistent across all rows.
6. Build records in the requested order. Then calculate summary counts and totals from the final records, not from a separate estimate.
7. Validate the final object against the template: required keys present, enums exact, arrays sorted, numbers rounded, and no narrative text outside JSON.

## Shared Field Conventions

Inventory records use `on_hand`, `reserved`, and `quarantined`. Product records include `active`, `safety_stock`, `overstock_threshold`, `supplier_id`, `unit_cost`, and `weight_lb`.

Use these stock calculations unless the task explicitly defines a different formula:

```text
gross_free = on_hand - reserved - quarantined
effective_available = max(0, gross_free - safety_stock)
```

Use `gross_free` to understand whether physical non-reserved stock exists. Use `effective_available` when the task mentions protected stock, safety stock, operating buffer, or asks for an "effective available" field. Quarantined and reserved quantities are never freely available.

For wave-style allocation or dispatch decisions, avoid overcommitting the same stock twice. Maintain a simple ledger by `(warehouse_id, sku)` when multiple lines compete for the same effective stock. Subtract shipped quantities and transfer-source quantities as decisions are assigned in the required output order. If the prompt clearly asks for independent per-order diagnostics rather than a simultaneous allocation, still check duplicate SKU/warehouse combinations and explain the assumption only in scratch work, not in the final JSON.

Customer records use `account_status` and `risk_flag`. Map customer exceptions with this precedence:

```text
account_status == "blocked"          -> account_blocked
account_status == "review_required"  -> review_required or account_review_required
risk_flag == "fraud_watch"           -> fraud_watch
risk_flag == "credit_watch"          -> credit_watch
otherwise                            -> none
```

Do not let a lower-priority risk flag hide a blocked or review-required account.

Product records with `active: false` are product-master exceptions. Do not auto-release inactive SKUs even if stock exists. Put inactive SKUs in the requested exception list and use the template's manual-review or product-master action when available.

## Expedite and Order Release Decisions

For expedite queues and order-level dispatch control:

- Fetch every listed order by ID or by wave, then fetch the customer, each product, target warehouse inventory, and a shipping quote.
- Compute line weight as `line.quantity * product.weight_lb`; order quote weight is the sum across lines.
- Call the quote endpoint with the order warehouse, destination ZIP, total weight, and requested shipping speed. Use `zone_distance`, `service_days`, and `total_cost` from the quote; output the cost with the template's currency field name and two decimals.
- Classify SKU exception lists from line-level checks. Sort SKU lists ascending and make them unique.

Useful inventory status precedence:

```text
inactive + shortage condition -> inactive_and_shortage
inactive product only         -> inactive_sku
gross_free < requested qty    -> shortage
gross_free can cover but effective_available cannot -> low_stock
otherwise                     -> ready
```

When several lines exist in an order, apply the most severe order-level status. A shortage on any active line makes the order a shortage unless an inactive-and-shortage combination is present. Low stock means the order is physically coverable only by consuming protected stock or leaving the buffer under the product safety level.

Useful release-decision precedence when the task does not provide stricter rules:

```text
hard customer stop or fraud/credit hold -> reject_hold or manual_review, hold_credit_or_fraud
review_required account                 -> manual_review, send_account_review
inactive product                        -> manual_review, escalate_product_master
shortage                                -> backorder, create_backorder
low_stock                               -> delayed_release, delay_and_monitor
ready                                   -> ship_now, release_to_pick
```

Use the exact enum names from the answer template. If the template separates `customer_exception`, `final_decision`, and `next_action`, derive each field independently but from the same precedence chain.

## Mixed-Warehouse Allocation and Transfers

For line-level allocation waves:

- Sort and process line actions by `order_id` then `line_id` unless instructed otherwise.
- Evaluate account-level stops before line inventory. Account-blocked, review-required, fraud-watch, and similar customer-risk conditions usually turn every line on that order into `manual_review`.
- Evaluate inactive products before stock movements. Inactive product lines should not become transfer or ship lines.
- For the requested warehouse, output `requested_effective_available` from the ledger before assigning the line.
- If requested effective stock covers the line, action is `ship`, ship quantity is the full requested quantity, transfer fields are zero/null, and backorder is zero.
- If requested effective stock covers part of the line and one other warehouse can cover the remainder from its effective stock, action is `transfer`; keep the requested-warehouse usable quantity as `ship_quantity` and transfer only the uncovered amount.
- If no single source warehouse can cover the uncovered amount and the template does not allow split transfers, use `backorder` for the remaining gap.
- Choose a transfer source deterministically: prefer a warehouse with enough effective stock; break ties by largest surplus after transfer, then by warehouse ID ascending. If the task gives a different tie-breaker, follow it.

Transfer request rows should mirror the line actions exactly. Totals such as `transfer_units` and `backorder_units` should be sums from final line rows.

Order rollups should be derived from final line actions:

- all ship lines -> `ready_to_ship`
- any manual review hard stop -> `manual_review`
- transfer lines with no backorder/manual review -> `needs_transfer`
- any backorder with no manual review -> `has_backorder`
- mixed ship/transfer/backorder states that do not fit a single category -> `mixed_actions`

## BOM, Kit, and Replenishment Planning

For kit-build or replenishment packages:

- Fetch each requested BOM by ID. The memo's target build quantity and build date usually override static BOM target metadata.
- Expand component demand as `target_build_quantity * quantity_per_kit`. If a SKU appears in multiple BOMs, sum the demand into one component row.
- Use the planning warehouse from the memo unless the task asks for each BOM's native warehouse.
- For each component, fetch product master, target warehouse inventory, other warehouse inventory, and open/confirmed POs for that SKU.
- Same-warehouse POs are timely only when their status is allowed by the prompt, their warehouse matches the target warehouse, and `eta <= needed_by`. Sort coverage PO IDs ascending.
- For shared components with multiple need dates, use the earliest relevant build date unless the task asks for staged coverage by date.

Conservative action order:

```text
target is already overstocked             -> overstock_excluded
target effective stock covers demand      -> no_action_stocked
timely same-warehouse POs cover the gap   -> timely_po_covered
inter-warehouse effective stock covers gap -> transfer_only
remaining gap exists                      -> purchase_required
```

Use `overstock_threshold` carefully. If the prompt says to avoid adding stock to an overstocked target, compare target current stock position to the threshold before creating transfers or purchase requisitions.

Purchase requisitions use the product's `supplier_id` and `unit_cost`. `extended_cost = quantity * unit_cost`, rounded to two decimals. Summary purchase cost should equal the rounded sum of requisition extended costs unless the template specifies raw-sum rounding.

Transfer requests should move only effective stock from non-target warehouses. Never use another warehouse's safety stock, reserved stock, or quarantined stock. Sort transfers exactly as requested, often by SKU, quantity descending, then source warehouse.

Excluded components should include a clear template-approved reason such as `target_overstock`, `timely_po_covers_gap`, or `stocked_no_gap`, plus supporting PO IDs when POs are the reason.

## Supplier Incidents and Quality Controls

Incident scorecards and quality-hold reviews usually filter by `open_date`. Use the endpoint `start` and `end` parameters, then verify locally that the inclusive date window is correct. Do not filter by `close_date` unless the prompt explicitly says so.

Incident fields to aggregate:

- `incident_type`: commonly `RMA` or `WORK_ORDER`
- `status`: open incidents have `status == "open"` and usually `close_date: null`
- `severity`: treat `high` and `critical` as severe when the memo says so
- `resolution_cost`: currency, sum and round at output
- `sku`: use for affected SKU sets
- `supplier_id`: join to `/suppliers` for `name` and `quality_status`

For duration metrics:

```text
closed incident duration = close_date - open_date in calendar days
open incident duration   = analysis_date - open_date in calendar days
```

Use normal date subtraction day counts and round averages to the requested precision.

For supplier scorecards:

- Include only suppliers with at least one filtered incident unless the prompt says to review a fixed supplier list.
- `incident_percentage = supplier_incident_count / filtered_incident_count * 100`, rounded to one decimal when requested.
- Count RMA and work-order incidents by exact `incident_type`.
- Count open incidents from `status`, not from missing close dates alone.
- Apply recommendation policies in the exact precedence order provided by the memo. Higher-precedence codes win even if lower conditions also match.
- Sort escalation lists by the policy's stated sort keys, not by the visible scorecard row order.

For procurement-control decisions over target suppliers:

- Review all target supplier IDs, even if one has no recent incidents.
- Collect recent incidents in the stated window, affected SKUs as sorted unique values, and sample incident IDs as sorted IDs capped at the template's maximum.
- Query both `status=open` and `status=confirmed` purchase orders when the prompt says open/confirmed POs.
- If the output has `held_po_ids`, include only POs for suppliers whose decision requires a hold. `monitor_only` suppliers usually have no held POs and should appear in release lists.
- When no explicit thresholds are supplied, use conservative control precedence: `quality_hold` with recent incidents or critical/severe risk -> freeze; `watch` status or material recent RMA/open/severe activity -> buyer review; approved suppliers with low recent activity -> monitor.

## Output Validation Checklist

Before finalizing JSON:

- Top-level keys exactly match the template's required set.
- Each row has all required item keys, even when the value is `0`, `null`, or an empty list.
- Enum strings exactly match the template. Do not invent friendlier labels.
- Sort all arrays as specified. Common defaults are ID ascending, SKU ascending, or explicit multi-key orders.
- Lists of IDs and SKUs are unique unless the template explicitly expects repeated rows.
- Currency fields have two decimals; percentages often have one decimal; duration averages often have two decimals.
- Summary counts are recomputed from final output rows.
- Shipping totals sum the per-record quote costs after applying the task's rounding convention.
- JSON contains no comments, Markdown fences, or narrative text.

When the task is large, write a short scratch script to fetch records, compute fields, and validate the answer object. Keep the final response as pure JSON matching the template.
