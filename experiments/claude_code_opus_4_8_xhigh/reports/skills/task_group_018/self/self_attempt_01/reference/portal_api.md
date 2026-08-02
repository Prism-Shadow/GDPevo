# Court Operations Portal — API reference

Read-only HTTP JSON API. Base URL is in `environment_access.md` as
`GDPEVO_ENV_BASE_URL` (e.g. `http://task-env:9018/`); substitute it wherever a prompt
writes `<TASK_ENV_BASE_URL>`. **No credentials.** Only `GET` is used. A prompt usually
lists a subset of endpoints — query only what is relevant to that task, but the full
catalog is below.

## Endpoints

| Endpoint | What it holds | Key fields |
|---|---|---|
| `/api/jurisdictions` | Courts and their config | `jurisdiction_code`, `court_name`, `county`, `state`, `timezone`, `policy_ref`, `active` |
| `/api/cases` | CMS case/defendant/counsel record (system of record for identity + counsel) | `case_number`, `defendant_first/last`, `defendant_dob`, `counsel_type`, `attorney_label_raw`, `attorney_name`, `status`, `disposition_date`, `jurisdiction_code`, `judge`, `source_system` |
| `/api/charges` | Per-count charge/sentence record | `case_number`, `count_no`, `offense_code`, `statute`, `description`, `plea`, `disposition`, `verdict`, `fine_amount`, `jail_days_imposed/suspended`, `probation_months`, `license_suspension_months`, `departure_type`, `departure_reason`, `assessment_code`, `presumptive_min/max_months` |
| `/api/docket-entries` | Docket/minute lines | `case_number`, `entry_id`, `entry_date`, `entry_type` (filing/hearing/disposition/financial/clerk_note), `source`, `text` |
| `/api/citations` | Traffic citation record | `citation_number`, `defendant_name`, `defendant_dob`, `event_date`, `hearing_date`, `statute`, `violation_code`, `violation_desc`, `speed_mph`, `zone_mph`, `plea`, `disposition`, `status`, `plan_approved`, `monthly_payment`, `first_due_date`, `jurisdiction_code` |
| `/api/fee-schedules` | Fee/assessment amounts, time-bounded | `fee_id`, `jurisdiction_code`, `fee_type` (court_cost/assessment/user_fee/fine), `label`, `amount`, `effective_date`, `end_date`, `mandatory`, `priority`, `violation_code`, `notes` |
| `/api/payment-policies` | Installment/plan policy per jurisdiction | `policy_id`, `jurisdiction_code`, `min_monthly`, `max_monthly`, `account_fee`, `down_payment_required`, `first_due_days`, `restitution_priority`, `return_to_court_offset_days`, `subsequent_petition_rule`, `notes` |
| `/api/forms` | Current form metadata per jurisdiction | `form_id`, `jurisdiction_code`, `form_name`, `label`, `required_fields`, `placeholder_instruction`, `revision_date`, `source_url` |
| `/api/financial-petitions` | Petition/budget record | `petition_id`, `case_number`, `petition_sequence`, `default_status`, `petitioner_name`, `income_monthly`, `obligations_monthly`, `household_size`, `public_assistance`, `employment_status`, `fines_costs_balance`, `restitution_balance`, `license_suspension_months`, `requested_monthly`, `probation_report_datetime`, `submitted_date`, `jurisdiction_code` |
| `/api/search` | Cross-entity keyword search | envelope `{count, query, results[]}`; each result carries `result_type` (cases / charges / docket_entries / …) and `result_id` |

All list endpoints return `{"count": N, "results": [...]}`.

## Query patterns

- **Discover everything tied to an ID**: `GET /api/search?q=<case_or_citation_or_petition_id>`.
  Returns mixed entity types; branch on each result's `result_type`. A partial term
  (e.g. a case-number prefix) returns all matches — useful for enumerating a batch.
- **Exact record lookup**: filter the entity endpoint by an identifying field —
  `GET /api/cases?case_number=<id>`, `GET /api/citations?citation_number=<id>`,
  `GET /api/charges?case_number=<id>`, `GET /api/financial-petitions?petition_id=<id>`,
  `GET /api/fee-schedules?jurisdiction_code=<code>`,
  `GET /api/payment-policies?jurisdiction_code=<code>`,
  `GET /api/forms?jurisdiction_code=<code>`.

## Gotchas

- **Unknown query params are ignored** — the endpoint returns the full unfiltered set
  (often capped at 100). Always check `count`/`results` to confirm your filter actually
  applied; do not assume the first result is your target.
- **`clerk_note` docket text may be redacted** ("Clerk note text redacted from public
  portal response."). Rely on the local hearing notes for the substance of what happened
  in the courtroom.
- The dataset spans many jurisdictions and years. Always constrain by
  `jurisdiction_code` (and by date, for fee schedules) so you don't pick a look-alike
  record from another county or an archived period.
- Map a jurisdiction name in the prompt to its `jurisdiction_code` via
  `/api/jurisdictions` when it isn't obvious from the IDs.
