# Court Operations Portal Reference

This guide covers detailed patterns for reconciling court records across the common task types observed in docket closeout workflows.

## Contents

1. Portal Endpoint Usage
2. Fee Handling by Case Type
3. Payment Plan Edge Cases
4. Form-Specific Patterns
5. Conflict Classification Detail
6. Validation Checklist

---

## 1. Portal Endpoint Usage

### GET /api/cases

Returns case records with defendant identity, case status, disposition information, and associated charge/citation links. Query by case number parameter.

Key fields to extract: defendant name, DOB, case status, disposition data, associated charge IDs.

### GET /api/charges

Returns charge records for a case, including the offense code, statute, plea, disposition, and lab-eligibility flags.

Important: the `offense_code` value from the portal is the canonical code. Use it unless the hearing notes document an amended charge that the portal does not yet reflect. Do not abbreviate or shorten the portal's offense code.

### GET /api/citations

Returns traffic or ordinance citation records. Use for traffic-violation closeout tasks. Contains violation code, speed alleged (if applicable), fine tier, and disposition fields.

### GET /api/fee-schedules

Returns the current fee schedule for the jurisdiction. This is the authoritative source for all fee amounts.

A fee schedule typically has a `schedule_id` and `effective_date`. Always use the current, in-effect schedule. If the schedule carries multiple tiers (e.g., speed brackets for traffic fines), select the tier matching the violation.

### GET /api/docket-entries

Returns existing docket entries for a case. Check this before creating new entries to avoid duplicates, and to verify whether a sentencing order has already been entered.

### GET /api/payment-policies

Returns the jurisdiction's payment policy: which fees are allowed, payment application order (restitution before fines/costs vs. fines/costs first), minimum monthly payment thresholds, and account-fee rules.

### GET /api/forms

Returns form metadata including form IDs, required fields, and field groups. Use when the task involves probation referrals (CC-1375 style), license suspension orders (CC-1379 style), or installment agreements.

### GET /api/financial-petitions

Returns existing financial petitions for a case. Check for prior petitions, defaults, or subsequent reviews before classifying a new petition.

### GET /api/search

Multi-domain search endpoint. Useful for finding cases by defendant name, citation number, or partial identifiers when the case number alone is ambiguous.

### GET /api/jurisdictions

Returns jurisdiction metadata (code, name, court type). Use to confirm the jurisdiction code for the output.

---

## 2. Fee Handling by Case Type

### Criminal disposition docket

Standard fees for a criminal sentencing closeout:

| Fee code | When to post | Amount source |
|---|---|---|
| fine | Judge imposed a fine in open court | Hearing notes amount |
| court_cost | Every disposed criminal case (unless waived by judge) | Portal fee schedule |
| drug_assessment / crime_lab_fee | Controlled-substance or lab-eligible conviction | Portal fee schedule |
| public_defender_user_fee | Counsel confirmed as public defender | Portal fee schedule |
| restitution | Restitution order exists in record | Order amount |

Do not post: account-management fees, collection fees, late fees, DMV reinstatement fees, copy fees, certification fees, court-reporter fees, court-appointed-attorney fees -- unless the portal payment policy or fee schedule explicitly authorizes them.

### Traffic citation closeout

Standard fees for a traffic violation closeout:

| Fee code | When to post | Amount source |
|---|---|---|
| standard_fine / presumptive_fine | Every disposed citation | Portal fee schedule, matched to violation tier |
| county_surcharge / surcharge | Every disposed citation | Portal fee schedule |

Amount due is standard_fine + county_surcharge (or the template's equivalent).

Unsupported charges (stale, not in the current schedule, or excluded by policy) go into `excluded_charges` or `unsupported_charge_total_included` as zero. The starting balance must not include them.

### Payment petition closeout

For cases with financial petitions:

| Element | Rule |
|---|---|
| fines_and_costs_balance | From the portal or clerk-stated amounts, not the petitioner's recollection |
| restitution_balance | From the portal or sentencing order; zero if no restitution order |
| account_fee_amount | Zero unless portal policy explicitly includes account fees |
| total_due | fines_and_costs_balance + restitution_balance (no account fee added unless policy-supported) |

---

## 3. Payment Plan Edge Cases

### First petition vs. subsequent review

- **First petition (initial_installment)**: The defendant's first request for a payment plan after disposition. Use the submitted date and requested amounts. The budget is reviewed for supportability.
- **Subsequent review**: A return to court for a payment plan modification. The existing plan terms may be in the portal; do not treat it as a fresh initial installment.
- **Deferred payment**: No regular monthly schedule; a single due date with the full amount.
- **Exempt no payment**: Policy or indigency determination exempts the defendant from payment.

### Restitution payment order

When both restitution and fines/costs are owed, the payment application order matters:

- **Restitution before fines/costs**: Each payment applies to restitution first, then fines/costs. Use when the petitioner requests it or policy mandates it.
- **Fines/costs before restitution**: Default order when restitution is not prioritized by policy or petitioner request.
- **Fines/costs only**: No restitution owed.

### Supportability classification

Compare the requested monthly payment against the petitioner's disposable income:

```
disposable_income = monthly_income - total_monthly_obligations
```

Policy thresholds (jurisdiction-specific) classify the result:

- **supportable**: Requested amount is within the policy's acceptable range
- **below_policy_minimum**: Requested amount is too low per policy
- **above_policy_maximum**: Requested amount exceeds what policy allows
- **unsupported_by_budget**: Disposable income is negative or insufficient

### Schedule computation

```
total_installments = ceil(total_due / regular_installment_amount)
final_payment_amount = total_due - regular_installment_amount * (total_installments - 1)
```

If `final_payment_amount == regular_installment_amount`, then `total_installments` is simply `total_due / regular_installment_amount` and all payments are equal. The final payment line still exists in the output with the same amount.

If `final_payment_amount == 0`, reduce `total_installments` by 1 and set `final_payment_amount` equal to `regular_installment_amount`.

The return-to-court date should be after the final due date -- typically 1-2 months later per local practice. Use the candidate date from the petition if provided.

---

## 4. Form-Specific Patterns

### CC-1375 (Probation Referral)

Field mapping:

| Form field | Source | Fallback |
|---|---|---|
| case_number | Case record | -- |
| defendant_name | Case record | -- |
| conviction_date | Sentencing notes or portal | -- |
| probation_type | Sentencing notes: "supervised" | -- |
| probation_term_months | Sentencing notes: judge's stated months | 0 if no probation ordered |
| report_datetime | Sentencing/probation notes | null if no report scheduled |
| probation_officer_or_office | Sentencing/probation notes | TBD from case file |
| defendant_identifier_if_known | Case record | TBD from case file |

When no supervised probation was ordered (status: not_ordered), probation_term_months is 0 and report_datetime is null.

### CC-1379 (License Suspension and Installment Payment Order)

License suspension fields:

| Form field | Source | Fallback |
|---|---|---|
| suspension_effective_date | Conviction date (not release date) | -- |
| license_suspension_months | Sentencing or probation notes | -- |
| suspension_end_date | start_date + suspension_months | -- |
| driver_license_number | Case record or DMV link | TBD from case file |

Installment order fields:

| Form field | Source |
|---|---|
| total_due | Fee reconciliation |
| restitution_due | Restitution balance |
| installment_amount | Approved monthly amount |
| payment_interval | monthly |
| first_due_date | From petition or policy |
| final_due_date | Computed from schedule |
| return_to_court_date | From petition or computed |

---

## 5. Conflict Classification Detail

### identity

**Pattern**: Name typo in finance queue (e.g., "Jons" vs. "Jones"). DOB one day off. Blank DOB that needs verification.

**Resolution**: Portal CMS is authoritative for identity unless a corroborating memo provides a paper-file correction. A hearing note with a "?" on the name is a signal, not the resolution -- check the portal.

### counsel

**Pattern**: Finance queue says "PD J. Doe" but a defense cover memo says appointed private counsel. Calendar abbreviation "APD" used for an attorney who is not from the public defender office.

**Resolution**: Hearing notes and corroborating memos that identify the actual attorney and appointment type override the portal/queue label. If the corroborating memo confirms appointed private, classify as `appointed_private` and exclude the PD user fee.

### status

**Pattern**: Finance queue marks a case "disposed" but the judge withheld signature. Draft worksheet carries a plea line for a case that was continued.

**Resolution**: If the judge did not sign the order or the case was continued for status, use `hold_unsigned_order` or `exclude_pending`. Do not post financials. Mark the case as deferred or pending.

### fee_schedule

**Pattern**: Local worksheet uses a 2023 drug assessment amount when the case is a 2025 disposition. Fee omitted from a worksheet that the portal schedule requires.

**Resolution**: Fetch the current portal fee schedule. Use its amounts. Flag the discrepancy in audit findings with resolution source `use_fee_schedule`.

### departure

**Pattern**: Draft worksheet carries "dispositional departure" but the judge expressly said "no separate departure finding" or "top of the range."

**Resolution**: The judge's spoken ruling controls. Set departure_status to `no_departure` or `none`. Flag the worksheet discrepancy in audit findings with resolution source `use_hearing_notes`.

---

## 6. Validation Checklist

Before finalizing any closeout JSON, verify:

- [ ] All required top-level keys present
- [ ] Array items sorted per template ordering rules (case_number ascending, citation_number ascending, etc.)
- [ ] All currency values: two decimal places (150.00 not 150 or 150.0)
- [ ] All dates: ISO 8601 YYYY-MM-DD
- [ ] All enum values match the template's allowed sets exactly
- [ ] Held/pending cases: financial totals zero, counted in held count not assessed count
- [ ] Register totals: each fee-code total sums individual case fee items; grand total sums all fee-code totals
- [ ] No invented DOB, SSN, address, phone, license number, or contact info
- [ ] Placeholder value matches template (commonly "TBD from case file")
- [ ] Disposed cases have docket entries; held cases have disposition-hold entries
- [ ] Fee amounts trace to the portal schedule or the judge's spoken sentence
- [ ] Administrative fees excluded unless portal policy explicitly includes them
- [ ] Payment plan schedule: installments, final payment, and dates are internally consistent
- [ ] License suspension end date computed correctly from start date plus months
