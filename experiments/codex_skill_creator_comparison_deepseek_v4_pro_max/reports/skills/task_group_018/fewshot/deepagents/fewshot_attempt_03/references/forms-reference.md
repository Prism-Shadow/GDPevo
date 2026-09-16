# Forms Reference

## Common Court Forms

### CC-1375 — Probation Referral (Virginia)

This form is used for supervised probation referrals in Virginia circuit courts.

**Required fields** (fill from case materials and portal):
- `form_id`: always `"VA_CC1375"`
- `form_label`: `"CC-1375 Probation Referral"`
- `case_number`: from the case record
- `defendant_name`: from the case record
- `conviction_date`: from the sentencing intake or portal charges record
- `probation_type`: `"supervised"` when probation was ordered, `"unsupervised"` if ordered but not supervised, `"none"` when no probation was ordered
- `probation_term_months`: from the sentencing order
- `report_datetime`: from the sentencing intake or probation notes (ISO datetime)
- `probation_officer`: use `"TBD from case file"` if absent from all materials
- `probation_office_location`: use `"TBD from case file"` if absent from all materials

**When to prepare**: Only when `probation_referral_required` is true or `supervised_probation_months > 0`. If no supervised probation was ordered, set `cc1375_status` to `"not_ordered"` with `probation_term_months: 0` and `report_datetime: null`.

### CC-1379 — License Suspension and Installment Payment Order (Virginia)

This form combines driver's license suspension consequences with installment payment plan terms for DUI and similar convictions.

**Required fields:**
- `form_id`: always `"VA_CC1379"`
- `form_label`: `"CC-1379 Installment/License Order"`
- `case_number`, `defendant_name`: from the case record
- `driver_license_number`: use `"TBD from case file"` when absent
- `license_suspension.status`: `"suspended"` unless no suspension was ordered
- `license_suspension.effective_date`: conviction date (use conviction date, not release date, as the suspension start)
- `license_suspension.months`: from the sentencing order
- `license_suspension.basis`: `"dui_conviction"` for DUI cases

**Payment order fields:**
- `agreement_type`: `"initial_installment"` for first-time petitions, `"subsequent_review"` for later reviews
- `policy_id`: from the portal payment policy for the jurisdiction
- `total_due`: fines_and_costs + restitution (account fees excluded unless supported by policy)
- `down_payment`: 0.00 unless ordered
- `installment_amount`: the approved monthly amount
- `first_due_date`, `final_due_date`, `return_to_court_date`: computed per payment plan math
- `return_to_court_trigger`: `"nonpayment"` unless otherwise specified

### Extended Payment Plan Agreement (Oregon 22nd JD)

This local form is used for post-disposition payment plans in Oregon traffic matters.

**Field labels** (from the form excerpt):
- `Case # / Account #`: citation number when no separate account exists
- `Case/Account Balance`: the amount due
- `Action Table(s) / Notes`: clerk notes area
- `TERMS of PAYMENT`: payment schedule terms

**Mapping:**
- `form_id`: `"OR_22JD_PLAN"` for 22nd Judicial District
- `form_label`: `"extended_payment_plan_agreement"`
- `account_reference`: citation number (used when no separate case/account number exists)

## Placeholder Convention

### The Rule

For any field required by a form or template that cannot be completed from the available materials (portal, case file, hearing notes, petition, audit memo), use the exact literal string:

```
TBD from case file
```

Never invent a value. Never use "unknown", "N/A", "pending", or a blank string.

### Fields That Commonly Require Placeholders

These fields are frequently missing from case materials and should use the placeholder unless explicitly present:

- `driver_license_number` — absent from most criminal case files
- `ssn` — absent from most public-facing records
- `mailing_address` — may not appear in the materials
- `residence_address` — may not appear in the materials
- `phone_number` / `phone` — may not appear in the materials
- `probation_officer` — often assigned after sentencing
- `probation_office_location` — often assigned after sentencing
- `dob_for_entry` — use placeholder only when DOB is genuinely blank (not just mismatched) and must be verified before entry

### Reason Codes for Placeholders

| Reason Code | Meaning |
|-------------|---------|
| `missing_identifier` | SSN, driver license number, or similar government ID |
| `missing_contact` | Address, phone, or similar contact detail |
| `missing_office_detail` | Probation office location or officer assignment |
| `missing_party_detail` | Other party-specific detail not in the file |

### When Not to Use a Placeholder

If the information is available from any allowed source (portal, case file, any payload file), use it. Only use the placeholder when every allowed source is silent on that field.
