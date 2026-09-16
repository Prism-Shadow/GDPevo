# Weekly payroll review

Use this for weekly payroll packages driven by a production schedule and roster.

## Endpoints

- `/api/payroll/rate-book`
- `/api/payroll/productions`

## Data model

- The rate book provides `service_rates`, `service_time_limits`, `premium_pct`, `weekly_guarantee`, and the conflict thresholds.
- `productions` contains one production with a `schedule` and a `roster`.
- Use `production_id` from the memo to select the production.

## Calculations

- `service_counts` counts schedule rows by exact `service_type` label.
- Use the schedule and roster together to compute per-musician pay.
- Rehearsal pay is hourly with a 3-hour minimum call.
- Performance, audit, and sound-check rates come from the rate book service rates.
- Apply premiums to the musician's base service pay before vacation.
- Map roster flags to the premium keys in the rate book: `principal` or `lead` -> `principal_or_lead`, `quartet` -> `quartet`, `electronic` -> `electronic`, and `title == Concertmaster` -> `concertmaster`.
- `doubles` uses the doubles premium structure from the rate book.
- `vacation` is 4% of base service pay plus premiums when `vacation_eligible` is true.
- `guarantee_adjustment` fills the shortfall to `weekly_guarantee` for guaranteed regular players whose base service pay is below the guarantee.
- Treat any substitute-specific adjustment as its own category total and per-musician line item; do not merge it into premium or doubles.
- Omit zero-value category entries inside each musician's `categories` map.

## Conflict flags

- `REHEARSAL_EARLY_START` when any rehearsal starts before `09:00`.
- `REHEARSAL_LATE_END` when any rehearsal ends after `18:30`.
- `SERVICE_OVER_TIME_LIMIT` when a service duration exceeds the rate-book limit for that service type.
- `SOUND_CHECK_DURATION_MISMATCH` when a sound-check duration does not match the labeled service.
- Sort `conflict_flags` alphabetically.

## Output discipline

- Order `per_musician` by `musician_id`.
- Use the highest-total musician for `top_paid_musician_id`; break ties by `musician_id`.
- Keep service labels exact, including `1hr Sound Check` and `2hr Sound Check`.
