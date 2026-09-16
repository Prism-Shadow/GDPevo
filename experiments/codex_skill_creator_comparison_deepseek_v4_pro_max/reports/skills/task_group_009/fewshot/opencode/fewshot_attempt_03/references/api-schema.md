# Crescent Finance Ops API -- Schema Reference

## Endpoint summary

| Endpoint | Returns | Description |
|---|---|---|
| `/api/manifest` | object | Entity index, public IDs, record counts |
| `/api/finance/branches` | array | All branches with region membership |
| `/api/finance/period-map` | array | M-number to fiscal-year/month mapping |
| `/api/finance/accounts` | array | Chart of accounts with categories |
| `/api/finance/records` | array | Per-account, per-branch period values |
| `/api/compensation/rate-book` | object | Pay scale rules and constants |
| `/api/compensation/rosters` | array | Per-employee roster entries |
| `/api/compensation/scenarios` | object | Named forecast scenario growth factors |
| `/api/payroll/rate-book` | object | Service rates, premiums, conflict thresholds |
| `/api/payroll/productions` | array | Weekly production schedules and rosters |

All endpoints are read-only GET. No query parameters, no pagination -- each
call returns the full dataset.

---

## `/api/manifest`

The manifest is optional; use it to confirm available endpoints and public
entities. Key fields:

| Field | Type | Notes |
|---|---|---|
| `public_entities.branches` | array | Every branch with `branch_id`, `branch_name`, `region_id` |
| `public_entities.ensembles` | array | `[ensemble_id, ensemble_name]` pairs |
| `public_entities.productions` | array | Every production with `production_id` and `title` |
| `record_counts` | object | Row counts for each dataset |

---

## `/api/finance/branches`

Returns an array. Each item:

| Field | Type | Example |
|---|---|---|
| `branch_id` | string | `"BR-004"` |
| `branch_name` | string | `"Harbor North"` |
| `region_id` | string | `"REG-WEST"` |
| `region_name` | string | `"West"` |

Branches are the only source of branch-to-region membership.

Branch IDs: BR-001 through BR-012. Region IDs: REG-NORTH, REG-WEST, REG-EAST, REG-SOUTH.

---

## `/api/finance/period-map`

Returns an array of 24 period objects. Each item:

| Field | Type | Example |
|---|---|---|
| `fiscal_year` | integer | `2024` or `2025` |
| `month_name` | string | `"Jan"` |
| `month_number` | integer | 1-12 |
| `period` | string | `"M1"` through `"M24"` |

**Fixed convention:** M1-M12 = FY2024, M13-M24 = FY2025. Always confirm with
this endpoint, but the convention is stable across tasks.

---

## `/api/finance/accounts`

Returns an array of 14 account definitions. Each item:

| Field | Type | Example |
|---|---|---|
| `account` | string | `"product_revenue"` |
| `category` | string | `"revenue"`, `"cogs"`, `"sga"`, `"allocations"`, `"operating"` |
| `display_name` | string | `"Product Revenue"` |
| `metric_type` | string | `"currency"` or `"count"` |

### Currency accounts (aggregate into income statement lines)

| Account | Category |
|---|---|
| `product_revenue` | revenue |
| `service_revenue` | revenue |
| `direct_materials_cogs` | cogs |
| `direct_labor_cogs` | cogs |
| `sales_sga` | sga |
| `admin_sga` | sga |
| `occupancy_sga` | sga |
| `shared_service_allocations` | allocations |

### Operating (count) accounts

| Account | Category | Use |
|---|---|---|
| `orders` | operating | -- |
| `revenue_units` | operating | Denominator for ARPU |
| `active_customers` | operating | -- |
| `labor_headcount` | operating | Denominator for `sales_per_labor_headcount` |
| `admin_headcount` | operating | -- |
| `backlog` | operating | -- |

---

## `/api/finance/records`

Returns an array of 168 records (14 accounts x 12 branches). Each item:

| Field | Type | Example |
|---|---|---|
| `account` | string | `"product_revenue"` |
| `branch_id` | string | `"BR-004"` |
| `branch_name` | string | `"Harbor North"` |
| `region_id` | string | `"REG-WEST"` |
| `values` | object | `{ "M1": 100.0, "M2": 110.0, ... "M24": 132255.93 }` |

The `values` object always contains all 24 periods M1 through M24. To compute
any period total: filter by account/branch/period combination and sum the
values.

---

## `/api/compensation/rate-book`

Returns a single object with the pay structure:

| Field | Type | Notes |
|---|---|---|
| `business_rules` | array of strings | Important edge-case rules (read them) |
| `current_year` | integer | e.g. `2026` |
| `minimum_weekly_scale` | number | Base weekly pay, e.g. `2520.0` |
| `pay_types` | array of strings | Canonical order: Minimum Weekly Scale, Titled Position Premium, Seniority, Overscale |
| `quarter_weeks` | object | `{ "Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13 }` |
| `seniority_weekly` | array of band objects | Each band has `min_years`, `max_years` (or null), `weekly_amount` |
| `title_premium_pct` | object | Title-to-percentage mapping |

### Seniority bands

Seniority is based on `years_of_service`. Find the band where
`min_years <= years_of_service <= max_years` (treat `null` max as infinity).
The `weekly_amount` from that band is the seniority weekly rate.

### Title premiums

| Title | Percentage |
|---|---|
| Assistant Principal | 10% |
| Associate Principal | 10% |
| Concertmaster | 22% |
| Principal | 20% |
| Section Lead | 15% |

---

## `/api/compensation/rosters`

Returns an array of roster entries across all ensembles. Filter by `ensemble_id`.
Each item:

| Field | Type | Notes |
|---|---|---|
| `employee_id` | string | e.g. `"ENS-REDWOOD-001"` |
| `ensemble_id` | string | e.g. `"ENS-REDWOOD"` |
| `ensemble_name` | string | e.g. `"Redwood Pops"` |
| `title` | string | One of the title premium titles, or empty string |
| `years_of_service` | integer | Used for seniority band lookup |
| `overscale_weekly` | number | Additional weekly amount beyond scale |
| `combined_overscale_includes_title` | boolean | If true, title premium is NOT added separately |
| `weeks_by_quarter` | object | `{ "Q1": N, "Q2": N, "Q3": N, "Q4": N }` |
| `notes` | string | Free-form notes |

---

## `/api/compensation/scenarios`

Returns an object keyed by `scenario_id`. Each scenario has `year_plus_1` and
`year_plus_2` growth factor objects. Each growth object:

| Field | Type | Notes |
|---|---|---|
| `mws_growth` | number | Growth rate for minimum weekly scale |
| `overscale_growth` | number | Growth rate for overscale weekly amounts |
| `seniority_growth` | number | Growth rate for seniority band weekly_amounts |
| `title_pct_multiplier` | number | Multiplier on title_premium_pct values |

Available scenarios: `case_cedar_negotiation`, `case_maple_board`,
`case_oak_sensitivity`, `case_redwood_baseline`.

---

## `/api/payroll/rate-book`

Returns a single object:

| Field | Type | Notes |
|---|---|---|
| `business_rules` | array of strings | Critical calculation rules |
| `service_rates` | object | Service type to base rate mapping |
| `premium_pct` | object | Premium type to percentage mapping |
| `conflict_thresholds` | object | CBA compliance thresholds |
| `service_time_limits` | object | Max hours per service type |
| `weekly_guarantee` | number | Minimum weekly pay for guaranteed regulars |

### Service rates

| Service Type | Rate |
|---|---|
| 1hr Sound Check | $80.00 |
| 2hr Sound Check | $142.50 |
| Audit | $260.25 |
| Performance | $260.25 |
| Rehearsal | $58.75 (hourly, with 3-hour minimum call -- see business rules) |

### Premium percentages

| Premium | Percentage | Applies when |
|---|---|---|
| `principal_or_lead` | 15% | `principal` or `lead` is true |
| `concertmaster` | 20% | Not available in standard roster; reserved |
| `quartet` | 15% | `quartet` is true |
| `electronic` | 25% | `electronic` is true |
| `first_double` | 25% | `doubles` >= 1 |
| `additional_double` | 10% | Each double beyond the first |
| `vacation` | 4% | `vacation_eligible` is true (on base + premiums) |

### Conflict thresholds

| Field | Value |
|---|---|
| `rehearsal_earliest_start` | `"09:00"` |
| `rehearsal_latest_end` | `"18:30"` |

### Service time limits

| Service Type | Hours |
|---|---|
| 1hr Sound Check | 1.0 |
| 2hr Sound Check | 2.0 |
| Audit | 3.0 |
| Performance | 3.0 |
| Rehearsal | 5.0 |

---

## `/api/payroll/productions`

Returns an array of production objects. Filter by `production_id`. Each item:

| Field | Type | Notes |
|---|---|---|
| `production_id` | string | e.g. `"PROD-HAMILTON-26"` |
| `title` | string | e.g. `"Hamilton Tour Week 26"` |
| `week_start` | string | ISO date of the Monday |
| `schedule` | array | Service events for the week |
| `roster` | array | Musicians assigned to this production |

### Schedule item

| Field | Type | Notes |
|---|---|---|
| `service_id` | string | e.g. `"H26-S01"` |
| `date` | string | ISO date |
| `service_type` | string | One of: Rehearsal, Performance, Audit, 1hr Sound Check, 2hr Sound Check |
| `start_time` | string | `"HH:MM"` format |
| `end_time` | string | `"HH:MM"` format |
| `duration_hours` | number | Actual duration in decimal hours |

### Roster item

| Field | Type | Notes |
|---|---|---|
| `musician_id` | string | e.g. `"M-H26-01"` |
| `name` | string | Full name |
| `instrument` | string | Instrument played |
| `assigned_service_ids` | array of strings | Which services this musician plays |
| `principal` | boolean | Principal player |
| `lead` | boolean | Section lead |
| `quartet` | boolean | Quartet member |
| `electronic` | boolean | Uses electronic instrument |
| `doubles` | integer | Number of extra instruments |
| `substitute` | boolean | Substitute (different pay rules) |
| `vacation_eligible` | boolean | Earns vacation pay |
