# Field-by-field playbook

Generic guidance for the recurring field families in these closeout templates.
Always defer to the specific `answer_template.json` in front of you for the exact
key names and enum spellings; this file explains *how to decide each value*.

## Audit / case-audit findings

One finding per reconciled conflict. Typical keys: case id, an `issue_type`
(identity / counsel / status / fee_schedule / departure / lab-fee / dob-missing /
apd-label / no-final-order …), the conflicted value, the corrected value, and a
`resolution_source`.

- Choose `issue_type` from what disagreed (a queued DOB vs portal DOB = identity;
  a `PD`/`APD` label vs portal counsel = counsel; a stale amount = fee_schedule;
  a draft "dispositional departure" the judge rejected = departure; an unsigned/
  continued order = status/no-final-order).
- Choose `resolution_source` from the authority that settled it: the portal/CMS
  (identity, counsel, status), the hearing/closeout notes or on-record
  clarification (plea, adjudication, departure, counsel clarified in court), a
  corroborating memo, the current fee schedule (amounts), or "hold because
  unsigned".
- Free-text conflicted/corrected description strings are usually not the scored
  part; the scored part is the ids and the enum choices. Get those exactly right.

## Dispositions

- `case_status` / `entry_status`: from the portal + docket. disposed → enter;
  deferred/continued/pending or "no final order signed" → hold/exclude, and set
  `disposition_date` to null.
- `plea`: from the courtroom record. Guilty, no-contest map straight through. A
  bench-trial conviction (defendant contested) maps to the template's
  "not applicable / not entered" plea value, because a not-guilty-then-convicted
  plea is not usually an allowed enum. A continued matter with incomplete plea
  paperwork = "not entered".
- `primary_outcome`: guilty_plea / no_contest_guilty / bench_trial_guilty /
  continued_pending — read it off the notes.
- `charge_disposition`: the courtroom adjudication wins over a stale charge row.
- Counts: convicted count vs dismissed/amended-away count. A single count that was
  amended from one offense to another and then convicted is normally 1 conviction;
  do not manufacture extra counts.
- `departure_status`: express judge finding only; else no-departure. Felony with no
  departure → the "none" value; misdemeanor → the "not evaluated (misdemeanor)"
  value; pending → the "not entered (pending)" value.

## Fee entries / reconciliation

- Court cost: the jurisdiction's current mandatory court cost.
- Fine: the amount actually imposed in court (0 if waived).
- Drug/lab/assessment: the current amount, only on a qualifying (controlled-
  substance/drug) conviction; 0 if the count was amended to a non-drug offense.
- Public-defender user fee: only for `public_defender` counsel, not waived.
- `fee_status`: post for a disposed matter; hold/do-not-post for a held/pending one
  (all its amounts 0).
- `case_total` = sum of that case's posted line items.

## Docket / register entries and totals

- Disposed matter → sentencing-order-entered code, entry date = disposition date,
  register action = enter disposition + financials.
- Held/continued matter → continued/no-disposition code, entry date null, register
  action = exclude / no final order.
- Totals: disposed vs held/excluded counts; per-fee-type totals; grand/batch total
  — all summed over posted matters only.

## Traffic violation entries

- `violation_code` / `fine_tier`: **absolute speed ≥ 100 mph → the "100 or greater"
  tier** (this overrides the over-limit tier). Otherwise the tier is
  `(speed - zone)` over the limit (21–30, 31–40, …). Confirm against the citation
  row's `violation_code`.
- `fee_schedule_source`: the current standard-fine schedule id for that tier — not
  the stale/old id and not the statutory-maximum note.
- `standard_fine` = current schedule amount; `county_surcharge` = once per citation;
  `amount_due = standard_fine + county_surcharge`.
- `agreement_sequence`: post_disposition when the plan was approved after the
  disposition was entered.

## Excluded / do-not-add charges

List the charges that were considered but must stay out of the balance. Reason
codes distinguish *why*: stale schedule, not-in-hearing-order / no-triggering-event
(no late/default/referral/returned-check/DMV/traffic-school event occurred),
not-current-policy (e.g. an obsolete service charge the current policy dropped), or
not-part-of-balance / no-order-or-policy-support for a zero-balance line. Only list
items that were actual candidate line items or that the template's enum enumerates;
do not pad the list.

## Probation-referral (CC-1375-style) fields

- Status = prepare-referral when supervised probation was ordered; not-ordered when
  the notes say no referral order was signed (then term = 0 and report datetime =
  null, even if a portal field carries a tentative datetime).
- `report_datetime`: the ordered reporting datetime from the notes/portal, in ISO
  local datetime.
- Officer / office location: `TBD from case file` if absent.

## License-suspension + installment (CC-1379-style) fields

- Suspension status suspended for a DUI/qualifying conviction; `effective_date` =
  conviction date; `months` from the order/portal; `end = start + months`.
- `basis`: dui_conviction for a DUI; else other.
- Driver-license number: `TBD from case file` if absent.
- Payment order: see `payment_math.md`. `agreement_type` = initial-installment for
  a first petition; policy id from the payment policy; account fee per policy
  (0 → excluded); down payment per policy; return-to-court trigger = nonpayment for
  a first installment order unless the template/notes indicate otherwise.

## Budget / support classification

- `disposable = monthly_income - monthly_obligations`.
- Supported when the selected monthly is within `[min_monthly, max_monthly]` and
  `<= disposable`. Otherwise below-minimum, above-maximum, or unsupported-by-budget
  per the template's enum.
- Report the policy band (min/max) and the selected amount.
