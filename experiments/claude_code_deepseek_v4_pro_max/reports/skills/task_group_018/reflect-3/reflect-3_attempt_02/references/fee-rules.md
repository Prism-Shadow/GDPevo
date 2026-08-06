# Fee Reconciliation Rules

## Counsel-Type Fee Rules

| Counsel Type | PD User Fee | Rule |
|-------------|-------------|------|
| `public_defender` | Post (unless waived) | Include the PD user fee per current schedule |
| `appointed_private` | Exclude | Appointed private counsel is not the public defender's office |
| `retained` | Exclude | Defendant hired their own attorney |
| `unknown` | Hold for verification | Do not post until counsel type is confirmed |

## Assessment Triggers

| Assessment | Trigger |
|-----------|---------|
| Drug assessment | Controlled-substance conviction (Ark. Code 5-64) |
| Crime lab fee | Judge specifically orders it on the record for a controlled-substance count |
| No assessment | Conviction is not for a controlled substance, or count was amended away from drug charge |

## Mandatory vs. Discretionary Fees

- **Mandatory fees** (court costs): Always post for disposed criminal/traffic matters, per the current jurisdiction schedule
- **Discretionary fees** (PD user fee): Post only when the counsel trigger is met AND the fee was not waived on the record
- **Event-triggered fees**: Post only when the triggering event occurred (late payment → late fee; collection referral → collection fee; DMV action → DMV fee)

## Always-Exclude List

Unless the current payment policy or a specific court order explicitly authorizes them for this case:

- Late-payment fees (no overdue payment)
- Collection referral fees (no collection referral)
- DMV reinstatement fees (no DMV action ordered)
- Returned-check fees (no returned payment)
- Account-management fees (not authorized by current policy, or policy sets `account_fee: 0.00`)
- Restitution (no restitution order in the record)
- Traffic-school fees (traffic school not ordered)
- Copy/certification fees (not part of normal sentencing)

## Fee Amount Resolution

1. Check the hearing notes for the amount pronounced in court (fine, costs)
2. Verify the amount against the current fee schedule for the jurisdiction
3. If the schedule has a different amount than the queue, use the schedule and flag as a `fee_schedule` audit issue
4. For assessments, use the schedule amount effective on the disposition date — not an older year's amount
