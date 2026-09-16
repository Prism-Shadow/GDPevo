# Payroll Domain Reference

The payroll endpoints (`/api/payroll/rate-book`, `/api/payroll/productions`) support
weekly production payroll calculations, per-musician breakdowns, and CBA/contract
conflict flag detection.

## Rate Book Structure

- `service_rates`: per-service-type base rates (Performance, Audit, Rehearsal,
  1hr Sound Check, 2hr Sound Check).
- `premium_pct`: percentage multipliers for bonus conditions.
- `conflict_thresholds`: time boundaries for contract compliance.
- `weekly_guarantee`: minimum weekly base pay for guaranteed regular players.
- `service_time_limits`: maximum allowed hours per service type.
- `business_rules`: narrative rules that encode payroll logic.

## Production Data

Each production entry has a `production_id`, `roster` array of musicians, and
`schedule` array of service events. A musician's `assigned_service_ids` links them
to the services they performed.

### Musician Roster Fields

| Field | Meaning |
|-------|---------|
| `assigned_service_ids` | Which services the musician played |
| `doubles` | Number of extra instruments beyond the primary |
| `electronic` | Whether electronic instrument premium applies |
| `instrument` | Primary instrument |
| `lead` | Whether the musician is a section lead |
| `musician_id` | Unique ID |
| `name` | Display name |
| `principal` | Whether the musician is a principal player |
| `quartet` | Whether quartet premium applies |
| `substitute` | If true, musician is a substitute (not regular) |
| `vacation_eligible` | Whether vacation pay applies |

### Schedule Fields

| Field | Meaning |
|-------|---------|
| `service_id` | Unique service ID |
| `service_type` | Performance, Rehearsal, Audit, 1hr Sound Check, 2hr Sound Check |
| `start_time` | HH:MM 24-hour |
| `end_time` | HH:MM 24-hour |
| `duration_hours` | Decimal hours |
| `date` | ISO date |

## Per-Musician Pay Calculation

For each musician, compute pay by iterating over their assigned services. For each
service the musician is assigned to:

### Step 1: Base Service Pay

Look up `service_rates[service_type]` -- this is the per-service rate.

**Rehearsal rule**: Rehearsal is priced per hour at the rehearsal rate, with a
3-hour minimum. Use:
`max(3.0, duration_hours) * service_rates["Rehearsal"]`.

**All other service types**: Use the flat `service_rates` value directly. Sound
check, audit, and performance rates are per-service, not per-hour.

### Step 2: Premiums

Premiums apply to **base service pay**. Compute these per service:

1. **Principal or Lead**: If `principal` or `lead` is true, add
   `base_pay * premium_pct["principal_or_lead"]`.

2. **Quartet**: If `quartet` is true, add
   `base_pay * premium_pct["quartet"]`.

3. **Electronic**: If `electronic` is true, add
   `base_pay * premium_pct["electronic"]`.

4. **Doubles**: If `doubles >= 1`, add
   `base_pay * premium_pct["first_double"]`.
   If `doubles >= 2`, also add
   `(doubles - 1) * base_pay * premium_pct["additional_double"]`.

Sum all premiums into a `total_premiums` amount per service.

### Step 3: Vacation

If `vacation_eligible` is true:
`vacation_pay = (base_pay + total_premiums) * premium_pct["vacation"]`.

If `vacation_eligible` is false, vacation = 0.

### Step 4: Per-Service Total

`service_total = base_pay + total_premiums + vacation_pay`.

### Step 5: Weekly Guarantee Adjustment

The guarantee adjustment applies **only to guaranteed regular players** -- musicians
where `substitute` is `false`. Substitutes never receive a guarantee adjustment.

For a guaranteed regular player:
- Compute `total_base_service_pay` = sum of base service pay across all assigned
  services (do not include premiums or vacation in this sum).
- If `total_base_service_pay < weekly_guarantee`:
  `guarantee_adjustment = weekly_guarantee - total_base_service_pay`.
- Otherwise, guarantee_adjustment = 0.

### Step 6: Substitute Adjustment

Only for musicians where `substitute` is `true`.

Compute the median number of assigned services among all **non-substitute**
musicians on the roster. If there is an even number of regulars, use the higher
of the two middle values (upper median). Let this be `median_regular_services`.

Let `n_sub_services` be the number of services assigned to the substitute.

`substitute_adjustment = max(0, median_regular_services - n_sub_services)
  * service_rates["Performance"]`.

Note: the substitute adjustment is always denominated at the Performance service
rate regardless of which service types the substitute missed.

**In per_musician categories**: Add the substitute_adjustment amount to the
musician's `performance` category total. Also list it separately as
`substitute_adjustment`.

**In category_totals**: List `substitute_adjustment` as its own category. The
`performance` category total also includes the substitute adjustment amounts.

### Step 7: Musician Total

`musician_total = sum of all service totals + guarantee_adjustment
  + substitute_adjustment`.

Round the final total to 2 decimals.

## Category Totals

After computing pay for all musicians, aggregate by category:

- **performance**: sum of base pay for all Performance services across all
  musicians, PLUS all substitute_adjustment amounts.
- **audit**: sum of base pay for all Audit services.
- **rehearsal**: sum of base pay for all Rehearsal services.
- **sound_check**: sum of base pay for all Sound Check services (1hr and 2hr
  combined).
- **premium**: sum of all premium amounts across all musicians and services.
- **doubles**: sum of all doubles premium amounts across all musicians and
  services.
- **vacation**: sum of all vacation amounts.
- **guarantee_adjustment**: sum of all guarantee adjustments.
- **substitute_adjustment**: sum of all substitute adjustments. Omit this
  key when no substitutes exist; include it with 0.0 when zero subs or the
  calculation produces 0 for all subs.

## Per-Musician Categories

For each musician's `categories` object, include only categories where the
amount is nonzero. Map internal computations to these category keys:
`performance`, `audit`, `rehearsal`, `sound_check`, `premium`, `doubles`,
`vacation`, `guarantee_adjustment`, `substitute_adjustment`.

For a substitute: add their substitute_adjustment to the `performance` category
and also include a separate `substitute_adjustment` category.

## Weekly Total

Sum of all musician totals. Equal to the sum of category_totals values.

## Service Counts

Count distinct services by type from the schedule using the production's schedule
array. Each service in the schedule counts once, regardless of how many musicians
are assigned. Use the exact `service_type` strings as keys.

## Conflict Flag Detection

Check the schedule against the conflict thresholds from the rate book:

1. **REHEARSAL_EARLY_START**: Any Rehearsal service where `start_time` is earlier
   than `conflict_thresholds["rehearsal_earliest_start"]` (compare lexicographically
   as HH:MM strings). Example: a rehearsal starting at 08:45 when threshold is
   09:00 triggers the flag.

2. **REHEARSAL_LATE_END**: Any Rehearsal service where `end_time` is later than
   `conflict_thresholds["rehearsal_latest_end"]`. Example: a rehearsal ending at
   18:35 when threshold is 18:30 DOES trigger; ending at 16:35 does NOT.

3. **SERVICE_OVER_TIME_LIMIT**: Any service where `duration_hours` exceeds
   `service_time_limits[service_type]`. Strict greater-than; equal to or under
   the limit does not trigger.

4. **SOUND_CHECK_DURATION_MISMATCH**: A Sound Check service where the
   `duration_hours` differs from the nominal duration implied by its type.
   "1hr Sound Check" must have duration exactly 1.0 hours; "2hr Sound Check"
   must have duration exactly 2.0 hours. Any deviation triggers this flag.

Return `conflict_flags` as a sorted list (alphabetical order) using only the
enum strings above. Only include flags that are actually triggered.

## Top Paid Musician

The musician with the highest `total` value. If multiple musicians tie, pick the
one with the lowest (lexicographically first) `musician_id`.

## Per-Musician Output Order

Sort `per_musician` by `musician_id` in ascending alphabetical order.

## Formatting

- All currency values: round to 2 decimals.
- `per_musician` array: sorted ascending by `musician_id`.
- `conflict_flags`: sorted alphabetically.
- `category_totals` keys: include all applicable categories. Omit a category key
  entirely only if its total is zero and the template lists it as optional
  (e.g., `substitute_adjustment`). Otherwise include it with 0.0.
