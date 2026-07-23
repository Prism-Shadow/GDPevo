# Portal Endpoint Quick Reference

All endpoints are on the Court Operations Portal. Base URL is provided in the task's `environment_access.md`.

## GET /api/jurisdictions
Returns all active jurisdictions with `jurisdiction_code`, `county`, `state`, `court_name`, `policy_ref`, and `timezone`.

## GET /api/cases
Bulk endpoint returning all cases. Filter by searching for specific `case_number` values via `/api/search`.

Key fields per case:
- `case_number`, `defendant_first`, `defendant_last`, `defendant_dob`
- `counsel_type`, `attorney_name`, `attorney_label_raw`
- `status`, `disposition_date`, `judge`, `jurisdiction_code`
- `source_system`, `source_updated_at`

## GET /api/charges?case_number=<case>
Returns charge records for a specific case.

Key fields per charge:
- `charge_id`, `count_no`, `description`, `offense_code`, `statute`, `severity`
- `plea`, `disposition`, `verdict`
- `fine_amount`, `jail_days_imposed`, `jail_days_suspended`, `probation_months`
- `departure_type`, `departure_reason`
- `assessment_code` (e.g. "DRUG_ASSESSMENT" when drug assessment applies)
- `license_suspension_months`

## GET /api/docket-entries
Returns docket entries. Filter via `/api/search?q=<case>`.

Entry types: `filing`, `hearing`, `disposition`, `financial`, `clerk_note`, `continuance`

## GET /api/fee-schedules
Returns all fee schedule entries. Key fields:
- `fee_id`, `fee_type`, `jurisdiction_code`, `label`, `amount`
- `effective_date`, `end_date` (null = still active)
- `mandatory`, `violation_code`, `statute`, `priority`

**Important**: Always check `end_date`. Entries with an `end_date` before the disposition date are stale/archived and must not be used for current posting.

## GET /api/payment-policies
Returns payment policy per jurisdiction. Key fields:
- `policy_id`, `jurisdiction_code`, `policy_name`
- `min_monthly`, `max_monthly`
- `first_due_days`, `down_payment_required`
- `account_fee`, `restitution_priority`
- `return_to_court_offset_days`
- `subsequent_petition_rule`

## GET /api/forms
Returns form metadata per jurisdiction. Key fields:
- `form_id`, `form_name`, `jurisdiction_code`, `label`
- `placeholder_instruction` (e.g., "Use TBD from case file for unknown identifiers")
- `required_fields`, `revision_date`

## GET /api/citations
Returns traffic citation records. Key fields:
- `citation_number`, `defendant_name`, `defendant_dob`
- `violation_code`, `violation_desc`, `statute`
- `speed_mph`, `zone_mph`
- `plea`, `disposition`, `status`
- `plan_approved`, `monthly_payment`, `first_due_date`
- `jurisdiction_code`, `hearing_date`, `event_date`

## GET /api/financial-petitions
Returns financial petition records. Key fields:
- `petition_id`, `case_number`, `petitioner_name`
- `petition_sequence`, `submitted_date`, `default_status`
- `employment_status`, `income_monthly`, `obligations_monthly`, `household_size`, `public_assistance`
- `fines_costs_balance`, `restitution_balance`
- `requested_monthly`, `license_suspension_months`
- `probation_report_datetime`

## GET /api/search?q=<query>
Search across cases, docket entries, charges, financial petitions, and citations by case number or text.
