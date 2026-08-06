# Enum Values and Formatting Rules

## General formatting

- **Dates**: ISO 8601 `YYYY-MM-DD`. Use `null` where no date should be entered.
- **Datetimes**: ISO 8601 local `YYYY-MM-DDTHH:MM:SS`.
- **Currency**: Numbers with two decimal places, e.g., `150.00` not `150` or `150.0`.
- **Sorting**: Per the answer template's ordering_rules. Default is by case_number or petition_id ascending.

## Common enum values across task schemas

### Issue / audit types
- identity, counsel, status, fee_schedule, departure

### Resolution sources
- use_cms, use_hearing_notes, use_corrob_memo, use_fee_schedule, hold_unsigned_order

### Counsel types
- public_defender, appointed_private, retained, unknown

### Case statuses
- disposed, deferred, pending, continued

### Closeout / entry actions
- enter_disposition, hold_unsigned_order, no_closeout
- disposed_enter, pending_exclude
- enter_disposition_and_financials, exclude_no_final_order

### Plea values
- guilty, no_contest, not_guilty, none, not_entered, not_applicable

### Charge dispositions
- guilty, nolle_prosequi, deferred, pending, dismissed

### Departure statuses
- no_departure, durational_departure, dispositional_departure, not_applicable
- none (used in some schemas), not_evaluated_misdemeanor, not_entered_pending

### Fee codes
- fine, court_cost, drug_assessment, public_defender_user_fee, crime_lab_fee

### Fee statuses
- post, exclude, hold, do_not_post_pending

### Placeholder
- `"TBD from case file"` — the standard placeholder for missing identifiers

### Exclusion reason codes
- no_order_or_policy_support, not_current_policy, no_triggering_event, stale_schedule
- not_in_hearing_order, unsupported_post_disposition, not_part_of_balance
- continued_pending_no_final_order

### Payment plan enums
- agreement_type: initial_installment, extended_payment_plan, deferred_payment, subsequent_review
- plan_status: approved, not_approved, not_applicable
- schedule_interval: monthly, biweekly, weekly, deferred_single_due
- support_classification: supportable, below_policy_minimum, above_policy_maximum, unsupported_by_budget
- account_fee_treatment: excluded_by_policy, included_by_policy, verify_before_entry

### Form / license enums
- cc1375_status: prepare_referral, not_ordered
- license_start_basis: conviction_date, release_date, petition_date
- license_suspension status: suspended, not_suspended
- license_suspension basis: dui_conviction, other

## Important reminders

- Never replace enum values with prose descriptions. Use the exact enum string from the schema.
- If the answer template defines allowed enum values, use ONLY those values.
- When a field has no applicable value and the schema allows null, use null (not "N/A" or blank string).
