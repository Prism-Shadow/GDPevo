## When to Use

Use this skill when the task involves building a structured management‑reporting, compensation‑summary, payroll‑review, or forecast JSON payload for **Crescent Arts Collective** against the **Finance Ops API**. The task input will always include a `prompt.txt`, a `payloads/environment_access.json`, a `payloads/request_memo.json`, and a `payloads/answer_template.json`.

## Workflow

### 1. Read the Input Files

Read these four files from the task input directory:

- **`prompt.txt`** – business purpose and reporting focus
- **`payloads/environment_access.json`** – `base_url` (may be `<TASK_ENV_BASE_URL>` placeholder; resolve using step 2) and `available_endpoints`
- **`payloads/request_memo.json`** – task‑specific parameters: request/entity IDs, close / forecast periods, reporting‑focus lists, and any memo notes
- **`payloads/answer_template.json`** – the exact output schema: `required_top_level_keys`, `field_types`, and any `description` of ordering / rounding constraints

### 2. Resolve the Base URL

If `payloads/environment_access.json` contains a literal `<TASK_ENV_BASE_URL>` placeholder, open `environment_access.md` at the workspace root and use the `Base URL` listed there. Otherwise use the url from `environment_access.json` directly. All API calls are unauthenticated `GET` requests; append the endpoint path to the base URL.

### 3. Determine the Domain and Fetch All Relevant Data

Examine the `available_endpoints` array. It will belong to exactly one of three API domains. Fetch **every** endpoint listed — some relationships span multiple collections.

| Domain | Endpoint | What It Returns |
|---|---|---|
| Finance | `/api/finance/branches` | Branch metadata: id, name, region_id, region_name, labor_headcount |
| Finance | `/api/finance/period-map` | Period‑to‑fiscal‑year mapping for all close periods (M1–M24) |
| Finance | `/api/finance/accounts` | Account chart: account id, name, category (Revenue / COGS / SG&A / Allocations) |
| Finance | `/api/finance/records` | Financial records: branch_id, period, account_id, amount (actuals) |
| Compensation | `/api/compensation/rate-book` | Pay‑type definitions, rates, and annual escalation factors |
| Compensation | `/api/compensation/rosters` | Employee rosters: musician/employee id, name, ensemble_id, pay_type, service‑quarter ranges (start_qtr, end_qtr), overscale flag, partial‑quarter flag |
| Compensation | `/api/compensation/scenarios` | Forecast scenarios: ensemble_id, scenario_id, growth factors per pay type per projection year |
| Payroll | `/api/payroll/rate-book` | Service‑type rate definitions and CBA rule metadata |
| Payroll | `/api/payroll/productions` | Production schedules: production_id, services (type, start_time, end_time), musician assignments with contract flags |

Fetch every endpoint in parallel as a first step. Hold all response data in memory for computations.

### 4. Process Data According to the Domain

#### Finance Domain (branch close / regional reporting)

- **Period mapping**: Use the period‑map response to resolve M‑labels to fiscal years. Convention: M1–M12 = FY20##, M13–M24 = FY20##+1. The exact fiscal‑year values come from the period‑map endpoint, not from fixed rules.
- **Income statement**: Sum `amount` from `/api/finance/records` grouped by branch, period, and account category (Revenue, COGS, SG&A, Allocations). Compute `gross_margin = revenue - cogs`, `ebitda = gross_margin - sga - allocations`.
- **MoM variance**: Subtract prior‑period revenue from current‑period revenue for the target branch. `pct = amount / prior_revenue`.
- **FY comparisons**: Aggregate records for all months in each fiscal year. Compute `ebitda_margin = ebitda / revenue`, `arpu = revenue / labor_headcount`, `sales_per_labor_headcount = revenue / labor_headcount`. Growth rates use `(current - prior) / prior`.
- **Regional context**: Group branches by `region_id`. Sum FY2025 ebitda per region. Rank branches within region by ebitda descending (1 = highest).
- **Branch rankings**: Rank all branches by revenue growth (FY2025 vs FY2024) descending. Identify the branch with highest ARPU.
- **Reconciliation**: When aggregating branch data into region totals, compute `region_reconciliation_variance` as `sum(branch amounts) - region total from records`. This should be 0.0 if all data is consistent.

#### Compensation Domain (current‑year summary / board forecast)

- **Rate book**: Provides pay‑type names (Minimum Weekly Scale, Titled Position Premium, Seniority, Overscale) and base annual rates. The `pay_types` ordered list should preserve the rate‑book order.
- **Rosters**: Each roster entry has `musician_id` (or `employee_id`), `name`, `ensemble_id`, `pay_type`, `start_qtr`, `end_qtr`, `overscale` (boolean), `partial_quarter` (boolean).
- **Quarter totals**: For each employee, compute per‑quarter pay as `annual_rate / 4` for each quarter they are active (start_qtr ≤ quarter ≤ end_qtr). Sum across all employees per quarter. If an employee's service spans a partial quarter, include them in `partial_quarter_employee_count`.
- **Annual pay‑type totals**: Sum annual pay per pay type across employees. Annual pay = annual_rate for full‑year employees; adjust proportionally for partial‑year.
- **Overscale**: Count employees flagged with `overscale = true` in `combined_overscale_employee_count`.
- **Largest pay type**: The pay type with the highest annual total.
- **Forecasts (scenarios)**: The `/api/compensation/scenarios` endpoint returns growth factors per pay type per projection year. Apply each growth factor multiplicatively to the current‑year base for that pay type to produce year‑plus‑1 and year‑plus‑2 totals. Compute `growth_rate = (next_year - current_year) / current_year`.

#### Payroll Domain (weekly payroll review)

- **Rate book**: Maps service types (Performance, Rehearsal, Audit, Sound Check, etc.) to base pay rates. Also defines premium/doubles multipliers and CBA rule boundaries (e.g. max daily hours, allowed start/end windows).
- **Productions**: Each production contains a list of `services` (type, start_time, end_time) and a list of `musicians` (musician_id, name, contract_type, service_assignments, flags).
- **Service counts**: Count occurrences of each service type across the production.
- **Category totals**: For each pay category (performance, rehearsal, audit, sound_check, premium, doubles, vacation, guarantee_adjustment, substitute_adjustment), compute the total pay by applying the rate‑book rates and multipliers to the service assignments. Premium pay applies when services exceed CBA daily‑hour limits or fall outside allowed windows. Doubles pay applies when a musician performs multiple service roles. Guarantee adjustments cover minimum‑call guarantees. Substitute adjustments offset substitute musician rates.
- **Per‑musician totals**: For each musician, sum their pay across all categories and include a `categories` object with only nonzero amounts.
- **Conflict flags**: Inspect the production schedule and musician assignments for CBA rule violations. Enum values are: `REHEARSAL_EARLY_START` (rehearsal start before allowed window), `REHEARSAL_LATE_END` (rehearsal end after allowed window), `SERVICE_OVER_TIME_LIMIT` (service duration exceeds maximum), `SOUND_CHECK_DURATION_MISMATCH` (sound check duration differs from configured standard). Include only flags that actually apply; sort alphabetically.

### 5. Format the Output

Every response is a single JSON object conforming to `payloads/answer_template.json`.

**Universal formatting rules:**
- **Currency** values: round to **2 decimal places** using `Number(amount.toFixed(2))` or equivalent.
- **Percent / ratio** values: round to **4 decimal places** using `Number(rate.toFixed(4))` or equivalent.
- **Lists**: default sort is ascending by stable ID (branch_id, musician_id, etc.) unless the template explicitly specifies a rank‑based order.
- **Keys**: include every key listed under `required_top_level_keys` in the answer template, in the order given.
- **Zero values**: include `0` or `0.0` for currency fields with no activity; include `0.0` for percent fields with no change.
- **Enum values**: match the exact strings listed in the template's `field_types` (e.g. `"Minimum Weekly Scale"`, not `"minimum_weekly_scale"`).

### 6. Validate Before Returning

- Every `required_top_level_key` is present.
- Currency fields have exactly 2 decimal places.
- Percent/ratio fields have exactly 4 decimal places.
- Lists are in the correct sort order.
- No extra or missing keys at any nesting level.
- The result is a well‑formed JSON object (no trailing commas, all strings double‑quoted).
