# API Schemas

## Common identifier patterns

- **Branch IDs**: `BR-NNN` (e.g., `BR-004`)
- **Region IDs**: `REG-NORTH`, `REG-WEST`, `REG-EAST`, `REG-SOUTH`
- **Ensemble IDs**: `ENS-XXXX` (e.g., `ENS-REDWOOD`)
- **Employee IDs**: `ENS-XXXX-NNN` (ensemble prefix + serial)
- **Production IDs**: `PROD-XXXX-NN` (show name + week)
- **Musician IDs**: `M-XX-NN` (production initials + serial)
- **Service IDs**: `XX-SNN` (production initials + serial)
- **Scenarios**: `case_xxxx_yyyy` (ensemble + label)

## Finance endpoints

### GET /api/finance/branches

Returns an array of branch objects:

```json
{
  "branch_id": "BR-004",
  "branch_name": "Harbor North",
  "region_id": "REG-WEST",
  "region_name": "West"
}
```

### GET /api/finance/period-map

Returns an array of period mappings. Months M1-M12 map to FY2024, months M13-M24 map to FY2025.

```json
{
  "fiscal_year": 2024,
  "month_name": "Jan",
  "month_number": 1,
  "period": "M1"
}
```

### GET /api/finance/accounts

Returns an array of account definitions:

```json
{
  "account": "product_revenue",
  "category": "revenue",
  "display_name": "Product Revenue",
  "metric_type": "currency"
}
```

**Account categories**: `revenue` (product_revenue, service_revenue), `cogs` (direct_materials_cogs, direct_labor_cogs), `sga` (sales_sga, admin_sga, occupancy_sga), `allocations` (shared_service_allocations), `operating` (orders, revenue_units, active_customers, labor_headcount, admin_headcount, backlog).

### GET /api/finance/records

Returns an array of record objects, each representing one account-branch combination with a `values` object mapping periods (M1..M24) to numeric values.

```json
{
  "account": "product_revenue",
  "branch_id": "BR-004",
  "branch_name": "Harbor North",
  "region_id": "REG-WEST",
  "values": {
    "M1": 118330.31,
    "M2": 116982.57,
    "M24": 132255.93
  }
}
```

## Compensation endpoints

### GET /api/compensation/rate-book

Returns a single object:

```json
{
  "current_year": 2026,
  "minimum_weekly_scale": 2520.0,
  "pay_types": ["Minimum Weekly Scale", "Titled Position Premium", "Seniority", "Overscale"],
  "quarter_weeks": {"Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13},
  "seniority_weekly": [
    {"min_years": 0, "max_years": 4, "weekly_amount": 0.0},
    {"min_years": 5, "max_years": 9, "weekly_amount": 48.0},
    {"min_years": 10, "max_years": 14, "weekly_amount": 82.0},
    {"min_years": 15, "max_years": 19, "weekly_amount": 126.0},
    {"min_years": 20, "max_years": 24, "weekly_amount": 170.0},
    {"min_years": 25, "max_years": null, "weekly_amount": 215.0}
  ],
  "title_premium_pct": {
    "Assistant Principal": 0.10,
    "Associate Principal": 0.10,
    "Concertmaster": 0.22,
    "Principal": 0.20,
    "Section Lead": 0.15
  },
  "business_rules": [
    "Use roster quarter weeks, not a fixed 13-week quarter, when partial-quarter employees are listed.",
    "If combined_overscale_includes_title is true, do not add a titled position premium separately for that employee.",
    "For forecast years, add one year of service for Year + 1 and two years of service for Year + 2 before assigning seniority bands."
  ]
}
```

### GET /api/compensation/rosters

Returns an array of employee roster entries:

```json
{
  "employee_id": "ENS-REDWOOD-001",
  "ensemble_id": "ENS-REDWOOD",
  "ensemble_name": "Redwood Pops",
  "title": "Concertmaster",
  "years_of_service": 3,
  "overscale_weekly": 0.0,
  "combined_overscale_includes_title": false,
  "weeks_by_quarter": {"Q1": 13, "Q2": 13, "Q3": 13, "Q4": 13},
  "notes": ""
}
```

**Important fields**:
- `title` can be `null` for rank-and-file musicians
- `notes` containing "Partial-quarter" means the employee does not work all 13 weeks in every quarter
- `combined_overscale_includes_title` when true means the overscale amount already covers the title premium; do not add title premium on top

### GET /api/compensation/scenarios

Returns an object keyed by scenario ID. Each scenario has `year_plus_1` and `year_plus_2` objects with growth rates:

```json
{
  "case_maple_board": {
    "description": "Maple board planning case.",
    "year_plus_1": {
      "mws_growth": 0.035,
      "overscale_growth": 0.012,
      "seniority_growth": 0.018,
      "title_pct_multiplier": 1.0
    },
    "year_plus_2": {
      "mws_growth": 0.033,
      "overscale_growth": 0.014,
      "seniority_growth": 0.02,
      "title_pct_multiplier": 1.0
    }
  }
}
```

## Payroll endpoints

### GET /api/payroll/rate-book

Returns a single object:

```json
{
  "service_rates": {
    "Performance": 260.25,
    "Audit": 260.25,
    "Rehearsal": 58.75,
    "1hr Sound Check": 80.0,
    "2hr Sound Check": 142.5
  },
  "service_time_limits": {
    "Performance": 3.0,
    "Audit": 3.0,
    "Rehearsal": 5.0,
    "1hr Sound Check": 1.0,
    "2hr Sound Check": 2.0
  },
  "premium_pct": {
    "principal_or_lead": 0.15,
    "concertmaster": 0.20,
    "first_double": 0.25,
    "additional_double": 0.10,
    "electronic": 0.25,
    "quartet": 0.15,
    "vacation": 0.04
  },
  "conflict_thresholds": {
    "rehearsal_earliest_start": "09:00",
    "rehearsal_latest_end": "18:30"
  },
  "weekly_guarantee": 2082.0,
  "business_rules": [
    "Service rates and premiums come from this rate book.",
    "Rehearsal pay is hourly with a three-hour minimum call.",
    "Performance, audit, and sound-check rates are per service.",
    "Premiums are applied to the musician's base service pay before vacation.",
    "The doubles premium is 25% for the first extra instrument and 10% for each additional extra instrument.",
    "Vacation is 4% of base service pay plus premiums when vacation_eligible is true.",
    "A weekly guarantee adjustment applies only to guaranteed regular players when base service pay is below weekly_guarantee."
  ]
}
```

### GET /api/payroll/productions

Returns an array of production objects, each containing a roster and schedule:

```json
{
  "production_id": "PROD-HAMILTON-26",
  "roster": [
    {
      "musician_id": "M-H26-01",
      "name": "Avery Cole",
      "instrument": "Synthesizer",
      "assigned_service_ids": ["H26-S03", "H26-S04", "H26-S05", "H26-S06", "H26-S08"],
      "doubles": 1,
      "electronic": true,
      "lead": false,
      "principal": false,
      "quartet": false,
      "substitute": true,
      "vacation_eligible": false
    }
  ],
  "schedule": [
    {
      "service_id": "H26-S01",
      "date": "2026-05-19",
      "service_type": "Rehearsal",
      "start_time": "08:45",
      "end_time": "13:45",
      "duration_hours": 5.0
    }
  ]
}
```
