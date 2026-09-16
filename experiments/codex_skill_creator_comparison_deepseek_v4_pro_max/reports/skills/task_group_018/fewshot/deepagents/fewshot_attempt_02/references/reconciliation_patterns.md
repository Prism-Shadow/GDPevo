# Reconciliation Patterns

This reference covers the detailed reconciliation rules for court clerk closeout,
field-packet, and register tasks. Apply these rules after querying the portal and
reading all local payloads.

## Identity Reconciliation

When the local materials and portal disagree on defendant identity:

- If a corroborating memo (e.g., clerk audit memo) or defense-table correction
  in the hearing notes gives a specific name and DOB correction, use that.
  Example: queue says "John Doe DOB 1980-01-01" but defense cover memo says
  "Jon Doe DOB 1980-01-02" → use the corroborating memo values.
- If no local correction exists, use the portal CMS record.
- If the DOB is genuinely blank in all sources (portal, hearing notes, worksheets),
  use "TBD from case file" and set identity_action to use_placeholder_verify.
- Never borrow a DOB from a similarly-named defendant in search results.

## Counsel Reconciliation

Classify counsel into one of: retained, public_defender, appointed_private, unknown.

- "PD" or "PD J. Smith"-style labels are tentative. If a corroborating memo states
  the attorney is appointed private counsel paid by the county, reclassify as
  appointed_private. The public defender user fee is only eligible when counsel
  is actually classified as public_defender.
- "APD" abbreviations on calendars or worksheets are not definitive. Check whether
  a judge statement or defense memo confirms appointed private counsel. If so,
  classify as appointed_private and flag with apd_label_not_public_defender.
- "RET" or "retained" labels mean retained counsel. No public defender user fee applies.
- When counsel is appointed_private but a worksheet or queue still carries a PD
  user fee, exclude that fee from the financial entry.

## Fee Schedule Reconciliation

- Always use the current portal fee schedule for fee code amounts. When a local
  worksheet carries an older amount (e.g., drug assessment 125 from an archived
  schedule), replace it with the current portal amount.
- Fees to include only when supported by the current schedule or court order:
  fine, court_cost, drug_assessment, public_defender_user_fee, crime_lab_fee.
- Fees to exclude (set to 0.00) unless the portal payment policy or a specific
  signed order directly supports them: account_management_fee, collection_fee,
  dmv_fee, dmv_reinstatement_fee, late_fee, late_payment_fee, returned_check_fee,
  traffic_school_fee, court_appointed_attorney_fee, court_reporter_fee, restitution
  (when no restitution order exists).
- When excluding fees, record them in the excluded_charges or excluded_financial_items
  array with the appropriate reason_code.
- Fee reconciliation items should sort by case_number ascending.

## Departure Reconciliation

- When a legacy worksheet or queue shows a departure label but the hearing notes
  confirm the judge said no departure, use no_departure. The hearing notes control.
- departure_status values: no_departure, durational_departure, dispositional_departure,
  not_applicable, none, not_evaluated_misdemeanor, not_entered_pending.
- For misdemeanor-only cases where departure is not typically evaluated, use
  not_evaluated_misdemeanor.
- For pending cases with no final order, use not_entered_pending.

## Status and Closeout Decisions

- When a signed sentencing order was handed to the clerk on the hearing date,
  the case is disposed. Set case_status to disposed and closeout_action to
  enter_disposition. Post financial entries.
- When the hearing notes state no final order was signed (e.g., "judge did not
  sign the order," "matter continued for status," "no sentencing order was entered
  in open court"), the case is not disposed. Set status to deferred/pending,
  closeout_action to hold_unsigned_order or no_closeout, and do not post financial
  entries. Use a disposition_hold or CONTINUED_NO_DISPOSITION docket entry with
  financial_total 0.00.
- For exclusion records, set financial_posting_allowed to false and provide a
  next_status_check_date from the hearing notes.

## Payment Plan Construction

When the answer template requires a payment plan or installment order:

1. Query the portal payment policy for the jurisdiction. Extract minimum_monthly
   and maximum_monthly bands.
2. Compute monthly_disposable_income = monthly_income - monthly_obligations.
3. The approved_monthly_amount is either the petitioner's requested amount or
   an amount derived from the budget, constrained by the policy band. If the
   requested amount falls within the band and is <= disposable income, approve it.
4. Compute installments:
   - total_due = fines_and_costs_balance + restitution_balance (account_fee is 0
     unless the portal policy explicitly includes it).
   - full_installment_count = floor(total_due / monthly_amount)
   - final_payment_amount = total_due - (full_installment_count * monthly_amount)
   - total_installments = full_installment_count + (1 if final_payment_amount > 0 else 0)
   - final_due_date = first_due_date + (total_installments - 1) months
5. down_payment is 0 unless the petition requests one and it is approved.
6. return_to_court_date should be 2 months after the final_due_date unless the
   task materials provide a specific return date.
7. Classify the petition: initial_installment (first petition after disposition),
   subsequent_review (later modification), deferred_payment, or exempt_no_payment.
8. Support classification: supported_by_budget if monthly_amount <= disposable_income
   and within policy band; unsupported_by_budget if monthly_amount > disposable_income;
   below_policy_minimum or above_policy_maximum if outside the band.

## Placeholder Handling

For fields that are required by forms but missing from all available materials:

- Use exactly "TBD from case file" for: SSN, driver_license_number,
  residence_address, mailing_address, phone_number, probation_officer,
  probation_office_location, and any party or attorney contact details.
- Never invent identifiers, addresses, phone numbers, or contact names.
- Sort placeholder_fields by field name ascending. Sort missing_fields alphabetically.
- Record each placeholder with the appropriate reason_code: missing_identifier,
  missing_contact, missing_office_detail, or missing_party_detail.

## Enum Value Selection

Always use enum values exactly as defined in the answer template. Common patterns
across templates:

- Plea: guilty, no_contest, not_guilty, no_plea_recorded, not_entered, not_applicable.
  Use not_applicable for bench trials where no plea was entered.
- Finding/disposition: violation_found, guilty, dismissed, continued, nolle_prosequi,
  pending, deferred.
- Fine tier for traffic: speed_100_or_greater (100+ mph over limit),
  speed_31_to_40_over (31-40 mph over), speed_21_to_30_over (21-30 mph over).
- Fee schedule sources: use the form_id-style identifier from the portal (e.g.,
  F-OR22-100-2024 for the current 100+ mph schedule).
- Agreement sequence: post_disposition (plan approved after disposition entry),
  pre_disposition, same_entry_unknown, no_agreement.

## Batch Totals

Compute register/batch totals from the individual case entries:
- Sum financial totals only for cases with fee_status post / entry_status disposed_enter.
- Excluded/held cases contribute 0.00 to all financial totals.
- assessed_case_count / disposed_case_count counts only posted cases.
- held_case_count / excluded_pending_count counts only held/excluded cases.

## Sorting Rules

Follow the ordering_rules in the answer template exactly. Common rules:
- audit_findings: sort by case_number, then issue_type.
- case_dispositions / dispositions: sort by case_number.
- fee_reconciliation / fee_entries: sort by case_number.
- docket_entries / docket_register entries: sort by case_number.
- exclusions: sort by case_number.
- excluded_charges: sort by charge_code.
- matters: sort by citation_number.
- petitions: sort by petition_id.
- probation_referrals / license_orders: sort by case_number.
- placeholder_fields: sort by field name.
- placeholder_cases: sort by case_number; missing_fields sorted alphabetically.
