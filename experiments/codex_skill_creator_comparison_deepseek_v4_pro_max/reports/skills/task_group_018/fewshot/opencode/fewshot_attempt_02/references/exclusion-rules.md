# Fee and Charge Exclusion Rules

Not every fee or charge that appears in local materials should be posted to the
register. Apply these rules to determine what to exclude.

## Exclusion Decision Flow

For each candidate fee or charge:

1. **Is it in the current portal fee schedule?** Check effective_date and
   end_date. Archived/stale records (past end_date) do not count.
2. **Is it supported by a court order?** The hearing notes or sentencing order
   must support the fee.
3. **Is it triggered by an event that occurred?** Some fees (late fee, collection
   fee, DMV notice fee, returned-check fee) require a triggering event. If the
   hearing notes and local materials do not show the event happened, exclude.
4. **Does the fee depend on counsel type?** The public defender user fee only
   applies to public_defender cases, not appointed_private or retained.
5. **Does the fee depend on charge type?** Drug assessments and lab fees apply
   only to controlled-substance convictions, not amended-away charges.

If a fee fails any of these checks, it goes in the excluded list.

## Common Exclusion Reason Codes

Use these reason codes (from the answer template's enums where available):

- **stale_schedule** — fee amount is from an old/archived schedule; current
  schedule has a different amount or the fee no longer exists.
- **unsupported_post_disposition** — fee is not supported by current policy
  or schedule for post-disposition entry.
- **not_in_hearing_order** — fee was not ordered by the court in the hearing.
- **not_current_policy** — current payment/fee policy does not support the fee.
- **no_triggering_event** — fee requires an event (late payment, default,
  collection referral, DMV referral, returned check, traffic school order)
  that did not occur.
- **no_order_or_policy_support** — no court order or current policy supports
  this fee.
- **not_part_of_balance** — fee is not part of the current case balance
  (e.g. DMV reinstatement fee is a separate administrative fee).

## Fee-Specific Rules

### Account-management fee
- Exclude unless the current payment policy for the jurisdiction explicitly
  includes it. Obsolete form footers mentioning old service charges do not
  make the fee current.
- Reason: not_current_policy or no_order_or_policy_support.

### Late-payment fee
- Exclude unless there is evidence of a late or missed payment triggering
  the fee under current policy.
- Reason: no_triggering_event.

### Collection referral fee
- Exclude unless the case has been formally referred to collections.
- Reason: no_triggering_event.

### DMV notice / reinstatement fee
- Exclude from the case financial entry. These are separate administrative
  fees, not part of the sentencing balance.
- Reason: no_triggering_event (if no DMV referral) or not_part_of_balance.

### Returned-check fee
- Exclude unless there is evidence of a returned payment.
- Reason: no_triggering_event.

### Traffic-school fee
- Exclude unless the court ordered traffic school at the hearing.
- Reason: not_in_hearing_order.

### Restitution
- Exclude unless a restitution order exists in the sentencing materials.
  Always check the sentencing intake or hearing notes for a restitution line.
- Reason: no_order_or_policy_support.

### Copy / certification fee
- Exclude unless specifically requested or ordered. These are not part of
  normal sentencing or traffic disposition.
- Reason: no_triggering_event.

### Public defender user fee
- Apply only when counsel_type is public_defender. Exclude for
  appointed_private and retained counsel cases.
- Reason: no_order_or_policy_support (when counsel is not PD).

### Drug assessment / crime lab fee
- Apply only when the conviction count is a controlled-substance or drug
  offense. If the charge was amended to a non-drug count, exclude.
- This also applies to lab fees tied to controlled-substance convictions.
- When excluding, list it under the appropriate exclusion section.

### Stale fine amounts from old schedules
- When the finance queue or worksheet carries an amount from a prior year's
  schedule (e.g. a 2022 SOF table amount for a 2026 disposition), use the
  current schedule amount instead and list the stale amount as excluded.
- Reason: stale_schedule.

### Statutory maximum substitution
- A statutory maximum note from intake is not a fee schedule. If the current
  schedule has a specific fine tier, use it. Do not substitute the statutory
  maximum unless the current schedule is genuinely unavailable.
- Reason: unsupported_post_disposition.

## Exclusion List Format

Each excluded item must include:
- The charge_code / item name (from template enum if available)
- Which matters it applies to (all, or specific case/citation numbers)
- The reason_code

Sort excluded items as directed by the answer template (typically by
charge_code ascending or by case_number ascending).

## Batch-Level Exclusion: Held Cases

A case with no signed final order is not disposed. Do not post any financial
entry for it. The exclusion entry should identify the case, the reason
(continued_pending_no_final_order), and the next status check date if known.
