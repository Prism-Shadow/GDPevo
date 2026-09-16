# Portal API Reference

All endpoints live under `<TASK_ENV_BASE_URL>`. Every endpoint accepts standard
REST GET query parameters. Most return `{"count": N, "results": [...]}`.

## Summary table

| Endpoint | Primary query param | Use |
|---|---|---|
| `/api/jurisdictions` | none (returns all) | Look up `jurisdiction_code`, `policy_ref` |
| `/api/cases` | `jurisdiction_code`, `case_number` | Case identity, counsel, status |
| `/api/charges` | `case_number` | Count-level charge, plea, disposition, sentence |
| `/api/docket-entries` | `case_number` | Docket timeline, entry types |
| `/api/citations` | `citation_number`, `jurisdiction_code` | Traffic citation detail |
| `/api/fee-schedules` | `jurisdiction_code` | Active and stale fee records |
| `/api/payment-policies` | `jurisdiction_code`, `policy_id` | Payment plan rules |
| `/api/forms` | `jurisdiction_code` | Form metadata, required fields |
| `/api/financial-petitions` | `petition_id`, `case_number` | Petition budgets, balances |
| `/api/search` | `q` (free text) | General lookup |

## `/api/jurisdictions`

Returns all active jurisdictions. Key fields:

- `jurisdiction_code`: the canonical key (e.g. `"AR-RC"`, `"OR22-JEFF"`, `"VA-GLO"`)
- `policy_ref`: points to the payment-policy `policy_id` for that court
- `county`, `court_name`, `state`, `clerk_office`

No query params needed in practice; filter in your own code.

## `/api/cases`

Query by `jurisdiction_code` (returns all cases in that jurisdiction) or by
`case_number` for a single case. Each case record contains:

- `case_number`, `case_type` (always `"criminal"` in these tasks)
- `defendant_first`, `defendant_last`, `defendant_dob`
- `counsel_type` (`"retained"`, `"public_defender"`, or `"appointed_private"`)
- `attorney_name`, `attorney_label_raw`
- `status` (`"disposed"`, `"continued"`, `"deferred"`, `"pending"`)
- `disposition_date`, `filed_date`, `judge`, `prosecutor`
- `jurisdiction_code`, `source_system`, `source_updated_at`

The `attorney_label_raw` field may contain shorthand like `"PD"` or `"APD"`.
Do not rely on it alone; verify against the full hearing record.

## `/api/charges`

Query by `case_number`. Returns one result per count. Key fields:

- `count_no`, `offense_code`, `description`, `statute`, `severity`
- `plea`, `disposition`, `verdict`
- `fine_amount`, `jail_days_imposed`, `jail_days_suspended`
- `probation_months`, `license_suspension_months`
- `departure_type`, `departure_reason`

## `/api/docket-entries`

Query by `case_number`. Returns all docket events for that case, sorted
by `entry_date`. Fields: `entry_date`, `entry_type` (`"filing"`, `"hearing"`,
`"disposition"`, `"financial"`, `"clerk_note"`), `source`, `text`.

## `/api/citations`

Query by `citation_number` or `jurisdiction_code`. Traffic-only. Fields:

- `citation_number`, `defendant_name`, `defendant_dob`
- `statute`, `violation_code`, `violation_desc`
- `speed_mph`, `zone_mph`, `event_date`, `hearing_date`
- `plea`, `disposition` (e.g. `"violation found"`)
- `plan_approved`, `monthly_payment`, `first_due_date`

## `/api/fee-schedules`

Query by `jurisdiction_code`. Returns all fee records (active and archived) for
that jurisdiction. Each record has:

- `fee_id`, `fee_type` (one of `"standard_fine"`, `"court_cost"`, `"assessment"`,
  `"user_fee"`, `"county_surcharge"`, `"account_fee"`, `"miscellaneous"`,
  `"stale_local_fee"`)
- `amount`, `label`, `mandatory` (boolean)
- `effective_date`, `end_date` (null means still active)
- `priority`, `statute`, `violation_code`

To determine if a fee applies to a given case on a given date:
```
fee.effective_date <= disposition_date AND (fee.end_date IS NULL OR fee.end_date > disposition_date)
```

The `mandatory` flag: when true, the fee must be posted if the conviction
triggers it (controlled-substance conviction -> lab assessment; DUI conviction ->
court costs). When false, post only if the disposition order or policy
explicitly includes it.

## `/api/payment-policies`

Query by `jurisdiction_code` or `policy_id`. Returns payment plan rules:

- `policy_id`, `policy_name`, `jurisdiction_code`
- `min_monthly`, `max_monthly` — allowed installment band
- `down_payment_required` — amount or 0
- `first_due_days` — days after disposition date first payment is due
- `return_to_court_offset_days` — days after final payment for return-to-court
- `restitution_priority` — e.g. `"Restitution before fines and costs"` or
  `"Not applicable"`
- `account_fee` — amount, if any
- `subsequent_petition_rule`

## `/api/forms`

Query by `jurisdiction_code`. Returns form metadata:

- `form_id`, `form_name`, `label`, `jurisdiction_code`
- `required_fields` (array), `placeholder_instruction`
- `revision_date`

## `/api/financial-petitions`

Query by `petition_id` or `case_number`. Returns petition intake data:

- `petition_id`, `case_number`, `petitioner_name`
- `petition_sequence` (`"first"`, `"subsequent"`)
- `fines_costs_balance`, `restitution_balance`
- `income_monthly`, `obligations_monthly`, `household_size`
- `requested_monthly`, `employment_status`, `public_assistance`
- `probation_report_datetime`, `license_suspension_months`

## `/api/search`

Free-text search. Use it when you need to find a case by defendant name or other
non-indexed attribute. Returns results with the same shape as the originating
endpoint.
