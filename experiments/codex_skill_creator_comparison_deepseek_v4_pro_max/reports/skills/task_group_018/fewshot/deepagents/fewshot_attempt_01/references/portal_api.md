# Court Operations Portal API Reference

The portal is a REST API. Base URL is supplied by the task (typically
`<TASK_ENV_BASE_URL>`). No authentication is required. All endpoints return JSON.

## Endpoints

### GET /api/jurisdictions

Returns an array of jurisdiction records. Each record includes:

| Field | Type | Meaning |
|-------|------|---------|
| `jurisdiction_code` | string | Short code (e.g., `AR-RC`, `OR22-JEFF`, `VA-GLO`) |
| `state` | string | Two-letter state |
| `county` | string | County name |
| `court_name` | string | Full court name |
| `court_level` | string | `Circuit` or district |
| `clerk_office` | string | Office name |
| `active` | boolean | Whether jurisdiction is active |
| `policy_ref` | string | Reference to payment/sentencing policy |
| `phone` | string | Clerk phone |
| `timezone` | string | IANA timezone |

Use this to confirm the target jurisdiction exists and to retrieve its
`policy_ref` and `jurisdiction_code` for use throughout the closeout.

### GET /api/fee-schedules

Returns an array of fee records. Each record includes:

| Field | Type | Meaning |
|-------|------|---------|
| `fee_id` | string | Unique fee identifier |
| `jurisdiction_code` | string | Which jurisdiction this fee applies to |
| `fee_type` | string | `court_cost`, `standard_fine`, `assessment`, `user_fee`, `county_surcharge`, `account_fee`, `miscellaneous`, `stale_local_fee` |
| `violation_code` | string or null | Violation code this fee applies to (e.g., `ORS_811_109_100PLUS`) |
| `label` | string | Human-readable label |
| `amount` | number | Dollar amount |
| `effective_date` | ISO date | When this fee became current |
| `end_date` | ISO date or null | When this fee expired (null = still current) |
| `mandatory` | boolean | Whether the fee is mandatory for qualifying cases |
| `statute` | string or null | Statutory citation |
| `priority` | integer | Ordering priority |
| `notes` | string | Clerk notes |

**How to filter for current fees:** A fee is current when `effective_date` ≤
the disposition/event date AND (`end_date` is null OR `end_date` ≥ the
disposition/event date). Discard fees from other jurisdictions (match on
`jurisdiction_code`).

### GET /api/payment-policies

Returns an array of payment policy records. Filter by `jurisdiction_code`.

| Field | Type | Meaning |
|-------|------|---------|
| `policy_id` | string | Unique policy identifier |
| `jurisdiction_code` | string | Target jurisdiction |
| `policy_name` | string | Policy name |
| `min_monthly` | number | Minimum monthly payment |
| `max_monthly` | number | Maximum monthly payment |
| `down_payment_required` | number | Required down payment (usually 0) |
| `first_due_days` | integer | Days after petition/submission date the first payment is due |
| `return_to_court_offset_days` | integer | Days after final due date to set return-to-court |
| `account_fee` | number | Account management fee (0 means not applied) |
| `restitution_priority` | string | Order for applying payments |
| `subsequent_petition_rule` | string | Rule for later petitions |
| `notes` | string | Policy notes |

### GET /api/forms

Returns an array of form metadata records. Filter by `jurisdiction_code`.

| Field | Type | Meaning |
|-------|------|---------|
| `form_id` | string | Form identifier (e.g., `VA_CC1375`) |
| `jurisdiction_code` | string | Target jurisdiction |
| `label` | string | Form display label |
| `form_name` | string | Full form name |
| `required_fields` | array of strings | Fields the form requires |
| `placeholder_instruction` | string | How to handle missing values |
| `revision_date` | ISO date | Form revision date |
| `source_url` | string | Internal form URL |

### GET /api/cases

Query with `?case_number=<case-number>` (e.g., `?case_number=CR-25-0100`). Returns case records including
defendant identity, status, counsel, and charge summaries.

### GET /api/charges

Query with `?case_number=...`. Returns charge records including statute, plea,
disposition, and departure flags.

### GET /api/citations

Query with `?citation_number=<citation-number>` (e.g., `?citation_number=XX00-TR-0100`). Returns traffic citation
records including defendant, violation code, officer, and status.

### GET /api/docket-entries

Query with `?case_number=...`. Returns docket entry records including entry
type, date, and text.

### GET /api/financial-petitions

Query with `?petition_id=<petition-id>` or `?case_number=...`. Returns petition
records including balances, requested amounts, and budget information.

### GET /api/search

Query with `?q=<search term>`. Returns matching records across all types.
Use for defendant name lookups when a case number is not already known.

## Query Conventions

- Add `?case_number=...`, `?citation_number=...`, or `?petition_id=...` as
  query parameters to filter results.
- `jurisdiction_code` and `?q=` are passed as query parameters where the
  endpoint supports them.
- The portal may return noise/filler records for jurisdictions not relevant to
  the task. Filter by the target `jurisdiction_code`.
- Fee schedules and payment policies return records for all jurisdictions; you
  must filter to the target.
