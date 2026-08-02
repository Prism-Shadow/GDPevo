# Court Operations Portal — endpoint reference

Base URL: read `GDPEVO_ENV_BASE_URL` from `environment_access.md` at the repo root
(do not hardcode; it can vary per task). Every endpoint is `GET`, returns
`{"count": N, "results": [ ... ]}`, and supports **exact-match filtering by any
field name in the record** via query string (e.g. `?case_number=...`,
`?jurisdiction_code=...`). The root path `/` is not served (404) — use `/api/...`.
There is no auth. Prefer filtering by the target ID over paging the full list.

Use `scripts/portal.sh <endpoint> [key=value ...]` to query and pretty-print.

## /api/jurisdictions
Court directory. Fields: `jurisdiction_code`, `court_name`, `county`, `state`,
`court_level`, `clerk_office`, `phone`, `timezone`, `policy_ref`, `active`.
Covers multiple states/court types (AR circuit criminal, OR judicial-district
traffic, VA circuit). Use it to confirm the `jurisdiction_code` for the target
county named in the prompt.

## /api/cases  (CMS — authoritative identity)
One row per criminal case. Fields: `case_number`, `jurisdiction_code`,
`case_type`, `defendant_first`, `defendant_last`, `defendant_dob`,
`counsel_type` (`retained` | `public_defender` | `appointed_private`),
`attorney_name`, `attorney_label_raw` (may be noisy, e.g. `APD`, `RET - DOB
missing`), `status`, `disposition_date`, `filed_date`, `judge`, `prosecutor`,
`external_party_id`, `source_system`, `source_updated_at`.
Authoritative for defendant name/DOB and counsel classification. `defendant_dob`
can be `null` — that means the DOB is genuinely unknown, not that you should go
looking for a look-alike.

## /api/charges
Count-level rows. Fields: `case_number`, `charge_id`, `count_no`, `offense_code`,
`description`, `statute`, `severity`, `plea`, `disposition`, `verdict`,
`fine_amount`, `jail_days_imposed`, `jail_days_suspended`, `probation_months`,
`license_suspension_months`, `departure_type`, `departure_reason`,
`presumptive_min_months`, `presumptive_max_months`, `assessment_code`,
`offense_date`. **Caution:** this can be a stale/superseded screen (e.g. an
original count that was later amended or nolle-prosequi'd, or a draft departure).
When it conflicts with the signed hearing outcome, the hearing note controls.

## /api/citations  (traffic)
Fields: `citation_number`, `jurisdiction_code`, `defendant_name`,
`defendant_dob`, `event_date`, `hearing_date`, `officer`, `statute`,
`violation_code` (e.g. `ORS_811_109_100PLUS`), `violation_desc`, `speed_mph`,
`zone_mph`, `plea`, `disposition`, `status`, `plan_approved`, `monthly_payment`,
`first_due_date`. Authoritative for the traffic disposition and the
`violation_code` that keys the fine tier.

## /api/fee-schedules  (current amounts)
Fields: `fee_id`, `jurisdiction_code`, `fee_type` (`court_cost`, `assessment`,
`user_fee`, `standard_fine`, `county_surcharge`, ...), `amount`, `label`,
`violation_code` (for traffic fines), `mandatory`, `priority`, `statute`,
`effective_date`, `end_date`, `notes`.
**Pick the current row**: `end_date == null` and `effective_date <=` disposition
date. Rows with a past `end_date` are retained for audit history only — treat any
worksheet value matching a stale row as a value to correct, not to post. Some fees
are `mandatory: false` and apply only under a condition stated in `notes`
(e.g. public-defender user fee only when counsel is a public defender).

## /api/payment-policies
One row per jurisdiction. Fields: `policy_id`, `policy_name`, `jurisdiction_code`,
`min_monthly`, `max_monthly`, `first_due_days`, `return_to_court_offset_days`,
`account_fee`, `down_payment_required`, `restitution_priority`,
`subsequent_petition_rule`, `notes`. Drives installment band, first-due and
return-to-court date math, whether an account fee applies, and payment
application order.

## /api/forms
Fields: `form_id`, `form_name`, `label`, `jurisdiction_code`, `required_fields`,
`placeholder_instruction`, `revision_date`, `source_url`. Use to select the
correct form and its label/id enum, and to read the placeholder/account-reference
rule for that jurisdiction.

## /api/financial-petitions
Fields: `petition_id`, `case_number`, `jurisdiction_code`, `petitioner_name`,
`petition_sequence` (`first` | `second` | ...), `default_status`
(`current` | `default review` | ...), `submitted_date`, `employment_status`,
`income_monthly`, `obligations_monthly`, `household_size`, `public_assistance`,
`fines_costs_balance`, `restitution_balance`, `requested_monthly`,
`license_suspension_months`, `probation_report_datetime`. Use to confirm balances
and budget and to classify the petition (initial installment vs subsequent/default
review vs deferred).

## /api/search?q=...
Fuzzy lookup across record types; each hit adds `result_type` and `result_id`.
Empty `q` returns nothing. Useful to locate a record, but **look-alike hits are a
trap**: never borrow a DOB or other identity value from a search result for a
different (or DOB-null) party. Verify identity against the exact `/api/cases` or
`/api/citations` record.
