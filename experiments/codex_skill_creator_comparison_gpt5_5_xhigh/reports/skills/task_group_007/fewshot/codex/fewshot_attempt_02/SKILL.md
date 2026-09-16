---
name: northwind-erp-solver
description: Solve Northwind Components ERP decision tasks that require live API lookups and exact JSON output. Use when a prompt provides a Northwind memo and answer template for expedite queues, kit replenishment plans, supplier incident scorecards, warehouse transfer allocation, or procurement-control decisions.
---

# Northwind ERP Solver

## Overview
Use the prompt, payloads, and live ERP records to fill the exact JSON template. Keep output machine-readable, honor every sort order and enum, and round currency and percentages exactly as requested.

## Workflow
1. Read `prompt.txt`, every file under `input/payloads/`, and the matching `answer_template.json`.
2. Treat the template as the source of truth for keys, enum values, ordering, and rounding.
3. Pull only the public ERP records needed for the task from the base URL supplied by the task environment.
4. Compute derived fields before writing output.
5. Return JSON only. Do not add commentary, markdown, or extra keys.

## Shared Calculations
- Compute inventory `effective_available` as `on_hand - reserved - quarantined - safety_stock`.
- Treat positive `effective_available` of 1-10 units as `low_stock` unless the template says otherwise.
- Treat `effective_available < requested quantity` as `shortage`.
- Treat `product.active == false` as inactive stock.
- Compute shipping quote weight as `sum(line.quantity * product.weight_lb)` and call `/shipping/quote` with `warehouse_id`, `destination_zip`, and `weight_lb`.
- Map customer exceptions from account state first, then risk flag: blocked -> `account_blocked`, review_required -> `review_required`, fraud_watch -> `fraud_watch`, credit_watch -> `credit_watch`, otherwise `none`.
- Keep list fields sorted exactly as the template requires.

## Task Patterns
- Expedite queues and order decision files: see [northwind_patterns.md](references/northwind_patterns.md#expedite-queues).
- Kit replenishment runs: see [northwind_patterns.md](references/northwind_patterns.md#kit-replenishment).
- Supplier incident scorecards: see [northwind_patterns.md](references/northwind_patterns.md#supplier-scorecards).
- Mixed warehouse allocation waves: see [northwind_patterns.md](references/northwind_patterns.md#transfer-allocation).
- Procurement-control reviews: see [northwind_patterns.md](references/northwind_patterns.md#procurement-control).

## Output Discipline
- Follow the template's field names exactly.
- Preserve required casing for enums and identifiers.
- Round currency to 2 decimals and percentages to the requested precision.
- Prefer simple derivations over inferred shortcuts when the API exposes the needed records directly.
