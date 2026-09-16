---
name: northwind-erp-desk
description: Solve Northwind Components ERP desk tasks that turn a prompt, memo, and live task-environment API data into a strict JSON answer. Use when asked to prepare expedite queue decisions, allocation or transfer reviews, replenishment plans from BOMs, supplier incident scorecards, or procurement-control decisions from the shared Northwind ERP API and an answer template.
---

# Northwind ERP Desk

## Overview

Turn staged task payloads and live ERP records into the exact JSON object required by the answer template.

## Workflow

1. Read `prompt.txt`, every file under `input/payloads/`, and `answer_template.json`.
2. Treat the template as the contract. Use its exact field names, enum values, required keys, ordering rules, and precision rules.
3. Use the runner-supplied task base URL. Query `GET /manifest` when you need to confirm the available record shapes, then fetch only the records required from the live API.
4. Join the live records back to the memo, compute the requested decisions, and sort every list exactly as instructed.
5. Return JSON only. Do not add prose, fences, or commentary.

## Common API Areas

- Use `/orders`, `/customers`, `/products`, `/inventory`, `/warehouses`, and `/shipping/quote` for expedite and allocation tasks.
- Use `/boms`, `/products`, `/inventory`, `/warehouses`, and `/purchase_orders` for replenishment tasks.
- Use `/incidents` and `/suppliers` for supplier scorecards and procurement-control tasks.
- Use `/purchase_orders` when a task needs holds, releases, coverage, or timely supplier supply checks.

## Common Task Families

### Expedite and Allocation

- Derive each order or line decision from live order, customer, product, warehouse, and inventory state.
- Use effective availability, protected-stock rules, and customer-risk or product-status checks before deciding ship, transfer, backorder, manual review, hold, or reject.
- Keep shipped quantity, transfer quantity, and backorder quantity separate.
- Mark blocked orders only for account or risk stops, not for line-only product issues.
- Include shipping quotes from the live API when the template asks for them.

### Replenishment

- Expand each BOM to component demand from the requested build quantity.
- Compare total required units with target-warehouse stock, timely same-warehouse purchase orders, and feasible inter-warehouse transfers.
- Create purchase requisitions only for the remaining gap.
- Mark components as excluded when existing stock or timely POs already cover them, or when the template says the target is overstocked.

### Supplier Risk and Procurement Control

- Filter incidents to the requested analysis window.
- Aggregate counts, percentages, costs, durations, open counts, and severe counts per supplier.
- Apply the supplied recommendation precedence exactly.
- For procurement-control tasks, also collect affected SKUs and hold or release open and confirmed purchase orders as directed by the policy.

## Normalization

- Preserve exact field names from the template.
- Sort identifiers ascending unless the template says otherwise.
- Round currency to two decimals.
- Round percentages and durations to the precision stated by the template or memo.
- Use empty lists instead of null unless the template explicitly allows null.
- Recheck the final JSON against the template before returning it.
