# Court Operations Portal — Endpoint Reference

The portal is reached over the network from inside the environment. Use **only** the base URL and the `GET` endpoints listed in the task's `environment_access.md` file. Do not attempt to read server-side files or hit undocumented paths. No credentials are required within the network.

## Base URL

`http://task-env:9018/` (read from `environment_access.md`; the host may differ per environment — always read the file rather than assuming.)

## Endpoints

All endpoints are read-only `GET`. Each returns `{ "count": N, "results": [ ... ] }` unless it is a single search. Filter by appending a query parameter (the portal accepts the field name(s) shown for each endpoint). Where a list is large, narrow with the target identifier rather than paging the whole set.

### `GET /api/jurisdictions`
Court/jurisdiction directory. Fields: `jurisdiction_code`, `state`, `county`, `court_name`, `court_level`, `clerk_office`, `policy_ref`, `phone`, `timezone`, `active`. Use to map a court name in the prompt to a `jurisdiction_code` and to find the associated `policy_ref`.

### `GET /api/cases`
Authoritative criminal case records. Fields: `case_number`, `case_type`, `jurisdiction_code`, `defendant_first`, `defendant_last`, `defendant_dob`, `counsel_type`, `attorney_name`, `attorney_label_raw`, `status`, `disposition_date`, `filed_date`, `judge`, `prosecutor`, `source_system`, `source_updated_at`, `external_party_id`. Filter by `case_number`. This is the **canonical identity and status** source — correct local name/DOB typos and counsel mislabels against it.

### `GET /api/charges`
Per-case charge + sentence detail. Fields: `charge_id`, `case_number`, `count_no`, `offense_code`, `description`, `statute`, `severity`, `plea`, `disposition`, `verdict`, `fine_amount`, `jail_days_imposed`, `jail_days_suspended`, `probation_months`, `license_suspension_months`, `presumptive_min_months`, `presumptive_max_months`, `departure_type`, `departure_reason`, `assessment_code`, `offense_date`. Filter by `case_number`. Use to confirm offense code, plea, disposition, sentence terms, and departure status.

### `GET /api/docket-entries`
Case docket/register entries. Fields: `entry_id`, `case_number`, `entry_type`, `entry_date`, `entered_by`, `source`, `text`. Filter by `case_number`. Use to check whether a sentencing/disposition order actually exists and what the docket text says (controls whether a matter is disposed vs held/continued).

### `GET /api/citations`
Traffic violation records. Fields: `citation_number`, `jurisdiction_code`, `defendant_name`, `defendant_dob`, `statute`, `violation_code`, `violation_desc`, `speed_mph`, `zone_mph`, `event_date`, `hearing_date`, `plea`, `status`, `disposition`, `officer`, `monthly_payment`, `first_due_date`, `plan_approved`. Filter by `citation_number`. Use to confirm the violation code / speed tier and that the plan was approved.

### `GET /api/fee-schedules`
Effective fee/fine schedule rows. Fields: `fee_id`, `jurisdiction_code`, `fee_type`, `amount`, `label`, `mandatory`, `effective_date`, `end_date`, `priority`, `statute`, `violation_code`, `notes`. Filter by `jurisdiction_code` and/or `violation_code`. **This is the source of truth for amounts.** Pick the row whose `effective_date` ≤ relevant disposition date and `end_date` is null (or covers the date). Any amount sourced from a row labeled archived / `OLD` / a prior year is stale and must not be used.

### `GET /api/payment-policies`
Per-jurisdiction payment policy. Fields: `policy_id`, `policy_name`, `jurisdiction_code`, `min_monthly`, `max_monthly`, `account_fee`, `down_payment_required`, `first_due_days`, `return_to_court_offset_days`, `restitution_priority`, `subsequent_petition_rule`, `notes`. Use the min/max band to classify a requested/selected installment, `account_fee` to decide account-fee treatment, `restitution_priority` to decide payment-application order, and `first_due_days` / `return_to_court_offset_days` to derive due and return dates.

### `GET /api/forms`
Form metadata. Fields: `form_id`, `form_name`, `label`, `jurisdiction_code`, `revision_date`, `required_fields`, `placeholder_instruction`, `source_url`. Use to get the correct `form_id`/label for a form-driven section (e.g. CC-1375, CC-1379, extended payment plan) and the prescribed placeholder text/instruction for missing fields.

### `GET /api/financial-petitions`
Financial-counter petition records. Fields: `petition_id`, `case_number`, `jurisdiction_code`, `petitioner_name`, `petition_sequence`, `submitted_date`, `employment_status`, `income_monthly`, `household_size`, `obligations_monthly`, `public_assistance`, `fines_costs_balance`, `restitution_balance`, `license_suspension_months`, `requested_monthly`, `probation_report_datetime`, `default_status`. Filter by `petition_id` or `case_number`. Use to confirm balances, requested amount, and default/sequence status (first vs subsequent vs default-review).

### `GET /api/search`
Free-text fallback lookup. Accepts a `?query=<term>` parameter. Returns `{ "count", "query", "results": [ ... ] }`. Use when a target identifier is not surfaced by the matching list endpoint above, or to disambiguate a matter across endpoints by case/citation/petition/defendant name.

## How to use the portal in the loop

1. Read `environment_access.md` → base URL + which endpoints are allowed for this task (the prompt restates the relevant subset).
2. For each target matter, fetch its record from the matching endpoint (`/cases`, `/citations`, `/financial-petitions`) and, where needed, the supporting `/charges`, `/docket-entries`, `/fee-schedules`, `/payment-policies`, `/forms`.
3. Cross-check each local candidate value against the portal value and resolve per the precedence in `SKILL.md` step 4.
4. If a target is missing from the list endpoint, use `/api/search?query=<identifier>`.

If the portal is unreachable, retry once with a short backoff; if still unreachable, proceed using local materials for undisputed fields and mark any portal-dependent value for verification per the schema's `verify_before_entry` enum rather than inventing it.
