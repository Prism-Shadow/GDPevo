# Payroll Domain Rules

## API Endpoints

| Endpoint | Returns |
|----------|---------|
| `/api/payroll/rate-book` | Service rates, premium percentages, conflict thresholds, weekly guarantee, business rules |
| `/api/payroll/productions` | Per-production schedule and roster with musician attributes |

GET both endpoints once. No filtering parameters, no authentication.

## Service Types and Rates

| Service Type | Rate | Charged As |
|-------------|------|------------|
| `Performance` | 260.25 | Per service |
| `Audit` | 260.25 | Per service |
| `Rehearsal` | 58.75 | Hourly, 3-hour minimum call |
| `1hr Sound Check` | 80.00 | Per service |
| `2hr Sound Check` | 142.50 | Per service |

## Per-Musician Pay Computation

For each musician, iterate their `assigned_service_ids`. For each assigned service, look up its entry in the production `schedule` array to find `service_type` and `duration_hours`.

### Step 1: Base service pay

- **Performance / Audit / Sound Check (1hr, 2hr):** flat rate from the rate book.
- **Rehearsal:** `max(duration_hours, 3.0) * rehearsal_rate` (the 3-hour minimum call applies).

### Step 2: Premiums (applied to base service pay before vacation)

Identify applicable premiums from the musician's roster flags:

| Flag | Premium Rate | Applies |
|------|-------------|---------|
| `principal` true | `principal_or_lead` (0.15) | If true |
| `lead` true | `principal_or_lead` (0.15) | If true |
| `electronic` true | `electronic` (0.25) | If true |
| `quartet` true | `quartet` (0.15) | If true |
| `doubles >= 1` | `first_double` (0.25) | For the first extra instrument |
| `doubles >= 2` | `additional_double` (0.10) | For each additional extra instrument |

Multiple premiums are additive on base service pay, not compounding. Total premium per service = `base_pay * sum(applicable_premium_rates)`.

Doubles premium uses the number of extra instruments: 1 double triggers first_double (0.25), each additional double above 1 triggers additional_double (0.10). Example: `doubles=2` means premium = 0.25 + 0.10 = 0.35 of base pay.

### Step 3: Vacation

If `vacation_eligible` is true, add 4% of (base service pay + premiums). If false, vacation = 0.

### Step 4: Weekly Guarantee Adjustment

For non-substitute musicians only. Sum base service pay across all assigned services for the week. If this sum is below `weekly_guarantee` (2082.00), the musician receives a `guarantee_adjustment = weekly_guarantee - base_service_pay_sum`.

Substitute musicians (`substitute: true`) do not receive guarantee adjustments. They also do not receive vacation (their `vacation_eligible` is always false).

## Category Totals

Aggregate per-musician amounts into these categories:

| Category | What it includes |
|----------|-----------------|
| `performance` | Sum of all Performance service pay across all musicians |
| `audit` | Sum of all Audit service pay |
| `rehearsal` | Sum of all Rehearsal service pay (with 3hr minimum applied) |
| `sound_check` | Sum of all 1hr and 2hr Sound Check service pay |
 | `premium` | Sum of non-doubles premiums only (principal/lead, electronic, quartet) |
 | `doubles` | Sum of doubles-related premiums only (first_double + additional_double) |
| `vacation` | Sum of all vacation pay |
| `guarantee_adjustment` | Sum of all weekly guarantee adjustments |
| `substitute_adjustment` | When substitute musicians appear, the adjustment the regular musician would have received if they performed the same services. Compute: for each substitute, find the sum of base service pay for their assigned services, compute `weekly_guarantee - base_sum`, and if positive, include that amount. |

 **Important:** `premium` and `doubles` are separate, non-overlapping categories. `premium` includes only principal/lead, electronic, and quartet premiums. `doubles` includes only doubles-related premiums. A given dollar amount belongs to exactly one of these two categories.

## Service Counts

Count distinct services from the schedule by `service_type`. Merge `1hr Sound Check` and `2hr Sound Check` into one combined count if the template asks for a single sound-check count. Otherwise keep them separate as the schedule provides them.

## Conflict Flags

Check the schedule against the rate book `conflict_thresholds`:

| Flag | Condition |
|------|-----------|
| `REHEARSAL_EARLY_START` | Any Rehearsal `start_time` is earlier than `rehearsal_earliest_start` (09:00) |
| `REHEARSAL_LATE_END` | Any Rehearsal `end_time` is later than `rehearsal_latest_end` (18:30) |
| `SERVICE_OVER_TIME_LIMIT` | Any service's `duration_hours` exceeds its type's `service_time_limits` entry |
| `SOUND_CHECK_DURATION_MISMATCH` | A Sound Check service's `duration_hours` does not match its named type (1hr vs 2hr) |

Include only the flags that trigger. Sort the flag list alphabetically.

## Per-Musician Output

For the `per_musician` array, include every musician on the production roster. Order by `musician_id` ascending. For each, include only categories with nonzero amounts. The `total` is the sum of all category amounts for that musician.

## Rounding

- Currency values: round to 2 decimal places.
- Counts: integers.
