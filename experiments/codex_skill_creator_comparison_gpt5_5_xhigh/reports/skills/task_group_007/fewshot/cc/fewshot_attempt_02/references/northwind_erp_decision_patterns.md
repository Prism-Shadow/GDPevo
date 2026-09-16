# Northwind ERP Decision Patterns

These patterns summarize how to solve Northwind ERP decision tasks without hard-coding any prior answer. Always defer to the current prompt, memo, template, and API records when they disagree with a pattern below.

## Evidence Discipline

Start with a small evidence ledger:

| Need | Typical endpoints |
| --- | --- |
| API shape and hints | `/manifest` |
| Order headers and lines | `/orders`, `/orders/{order_id}` |
| Customer/account status | `/customers`, `/customers/{customer_id}` |
| Product master status and supplier/cost fields | `/products`, `/products/{product_id}` |
| Warehouse metadata | `/warehouses`, `/warehouses/{warehouse_id}` |
| Stock by SKU and warehouse | `/inventory`, `/inventory/{sku}` |
| BOM components | `/boms`, `/boms/{bom_id}` |
| Open or confirmed purchase order coverage | `/purchase_orders`, `/purchase_orders/{po_id}` |
| Supplier quality status | `/suppliers`, `/suppliers/{supplier_id}` |
| Supplier incidents | `/incidents`, `/incidents/{incident_id}` |
| Parcel or freight cost | `/shipping/quote` |

Fetch only public API endpoints. Do not read environment internals. Save raw responses while working if the task is complex; it makes cross-checking cheaper.

## Schema-First Construction

Before doing arithmetic, convert the answer template into a checklist:

- Required top-level keys.
- Required keys for each list item.
- Allowed enum values and nullable fields.
- Sort keys for each list.
- Numeric precision and date inclusivity.
- Summary lists that must be sorted and unique.

Write detail rows in a scratch structure, sort them, then compute the summary from those rows. This prevents mismatches where counts or totals do not agree with the emitted records.

## Inventory And Order Release

Use the live inventory record's own effective/free quantity if it exists. If not, compute effective availability by subtracting quantities that cannot be allocated, such as reserved, quarantined, allocated, committed, safety-stock, or operating-buffer fields. Do not use raw on-hand as releasable stock.

Decision precedence for order or line release tasks:

1. Customer/account stop conditions come first. Blocked, fraud, credit, or review-required statuses normally force hold or manual-review decisions for the affected order.
2. Product master blocks come next. Inactive or otherwise blocked products normally force line-level manual review or an inactive-SKU exception.
3. Inventory comes after account/product checks:
   - Requested warehouse can cover the line: release or ship the requested quantity.
   - Requested warehouse cannot cover the full line but another warehouse has enough free stock for the remaining quantity: ship any usable requested-warehouse quantity and create a transfer for the gap.
   - No warehouse can clear the required quantity: backorder or shortage.
4. If the template distinguishes low-stock from shortage, treat shortage as inability to fulfill the required quantity and low-stock as a post-fulfillment or threshold concern that still deserves listing.

When choosing transfer sources, use only transferable effective stock. If the task asks for one source warehouse, pick one source that can clear the remaining gap using deterministic tie breakers from the memo/template. If multiple sources are allowed, consume sources in a consistent order and then sort the output as requested.

## Dispatch And Expedite Decisions

For expedite or dispatch-control tasks, classify each order from the joined order, customer, product, inventory, warehouse, and quote evidence:

- Inventory status should reflect active product status and stock coverage across all lines.
- Customer exception should reflect the account or risk status, not the operator note alone.
- Final decision and next action should follow the template's allowed labels and the strongest applicable reason.
- Account/risk holds generally take precedence over shortage; product-master issues generally stop automatic release.
- Include SKU exception lists as sorted lists and keep them empty when none apply.
- Quote every requested order when the template requires a quote, even if the fulfillment decision is hold, review, or backorder.

## BOM Replenishment

For kit or BOM replenishment:

1. Expand each BOM component quantity by the requested build quantity.
2. Aggregate total required units by SKU across all requested builds.
3. For each SKU at the target warehouse, compute effective availability and the remaining gap.
4. Count timely same-warehouse purchase orders only when status and expected receipt date make them usable by the need date. Track the PO IDs that cover the gap.
5. Use feasible inter-warehouse transfer quantities before creating purchase requisitions when the memo says transfers can satisfy remaining need.
6. Create purchase requisitions only for the remaining uncovered gap. Use supplier and unit cost from current product or supplier records, and round extended cost at output.
7. Put already-covered or overstocked components into exclusions when the template provides an exclusion section.

Summary values should be calculated from final component rows, transfer requests, purchase requisitions, and the covered-gap quantity from timely purchase orders.

## Supplier Incident Scorecards

For scorecard tasks:

- Filter incidents by the requested date field and inclusive/exclusive window exactly as stated.
- Join supplier names and quality status from current supplier records.
- Count incident types from the API field values, not from incident descriptions.
- Count severe incidents using the severity list supplied in the request.
- For open incidents, compute duration from open date through the analysis date. For closed incidents, compute open date through close date. Use calendar-day arithmetic.
- Percentages use the denominator stated in the request, commonly the full filtered incident population.
- Recommendation codes must be evaluated in the request's precedence order. Stop at the first matching policy code.
- Sort escalation lists using the requested tie breakers.

For highest-cost or highest-share fields, define the candidate metric from the template/request, compute it from supplier rows, and apply deterministic tie breakers when needed.

## Procurement Quality Holds

For replenishment-control tasks by supplier:

1. Filter to target suppliers and the requested analysis window.
2. Count recent incidents, RMA incidents, severe/critical incidents, open incidents, affected SKUs, and sample incident IDs from the filtered incident set.
3. Join supplier quality status from `/suppliers`.
4. Join open or confirmed purchase orders from `/purchase_orders`.
5. Apply the memo's decision choices and policy:
   - Quality-hold suppliers with recent quality risk usually freeze new replenishment.
   - Watch suppliers with stronger recent severe/RMA signals usually require buyer review.
   - Suppliers without a hold/review decision should monitor only and have no held POs unless the template says otherwise.
6. Top-level held PO lists should be sorted unique unions of the supplier-level held lists.
7. Release supplier IDs should include only suppliers whose final decision is the monitor/release choice in the current template.

## Shipping Quotes

Use order, warehouse, customer destination, requested service speed, and memo overrides to build quote requests. Query the API rather than recreating pricing rules. Round quote costs to the precision requested in the template. Preserve integer service-day and zone-distance fields if the quote endpoint provides them.

## Final Checks

- All required keys are present at every level.
- Arrays are sorted exactly as requested.
- Summary counts match detail arrays.
- Currency, percentages, and average durations use the specified precision.
- ID lists are sorted and deduplicated unless the template says otherwise.
- No final values are borrowed from prior examples.
