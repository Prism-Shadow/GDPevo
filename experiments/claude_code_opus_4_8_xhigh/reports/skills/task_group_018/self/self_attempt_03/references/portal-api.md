# Court Operations Portal — API notes

The portal is the authoritative source of record. `environment_access.md` gives the base
URL (a variable the prompt writes as `<TASK_ENV_BASE_URL>`) and the list of allowed
endpoints. **No credentials; GET only.** Each task's `prompt.txt` lists the subset of
endpoints relevant to that deliverable — the full catalog is in `environment_access.md`.

## Endpoints (full catalog)

```
GET /api/jurisdictions        court name/county/state -> jurisdiction_code, policy_ref, timezone
GET /api/cases                criminal/other case records (identity, counsel, disposition)
GET /api/charges              per-count charge records (offense, plea, sentence, departure, fees)
GET /api/docket-entries       docket/register text lines per case
GET /api/citations            traffic citation records (violation_code, plea, finding, plan)
GET /api/fee-schedules        fee rows with effective/end dates, amounts, mandatory flags
GET /api/payment-policies     per-jurisdiction installment policy (bands, offsets, priorities)
GET /api/forms                form metadata (form_id, label, required_fields, revision)
GET /api/financial-petitions  petition intake (income, obligations, balances, requested plan)
GET /api/search               cross-type lookup by free-text query
```

## Response shape & querying

- Every list endpoint returns `{"count": N, "results": [ ... ]}`.
- **Filter by exact field** via query params, e.g. `?case_number=RC-25-0412`,
  `?jurisdiction_code=AR-RC`, `?citation_number=...`, `?petition_id=...`. Filtering
  returns only matching rows.
- **Pagination:** `?limit=` and `?offset=` are supported. A bare listing is capped
  (commonly 100 rows), so filter narrowly rather than scanning the whole table.
- **Search:** `GET /api/search?q=TERM` returns cross-type hits, each tagged with a
  `result_type` (e.g., `cases`) and a `result_id`. Use it to locate a record when you do
  not yet know the endpoint or jurisdiction, then re-fetch the typed endpoint for the
  full row.
- URL-join carefully: the base URL may end in `/` and endpoints begin with `/api/` —
  avoid a doubled slash.

## Selecting the right row

- **Jurisdiction:** map the court/county named in the prompt to a `jurisdiction_code`
  via `/api/jurisdictions` (also yields `policy_ref` and `timezone`).
- **Fee schedules:** rows carry `effective_date`, `end_date` (null = still active),
  `amount`, `fee_type`, `mandatory`, `priority`, `violation_code`. Choose the row whose
  window **contains the disposition date** (`effective_date ≤ disposition_date` and
  (`end_date` is null or `≥ disposition_date`)). Discard rows whose window has ended —
  those are retained only for audit history and are the "stale" amounts drafts carry.
- **Payment policies:** rows carry `min_monthly`, `max_monthly`, `first_due_days`,
  `down_payment_required`, `account_fee`, `restitution_priority`,
  `return_to_court_offset_days`, `subsequent_petition_rule`, and a `notes` field
  (e.g., "apply only fees effective on the disposition date"). These drive the
  installment band, first-due date, account-fee treatment, restitution ordering, and
  return-to-court date.
- **Forms:** rows carry `form_id`, `label`, `required_fields`, `revision_date`, and a
  `placeholder_instruction`. Prefer the portal's current form/label over an older local
  excerpt, but reproduce visible field labels exactly as the excerpt shows them when the
  template asks for `required_labels_used`.
- **Cases/charges/citations/petitions:** authoritative for identity (`counsel_type`,
  `defendant_dob`, name), disposition, per-count charge data, and petition financials.
  Note that a raw label field (e.g., `attorney_label_raw`) may be a mislabeled
  abbreviation — trust the resolved `counsel_type` and any on-record clarification.

## Practical tips

- Fetch each target matter with an exact-field filter; confirm identity and disposition
  before trusting any local number.
- When a local extract and the portal disagree, the portal (plus the signed courtroom
  result) wins — and that disagreement is usually itself an answer (an audit finding).
- Do not embed portal values you happened to see for one matter into reusable logic;
  always re-query for the matter at hand.
