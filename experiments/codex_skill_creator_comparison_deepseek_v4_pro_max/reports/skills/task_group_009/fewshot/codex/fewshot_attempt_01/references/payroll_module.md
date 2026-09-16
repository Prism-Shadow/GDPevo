## Table of Contents

- Endpoints and Schemas
- Service Computation Rules
- Category Total Aggregation
- Per-Musician Breakdown
- Conflict Flag Detection
- Guarantee and Substitute Adjustments

## Endpoints and Schemas

### GET /api/payroll/rate-book

Returns a rate-book object:

```
{
  "service_rates": {
    "1hr Sound Check": 80.0,
    "2hr Sound Check": 142.5,
    "Audit": 260.25,
    "Performance": 260.25,
    "Rehearsal": 58.75
  },
  "premium_pct": {
    "concertmaster": 0.2,
    "principal_or_lead": 0.15,
    "quartet": 0.15,
    "first_double": 0.25,
    "additional_double": 0.1,
    "electronic": 0.25,
    "vacation": 0.04
  },
  "weekly_guarantee": 2082.0,
  "service_time_limits": {
    "1hr Sound Check": 1.0,
    "2hr Sound Check": 2.0,
    "Audit": 3.0,
    "Performance": 3.0,
    "Rehearsal": 5.0
  },
  "conflict_thresholds": {
    "rehearsal_earliest_start": "09:00",
    "rehearsal_latest_end": "18:30"
  },
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

Key business rules from rate_book.business_rules:

- **Rehearsal**: hourly rate with a three-hour minimum call. Pay = rate * max(3, duration_hours).
- **Performance, Audit, Sound Check**: flat per-service rate. Pay = service_rate.
- **Premiums**: applied to the musician's base service pay before computing vacation.
- **Doubles**: first extra instrument = 25%, each additional = 10% of base service pay.
- **Vacation**: 4% of (base service pay + premiums), only when `vacation_eligible` is true.
- **Weekly guarantee**: applies only to guaranteed regular players (substitute=false AND guaranteed_regular true). If base service pay is below 2082.0, add the difference. Guaranteed regular status is implicit from the roster: non-substitute musicians are guaranteed regular.

### GET /api/payroll/productions

Returns a list of production objects. Each production has:

- `production_id`: string identifier
- `title`: display title
- `week_start`: ISO date string
- `schedule`: list of service objects with service_id, service_type, date, start_time, end_time, duration_hours
- `roster`: list of musician objects

**Schedule entry:**

```
{
  "service_id": "SVC-ID-01",
  "service_type": "Rehearsal",
  "date": "YYYY-MM-DD",
  "start_time": "HH:MM",
  "end_time": "HH:MM",
  "duration_hours": 5.0
}
```

**Roster entry:**

```
{
  "musician_id": "M-PROD-01",
  "name": "Musician Name",
  "instrument": "Instrument",
  "assigned_service_ids": ["SVC-ID-01", "SVC-ID-01", ...],
  "doubles": 1,
  "electronic": true,
  "lead": false,
  "principal": false,
  "quartet": false,
  "substitute": true,
  "vacation_eligible": false
}
```

## Service Computation Rules

For each musician, iterate over their `assigned_service_ids`. For each service:

1. **Look up the schedule entry** by `service_id` to get `service_type`, `duration_hours`, `start_time`, `end_time`.
2. **Base service pay**:
   - Rehearsal: `service_rates["Rehearsal"] * max(3.0, duration_hours)`. The minimum call is 3 hours; the rate is hourly.
   - All other types: flat `service_rates[service_type]`. Duration is informational but does not affect pay.
3. **Premiums** (stacked on base service pay):
   - `principal_or_lead`: if musician.principal is true OR musician.lead is true, add `base * premium_pct["principal_or_lead"]`
   - `concertmaster`: if musician has concertmaster role, add `base * premium_pct["concertmaster"]`. Not in the dataset but handled generically.
   - `quartet`: if musician.quartet is true, add `base * premium_pct["quartet"]`
   - `first_double`: if musician.doubles >= 1, add `base * premium_pct["first_double"]`
   - `additional_double`: if musician.doubles >= 2, add `(doubles - 1) * base * premium_pct["additional_double"]`
   - `electronic`: if musician.electronic is true, add `base * premium_pct["electronic"]`
4. **Vacation**: if `vacation_eligible` is true, add `(base + sum_of_premiums) * premium_pct["vacation"]`
5. **Guarantee adjustment**: computed after all services are processed (see below).
6. **Substitute adjustment**: computed at the end (see below).

Total service pay = base + premiums + vacation.

## Category Total Aggregation

Map each service to its payroll category:

| service_type | category |
|---|---|
| Performance | performance |
| Audit | audit |
| Rehearsal | rehearsal |
| 1hr Sound Check | sound_check |
| 2hr Sound Check | sound_check |

Premium and vacation amounts are tracked in their own categories:

- `premium`: sum of all premium amounts (principal_or_lead, quartet, first_double, additional_double, electronic, concertmaster)
- `doubles`: sum of first_double + additional_double premiums (a subset of premium)
- `vacation`: sum of all vacation amounts
- `guarantee_adjustment`: weekly guarantee shortfall (see below)
- `substitute_adjustment`: additional pay for substitute players (see below)

The answer template may request `doubles` as a separate category from `premium`. In that case:
- `premium` = sum of non-doubles premiums only (principal_or_lead, quartet, electronic, concertmaster)
- `doubles` = sum of first_double + additional_double

Check the answer template carefully -- if `doubles` is a required key in category_totals, split it out; otherwise keep all premiums in one bucket.

## Per-Musician Breakdown

For each musician, compute:

- `musician_id`: from roster
- `name`: from roster
- `total`: sum of all pay (base + premiums + vacation + adjustments), rounded to 2 decimals
- `categories`: a map of nonzero category names to currency amounts:
  - Only include categories with nonzero amounts. Omit a category if zero.
  - If the template splits doubles from premium, list both separately.
  - Include guarantee_adjustment and substitute_adjustment when nonzero.
  - Round all amounts to 2 decimals.

Sort per_musician list by `musician_id` ascending.

## Conflict Flag Detection

Scan the production schedule and roster for these conflicts. Add flags to the array when the condition is met; omit when not. Sort the final array alphabetically.

### REHEARSAL_EARLY_START

Any rehearsal service where `start_time` is earlier than `conflict_thresholds.rehearsal_earliest_start` ("09:00").

### REHEARSAL_LATE_END

Any rehearsal service where `end_time` is later than `conflict_thresholds.rehearsal_latest_end` ("18:30").

### SERVICE_OVER_TIME_LIMIT

Any service where `duration_hours` exceeds `service_time_limits[service_type]`. For example, a Performance lasting X.XX hours when the limit is 3.0 is fine; a Performance lasting 3.5 hours triggers the flag.

### SOUND_CHECK_DURATION_MISMATCH

Any sound-check service where the actual `duration_hours` does not match the declared duration in the service_type name. A "1hr Sound Check" must be exactly 1.0 hours; "2hr Sound Check" must be exactly 2.0 hours. If a schedule entry has service_type "1hr Sound Check" but duration_hours != 1.0, flag it.

## Guarantee and Substitute Adjustments

### Weekly Guarantee Adjustment

After computing base service pay for all services for a musician:

1. Sum the base service pay (before premiums and vacation).
2. If the musician is a guaranteed regular player (substitute=false) AND the base service pay is less than `weekly_guarantee` (2082.0):
   - `guarantee_adjustment` = weekly_guarantee - base_service_pay, rounded to 2 decimals
3. If base service pay >= weekly_guarantee, or the musician is a substitute: guarantee_adjustment = 0.

The guarantee adjustment applies at the musician level, not the category level. Add it as a separate category entry on the per-musician breakdown.

### Substitute Adjustment

If a musician is a substitute (`substitute` = true):

1. Compute the total service pay (base + premiums + vacation) for that musician.
2. `substitute_adjustment` = that total (the substitute's pay is the same as a regular player's would be, but it appears as a separate line item -- effectively a reimbursement to the substitute).
3. Add substitute_adjustment as a category in category_totals and in the musician's categories.

In the known data patterns, the substitute's total pay equals the service pay they would have earned as a regular player; it appears under `substitute_adjustment`.
