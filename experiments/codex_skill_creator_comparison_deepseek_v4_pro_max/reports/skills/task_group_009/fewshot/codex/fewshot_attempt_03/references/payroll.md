# Payroll Module

## Endpoints

- `GET /api/payroll/rate-book` — service rates, premium percentages, conflict thresholds, weekly guarantee, business rules, and service time limits.
- `GET /api/payroll/productions` — list of productions. Each has `production_id`, `title`, `week_start`, `schedule` (list of service entries), and `roster` (list of musicians with assigned_service_ids and flags).

## Service Types and Rates

Service types: Performance, Audit, Rehearsal, 1hr Sound Check, 2hr Sound Check. Rates come from `service_rates` in the rate book.

## Per-Musician Pay Computation

For each musician, iterate through their `assigned_service_ids`. For each service:

1. Look up the service by `service_id` in the production schedule.
2. Get the base rate from `service_rates` by `service_type`.
3. Compute base service pay:
   - Rehearsal: `max(rate * duration_hours, rate * 3.0)` (three-hour minimum call)
   - All others: flat per-service rate
4. Compute premiums on base service pay (additive):
   - `principal_or_lead` (15%): if `principal` or `lead` flag is true
   - `quartet` (15%): if `quartet` flag is true
   - `electronic` (25%): if `electronic` flag is true
   - `first_double` (25%): if `doubles` >= 1
   - `additional_double` (10% each): for each double beyond the first
5. Compute vacation: if `vacation_eligible` is true, add 4% of (base service pay + all premiums).
6. Per-service total = base + premiums + vacation.

After processing all services, check guarantee:
7. For non-substitute musicians: if total base service pay (before premiums and vacation) is below `weekly_guarantee`, add `weekly_guarantee - total_base_service_pay` as `guarantee_adjustment`.
8. For substitute musicians: add `substitute_adjustment` equal to the guarantee shortfall computed on the services they cover (same formula as step 7, but labeled substitute_adjustment).

## Per-Musician Category Breakdown

Each musician's `categories` object maps category names to currency amounts. Categories track where pay comes from:

- `performance`: sum of base pay for Performance services
- `rehearsal`: sum of base pay for Rehearsal services
- `sound_check`: sum of base pay for Sound Check services (1hr or 2hr)
- `audit`: sum of base pay for Audit services
- `premium`: sum of principal_or_lead, quartet, electronic premiums (excludes doubles)
- `doubles`: sum of first_double and additional_double premiums
- `vacation`: sum of vacation pay
- `guarantee_adjustment`: amount added to reach weekly_guarantee for regulars
- `substitute_adjustment`: amount added for substitute guarantee shortfall

Only include categories with nonzero amounts in the per-musician `categories`.

## Category Totals

Sum each category across all musicians. Include zero-value categories in `category_totals` (set to 0.0) only if required by the template structure.

## Weekly Total

Sum of all per-musician totals.

## Top Paid Musician

The `musician_id` with the highest `total`.

## Service Counts

Count occurrences of each `service_type` in the production schedule. Output as object mapping service_type string to integer count.

## Conflict Flags

Compare the production schedule against conflict thresholds in the rate book:

- **REHEARSAL_EARLY_START**: any Rehearsal with `start_time` before `rehearsal_earliest_start` (09:00)
- **REHEARSAL_LATE_END**: any Rehearsal with `end_time` after `rehearsal_latest_end` (18:30)
- **SERVICE_OVER_TIME_LIMIT**: any service with `duration_hours` exceeding its `service_time_limits` value
- **SOUND_CHECK_DURATION_MISMATCH**: any Sound Check whose `duration_hours` does not match the expected duration (1.0 for 1hr, 2.0 for 2hr)

Collect all detected flags and sort alphabetically.

## Rounding

All currency amounts: round to 2 decimals.

## Ordering

- `per_musician` list: ascending by `musician_id`.
- `conflict_flags`: sorted alphabetically.
