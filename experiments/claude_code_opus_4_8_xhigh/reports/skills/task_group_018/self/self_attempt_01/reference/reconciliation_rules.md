# Reconciliation decision table & worked patterns

Source-of-truth resolution, fee support, and the recurring computation patterns behind
these closeout tasks. Map every field name below to the **exact** key/enum the current
task's `answer_template.json` uses — the vocabularies differ per task.

## Field-by-field authority table

| Fact to decide | Authoritative source | Beats / corrects | Note |
|---|---|---|---|
| Defendant name, DOB | CMS `cases` record, corroborated by paper/defense memo | Stale finance-queue/worksheet name & DOB | If blank everywhere → placeholder + verify action; never borrow from a similar name |
| Counsel classification | CMS `cases.counsel_type` + `attorney_label_raw`, defense memo | A "PD" label copied onto a private-counsel case | `APD`/`APPT PRIVATE` = appointed_private, NOT public defender |
| Plea / finding | Hearing notes / minute order | Draft worksheet plea lines | |
| Charge amendment & conviction count | Hearing notes | CMS charge row still showing the original count/disposition + assessment code | Conviction count = the amended count |
| Departure finding | Hearing notes (what the judge said on the record) | `departure_type`/`departure_reason` carried on the CMS charge row or a draft worksheet | "top of range" ≠ departure |
| Order signed? (disposed vs held) | Hearing notes / docket | A queue `status: disposed` on an unsigned matter | No signed order → hold/exclude, post no money |
| Fee/assessment amount | Current `fee-schedules` row effective on disposition date | Archived rows (past `end_date`); stale worksheet amounts | See fee-validity test below |
| Plan policy (band, account fee, due timing, restitution priority) | `payment-policies` row for the jurisdiction | Old counter/worksheet fee rows and service charges | |
| Form id/label/required fields/placeholder rule | `forms` row for the jurisdiction | Obsolete local form footer/service charge | |

## Fee validity test

A fee-schedule row applies to a disposition only if:

```
effective_date <= disposition_date  AND  (end_date is null OR end_date >= disposition_date)
```

Pick the matching current row for the needed `fee_type` in that `jurisdiction_code`.
Discard archived rows (they carry a past `end_date` and a "stale/retained for audit"
note). Never post an amount from a worksheet that disagrees with the current row.

## Postable vs excluded money

- **Postable** only with direct support from a current fee schedule, the hearing/
  disposition order, or explicit current policy.
- **Public Defender User Fee** (`user_fee`, `mandatory:false`): post only for true
  `public_defender` counsel; exclude for appointed_private / retained.
- **Drug/lab assessment**: post only when the *conviction* count is the eligible offense,
  at the *current* amount. Amended-away → exclude the lab fee.
- **Always-exclude unless a record/order/current-policy directly supports it**:
  account-management/maintenance, collection/referral, late-payment, DMV/reinstatement,
  returned-check, restitution (unless ordered), copy/certification, traffic-school,
  court-reporter, court-appointed-attorney. No triggering event in the minutes → exclude
  with the "no_triggering_event" / "not_in_hearing_order" style reason code.
- **Held/deferred/continued matter**: post nothing; record the exclusion with a
  next-status date and `financial_posting_allowed=false`.

## Exclusion reason codes (use the template's exact enum)

Common families seen across tasks:
`stale_schedule`, `unsupported_post_disposition`, `not_in_hearing_order`,
`not_current_policy`, `no_triggering_event`, `no_order_or_policy_support`,
`not_part_of_balance`, `continued_pending_no_final_order`.

## Installment schedule pattern

Given reconciled `total_due`, approved `monthly`, and optional `down_payment`:

```
remaining              = total_due - down_payment
full_installment_count = floor(remaining / monthly)
if remaining % monthly == 0:
    final_payment_amount = monthly
    total_installments   = full_installment_count
else:
    final_payment_amount = remaining - full_installment_count * monthly   # the smaller last payment
    total_installments   = full_installment_count + 1
```

- `first_due_date`: policy-driven ("15th of next month" / submitted + `first_due_days`)
  or the date stated in the hearing note.
- `final_due_date`: `first_due_date` + `(total_installments - 1)` intervals.
- `return_to_court_date`: `disposition/first-due` + policy `return_to_court_offset_days`.
- Watch the template's split between "full payments" and "total installments" — the
  final partial payment counts as an installment but not as a full payment.

## Budget affordability pattern

```
monthly_disposable_income = monthly_income - monthly_obligations
```

Classify `requested/selected` monthly against the policy band
(`min_monthly`..`max_monthly`) and disposable income, using the template's exact enum
(supported / below_policy_minimum / above_policy_maximum / unsupported_by_budget /
needs_judge_review). Surface the band values where the schema asks.

- Account fee: include only if the jurisdiction policy's `account_fee` > 0 (else exclude
  a counter/worksheet account fee by policy).
- Payment application order: restitution-before-fines-and-costs only when restitution > 0
  and the policy states that priority; otherwise fines/costs only.

## Conditional forms/orders

- Probation referral (CC-1375-style): prepare only when supervised probation was ordered;
  otherwise mark not-ordered and leave report_datetime null.
- License order (CC-1379-style): start basis is normally the **conviction date** (a
  release-from-confinement date is memo context, not the suspension start); suspension end
  = start + ordered months.
- Keep unknown driver-license numbers and contact details as the required placeholder.

## Pre-submission checklist

- [ ] Every required top-level and per-item key present; no extra keys.
- [ ] Enum values verbatim (no prose substituted for an enum).
- [ ] Currency numeric, 2 decimals; dates/datetimes/times in the required ISO forms;
      `null` only where allowed.
- [ ] Lists sorted per the ordering rules (ascending on the named field(s)).
- [ ] Stale values corrected; unsupported money excluded; held matters posted no money.
- [ ] Missing required fields carry the exact placeholder — nothing invented or borrowed.
- [ ] Totals recomputed from posted lines only.
- [ ] JSON only, if the template requires it.
