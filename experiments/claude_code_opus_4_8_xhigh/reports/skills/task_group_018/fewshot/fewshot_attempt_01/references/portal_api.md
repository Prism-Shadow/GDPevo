# Court Operations Portal — API reference

The portal is the **authoritative case-management system (CMS)** and current
rule tables. Read the running environment's `environment_access.md` for the base
URL (`GDPEVO_ENV_BASE_URL`, e.g. `http://task-env:9018/`) and the list of
allowed endpoints. Credentials are `none`. The prompt substitutes the real base
URL for `<TASK_ENV_BASE_URL>`.

Always fetch live — do not hardcode amounts, codes, or bands from this file.
Endpoint availability varies per task; the prompt lists the ones you need.

## Conventions

- Every endpoint returns `{"count": N, "results": [ ... ]}` (search adds
  `"query"`). `financial-petitions`, `cases`, `charges`, `citations`,
  `docket-entries` all use this shape.
- **Exact-match filtering via query params** works on the natural key, e.g.
  `?case_number=RC-25-0412`, `?citation_number=OR26-TR-1188`,
  `?petition_id=VA-PET-716A`, `?jurisdiction_code=AR-RC`. Prefer a filtered
  request per target rather than downloading the whole table.
- `GET /api/search?q=<term>` is a fuzzy lookup over case/party records (matches
  names, returns case rows). Use it to verify a defendant identity by name. It
  does **not** index citation/petition numbers — use the exact filter for those.
  The param is `q` (empty/`query=` returns nothing).
- Curl pattern:
  `curl -s "$BASE/api/cases?case_number=<CASE>" | python3 -m json.tool`

## Endpoints and the fields that matter

### `GET /api/jurisdictions`
`jurisdiction_code`, `county`, `state`, `court_name`, `clerk_office`,
`timezone`, `policy_ref`, `active`. Resolve the target's `jurisdiction_code`
here; it keys the fee schedules, payment policies, and forms.

### `GET /api/cases`  (authoritative identity + disposition posture)
`case_number`, `defendant_first`/`defendant_last`, `defendant_dob`,
`counsel_type` (retained | public_defender | appointed_private),
`attorney_name`, `attorney_label_raw` (raw calendar abbreviation, may be wrong),
`judge`, `prosecutor`, `disposition_date`, `status` (disposed | deferred | ...),
`jurisdiction_code`, `case_type`, `filed_date`, `source_system`.
This row settles corrected name / DOB / counsel classification.

### `GET /api/charges`  (authoritative sentence numbers)
Per count: `count_no`, `offense_code`, `statute`, `severity`, `description`,
`plea`, `disposition`, `verdict`, `fine_amount`, `jail_days_imposed`,
`jail_days_suspended`, `probation_months`, `license_suspension_months`,
`assessment_code` (e.g. a drug/lab assessment trigger), `departure_type` /
`departure_reason`, `presumptive_min_months` / `presumptive_max_months`,
`offense_date`. Use for offense codes, statutes, and the numeric sentence.
Note: a charge row may carry a **stale** `departure_type` or a `disposition`
that the courtroom notes overrode — reconcile (see reconciliation_rules.md).

### `GET /api/citations`  (traffic — authoritative violation record)
`citation_number`, `defendant_name`, `defendant_dob`, `jurisdiction_code`,
`event_date`, `hearing_date`, `speed_mph`, `zone_mph`, `statute`,
`violation_code` (e.g. `ORS_811_109_100PLUS`), `violation_desc`, `plea`,
`disposition`, `status`, `plan_approved`, `monthly_payment`, `first_due_date`.
The `violation_code` keys the standard-fine fee schedule.

### `GET /api/fee-schedules`  (current + archived money rules)
`fee_id`, `jurisdiction_code`, `fee_type` (court_cost | assessment | user_fee |
county_surcharge | standard_fine | miscellaneous | stale_local_fee), `label`,
`amount`, `mandatory`, `priority`, `effective_date`, `end_date`, `statute`,
`violation_code`, `notes`. **Pick the row whose window covers the
disposition/event date**: `effective_date <= date` and
(`end_date` is null or `end_date >= date`). Rows with a past `end_date` or
`fee_type` `stale_local_fee` are archived — never post them. `notes` often
states the condition (e.g. "apply only when counsel is public defender").

### `GET /api/payment-policies`  (installment-plan rules)
`policy_id`, `jurisdiction_code`, `policy_name`, `min_monthly`, `max_monthly`,
`account_fee`, `down_payment_required`, `first_due_days`,
`return_to_court_offset_days`, `restitution_priority`, `subsequent_petition_rule`,
`notes`. Drives band validation, first-due/return-to-court dates, restitution
ordering, and whether an account fee is due (`account_fee` 0 → exclude).

### `GET /api/forms`  (form id / label / placeholder rules)
`form_id`, `jurisdiction_code`, `form_name`, `label`, `required_fields`,
`placeholder_instruction`, `revision_date`, `source_url`. Use for the exact
`form_id`/`form_label` an answer expects and the placeholder wording for
missing identifiers.

### `GET /api/financial-petitions`  (authoritative petition + budget)
`petition_id`, `case_number`, `jurisdiction_code`, `petitioner_name`,
`petition_sequence` (first | subsequent), `default_status` (current | default),
`submitted_date`, `income_monthly`, `obligations_monthly`, `household_size`,
`public_assistance`, `employment_status`, `requested_monthly`,
`fines_costs_balance`, `restitution_balance`, `license_suspension_months`,
`probation_report_datetime`. Authoritative for balances, budget, and sequence.

### `GET /api/docket-entries`
Per entry: `entry_id`, `case_number`, `entry_date`, `entry_type` (filing |
hearing | disposition | financial | clerk_note), `text`, `source`,
`entered_by`. Confirms whether a signed disposition exists vs. a deferred/held
status, and provides entry dates. Some `clerk_note` text is redacted in the
public response — do not treat redaction as data.
