# Payroll Domain

## Service rates

Each service in the production schedule has a type and rate:

| Service Type | Rate | Unit | Time Limit |
|---|---|---|---|
| Performance | 260.25 | per service | 3.0 hrs |
| Audit | 260.25 | per service | 3.0 hrs |
| Rehearsal | 58.75 | hourly, 3-hr min | 5.0 hrs |
| 1hr Sound Check | 80.00 | per service | 1.0 hrs |
| 2hr Sound Check | 142.50 | per service | 2.0 hrs |

## Service pay computation

For each service a musician is assigned to, compute base pay:
- **Performance / Audit**: flat rate of 260.25
- **Sound Check** (1hr or 2hr): flat rate (80.00 or 142.50)
- **Rehearsal**: hourly rate x max(3 hours, actual duration). The rehearsal rate is 58.75/hour but the minimum is always 3 hours, so the base is 58.75 x max(3, duration_hours).

## Premiums

Premiums are computed as percentages of the base service pay, applied **before** vacation. A musician may qualify for multiple premiums on the same service:

- **Principal or Lead**: 15% if `principal` or `lead` is true
- **Quartet**: 15% if `quartet` is true
- **Electronic**: 25% if `electronic` is true
- **Doubles**: 25% for the first extra instrument if `doubles >= 1`, plus 10% for each additional instrument beyond the first (if `doubles >= 2`, add 0.10 for each beyond the first)

All premium percentages are additive. Sum them, then multiply the base pay by (1 + total_premium_pct).

## Vacation

Vacation is 4% of (base service pay + premium amounts). It only applies to musicians with `vacation_eligible: true`.

## Weekly guarantee adjustment

A weekly guarantee of 2082.00 applies only to **regular, non-substitute** musicians. The guarantee is the minimum weekly total a regular musician should earn from base service pay.

Adjustment computation:
1. Compute base service pay across all assigned services (before premiums and vacation)
2. If base service pay < 2082.00 AND the musician is not a substitute: `guarantee_adjustment = 2082.00 - base_service_pay`
3. If base service pay >= 2082.00: guarantee_adjustment = 0.00

The guarantee adjustment is added after premiums and vacation as a separate line item.

## Substitute adjustment

A substitute musician's pay for their assigned services belongs in the `substitute_adjustment` category. When a musician has `substitute: true`:
- Their base service pay + premiums + vacation are totaled under `substitute_adjustment`
- They are NOT eligible for weekly guarantee adjustment

Do NOT double-count substitute musicians' pay in both regular category totals and substitute_adjustment. Their pay appears only in substitute_adjustment.

## Per-musician totals

For each musician, compute:
- Total pay across all assigned services (base + premiums + vacation + guarantee_adjustment, or substitute_adjustment for substitutes)
- A `categories` object mapping each nonzero pay category name to its currency amount

Categories to track per musician:
- `performance`: base pay for Performance services
- `audit`: base pay for Audit services
- `rehearsal`: base pay for Rehearsal services
- `sound_check`: base pay for both 1hr and 2hr Sound Check services (summed)
- `premium`: sum of all premium amounts (principal/lead, quartet, electronic, doubles)
- `doubles`: doubles premium amounts (if tracked separately)
- `vacation`: vacation pay amounts
- `guarantee_adjustment`: guarantee top-up amounts
- `substitute_adjustment`: pay for substitute-covered services (only for substitute musicians)

**Category totals**: Sum each category across all musicians. The `weekly_total` is the sum of all category totals.

**Per-musician list**: Ordered by `musician_id` ascending.

## Top paid musician

The musician with the highest `total`. If tied, the first by musician_id ascending order.

## Service counts

Count services by type across the schedule:
- "Performance": count of Performance services
- "Audit": count of Audit services
- "Rehearsal": count of Rehearsal services
- "1hr Sound Check": count of 1hr Sound Check services
- "2hr Sound Check": count of 2hr Sound Check services

Only include service types that actually appear in the schedule.

## Conflict detection

Check the production schedule against the conflict thresholds from the rate book. Possible conflict flags:

- **REHEARSAL_EARLY_START**: any Rehearsal service with `start_time` earlier than `rehearsal_earliest_start` (default "09:00"). Compare as time strings using string comparison since they are in HH:MM format.
- **REHEARSAL_LATE_END**: any Rehearsal service with `end_time` later than `rehearsal_latest_end` (default "18:30").
- **SERVICE_OVER_TIME_LIMIT**: any service where `duration_hours` exceeds the service's time limit from `service_time_limits`.
- **SOUND_CHECK_DURATION_MISMATCH**: a "1hr Sound Check" with duration_hours not equal to 1.0, or a "2hr Sound Check" with duration_hours not equal to 2.0.

Sort conflict flags alphabetically in the output.
