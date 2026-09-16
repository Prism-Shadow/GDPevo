---
name: crescent-finance-ops
description: Compute branch close reporting, regional management views, compensation summaries, compensation forecasts, and weekly payroll reviews for Crescent Arts Collective against the Crescent Finance Ops REST API. Use when the task environment provides a base URL, a request memo, and an answer template for any Crescent finance, compensation, or payroll reporting task.
---

# Crescent Finance Ops

## Workflow

Every task in this domain follows the same pattern:

1. Read `payloads/environment_access.json` — extract `base_url`.
2. Read `payloads/request_memo.json` — extract target entity IDs, period ranges, focus list.
3. Read `payloads/answer_template.json` — the exact JSON shape to return. Never add or omit keys.
4. Query the relevant API endpoints (see Domain Dispatch below).
5. Compute metrics using the formulas in the reference files.
6. Return exactly one JSON object matching the template.

Use `curl -s "<base_url>/endpoint?params"` for every API call. Parse JSON with `python3 -c` or `python3 -m json.tool`.

## Domain Dispatch

Match the task's required endpoints to the domain:

| Domain | Endpoints | Reference |
|---|---|---|
| Finance (branch/regional reporting) | `/api/finance/*` | [references/finance.md](references/finance.md) |
| Compensation (summaries, forecasts) | `/api/compensation/*` | [references/compensation.md](references/compensation.md) |
| Payroll (weekly review) | `/api/payroll/*` | [references/payroll.md](references/payroll.md) |

## Output Conventions (all domains)

- **Currency values**: 2 decimal places. Use standard round-half-up. In Python: `Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)`.
- **Percent/ratio values**: 4 decimal places. Use standard round-half-up. In Python: `Decimal(str(value)).quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP)`.
- **Lists of IDs**: ascending stable order unless the template says "rank_desc" or similar.
- **Enums**: use exact string values from the template.
- **Keys**: include every key in the template; never add extras.
- **Period convention**: M1–M12 = "FY2024", M13–M24 = "FY2025".

## Cross-Domain Rules

- Always cross-check that the computed total equals the sum of its parts.
- For reconciliation fields: compute both the aggregate and the sum-of-parts; the difference should be 0.0.

## Verification

Before submitting, verify:

1. Every required top-level key from the answer template is present.
2. All currency values are rounded to 2 decimals using standard round-half-up.
3. All percent/ratio values are rounded to 4 decimals using standard round-half-up.
4. Lists use the template-prescribed ordering.
5. Enum values match the template exactly (case-sensitive).
6. The output is a single JSON object — no wrapping array, no extra text.
