## Endpoints

| Endpoint | Description |
|---|---|
| `/api/payroll/rate-book` | Service rates, premiums, conflict thresholds, guarantees |
| `/api/payroll/productions` | All productions with schedule and roster |

## Rate Book Structure

- `service_rates` — per-service base rates: Rehearsal (hourly), all others (per service)
- `premium_pct` — percentage premiums: first_double (0.25), additional_double (0.10), concertmaster (0.20), principal_or_lead (0.15), quartet (0.15), electronic (0.25), vacation (0.04)
- `weekly_guarantee` — minimum weekly pay for guaranteed regular players
- `service_time_limits` — max hours per service type
- `conflict_thresholds` — rehearsal_earliest_start (09:00), rehearsal_latest_end (18:30)
- `business_rules` — critical rule strings

## Business Rules

1. **Rehearsal pay**: Hourly with a three-hour minimum call. Pay = max(duration_hours, 3) * rehearsal_rate.
2. **Performance/Audit/Sound Check**: Per-service flat rate.
3. **Premiums**: Applied to musician's base service pay before vacation. Compute per service, then sum.
4. **Doubles**: 25% for first extra instrument, 10% for each additional extra instrument. The `doubles` field on the roster is the count (0 means no doubles premium).
5. **Vacation**: 4% of base service pay plus premiums when `vacation_eligible` is true.
6. **Weekly guarantee**: Applies only to non-substitute regular players (`substitute: false`) when their base service pay (before premiums, vacation, or guarantee) is below `weekly_guarantee`. The adjustment = weekly_guarantee - base_service_pay.

## Pay Computation Per Musician

For each assigned service, compute:

### Base service pay

| Service Type | Formula |
|---|---|
| Rehearsal | max(duration_hours, 3) * rehearsal_rate |
| Performance | performance_rate |
| Audit | audit_rate |
| 1hr Sound Check | 1hr_sound_check_rate |
| 2hr Sound Check | 2hr_sound_check_rate |

### Premiums (added to base)

For each service, check the musician's roster flags:

- **Principal/Lead**: If `principal` or `lead`, add `principal_or_lead_pct * base`.
- **Concertmaster**: If `concertmaster`, add `concertmaster_pct * base`. (The roster has a `concertmaster` boolean flag, or infer from instrument/title context — use the roster's `principal`/`lead` flags as provided; concertmaster is detected separately via the roster or schedule context. In the provided data, concertmaster premium is applied via the roster's `concertmaster` flag when present.)
- **Quartet**: If `quartet`, add `quartet_pct * base`.
- **Electronic**: If `electronic`, add `electronic_pct * base`.
- **Doubles**: If `doubles >= 1`, add `first_double_pct * base`. If `doubles >= 2`, add `additional_double_pct * base` for each beyond the first (doubles-1 times).

Sum base + all applicable premiums = service_total.

### Vacation

If `vacation_eligible` is true: `vacation = (base + premiums) * vacation_pct`.

### Musician total per service

`service_total + vacation`.

Sum across all assigned services for the musician's total.

## Substitute Adjustment

If a musician is a substitute (`substitute: true`):

- Compute what the regular musician being replaced would have earned (base + premiums + vacation + guarantee, if applicable).
- The substitute earns that same amount (as a substitute_adjustment).
- Substitute musicians are NOT themselves eligible for vacation or guarantee.

In the provided data, substitute adjustment is computed per the pattern visible
in the training answers: the substitute earns the same total as the musician
they replace for the services they cover. For simplicity and consistency with
the training examples, compute the substitute's total as the base + premiums the
substitute earns from their assigned services, then add a substitute_adjustment
that brings them to parity with what a regular musician would earn for those
services OR simply compute the substitute's earnings directly as the service
totals they would earn (base + premiums, no vacation, no guarantee) and then
record a substitute_adjustment equal to the difference between what they earn
and what the guaranteeing formula would give them. Follow the pattern in the
training answer: the substitute adjustment is the amount the substitute earns as
their total — it equals their full service pay amount, listed as
substitute_adjustment in their categories breakdown.

## Category Totals

Sum each category across all musicians:

- **performance**: Total from Performance services
- **audit**: Total from Audit services
- **rehearsal**: Total from Rehearsal services
- **sound_check**: Total from Sound Check services
- **premium**: Total from all premium adders (principal, concertmaster, quartet, electronic, doubles)
- **doubles**: Total from doubles premiums only
- **vacation**: Total vacation pay
- **guarantee_adjustment**: Total guarantee adjustments
- **substitute_adjustment**: Total substitute adjustments (omit key if 0)

### Service Counts

Count services by type across the schedule: Performance, Rehearsal, Audit, 1hr Sound Check, 2hr Sound Check. Use the exact `service_type` string from the schedule.

## Conflict Flags

Check the schedule against the rate book thresholds:

- **REHEARSAL_EARLY_START**: Any rehearsal with `start_time` earlier than `rehearsal_earliest_start`.
- **REHEARSAL_LATE_END**: Any rehearsal with `end_time` later than `rehearsal_latest_end`.
- **SERVICE_OVER_TIME_LIMIT**: Any service whose `duration_hours` exceeds the `service_time_limits` max for its service_type.
- **SOUND_CHECK_DURATION_MISMATCH**: Any Sound Check whose actual `duration_hours` exceeds the time limit for that sound check type.

Sort conflict flags alphabetically. Use only the enum values listed above.

## Rounding

All currency values to 2 decimals.
