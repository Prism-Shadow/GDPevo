# Payroll Reporting

## Inputs

- `/api/manifest`
- `/api/payroll/rate-book`
- `/api/payroll/productions`

## Rate book facts

- Use the service rates for `Performance`, `Audit`, `1hr Sound Check`, `2hr Sound Check`, and `Rehearsal`.
- Rehearsal pay is hourly with a 3-hour minimum call.
- Premium percentages come from the payroll rate book and are applied to the musician's base service pay.
- Doubles use the first-double and additional-double percentages from the rate book.
- Vacation is 4% of base service pay plus premiums and doubles when `vacation_eligible` is true.
- Weekly guarantee is the rate-book guarantee threshold.

## Service rollup

- `service_counts` = schedule rows counted by `service_type`.
- Build musician totals from the roster rows and their assigned service IDs.
- Keep `per_musician` ordered by `musician_id`.
- Include only nonzero categories in each musician's `categories` object.
- Keep `conflict_flags` sorted alphabetically.

## Conflict checks

- `REHEARSAL_EARLY_START` if any rehearsal starts before `09:00`.
- `REHEARSAL_LATE_END` if any rehearsal ends after `18:30`.
- `SERVICE_OVER_TIME_LIMIT` if any service duration exceeds the rate-book limit for that service type.
- `SOUND_CHECK_DURATION_MISMATCH` if a sound-check duration does not match its labeled `1hr` or `2hr` class.

## Adjustment lines

- Compute guarantee top-ups as separate adjustment lines when the template asks for them.
- Keep substitute-specific top-ups separate from the general guarantee adjustment when the production data calls for it.
