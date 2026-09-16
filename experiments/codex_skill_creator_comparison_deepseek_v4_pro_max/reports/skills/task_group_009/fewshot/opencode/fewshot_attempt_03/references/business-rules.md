# Crescent Finance Ops -- Business Rules

This reference covers compensation and payroll calculation rules with step-by-step
examples. Read this before computing any ensemble costs, forecasts, or production
payroll.

---

## Compensation -- Current-Year Calculation

### Step 1: Fetch inputs

```bash
curl -s $BASE_URL/api/compensation/rate-book
curl -s $BASE_URL/api/compensation/rosters
```

### Step 2: Filter roster by `ensemble_id`

Only employees whose `ensemble_id` matches the request memo's ensemble.

### Step 3: Compute four pay types per employee per quarter

For each employee and each quarter Q = Q1, Q2, Q3, Q4:

```
weeks = roster_entry.weeks_by_quarter[Q]
mws     = weeks x minimum_weekly_scale
```

**Titled Position Premium:**

```
if combined_overscale_includes_title:
    title_prem = 0.0
else:
    title_pct = rate_book.title_premium_pct[roster_entry.title]
    title_prem = weeks x minimum_weekly_scale x title_pct
```

If `roster_entry.title` is an empty string, `title_pct` is effectively 0
(no mapping in the rate book).

**Seniority:**

Find the band in `rate_book.seniority_weekly` where
`min_years <= roster_entry.years_of_service <= max_years` (null max = no upper bound).
Use the band's `weekly_amount`.

```
seniority = weeks x band.weekly_amount
```

**Overscale:**

```
overscale = weeks x roster_entry.overscale_weekly
```

### Step 4: Sum per quarter

```
quarter_total[Q] = mws + title_prem + seniority + overscale
```

### Step 5: Annual total and pay type totals

```
annual_total = sum(quarter_total[Q] for Q in Q1..Q4)
annual_pay_type_totals[TYPE] = sum of that type across all four quarters and all employees
quarter_totals[Q] = sum of quarter_total[Q] across all employees
```

### Step 6: Identify largest pay type

The pay type with the highest `annual_pay_type_totals` value.

### Roster counts

- `roster_count`: total employees after filtering by `ensemble_id`.
- `combined_overscale_employee_count`: employees where
  `combined_overscale_includes_title` is true.
- `partial_quarter_employee_count`: employees where any `weeks_by_quarter`
  value differs from the rate book's `quarter_weeks` default (13). Only count
  non-zero variance -- an employee with all quarters at exactly 13 does not
  count.

---

## Compensation -- Forecast Calculation

### Step 1: Additional fetch

Include `/api/compensation/scenarios` alongside rate-book and rosters.

### Step 2: Look up scenario

```python
scenario = scenarios[request_memo.scenario_id]
```

### Step 3: Current year

Compute identically to the current-year summary above. The rate book and
roster values are used as-is.

### Step 4: Year + 1

Apply the `year_plus_1` growth factors to derive a modified rate book:

```
mws_y1 = minimum_weekly_scale x (1 + year_plus_1.mws_growth)
```

For each seniority band:

```
seniority_y1[band].weekly_amount = band.weekly_amount x (1 + year_plus_1.seniority_growth)
```

For each title premium:

```
title_pct_y1[title] = title_premium_pct[title] x year_plus_1.title_pct_multiplier
```

For each employee's overscale:

```
overscale_y1 = roster_entry.overscale_weekly x (1 + year_plus_1.overscale_growth)
```

For each employee's years of service:

```
yos_y1 = roster_entry.years_of_service + 1
```

Then recompute all four pay types using the modified values. Use the same
`weeks_by_quarter` from the roster (roster weeks stay constant across years).
Sum to get the Year + 1 annual total.

### Step 5: Year + 2

Apply `year_plus_2` growth factors **on top of** Year + 1 values:

```
mws_y2 = mws_y1 x (1 + year_plus_2.mws_growth)
```

Senority amounts, title premiums, and overscale all compound on the Year + 1
values (not the originals):

```
seniority_y2[band].weekly_amount = seniority_y1[band].weekly_amount x (1 + year_plus_2.seniority_growth)
title_pct_y2[title] = title_pct_y1[title] x year_plus_2.title_pct_multiplier
overscale_y2 = overscale_y1 x (1 + year_plus_2.overscale_growth)
```

Years of service:

```
yos_y2 = roster_entry.years_of_service + 2
```

Then recompute. For Year + 2 reporting, provide the quarter and pay type
detail at the Year + 2 level.

### Step 6: Growth rates

```
year_plus_1_vs_current = (annual_total_y1 - annual_total_current) / annual_total_current
year_plus_2_vs_year_plus_1 = (annual_total_y2 - annual_total_y1) / annual_total_y1
```

### Step 7: Largest growth pay type

Compare each pay type's Year + 2 total vs its current-year total. The type
with the largest absolute growth (Year + 2 minus current) is the
`largest_growth_pay_type`. (If tied, use canonical order.)

---

## Payroll -- Weekly Production Calculation

### Step 1: Fetch inputs

```
curl -s $BASE_URL/api/payroll/rate-book
curl -s $BASE_URL/api/payroll/productions
```

Filter productions to the requested `production_id`.

### Step 2: Service base rate

For a given service with type and `duration_hours`:

```
if service_type == "Rehearsal":
    base = 58.75 × max(duration_hours, 3.0)   # hourly with 3-hour minimum call
else:
    base = service_rates[service_type]         # flat per-service rate
```

### Step 3: Service counts

Count each distinct `service_type` across all schedule entries. Map schedule
items to service type directly. Service types are: Performance, Rehearsal,
Audit, 1hr Sound Check, 2hr Sound Check.

### Step 4: Per-musician calculation

For each musician on the roster:

**a. Identify assigned services.** Cross-reference `assigned_service_ids` with
the schedule array.

**b. For each assigned service, compute the inflatable base:**

```
raw_base = service_base_rate(service)
```

If the musician is a **substitute** AND the service type is **Performance**:

```
base = raw_base × 1.5
```

Otherwise `base = raw_base`. The 0.5× extra for substitute performances is
tracked separately as `substitute_adjustment` (see below).

**c. Premiums on the computed base:**

```
premiums = 0.0
if musician.principal or musician.lead:
    premiums += base × principal_or_lead_pct   # 15%
if musician.quartet:
    premiums += base × quartet_pct             # 15%
if musician.electronic:
    premiums += base × electronic_pct          # 25%
# Doubles
if musician.doubles >= 1:
    premiums += base × first_double_pct        # 25%
if musician.doubles >= 2:
    premiums += base × additional_double_pct × (musician.doubles - 1)  # 10% each
```

**d. Vacation on (base + premiums):**

```
if musician.vacation_eligible AND NOT musician.substitute:
    vacation = (base + premiums) × 4%
else:
    vacation = 0.0
```

**e. Accumulate per-service totals:**

For each service, the musician earns: `base + premiums + vacation`.

Sum across all assigned services to get:
- `musician_base_total` (sum of raw_base across all services, used for guarantee check)
- `musician_premium_total` (sum of premiums)
- `musician_vacation_total` (sum of vacation)
- `musician_inflated_total` (sum of base + premiums + vacation, using inflated base for substitute performances)

**f. Substitute adjustment** (substitutes only):

```
substitute_adjustment = 0.0
for each assigned performance service:
    substitute_adjustment += 0.5 × raw_base_of_that_performance
```

Substitute adjustment is the total 0.5× increment on performances. It is
additive -- added to the inflated total after premiums.

**g. Guarantee adjustment** (non-substitutes only):

```
if NOT musician.substitute AND musician_base_total (raw) < weekly_guarantee:
    guarantee_adjustment = weekly_guarantee - musician_base_total
    musician_final_total = weekly_guarantee + musician_premium_total + musician_vacation_total
else:
    guarantee_adjustment = 0.0
    musician_final_total = musician_inflated_total
```

The guarantee replaces **only the raw base portion**, not premiums or vacation.
Premiums and vacation earned above base are always preserved.

**h. Final musician total for substitutes:**

```
musician_final_total = musician_inflated_total + substitute_adjustment
```

### Step 4: Category totals

For each category, sum the relevant amounts across all musicians:

| Category | What to sum |
|---|---|
| `performance` | Base rate x number of Performance services assigned |
| `audit` | Base rate x number of Audit services assigned |
| `rehearsal` | Base rate x number of Rehearsal services assigned (note: rehearsal is hourly, 3-hour minimum call -- see below) |
| `sound_check` | Base rate x number of Sound Check services assigned |
| `premium` | Sum of all premium amounts |
| `doubles` | Sum of all doubles premium amounts (first_double + additional_double) |
| `vacation` | Sum of all vacation amounts |
| `guarantee_adjustment` | Sum of all guarantee adjustments |
| `substitute_adjustment` | Sum of all substitute base amounts |

**Important:** The category breakdown uses the *actual* amounts computed above,
not a separate derivation. Some templates decompose premiums into sub-categories.
Always check the answer template's `field_types` for the exact category list
required.

### Step 5: Rehearsal minimum call

The payroll rate book says: "Rehearsal pay is hourly with a three-hour minimum
call." This means the rehearsal service rate ($58.75) is the hourly rate, and
the base pay for a rehearsal service is:

```
rehearsal_base = 58.75 x max(schedule_entry.duration_hours, 3.0)
```

This minimum applies only to Rehearsal, not to other service types. For all
other services, use the flat `service_rates` value regardless of duration.

### Step 6: Conflict flags

Check the entire schedule once:

**REHEARSAL_EARLY_START:** Any Rehearsal where `start_time` is before
`conflict_thresholds.rehearsal_earliest_start` (`"09:00"`). Compare as
strings or parse as HH:MM -- both work since times are zero-padded.

**REHEARSAL_LATE_END:** Any Rehearsal where `end_time` is after
`conflict_thresholds.rehearsal_latest_end` (`"18:30"`).

**SERVICE_OVER_TIME_LIMIT:** Any service where `duration_hours` exceeds
`service_time_limits[service_type]`. For example, a Performance at 2.75 hours
is within the 3.0 limit, but a Performance at 3.5 hours exceeds it.

**SOUND_CHECK_DURATION_MISMATCH:** A sound check where the actual duration
does not match its label. "1hr Sound Check" should have `duration_hours` of
1.0 (allow small floating-point tolerance, e.g., within 0.05). "2hr Sound
Check" should have `duration_hours` of 2.0.

Sort flags alphabetically. Only include flags that actually fire.

### Step 7: Top-paid musician

The musician with the highest final total. Break ties by `musician_id`
ascending.

---

## Rounding rules (applied everywhere)

| Field type | Precision | Python |
|---|---|---|
| Currency | 2 decimals | `round(value, 2)` |
| Percent / ratio | 4 decimals | `round(value, 4)` |
| Integer counts | Integer | No rounding |

Do not round intermediate values -- only round the final values placed into
the output JSON. This prevents accumulated rounding error.

---

## Sorting rules (applied everywhere)

| Output field | Sort order |
|---|---|
| `branch_ids` | Ascending string order (BR-004, BR-005, BR-006, ...) |
| `pay_types` | Canonical order: Minimum Weekly Scale, Titled Position Premium, Seniority, Overscale |
| `per_musician` | Ascending `musician_id` (M-H26-01, M-H26-02, ...) |
| `conflict_flags` | Alphabetical |
| `branch_rankings` keys | As defined in template; `_rank_desc` implies descending sort |

---

## Common pitfalls

1. **Forgetting rehearsal minimum call.** The rehearsal service rate ($58.75)
   is hourly. Base pay = 58.75 x max(duration, 3.0). Not a flat rate.

2. **Double-counting or missing combined_overscale_includes_title.** When
   true, set title premium to zero. The overscale amount already covers it.

3. **Not reading the rate book's business_rules.** The rate book contains
   critical rules (e.g., "If combined_overscale_includes_title is true, do
   not add a titled position premium separately"). Always read the
   `business_rules` array and apply every rule.

4. **Applying premiums to substitute musicians.** Substitutes DO get premiums
   on their inflated base (1.5x for performances). They do NOT get vacation
   or guarantee adjustment. Substitute adjustment (0.5x of raw performance
   base) is additive on top.

5. **Mixing up `concertmaster` premium.** The payroll rate book lists a
   `concertmaster` premium (20%), but the roster flag for concertmaster is
   not present in the standard roster schema. Only apply this premium if a
   `concertmaster_role` flag exists and is true. Do not infer it from
   instrument names.

6. **Rounding intermediate values.** Only round final output values.
   Intermediate sums should use full floating-point precision.

7. **Missing a category in category_totals.** Always check the answer
   template's `field_types.category_totals` for every required key. Some
   templates expect premiums and doubles as separate category entries; others
   combine them. Match the template exactly.

8. **Performance service rate is per service, not hourly.** Unlike Rehearsal,
   Performance, Audit, and Sound Check rates are flat per-service rates no
   matter the duration.
