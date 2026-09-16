# Domain Reference

Data structures returned by each Crescent Finance Ops API endpoint.

## Finance Endpoints

### GET /api/finance/branches

Returns an array of branch objects with `branch_id`, `branch_name`, `region_id`, `region_name`.
12 branches across 4 regions:
- **REG-NORTH**: BR-001 (Aurora North), BR-002 (Granite Bay), BR-003 (Lakeview)
- **REG-WEST**: BR-004 (Harbor North), BR-005 (Pine Hill), BR-006 (Mesa Ridge)
- **REG-EAST**: BR-007 (Riverbend), BR-008 (Old Port), BR-011 (Summit Yard)
- **REG-SOUTH**: BR-009 (Beacon South), BR-010 (Coral Point), BR-012 (Valley Forge)

### GET /api/finance/period-map

Returns an array of period objects. **M1-M12 = FY2024, M13-M24 = FY2025.**
Each entry: `{"fiscal_year": 2025, "month_name": "Dec", "month_number": 12, "period": "M24"}`.

### GET /api/finance/accounts

Returns an array of account definitions with `account`, `category`, `display_name`, `metric_type` (currency or count).

Currency accounts: product_revenue, service_revenue, direct_materials_cogs, direct_labor_cogs, sales_sga, admin_sga, occupancy_sga, shared_service_allocations.
Count accounts: orders, revenue_units, active_customers, labor_headcount, admin_headcount, backlog.

### GET /api/finance/records

Returns an array of records, each tying an account to a branch with period values. Example:

```json
{
  "account": "product_revenue",
  "branch_id": "BR-004",
  "branch_name": "Harbor North",
  "region_id": "REG-WEST",
  "values": {"M1": 145075.37, "M2": 145412.94, ..., "M24": 168830.82}
}
```

Each account-branch pair is a separate record. Values keys are M1 through M24.

## Compensation Endpoints

### GET /api/compensation/rate-book

Single object. Key fields:
- `current_year` (2026), `minimum_weekly_scale` (2520.00)
- `pay_types`: ["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"]
- `quarter_weeks`: {"Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13} — default weeks; actual roster weeks_by_quarter overrides this
- `seniority_weekly`: Array of bands with min_years, max_years, weekly_amount
- `title_premium_pct`: Maps title to percentage (Assistant Principal 0.10, Associate Principal 0.10, Concertmaster 0.22, Principal 0.20, Section Lead 0.15)
- `business_rules`: Array of rule strings

### GET /api/compensation/rosters

Returns array of employee records. Key fields per employee:
- `employee_id`, `ensemble_id`, `ensemble_name`, `title` (string or null)
- `years_of_service` (integer), `overscale_weekly` (float)
- `combined_overscale_includes_title` (boolean): when true, overscale already covers title premium; do NOT add separate titled position premium
- `notes`: "Partial-quarter service schedule." means some quarters differ from 13 weeks
- `weeks_by_quarter`: {"Q1": 13, "Q2": 9, "Q3": 13, "Q4": 13} — use these, not the rate-book default

### GET /api/compensation/scenarios

Returns an object keyed by scenario_id (e.g., "case_maple_board"). Each scenario has `year_plus_1` and `year_plus_2` with:
- `mws_growth`, `overscale_growth`, `seniority_growth`: multiplicative factors (new = old * (1 + growth))
- `title_pct_multiplier`: scales all title premium percentages

## Payroll Endpoints

### GET /api/payroll/rate-book

Single object. Key fields:
- `service_rates`: {"Performance": 260.25, "Audit": 260.25, "Rehearsal": 58.75, "1hr Sound Check": 80.00, "2hr Sound Check": 142.50}
- `service_time_limits`: {"Performance": 3.0, "Audit": 3.0, "Rehearsal": 5.0, "1hr Sound Check": 1.0, "2hr Sound Check": 2.0}
- `premium_pct`: {"concertmaster": 0.20, "principal_or_lead": 0.15, "quartet": 0.15, "electronic": 0.25, "first_double": 0.25, "additional_double": 0.10, "vacation": 0.04}
- `conflict_thresholds`: {"rehearsal_earliest_start": "09:00", "rehearsal_latest_end": "18:30"}
- `weekly_guarantee`: 2082.00
- `business_rules`: Array of rule strings

### GET /api/payroll/productions

Returns array of production objects. Each production has:
- `production_id`, `title`, `week_start`
- `roster`: array of musicians, each with `musician_id`, `name`, `instrument`, boolean flags (principal, lead, quartet, electronic, substitute, vacation_eligible), `doubles` count, and `assigned_service_ids` (array of service IDs the musician plays on)
- `schedule`: array of services, each with `service_id`, `date`, `service_type`, `start_time`, `end_time`, `duration_hours`

A musician is only paid for services listed in their `assigned_service_ids`. Service counts come from the schedule array (not assignments).
