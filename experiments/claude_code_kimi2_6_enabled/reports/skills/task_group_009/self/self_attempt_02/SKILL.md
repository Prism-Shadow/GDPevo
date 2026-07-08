# Crescent Arts Collective — Finance Ops Reporting Skill

## 1. Environment Setup
- **Always use the remote API** specified in `environment_access.md` (e.g. `GDPEVO_ENV_BASE_URL`).
- Ignore any `localhost` / `127.0.0.1` URLs inside `payloads/environment_access.json`; the remote entrypoint overrides them.
- Do not read, enter, or run anything in an `env/` source directory.

## 2. Input Files to Read
For every task, read these staged payloads **before** calling the API:
1. `payloads/environment_access.json` — note the listed endpoints only; override the `base_url`.
2. `payloads/request_memo.json` — extract target IDs, periods, years, focus lists, and any memo notes.
3. `payloads/answer_template.json` — this is the authoritative output schema. Copy its required keys and field types exactly.

## 3. API Endpoint Mapping
| Task Family | Endpoints to Call |
|-------------|-------------------|
| Branch / Regional close (`/api/finance/*`) | `/api/finance/branches`, `/api/finance/period-map`, `/api/finance/accounts`, `/api/finance/records` |
| Compensation summary / forecast (`/api/compensation/*`) | `/api/compensation/rate-book`, `/api/compensation/rosters` (+ `/api/compensation/scenarios` for forecasts) |
| Payroll review (`/api/payroll/*`) | `/api/payroll/rate-book`, `/api/payroll/productions` |

Call only the endpoints relevant to the task family. Query all records needed to compute every required output field.

## 4. Core Calculation Rules
- **Currency fields** → round to **2 decimals** (`round(x, 2)`).
- **Percent, ratio, and growth-rate fields** → round to **4 decimals** (`round(x, 4)`), expressed as decimal values (e.g. `0.1523` for 15.23%).
- **Period convention mapping** (`period-map`):<br>
  `M1`–`M12` → one fiscal year string, `M13`–`M24` → the next fiscal year string. Use the map to resolve `current_month` / `prior_month` labels.
- **Income statement line items**: revenue, cogs, gross_margin, sga, allocations, ebitda.<br>
  Compute gross_margin and ebitda from the underlying account/record data if not provided directly.
- **Growth / variance**:<br>
  `pct = (current - prior) / prior` when prior ≠ 0; handle zero-prior explicitly (return `0.0` or `null` per template guidance).
- **EBITDA margin** = `ebitda / revenue` (revenue ≠ 0).
- **Sales per labor headcount** = `revenue / labor_headcount` (use active roster/headcount data).
- **ARPU** = `revenue / user_count` or defined metric from finance records.
- **Rankings** are **descending** (`1` = highest value). Ties: preserve stable ascending ID order.
- **Reconciliation variance** = sum of branch values − region total (or similar cross-foot per task context), rounded to currency.

## 5. Output Formatting Conventions
- Return **exactly one JSON object**.
- Include **all** `required_top_level_keys` from `answer_template.json`; missing keys cause validation failure.
- **List ordering**:
  - Default: **ascending by stable ID** (e.g. `branch_id`, `musician_id`) unless a rank field or explicit template instruction states otherwise.
  - `conflict_flags` → **alphabetically sorted**.
  - `per_musician` → ordered by `musician_id` ascending.
- **Enum values** (e.g. pay types, conflict flags) must match the template strings exactly, including case and spaces.
- Do **not** include test answers, derivations, or extra commentary inside the JSON.

## 6. Compensation-Specific Conventions
- Pay types from the rate book are the authoritative ordered list.
- **Annual totals** = sum of quarters or direct annual aggregation.
- **Quarter totals** = sum of applicable weeks/services in that quarter.
- **Overscale counts**: employees receiving any overscale pay in the period.
- **Partial-quarter counts**: employees with service that does not cover the full quarter.
- **Largest pay type / largest growth pay type**: determined by absolute annual total or absolute growth amount; break ties by ascending pay-type name if needed.

## 7. Payroll-Specific Conventions
- Service types map to pay categories (performance, audit, rehearsal, sound_check, premium, doubles, vacation, guarantee_adjustment, substitute_adjustment).
- **Weekly total** = sum of all category totals.
- **Per-musician totals** = sum of categories for that musician; include only nonzero categories in the `categories` object.
- **Top-paid musician** = highest `total`; break ties by ascending `musician_id`.
- **Conflict flags** (CBA checks): derive from production schedule vs. rate-book rules (e.g. early/late rehearsal, overtime, sound-check duration mismatch). Return only flags that are triggered, sorted alphabetically.

## 8. Verification Checklist
- [ ] Remote base URL used for every request.
- [ ] All required top-level keys present in final JSON.
- [ ] Currency rounded to 2 decimals; percents/ratios to 4 decimals.
- [ ] Lists sorted per convention (ascending ID, alphabetical, or rank-ordered as specified).
- [ ] Zero-division cases handled gracefully.
- [ ] Derived fields (margins, growth, rankings, variance) recalculated from raw API data, not hard-coded.
