## Payroll API Reference — Crescent Finance Ops

### Endpoints

| Endpoint | Description | Query Params |
|---|---|---|
| `/api/payroll/rate-book` | Service rates, premiums, weekly guarantee, conflict thresholds, business rules | none |
| `/api/payroll/productions` | Production schedule and roster for a given week | `production_id` |

### Rate Book Structure

- `service_rates`: per-service rates for Performance, Rehearsal (hourly), Audit, 1hr Sound Check, 2hr Sound Check
- `service_time_limits`: max hours per service type
- `premium_pct`: percentages for first_double (0.25), additional_double (0.10), concertmaster (0.20), principal_or_lead (0.15), quartet (0.15), electronic (0.25), vacation (0.04)
- `weekly_guarantee`: 2082.00
- `conflict_thresholds`: `rehearsal_earliest_start` ("09:00"), `rehearsal_latest_end` ("18:30")
- `business_rules`: array of rule strings

### Production Structure

Each `/api/payroll/productions` returns an array (even for a single production by id). Each entry has:
- `production_id`, `title`, `week_start`
- `schedule`: array of service objects [{service_id, date, service_type, start_time, end_time, duration_hours}]
- `roster`: array of musician objects [{musician_id, name, instrument, assigned_service_ids, doubles, electronic, lead, principal, quartet, substitute, vacation_eligible}]

### Per-Service Pay Calculation

**Rehearsal (hourly, 3-hour minimum call)**:
- `rehearsal_pay = max(3.0, duration_hours) * service_rates["Rehearsal"]`

**Performance / Audit (per service)**:
- `pay = service_rates[service_type]`

**Sound Check (per service)**:
- `pay = service_rates[service_type]`

### Premiums

Premiums stack additively. Compute per-musician premium percentages once (they apply to every service assigned to that musician):

- `principal_or_lead_pct = premium_pct["principal_or_lead"]` if `principal` OR `lead` is true
- `quartet_pct = premium_pct["quartet"]` if `quartet` is true
- `electronic_pct = premium_pct["electronic"]` if `electronic` is true
- `doubles_pct = premium_pct["first_double"]` if `doubles >= 1`, plus `premium_pct["additional_double"]` per instrument beyond the first: `max(0, doubles-1) * premium_pct["additional_double"]`

These percentages are applied to total base pay, not per-service. Compute `non_doubles_premium_pct = principal_or_lead_pct + quartet_pct + electronic_pct`. Then:
- `premium = total_base_pay * non_doubles_premium_pct`
- `doubles = total_base_pay * doubles_pct`

**Substitute adjustment**: For a substitute musician:
1. Find the set of service IDs assigned to ALL regular (non-substitute) musicians — compute the set intersection across all regular musicians.
2. Count how many services from that intersection the substitute is NOT assigned to.
3. `substitute_adjustment = (missing_count) * service_rates["Performance"]`
4. Add `substitute_adjustment` to the substitute's performance base pay. Premiums (non-doubles and doubles) are computed on the inflated base pay. Vacation also uses the inflated base.
5. The `substitute_adjustment` value also appears as a separate category in the musician's output.

Substitute musicians do NOT receive vacation or guarantee_adjustment (even if `vacation_eligible` is true).

### Vacation

If `vacation_eligible` is true AND musician is not a substitute:
`vacation = (total_base_pay + premium + doubles) * premium_pct["vacation"]`

Vacation is computed on the musician's total (base + all premiums), not per-service.

### Weekly Guarantee Adjustment

For non-substitute musicians only: if `total_base_pay < weekly_guarantee`, then:
`guarantee_adjustment = weekly_guarantee - total_base_pay`

The adjustment applies to the musician's total, not per-service.

### Per-Musician Totals

For each musician compute:
- `musician_id`, `name`
- `total`: sum of all base pay + premium + doubles + vacation + guarantee_adjustment + substitute_adjustment
- `categories`: object mapping nonzero category names to their currency values. Include: `performance`, `audit`, `rehearsal`, `sound_check`, `premium`, `doubles`, `vacation`, `guarantee_adjustment`, `substitute_adjustment`.

Order per_musician by `musician_id` ascending.

### Category Totals

`premium` and `doubles` are separate, non-overlapping categories:
- **premium**: principal_or_lead + quartet + electronic premiums (excludes doubles)
- **doubles**: first_double + additional_double premiums only

Sum across all musicians for each category:
- **performance**: base pay for Performance services
- **audit**: base pay for Audit services
- **rehearsal**: base pay for Rehearsal services
- **sound_check**: base pay for Sound Check services
- **premium**: non-doubles premiums
- **doubles**: doubles premiums
- **vacation**: vacation amounts
- **guarantee_adjustment**: weekly guarantee adjustments
- **substitute_adjustment**: substitute musician adjustment (positive amount)

### Service Counts

`service_counts` is an object mapping each service_type string to the integer count of occurrences of that type in the schedule. Only count each service once regardless of how many musicians are assigned.

### Conflict Flags

Check the schedule for these issues. Return alphabetically sorted list of enum values that apply:

- **REHEARSAL_EARLY_START**: Any Rehearsal service with `start_time` < `rehearsal_earliest_start` ("09:00")
- **REHEARSAL_LATE_END**: Any Rehearsal service with `end_time` > `rehearsal_latest_end` ("18:30")
- **SERVICE_OVER_TIME_LIMIT**: Any service whose `duration_hours` > `service_time_limits` for that service type
- **SOUND_CHECK_DURATION_MISMATCH**: A sound check service whose `duration_hours` != `service_time_limits` for that type

### Top Paid Musician

`top_paid_musician_id`: the `musician_id` with the highest `total` across all musicians.

### Output Conventions

- All currency: 2 decimal places using standard round-half-up. In Python use `Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)`.
- `per_musician` ordered by musician_id ascending
- `conflict_flags` sorted alphabetically
- `categories` inside per_musician: only include nonzero amounts (use threshold > 0.001)
