# Fee Reconciliation Rules

When reconciling financial entries across hearing notes, worksheets, audit
memos, portal fee schedules, and petition summaries, follow these rules
strictly.

## Filtering the Fee Schedule

1. `jurisdiction_code` must match the target jurisdiction.
2. `effective_date` ≤ the disposition/event date.
3. `end_date` is null OR `end_date` ≥ the disposition/event date.

A fee that fails any of these three checks is stale and must not be posted.

## Mandatory Fees

These always post for qualifying cases:

### Court Costs

Every disposed criminal or traffic case pays court costs. The current amount for
the target jurisdiction appears in the fee schedule with `fee_type` of
`court_cost` and `mandatory: true`.

### Drug / Controlled-Substance Assessments

When the conviction is for a controlled-substance offense:

- Check the fee schedule for an assessment with `fee_type: "assessment"` and a
  `statute` referencing the controlled-substance code.
- The current amount applies. Reject stale/archived amounts even if a worksheet
  or finance queue still carries them.

### Lab Fees (Arkansas)

When the conviction is for a controlled-substance offense in an Arkansas circuit
court, the crime laboratory fee is mandatory. Check the fee schedule for the
current lab fee amount (fee_type: "assessment", statute referencing Ark. Code
12-12).

### County Surcharges (Traffic)

Traffic citations in some jurisdictions carry a mandatory county surcharge.
Add it once per citation.

## Conditional Fees

These post only when the condition is met:

### Public Defender User Fee

- Applies only when counsel is a public defender (not appointed private, not
  retained).
- If the audit memo or hearing notes clarify that counsel is appointed private
  despite a worksheet label of "PD" or "APD", do not post the PD user fee.

### Fines

- Post only the fine amount announced by the judge in the hearing notes.
- If the judge waived the fine, post $0.00.
- If the matter is deferred/continued without a signed order, post $0.00 for
  all fees.

## Prohibited Fees

Do not add these to the starting balance or register unless explicitly ordered:

| Fee | Reason |
|-----|--------|
| Account management fee | Not part of balance unless current policy explicitly applies it |
| Late payment fee | No triggering event at disposition |
| Collection referral fee | No triggering event at disposition |
| DMV notice/reinstatement fee | Not in hearing order |
| Returned check fee | No triggering event at disposition |
| Restitution | Not ordered in the sentencing record |
| Copy or certification fee | Not part of normal disposition |
| Traffic school fee | Not in hearing order |
| Court-appointed attorney fee | No order or policy support |
| Court reporter fee | No order or policy support |

## Account Fee Special Case

Payment policies may carry an `account_fee` field. For most jurisdictions this
is $0.00 (not applied). Check the policy record for the target jurisdiction.
When the policy record says $0.00, the account fee amount due is $0.00 and the
treatment is `excluded_by_policy`.

## Stale Worksheet Amounts

Worksheets, finance queue extracts, and intake cover sheets may carry:

- Old fee schedule amounts superseded by current schedules.
- Draft fines for unsigned orders.
- Fees for charges that were amended away.

Always replace stale amounts with the current portal schedule. Never post
financial entries for a case where the final order was not signed.
