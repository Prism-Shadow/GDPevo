# Output Conventions

This document specifies the formatting and structural rules for JSON output in ERP finance review tasks.

## General Rules

1. Return **JSON only**. No narrative text, explanations, or markdown outside the JSON structure.
2. Match the supplied answer template exactly: follow all required keys, allowed enum values, key order, and type constraints.
3. If a template specifies a `required_top_level_keys` list, output those keys in that order.

## ID List Ordering

All lists of identifiers (claim IDs, business IDs, invoice IDs, close log IDs) must be sorted in **ascending lexicographic order** unless the template specifies another ordering.

Examples:

- `["CLM-2025-0015", "CLM-2025-0037", "CLM-2025-OPS-017"]` — standard lexicographic
- `["BUS-2025-0006", "BUS-2025-0009", "BUS-2025-0018"]` — numeric ID parts sorted as strings

For invoice lists tied to a scope file, preserve the scope file's order.

## Numeric Precision

Currency amounts are in **USD** with exactly **2 decimal places**.

- `1842.36`, `0.00`, `287918.71` — always 2 decimals
- When computing totals, sum first, then round to 2 decimals to avoid cumulative rounding error
- Use `0.00` for zero amounts, never `0` or `null`

Counts are whole integers.

## Enum Values

Use allowed enum values exactly as defined in the template:

- `approve`, `awaiting_information`, `escalate` — not `Approved` or `Escalate`
- `release`, `hold`, `escalate` — not `Release` or `Hold`
- `reconciled`, `variance_review`, `requires_reconciliation` — exact spelling
- `blocked`, `open_payables`, `ready_to_close` — exact spelling
- `ready_to_send`, `needs_ap_refresh`, `blocked` — exact spelling

## Boolean and Empty Values

- Boolean values: use JSON `true` and `false` (lowercase).
- Empty lists: use `[]`.
- Empty objects: use `{}`.
- No `null` values unless the template explicitly allows them.

## Object Key Order

When an answer template provides a `top_level_order` array, output keys in that exact order. Otherwise, follow the `required_top_level_keys` order. Within nested objects, follow the template's `required_keys` order.

## Field-Specific Rules

### Per-Business Objects

For vendor review tasks, the `hard_stop_flags` values are always alphabetically sorted lists. An empty flags list is `[]`, never omitted.

### Per-Claim Objects

For stale snapshot tasks, every candidate claim ID must appear as a key in `stale_snapshot_corrections` and `ap_balance_by_claim`, even if the value is `current_snapshot_ok` or `0.00`.

### In-Scope Lists

For prepaid reconciliation, `selected_invoice_ids` preserves the scope file order. All other ID lists are sorted ascending.
