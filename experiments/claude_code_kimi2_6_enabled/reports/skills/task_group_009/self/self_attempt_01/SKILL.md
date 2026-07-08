# Crescent Arts Collective — Finance Ops Reporting

## Environment & API
- Always use the remote base URL from `environment_access.md` (`GDPEVO_ENV_BASE_URL`). Do not use localhost or `127.0.0.1` even if staged JSON files list them.
- Do not read, list, or enter any `env/` source directory. Interact only with the remote API.

### Endpoint families
| Domain | Endpoints |
|---|---|
| Finance | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` |
| Compensation | `/api/compensation/rate-book`, `/api/compensation/rosters`, `/api/compensation/scenarios` |
| Payroll | `/api/payroll/rate-book`, `/api/payroll/productions` |

## General workflow
1. Read `environment_access.md` to get the true remote base URL.
2. Read `payloads/request_memo.json` to extract targets (branch/region/ensemble/production IDs, periods, years, scenario ID).
3. Read `payloads/answer_template.json` to identify required top-level keys, field types, and ordering rules.
4. Fetch all necessary data from the relevant Finance Ops endpoints.
5. Compute derived values, apply rounding, sort/order collections, and assemble a **single JSON object** matching the template exactly.

## Rounding
- **Currency**: round to **2 decimals**.
- **Percent / ratio fields** (e.g., `revenue_growth_pct`, `ebitda_margin`, `growth_rates`): round to **4 decimals** as decimal values (e.g., `0.1234` for 12.34%).

## Ordering & ID conventions
- Lists of IDs (`branch_ids`, `branch_ids` in region context, etc.) must be **ascending** (stable sort) unless a rank field explicitly states otherwise.
- `per_musician` arrays must be ordered by `musician_id` ascending.
- `conflict_flags` must be sorted **alphabetically**.
- `pay_types` must follow the order returned by the rate book.

## Financial calculation rules
- `gross_margin = revenue - cogs`
- `ebitda = gross_margin - sga - allocations`
- `ebitda_margin = ebitda / revenue`
- Growth percentages: `(current - prior) / prior`
- Period convention mapping (from period-map):
  - `M1`–`M12` → first fiscal year (e.g., FY2024)
  - `M13`–`M24` → second fiscal year (e.g., FY2025)
- Regional reconciliation: sum branch-level values and compare to region total; report variance as `region_reconciliation_variance`.

## Ranking rules
- `*_rank_desc` fields: **1 = highest / best**.
- `top_*_branch_id` = branch with highest value.
- `bottom_*_branch_id` = branch with lowest value.
- `largest_pay_type` = pay type with the highest annual total.
- `largest_growth_pay_type` = pay type with the highest growth rate.
- `top_paid_musician_id` = musician with the highest total pay.

## Compensation specifics
- Pay type enum values (exact strings):
  - `Minimum Weekly Scale`
  - `Titled Position Premium`
  - `Seniority`
  - `Overscale`
- `combined_overscale_employee_count` = count of employees with any overscale amount > 0.
- `partial_quarter_employee_count` = count of employees with partial service in any quarter.
- Quarter totals: `Q1`, `Q2`, `Q3`, `Q4` must sum to the annual total.

## Payroll specifics
- Service types map to pay categories; aggregate into:
  - `performance`, `audit`, `rehearsal`, `sound_check`, `premium`, `doubles`, `vacation`, `guarantee_adjustment`, `substitute_adjustment`
- Conflict flag enum values (exact strings):
  - `REHEARSAL_EARLY_START`
  - `REHEARSAL_LATE_END`
  - `SERVICE_OVER_TIME_LIMIT`
  - `SOUND_CHECK_DURATION_MISMATCH`
- `category_totals` and `per_musician.categories` should include only **nonzero** categories where applicable (follow template instructions).

## Output compliance
- Return exactly **one JSON object**.
- Include **all required top-level keys** from `answer_template.json`.
- Use the field types specified in the template (currency, integer, decimal percent, string, list, object).
- Do not include extra commentary or keys outside the template unless explicitly allowed.
