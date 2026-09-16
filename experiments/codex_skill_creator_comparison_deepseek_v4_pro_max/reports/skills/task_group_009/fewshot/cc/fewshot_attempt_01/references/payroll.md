# Payroll Module - Weekly Touring Production Pay

This reference covers weekly payroll totals, service counts, category totals,
per-musician breakdowns, and CBA conflict flags from the `/api/payroll/`
endpoints.

---

## Endpoints and Data Model

### `/api/payroll/rate-book`

```json
{
  "business_rules": [...],
  "conflict_thresholds": {
    "rehearsal_earliest_start": "09:00",
    "rehearsal_latest_end": "18:30"
  },
  "premium_pct": {
    "additional_double": 0.1,
    "concertmaster": 0.2,
    "electronic": 0.25,
    "first_double": 0.25,
    "principal_or_lead": 0.15,
    "quartet": 0.15,
    "vacation": 0.04
  },
  "service_rates": {
    "1hr Sound Check": 80.0,
    "2hr Sound Check": 142.5,
    "Audit": 260.25,
    "Performance": 260.25,
    "Rehearsal": 58.75
  },
  "service_time_limits": {
    "1hr Sound Check": 1.0,
    "2hr Sound Check": 2.0,
    "Audit": 3.0,
    "Performance": 3.0,
    "Rehearsal": 5.0
  },
  "weekly_guarantee": 2082.0
}
```

### `/api/payroll/productions`

Returns all productions. Each production has:

- `production_id`, `title`, `week_start`
- `schedule`: list of service events with `service_id`, `service_type`,
  `start_time`, `end_time`, `duration_hours`, `date`
- `roster`: list of musicians with `musician_id`, `name`, `instrument`,
  `assigned_service_ids`, and flags: `lead`, `principal`, `quartet`,
  `electronic`, `doubles` (count), `substitute`, `vacation_eligible`

---

## Business Rules (from rate book)

1. Rates and premiums come from the rate book.
2. Rehearsal pay is hourly with a three-hour minimum call.
3. Performance, audit, and sound-check rates are per-service (flat).
4. Premiums are applied to base service pay before vacation.
5. Doubles: 25% for the first extra instrument, 10% for each additional.
6. Vacation is 4% of (base service pay + premiums) when `vacation_eligible`
   is true.
7. Weekly guarantee adjustment: for guaranteed regular players
   (`substitute` = false), if base service pay (before premiums and vacation)
   is below `weekly_guarantee`, the adjustment = weekly_guarantee - base.

---

## Service Counts

Count the number of services in the production schedule by `service_type`.
Only include service types that actually appear. Use the exact service_type
string from the schedule, e.g. "Performance", "Rehearsal", "Audit",
"1hr Sound Check".

---

## Per-Musician Pay Computation

For each musician on the roster, compute the following. Write a Python script
to handle the iteration, as the arithmetic involves many per-service lookups.

### Step 1: Base service pay

For each service the musician is assigned to:
- Look up the service by `service_id` in the production schedule.
- **Rehearsal**: max(3.0, duration_hours) * 58.75 (three-hour minimum call)
- **Performance, Audit, Sound Check**: flat rate from `service_rates`

Sum across all assigned services. This is the musician's `base_service_pay`.

### Step 2: Premiums

Premiums are computed per-service on the service's base rate. A single premium
flag applies to every service the musician is assigned to, multiplying the
per-service base rate.

Flags that trigger premiums:
- `principal` true or `lead` true -> principal_or_lead (0.15)
- `quartet` true -> quartet (0.15)
- `electronic` true -> electronic (0.25)
- `doubles` >= 1 -> first_double (0.25) on all services
- `doubles` >= 2 -> additional_double (0.10) * (doubles - 1) on all services

Sum all premium amounts across all assigned services. Split into two
categories:
- **premium**: sum of non-doubles premiums (principal_or_lead, quartet, electronic)
- **doubles**: sum of doubles premiums (first_double + additional_double)

### Step 3: Vacation

If `vacation_eligible` is true:
`vacation` = (base_service_pay + total of all premiums including doubles) * 0.04

### Step 4: Guarantee adjustment

If `substitute` is false and `base_service_pay` < `weekly_guarantee`:
`guarantee_adjustment` = `weekly_guarantee` - `base_service_pay`

This is a separate output category; it does not alter the service category
amounts.

### Step 5: Substitute adjustment

If `substitute` is true: the musician is not eligible for guarantee
adjustments. Compute `substitute_adjustment` = `base_service_pay`.

This is a separate output category. The substitute's normal service base pay
still appears under its respective categories (performance, audit, etc.).

---

## Category Mapping

After computing all amounts, assign each to its output category:

| Category | What it contains |
| --- | --- |
| `performance` | Sum of Performance service base rates |
| `rehearsal` | Sum of Rehearsal service base rates (with 3hr minimum) |
| `audit` | Sum of Audit service base rates |
| `sound_check` | Sum of Sound Check service base rates (1hr or 2hr) |
| `premium` | Sum of non-doubles premiums (principal_or_lead, quartet, electronic) |
| `doubles` | Sum of doubles premiums (first_double + additional_double) |
| `vacation` | Vacation pay (4% eligibility) |
| `guarantee_adjustment` | Weekly guarantee shortfall for non-substitutes |
| `substitute_adjustment` | Base service pay for substitutes |

### Category totals (aggregate)

Sum each category across all musicians for the top-level `category_totals` object.

### Weekly total

Sum all category totals. This is `weekly_total`.

---

## CBA Conflict Flags

Check the full production schedule against conflict thresholds:

1. **REHEARSAL_EARLY_START**: any Rehearsal service where start_time <
   `rehearsal_earliest_start` (09:00). Compare strings lexicographically.

2. **REHEARSAL_LATE_END**: any Rehearsal service where end_time >
   `rehearsal_latest_end` (18:30). Compare strings lexicographically.

3. **SERVICE_OVER_TIME_LIMIT**: any service where duration_hours strictly
   exceeds the limit for that service_type in `service_time_limits`.

4. **SOUND_CHECK_DURATION_MISMATCH**: a Sound Check service whose actual
   duration_hours, rounded to the nearest integer, does not match the
   expected hours from its type label (1 for "1hr Sound Check", 2 for
   "2hr Sound Check").

Return flags as a sorted list alphabetically. Only include flags that
actually apply to the production schedule.

---

## Per-Musician Output

For the `per_musician` array:

- `musician_id`: from roster
- `name`: from roster
- `total`: sum of all category amounts for that musician
- `categories`: object with only nonzero category amounts, keyed by category
  name (lowercase with underscores: performance, rehearsal, audit,
  sound_check, premium, doubles, vacation, guarantee_adjustment,
  substitute_adjustment)

Order the array by `musician_id` ascending.

### Top paid musician

`top_paid_musician_id` = `musician_id` with the highest `total`.
If two musicians have the same total, choose the one with the lower
`musician_id`.
