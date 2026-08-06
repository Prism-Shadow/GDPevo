# SLA Policy Reference

## Days-to-Due by Severity

| Severity | Days to Due |
|----------|-------------|
| S1       | 3           |
| S2       | 10          |
| S3       | 21          |
| S4       | 45          |

Source: `GET /api/sla-policy`

## SLA Deadline Calculation

SLA deadline = `created_at` + `days_to_due[severity]`

An item is **overdue** if:
- It is still open on the as-of date (closed_at is null or > as_of), AND
- The SLA deadline is before the as-of date

A recently-closed item may also be counted as overdue if:
- It was closed within the recent-closed window, AND
- It was closed AFTER its SLA deadline

## Aging Buckets

Days past SLA deadline:
- 0–3 days
- 4–7 days
- 8–14 days
- 15–30 days
- 31+ days

## Snapshot Rules

- As-of date determines what "open" means.
- Items created AFTER the as-of date must be excluded from the SLA population.
- Recently-closed window: items closed within N days before the as-of date are included.
