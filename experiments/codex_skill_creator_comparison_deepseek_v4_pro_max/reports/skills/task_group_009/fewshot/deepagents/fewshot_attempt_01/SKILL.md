---
name: crescent-finance-ops
description: "Crescent Arts Collective Finance Ops API reporting for branch financials, ensemble compensation, and production payroll. Use when a task involves the Crescent Finance Ops API (base URL in environment_access.json or environment_access.md), references endpoints under /api/finance/, /api/compensation/, or /api/payroll/, and asks for a structured JSON result from a request memo and answer template. Triggers on phrases like branch close, regional view, compensation summary, board forecast, payroll review, or request_memo.json with answer_template.json."
---

# Crescent Finance Ops

## Overview

Query the Crescent Finance Ops REST API and compute structured JSON answers for branch reporting, ensemble compensation, and production payroll. Every task supplies a base URL, a request memo, and an answer template. Fetch all needed API data in one pass, compute, and emit a single JSON object matching the template.

## Three Domains

Tasks fall into one of three domains. Read the corresponding reference file before computing results:

| Domain | Reference | Endpoints |
|--------|-----------|-----------|
| Branch financials | [references/finance.md](references/finance.md) | /api/finance/branches, /api/finance/period-map, /api/finance/accounts, /api/finance/records |
| Ensemble compensation | [references/compensation.md](references/compensation.md) | /api/compensation/rate-book, /api/compensation/rosters, /api/compensation/scenarios |
| Production payroll | [references/payroll.md](references/payroll.md) | /api/payroll/rate-book, /api/payroll/productions |

## Workflow

1. Read request_memo.json (or its equivalent) to identify the task type, target entity, and reporting focus.
2. Read answer_template.json to understand required keys and field types.
3. Fetch every endpoint listed for the domain. GET with no auth. Parse with a JSON parser, never invent a format.
4. Read the domain reference file and compute every value the template demands.
5. Assemble the result as one JSON object. Round currency to 2 decimals and ratios to 4 decimals. Order lists as the template specifies (ascending IDs, ascending musician IDs, rate-book order for pay types, alphabetical for conflict flags). Use integer types for counts and ranks.
6. Return only the JSON object. Do not wrap it in markdown or add commentary.

## Common Conventions

- Period map: M1-M12 = FY2024, M13-M24 = FY2025. Always confirm against the /api/finance/period-map response.
- Ranking: Use descending rank (1 = best / highest) unless the template says ascending.
- Sum-of-parts consistency: When a region total is the sum of its branch totals, sum the individual branch values rather than re-aggregating from raw records. The reconciliation variance checks this.
- Template compliance: Every top-level key in the answer template must appear in the output. Do not add extra keys.
