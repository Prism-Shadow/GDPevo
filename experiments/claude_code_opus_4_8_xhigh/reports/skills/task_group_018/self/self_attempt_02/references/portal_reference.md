# Court Operations Portal — endpoint & field reference

Read-only. Base URL and the allowed endpoint list come from
`environment_access.md` (`GDPEVO_ENV_BASE_URL`, no credentials). Which endpoints
are relevant is restated in each task's `prompt.txt`; only call allowed ones.

- All endpoints are `GET` and return `{"count": N, "results": [ ... ]}`.
- Filter with query params, e.g. `?case_number=<id>`,
  `?jurisdiction_code=<code>`, `?citation_number=<id>`, `?petition_id=<id>`.
- `GET /api/search?q=<identifier>` returns mixed rows; each carries
  `result_type` (`cases`, `charges`, `docket_entries`, …) and `result_id`. Good
  for locating a record when you only have an id.
- The portal deliberately contains **noise**: stale/ended fee rows, "Copy or
  certification" and "Archived local fee" rows, other jurisdictions' data, and
  charge-screen values that may be superseded by the signed courtroom record.
  Filter and verify — do not grab the first match.

## /api/jurisdictions
`jurisdiction_code`, `court_name`, `county`, `state`, `court_level`,
`clerk_office`, `phone`, `timezone`, `policy_ref`, `active`.

## /api/cases  — authoritative for identity, counsel, status
`case_number`, `jurisdiction_code`, `case_type`, `defendant_first`,
`defendant_last`, `defendant_dob`, `counsel_type`
(`retained` | `public_defender` | `appointed_private` | `unknown`),
`attorney_name`, `attorney_label_raw` (raw/abbreviated label — distrust it),
`status` (`disposed` | `deferred` | `pending` | `continued` | `closed`),
`disposition_date`, `filed_date`, `judge`, `prosecutor`, `external_party_id`,
`source_system` (e.g. `AOC-CMS`, `Legacy-CMS`), `source_updated_at`.

## /api/charges  — verify against the signed record before trusting
`case_number`, `charge_id`, `count_no`, `offense_code`, `description`,
`statute`, `severity`, `plea`, `disposition`
(`guilty` | `nolle prosequi` | `deferred` | `pending` | `dismissed`),
`fine_amount`, `jail_days_imposed`, `jail_days_suspended`, `probation_months`,
`license_suspension_months`, `presumptive_min_months`, `presumptive_max_months`,
`departure_type` (`durational` | `dispositional` | `none`), `departure_reason`,
`assessment_code` (e.g. `DRUG_ASSESSMENT` or null), `verdict`, `offense_date`.
NOTE: `disposition` and `departure_*` here can be stale/draft. If the hearing
notes (corroborated by the audit memo) say otherwise — e.g. "top of range, not a
departure", or guilt adjudicated where the screen says `nolle prosequi` — the
signed courtroom record controls.

## /api/docket-entries
`case_number`, `entry_id`, `entry_date`, `entry_type`
(`filing` | `hearing` | `disposition` | `financial` | `clerk_note`),
`text`, `entered_by`, `source`. The `disposition` entry's text records the
official status (watch for "status deferred"). `clerk_note` text may be redacted.

## /api/citations  — traffic
`citation_number`, `jurisdiction_code`, `defendant_name`, `defendant_dob`,
`officer`, `event_date`, `hearing_date`, `plea`, `disposition`, `status`,
`statute`, `violation_code` (`ORS_811_109_100PLUS` | `ORS_811_109_31_40` |
`ORS_811_109_21_30` | …), `speed_mph`, `zone_mph`, `plan_approved`,
`monthly_payment`, `first_due_date`.

## /api/fee-schedules  — pick the row effective on the disposition date
`fee_id`, `jurisdiction_code`, `fee_type` (`court_cost` | `assessment` |
`user_fee` | `standard_fine` | `county_surcharge` | `account_fee` |
`miscellaneous` | `stale_local_fee`), `violation_code` (traffic fines only),
`label`, `amount`, `effective_date`, `end_date` (null = still current),
`mandatory`, `priority`, `statute`, `notes`.
Selection: same jurisdiction + fee_type (+ violation_code) + effective window
contains disposition date + not a NOISE/`stale_local_fee`/`miscellaneous`
copy-fee row.

## /api/payment-policies  — plan bands & timing
`policy_id`, `jurisdiction_code`, `policy_name`, `min_monthly`, `max_monthly`,
`account_fee` (0 on most; >0 means the jurisdiction may charge it),
`down_payment_required`, `first_due_days`, `return_to_court_offset_days`,
`restitution_priority` (text — "Restitution before fines and costs" vs "Not
applicable"), `subsequent_petition_rule`, `notes` (may state the first-due
convention, e.g. "usually the 15th of the next month").

## /api/forms
`form_id`, `form_name`, `jurisdiction_code`, `label`, `required_fields`,
`placeholder_instruction` (the exact placeholder handling to follow),
`revision_date`, `source_url`.

## /api/financial-petitions
`petition_id`, `case_number`, `jurisdiction_code`, `petitioner_name`,
`petition_sequence` (`first` | `second` | …), `default_status`
(`current` | `default review`), `submitted_date`, `employment_status`,
`income_monthly`, `obligations_monthly`, `household_size`, `public_assistance`,
`fines_costs_balance`, `restitution_balance`, `requested_monthly`,
`license_suspension_months`, `probation_report_datetime`.
When a task also supplies a local petition/budget payload, treat the portal
record as the reference to reconcile the local counter figures against.
