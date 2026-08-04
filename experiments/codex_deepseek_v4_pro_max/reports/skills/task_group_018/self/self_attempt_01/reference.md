# Court Clerk Portal Reference — Reusable Enums & Patterns

Common enum values, fee codes, and schema shapes observed across court-clerk closeout and financial-packet tasks. Use these as a catalog when building answers to new tasks.

## Audit & Conflict Resolution

### Issue Types

| Value | Meaning |
|---|---|
| `identity` | Defendant name, DOB, or identifier conflict |
| `counsel` | Attorney classification conflict |
| `status` | Case disposition status conflict |
| `fee_schedule` | Fee amount or schedule version conflict |
| `departure` | Departure finding conflict |

### Resolution Sources

| Value | Meaning |
|---|---|
| `use_cms` | Portal/CMS record controls |
| `use_hearing_notes` | Courtroom bench notes control |
| `use_corrob_memo` | Corroborating audit memo controls |
| `use_fee_schedule` | Current fee schedule controls |
| `hold_unsigned_order` | Defer until signed order |
| `use_cms_identity` | CMS identity record controls |
| `verify_before_entry` | Must verify before posting |
| `exclude_pending` | Exclude from current batch |

### Counsel Classifications

| Value | Meaning | PD Fee Applies? |
|---|---|---|
| `public_defender` | Attorney from the PD office | Yes |
| `appointed_private` | Private attorney paid by county | No |
| `retained` | Privately retained by defendant | No |
| `unknown` | Classification uncertain | Verify |

## Case Status & Disposition

### Case Statuses

| Value | Meaning |
|---|---|
| `disposed` | Final order signed; ready to post |
| `deferred` | Deferred adjudication; no final order |
| `pending` | Awaiting further action |
| `continued` | Continued to a future date |

### Closeout Actions

| Value | Meaning |
|---|---|
| `enter_disposition` | Post disposition and financials |
| `hold_unsigned_order` | Hold until signed order available |
| `no_closeout` | No closeout entry for this case |

### Pleas

| Value |
|---|
| `guilty` |
| `no contest` |
| `not guilty` |
| `none` |
| `not_entered` |
| `not_applicable` |
| `no_plea_recorded` |

### Charge Dispositions

| Value |
|---|
| `guilty` |
| `nolle_prosequi` |
| `deferred` |
| `pending` |
| `dismissed` |

### Findings (Traffic)

| Value |
|---|
| `violation_found` |
| `dismissed` |
| `continued` |
| `verify_before_entry` |

### Primary Outcomes (Criminal)

| Value |
|---|
| `guilty_plea` |
| `no_contest_guilty` |
| `bench_trial_guilty` |
| `continued_pending` |

### Departure Statuses

| Value | Meaning |
|---|---|
| `no_departure` | No departure found |
| `durational_departure` | Sentence length departure |
| `dispositional_departure` | Disposition type departure |
| `not_applicable` | Departure not applicable |
| `none` | No departure |
| `not_evaluated_misdemeanor` | Misdemeanor — not evaluated |
| `not_entered_pending` | Pending case — not entered |

## Financial — Fee Codes & Statuses

### Fee Codes

| Value | Typical Context |
|---|---|
| `fine` | Monetary penalty imposed by court |
| `court_cost` | Mandatory circuit/district court cost |
| `drug_assessment` | Controlled-substance conviction assessment |
| `public_defender_user_fee` | PD office representation fee |
| `crime_lab_fee` | Controlled-substance lab assessment |

### Fee Statuses

| Value | Meaning |
|---|---|
| `post` | Include in register |
| `exclude` | Exclude from register |
| `hold` | Hold pending further action |
| `do_not_post_pending` | Do not post — case pending |

### Unsupported Fee / Charge Reason Codes

| Value | Meaning |
|---|---|
| `stale_schedule` | Amount from outdated fee schedule |
| `unsupported_post_disposition` | Not supported post-disposition |
| `not_in_hearing_order` | Not in the hearing order |
| `not_current_policy` | Not supported by current policy |
| `no_triggering_event` | No event triggering this fee |
| `no_order_or_policy_support` | No order or policy basis |
| `not_part_of_balance` | Not part of the account balance |

## Docket & Register

### Docket Entry Types

| Value |
|---|
| `sentencing_order` |
| `disposition_hold` |

### Register Actions

| Value |
|---|
| `enter_disposition_and_financials` |
| `exclude_no_final_order` |

### Docket Codes

| Value |
|---|
| `SENTENCING_ORDER_ENTERED` |
| `CONTINUED_NO_DISPOSITION` |

### Exclusion Reasons

| Value |
|---|
| `continued_pending_no_final_order` |

## Payment Plans

### Plan Statuses

| Value |
|---|
| `approved` |
| `not_approved` |
| `not_applicable` |
| `verify_before_entry` |

### Agreement Types

| Value |
|---|
| `extended_payment_plan` |
| `standard_due_date_only` |
| `none` |
| `verify_before_entry` |
| `initial_installment` |
| `deferred_payment` |
| `subsequent_review` |
| `no_agreement` |

### Petition Classifications

| Value |
|---|
| `initial_installment` |
| `subsequent_review` |
| `deferred_payment` |
| `exempt_no_payment` |

### Support Classifications

| Value | Meaning |
|---|---|
| `supported_by_budget` | Budget supports the requested amount |
| `supportable` | Budget can support the plan |
| `below_policy_minimum` | Below the policy minimum payment |
| `above_policy_maximum` | Above the policy maximum payment |
| `unsupported_by_budget` | Budget cannot support the plan |
| `needs_judge_review` | Requires judicial review |

### Payment Application Orders

| Value |
|---|
| `fines_costs_only` |
| `restitution_before_fines_costs` |
| `fines_costs_before_restitution` |

### Account Fee Treatments

| Value |
|---|
| `excluded_by_policy` |
| `included_by_policy` |
| `verify_before_entry` |

### Schedule Intervals

| Value |
|---|
| `monthly` |
| `biweekly` |
| `weekly` |
| `deferred_single_due` |

### License Start Bases

| Value | Meaning |
|---|---|
| `conviction_date` | Suspension from conviction date |
| `release_date` | Suspension from release date |
| `petition_date` | Suspension from petition date |

## Traffic Violation — Specific

### Violation Codes (Oregon)

| Value | Meaning |
|---|---|
| `ORS_811_109_100PLUS` | 100+ mph over limit |
| `ORS_811_109_31_40` | 31-40 mph over limit |
| `ORS_811_109_21_30` | 21-30 mph over limit |
| `other` | Other violation |

### Fine Tiers

| Value |
|---|
| `speed_100_or_greater` |
| `speed_31_to_40_over` |
| `speed_21_to_30_over` |
| `statutory_maximum` |
| `verify_before_entry` |

### Fee Schedule Sources

| Value |
|---|
| `F-OR22-100-2024` |
| `F-OR22-31-2024` |
| `F-OR22-100-OLD` |
| `statutory_maximum_note` |
| `local_memo_only` |
| `verify_before_entry` |

## Form Reference

### Common Form Families

| Form Family | Label |
|---|---|
| `CC-1375` | Notice of Referral to Probation Officer |
| `CC-1379` | License Suspension and Installment Payment Order |
| `OR_22JD_PLAN` | 22nd Judicial District Extended Payment Plan |

### CC-1375 Statuses

| Value |
|---|
| `prepare_referral` |
| `not_ordered` |

### Form Field Labels (Payment Plans)

| Label |
|---|
| `Case # / Account #` |
| `Case/Account Balance` |
| `Action Table(s) / Notes` |
| `TERMS of PAYMENT` |

## Placeholder Value

| Value | When |
|---|---|
| `TBD from case file` | Missing identifier, contact, or detail that a form requires but the case file does not contain |

## Common Audit Flags

| Value | Meaning |
|---|---|
| `amended_non_lab_conviction` | Amended charge, no lab fee for non-CS conviction |
| `lab_fee_worksheet_omitted` | Worksheet missing required lab fee |
| `dob_missing_verify` | DOB blank, must verify |
| `apd_label_not_public_defender` | APD label but attorney is appointed private |
| `no_final_order_pending` | No final signed order exists |

## Computable Patterns

### Installment Math

Given `total_due`, `monthly_payment`, `first_due_date`:

```
full_installment_count = floor(total_due / monthly_payment)
final_payment_amount = total_due - (full_installment_count * monthly_payment)
total_installments = full_installment_count + (final_payment_amount > 0 ? 1 : 0)
final_due_date = first_due_date + (total_installments - 1) months
```

### Disposable Income

```
monthly_disposable_income = monthly_income - total_monthly_obligations
```

### Register Totals

Sum each fee category across disposed cases only. Do not include held/pending cases.

```
court_cost_total = sum of court_cost from disposed cases
fine_total = sum of fine from disposed cases
assessment_total = sum of drug_assessment from disposed cases
user_fee_total = sum of public_defender_user_fee from disposed cases
lab_fee_total = sum of crime_lab_fee from disposed cases
grand_total = sum of all posted fee lines
```
