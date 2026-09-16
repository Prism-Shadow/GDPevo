---
name: northwind-erp-ops
description: Solve Northwind Components ERP decision tasks that require reading staged memos/templates, joining live public API data, and returning exact JSON for dispatch-control, replenishment, transfer allocation, supplier incident scorecards, or procurement-quality workflows. Use when a prompt mentions Northwind Components, the task environment API, a queue/memo/answer template, or any of the staged ERP decision files.
---

# Northwind ERP Ops

Read the prompt, the answer template, and every payload file before doing anything else. Then use the public ERP API at the task environment base URL to fill the requested JSON exactly.

## Workflow
1. Identify the task family from the template fields and memo.
2. Fetch the required live records from the public endpoints in [references/northwind-erp.md](references/northwind-erp.md).
3. Join records by ID, compute the requested metrics, and sort every array exactly as the template says.
4. Round money to 2 decimals, percentages to 1 decimal, durations to 2 decimals, and keep dates in `YYYY-MM-DD`.
5. Return JSON only.

## Shared rules
- Treat the template as authoritative for field names, allowed values, and ordering.
- Use `speed`, not `shipping_speed`, when calling `/shipping/quote`.
- Compute effective inventory as `on_hand - reserved - quarantined`.
- Use product `safety_stock` as the operating buffer when deciding whether stock is really available to ship or transfer.
- For shipping quotes, sum `quantity * product.weight_lb` across all lines before calling the quote API.
- Prefer live endpoint data over memo hints when they disagree.

## Dispatch and transfer reviews
- Derive customer exception codes from the customer record.
- Treat inactive products as line-level manual review.
- Ship only the quantity that can be released without breaking the warehouse safety buffer.
- If a line needs more than the local release can supply, transfer the uncovered remainder from eligible stock at another warehouse.
- If no warehouse can cover the remainder, backorder it.
- Use `low_stock` only for lines that can still ship but are operationally tight.

## Replenishment planning
- Expand each BOM into component demand.
- Set `target_effective_available` to the target warehouse's effective availability minus the component safety stock.
- Count `timely_po_qty` only from open or confirmed POs at the target warehouse whose ETA is on or before the build date.
- Use transfers first when other warehouses have effective stock; purchase only the uncovered remainder.
- Exclude components that are already covered or should not receive more stock.

## Supplier quality tasks
- Filter incidents by the memo's window on `open_date`.
- Group by supplier and join supplier master data.
- Compute counts, percentages, costs, durations, open/severe totals, and the ordered recommendation code exactly as the policy says.
- When the schema has a `blocked_orders` field, use it for the account/risk stops the prompt describes; if the template also has separate manual-review fields, keep `review_required` separate from hard blocks. Do not merge the buckets unless the schema does.

## Reference
See [references/northwind-erp.md](references/northwind-erp.md) for endpoint details and recurring formulas.
