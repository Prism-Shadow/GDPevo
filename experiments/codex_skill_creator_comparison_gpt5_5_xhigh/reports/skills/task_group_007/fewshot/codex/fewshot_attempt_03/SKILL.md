---
name: northwind-erp-decisions
description: Solve Northwind Components ERP decision tasks that require strict JSON output from live API data. Use when a prompt references the shared Northwind ERP API, a memo or answer template, and asks for order dispatch, replenishment, supplier incident scorecards, allocation decisions, or procurement controls.
---

# Northwind ERP Decisions

## Overview
Use the staged prompt and answer template as the contract. Pull the live Northwind ERP records, compute the required decisions locally, and return JSON only.

## Workflow
1. Read the prompt, memo, and answer template first.
2. Fetch the needed collections from `TASK_ENV_BASE_URL`.
3. Join and filter records locally.
4. Use [references/northwind_erp.md](references/northwind_erp.md) for endpoint shapes and stock math.
5. Match the template exactly: keys, ordering, enums, null handling, and rounding.

## Rules
- Use the request payload's policy, thresholds, precedence, and date window exactly as written.
- Do not invent missing fields or reorder output keys.
- Round currency to 2 decimals. Follow any other precision rule in the template.
- Sort every list exactly as requested.
- Treat inactive products, blocked or risky accounts, shortages, and overstock as separate control paths.

## Common patterns
### Dispatch and allocation
- Compute line- or order-level stock status from effective stock.
- Quote shipping with warehouse, destination zip, and total line weight.
- Escalate blocked or risky accounts before release.

### Replenishment and BOM planning
- Expand demand from `quantity_per_kit x build_quantity`.
- Compare demand with target warehouse effective stock.
- Count same-warehouse open or confirmed POs that arrive in time as timely coverage.
- Use transfers only for uncovered quantity that another warehouse can supply without protected stock.
- Requisition the remaining gap from the supplier tied to the SKU.

### Supplier quality and incidents
- Filter incidents to the requested window and date field.
- Compute open and closed durations exactly as the memo defines.
- Apply recommendation precedence from the request payload, not from memory.

### Procurement controls
- Aggregate recent incidents, RMAs, open incidents, and held POs by supplier.
- Hold open or confirmed POs for suppliers the policy freezes or sends to buyer review.
- Release only suppliers marked for monitoring.

## Output
Return a single JSON object and nothing else.
