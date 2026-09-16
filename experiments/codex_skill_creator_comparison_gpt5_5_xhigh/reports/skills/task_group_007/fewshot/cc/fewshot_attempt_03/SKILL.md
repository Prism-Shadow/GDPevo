---
name: northwind-erp
description: Solve Northwind ERP decision-file tasks from a memo plus answer template by querying the live ERP API and returning strict JSON. Use whenever the user mentions Northwind Components, ERP order waves, BOM replenishment, supplier quality scorecards, allocation or transfer decisions, procurement holds, shipping quotes, or any similar workflow that needs live orders, inventory, products, customers, suppliers, incidents, purchase orders, or BOM data.
---

# Northwind ERP Decision Files

Treat the memo and answer template as the contract. The template defines the exact keys, allowed values, ordering, and rounding; the live API supplies the facts.

## Workflow
1. Read every attached memo and the answer template first.
2. Identify the task family and the fields that matter.
3. Query the live API only for the entities the task needs.
4. Build a scratch table for the facts, then map those facts to the template exactly.
5. Return JSON only. No commentary, markdown, or fenced code.

## Reference
Load [`references/northwind_api.md`](references/northwind_api.md) when you need endpoint names, response fields, or calculation notes.

## Core rules
- Use the live API as the source of truth. Do not rely on cached snapshots or memory.
- Follow memo policy and template precedence literally when they are explicit.
- Keep every array sorted exactly as the template says.
- Round currency to 2 decimals unless the template says otherwise.
- Round percentages and durations to the precision in the template.
- Do not add fields that the template does not ask for.
- Prefer narrow, traceable calculations over clever shortcuts.

## Common task families

### Order waves and allocation files
- Pull orders, customers, products, inventory, warehouses, and shipping quotes.
- Use product `active` as a hard status signal.
- Use inventory `on_hand`, `reserved`, and `quarantined` to compute effective availability.
- If the task needs a shipping quote, quote the requested warehouse, destination zip, weight, and speed from the order or memo.
- Let account, risk, or product blocks override simple stock release when the template or memo says they do.

### BOM and replenishment plans
- Pull BOMs, products, inventory, and purchase orders.
- Compute component demand from `build_quantity x quantity_per_kit`.
- Split coverage into current stock, internal transfers, timely PO coverage, and new purchase needs.
- Exclude components that are already covered or should not receive more stock when the template asks for exclusions.

### Supplier quality and incident scorecards
- Pull incidents and suppliers, and use purchase orders if the memo asks for held or released PO decisions.
- Filter incidents by the memo's window and status rules.
- Count incidents, RMAs, work orders, open cases, and severe cases exactly as requested.
- Apply the recommendation policy in precedence order.

## Final pass
Before you answer, compare the draft against the template one more time:
- top-level keys
- nested keys
- sort order
- enum values
- numeric precision
- presence of every required summary field
