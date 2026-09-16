# Crescent Payroll — Weekly Production Payroll Reference

## Endpoints

| Endpoint | Description |
|---|---|
| `/api/payroll/rate-book` | Service rates, premium percentages, conflict thresholds, business rules, weekly guarantee |
| `/api/payroll/productions` | List of productions; each has `production_id`, `title`, `week_start`, `schedule`, `roster` |

## Rate Book Structure

`service_rates` (per-service rates keyed by service_type string), `premium_pct` (applicable premium percentages), `conflict_thresholds` (`rehearsal_earliest_start`, `rehearsal_latest_end`), `service_time_limits` (max hours per service_type), `weekly_guarantee`, `business_rules` (list of strings).

## Schedule

Each entry: `service_id`, `date`, `service_type` (one of "Rehearsal", "Performance", "Audit", "1hr Sound Check", "2hr Sound Check"), `start_time`, `end_time`, `duration_hours`.

## Roster

Each musician: `musician_id`, `name`, `assigned_service_ids` (list), `doubles` (int count), booleans `lead`, `principal`, `quartet`, `electronic`, `substitute`, `vacation_eligible`.

## Payroll Business Rules

1. **Rehearsal**: hourly rate with a three-hour minimum call — `max(3, duration_hours) × rehearsal_rate`.
2. **Performance, Audit, Sound Check**: flat per-service rate from `service_rates`.
3. **Premiums**: applied to the musician's base service pay for each service before vacation is calculated.
4. **Doubles**: first extra instrument = 25% of base service pay; each additional extra = 10% of base service pay.
5. **Vacation**: 4% of (base service pay + all premiums), only when `vacation_eligible` is true.
6. **Guarantee adjustment**: only for non-substitute (regular) players when total base service pay < `weekly_guarantee`. Adjustment = `weekly_guarantee - base_service_pay`.
7. **Substitutes**: do not receive guarantee adjustments. They are not vacation eligible (vacation_eligible=false by convention for subs). They use the same base service rates as regular musicians.

## Service Categories for Totals

| Category | What It Includes |
|---|---|
| `performance` | Per-service flat rate for Performance services |
| `audit` | Per-service flat rate for Audit services |
| `rehearsal` | Hourly rehearsal pay with 3-hour minimum call |
| `sound_check` | Per-service flat rate for 1hr/2hr Sound Check services |
| `premium` | All non-doubles premiums: principal_or_lead (15%), concertmaster (20%), quartet (15%), electronic (25%) |
| `doubles` | First double (25%) and additional doubles (10% each) |
| `vacation` | 4% of (base service pay + all premiums) for vacation-eligible musicians |
| `guarantee_adjustment` | Weekly guarantee shortfall for non-substitute regular players |
| `substitute_adjustment` | When applicable, any substitute-specific adjustment from the business rules |

## Conflict Flags

Check the schedule against conflict thresholds. Available flags:

| Flag | Condition |
|---|---|
| `REHEARSAL_EARLY_START` | Any rehearsal `start_time` earlier than `rehearsal_earliest_start` |
| `REHEARSAL_LATE_END` | Any rehearsal `end_time` later than `rehearsal_latest_end` |
| `SERVICE_OVER_TIME_LIMIT` | Any service `duration_hours` exceeds `service_time_limits[service_type]` |
| `SOUND_CHECK_DURATION_MISMATCH` | Sound Check where actual duration differs from the service-type nominal label by > 0.25 hours (e.g. a "1hr Sound Check" running 1.5h) |

Sort conflict flags alphabetically.

## Per-Musician Calculation

For each musician:

1. **Base service pay**: for each assigned service, apply the per-service rate. Rehearsals = `max(3, duration_hours) × rehearsal_rate`. Others = flat `service_rates[service_type]`.
2. **Premiums per service**, computed on that service's base pay:
   - `concertmaster` (20%): if `principal` AND `lead` (replaces `principal_or_lead`)
   - `principal_or_lead` (15%): if `principal` OR `lead`, but NOT when concertmaster already triggered
   - `quartet` (15%): if `quartet`
   - `electronic` (25%): if `electronic`
   - `first_double` (25%): if `doubles` >= 1
   - `additional_double` (10% each): for each double beyond the first
3. **Vacation**: 4% of (total base service pay + total premiums), only if `vacation_eligible`.
4. **Guarantee adjustment**: if not substitute and total base service pay < weekly_guarantee, add the shortfall. If substitute, none.
5. **Total**: base service pay + premiums + vacation + guarantee_adjustment.
6. **Categories**: for per_musician output, include only category keys with nonzero amounts.

## Top Paid Musician

The `musician_id` with the highest total weekly pay.

## Weekly Total

Sum of all musician totals.

## Service Counts

Count of each distinct `service_type` from the schedule (not per-musician), keyed by service_type string.
