---
name: court-clerk-closeout-reconciliation
description: >-
  Prepare a structured JSON closeout/register/field-packet for a court clerk by
  reconciling messy local materials (bench/hearing notes, clerk worksheets,
  finance-queue extracts, petition & budget summaries, form excerpts) against the
  authoritative court-operations records the task exposes (case, charge, docket,
  citation, fee-schedule, payment-policy, form, and financial-petition records).
  Use for criminal sentencing closeouts, traffic-violation dispositions with
  payment plans, and post-sentencing field packets (probation-referral / license
  suspension / installment-order forms). Trigger words: closeout, disposition
  register, reconcile, audit findings, fee reconciliation, payment plan /
  installment order, sentencing packet, clerk worksheet, hearing/bench notes.
---

# Court clerk closeout & reconciliation

These tasks give you (a) **local materials** that are explicitly unreliable —
bench/hearing notes with shorthand, draft worksheets, finance-queue imports,
petition intake sheets, form excerpts — and (b) an **authoritative court records
portal** (read-only lookups for cases, charges, docket entries, citations,
fee schedules, payment policies, forms, financial petitions). Your job is to
**reconcile** them into one JSON object that exactly matches the task's
`answer_template.json`.

The core skill is knowing **which source wins for which field**, catching
**stale/draft artifacts**, refusing to **invent or over-charge**, and getting the
**arithmetic and formatting** exactly right.

## Workflow

1. **Read the prompt + `answer_template.json` first.** The template defines the
   required top-level keys, the shape of each list item, every enum's allowed
   values, sort orders, and currency/date formats. Build your answer to that
   contract — never emit prose where an enum value is required.
2. **Read every local payload.** Note which values are flagged as draft, carried
   forward, archived, "old worksheet," "ready to post," etc. — those are suspects.
3. **Pull the authoritative record for each target** case / citation / petition
   from the portal (identity, counsel, status, charges, and the relevant
   fee-schedule, payment-policy, and form rows for that jurisdiction). Match by
   the identifier the task gives you; read the whole collection and filter
   locally rather than probing.
4. **Reconcile field by field** using the source-of-truth rules below.
5. **Compute** fees, totals, and any payment schedule with the arithmetic rules
   below; re-derive, don't copy the draft numbers.
6. **Format and sort** exactly as the template says, then self-check against the
   pre-submission checklist.

## Source-of-truth rules (who wins)

- **System-of-record portal case data wins for identity and standing:** legal
  name, date of birth, counsel type & attorney, case status, and the structured
  charge fields. A finance queue / worksheet that disagrees is usually a stale
  import — correct it to the portal value.
- **Hearing / bench notes win for what actually happened in the courtroom:** the
  plea entered, whether guilt was adjudicated, the pronounced sentence (fine,
  jail imposed/suspended, probation), amendments, and whether a final order was
  signed. Trust them over stale worksheet outcomes ("Dismissed", "draft guilty
  plea", pre-amendment charges).
- **When a portal charge row looks corrupted or mismatched** (e.g., a statute or
  offense label that clearly doesn't fit the offense described in court), prefer
  the hearing notes for the substantive offense/severity, and let the courtroom
  facts drive derived fields (e.g., felony-vs-misdemeanor treatment).
- **Current fee schedule wins for amounts.** Draft/archived amounts on worksheets
  are for audit history only.
- **A corroborating memo** (e.g., a defense cover memo) can resolve a conflict
  that both the queue got wrong and the notes only hint at.
- **An unsigned/continued order means "hold"** — the courtroom record beats any
  draft disposition sheet that assumed the case closed.
- Record each conflict you resolve as an audit finding: the conflicted value,
  the corrected value, and which source resolved it.

## Stale / draft artifacts to catch

- **Old fee amounts.** Use the schedule row whose `effective_date` ≤ the
  disposition/hearing date and whose `end_date` is null or ≥ that date. Ignore
  ended rows even if a worksheet still cites them.
- **Spurious sentencing departures.** Only record a departure if the courtroom
  actually pronounced one. "Top of the range" / "within the plea-agreement cap"
  means **no departure**. Legacy "dispositional/durational departure" text
  carried from a draft worksheet should be corrected to no-departure unless the
  judge confirmed a departure. Departures are a **felony** concept — for
  misdemeanors use the "not evaluated (misdemeanor)" value; for pending/continued
  matters use the "not entered / pending" value.
- **Pre-amendment charges.** If a count was amended to a different charge, the
  conviction is the **amended** charge. Count the amended-away original as a
  dismissed/amended-away count, and drop any fee that only attached to the
  original charge (see crime-lab fee below).
- **Draft dispositions on unsigned orders / continued matters** — see "Held".

## Fees: apply only what is supported

Never add a fee that no current schedule row, portal record, or triggering
event/order supports. Typical fees to **exclude** unless directly supported:
account-management/maintenance, collection/referral, late-payment, DMV/notice/
reinstatement, returned-check, traffic-school, copy/certification, restitution
(when none was ordered), court-reporter, and court-appointed-attorney fees.
When the template asks you to *list* excluded items, list each with the reason it
fails (stale schedule, not in the hearing order, no triggering event occurred,
not current policy, unsupported post-disposition). An obsolete "service charge"
in an old form footer is **not** current policy — exclude it and record the
applied amount as 0.

Gating rules that recur:

- **Public-defender user fee:** apply only when `counsel_type` is
  `public_defender`. Never for appointed-private or retained counsel.
- **Crime-lab / drug assessment fee:** apply only to a **controlled-substance
  conviction** count. If the drug count was amended away to a non-drug charge,
  there is no lab fee even if a worksheet still lists one. If the judge reminded
  the clerk of the lab assessment on a CS conviction, it **is** due even if the
  worksheet omitted it.
- **Mandatory court costs** apply to a disposed case; a waived fine is 0.

## Held / pending / deferred / continued matters

If no final order was signed (matter continued, deferred, plea paperwork
incomplete, status issue raised), then: do **not** post financials, do **not**
enter a disposition, use the "hold" / "exclude / no final order" actions and
statuses, set the disposition date to null, set posted amounts to 0, mark
financial posting not allowed, capture the **next-setting date** as the status
check, and **exclude the matter from register/batch totals** (count it separately
as held/excluded).

## Identity & placeholders — never invent

- Do not invent identifiers or contact details. For a form field that is required
  but genuinely absent from all materials (SSN, address, phone, driver-license
  number, probation officer/office), use the **exact placeholder string the
  materials specify** (commonly `TBD from case file`), and — where the template
  has a placeholder list — record the field name and a reason.
- Never borrow a value (e.g., a DOB) from a similarly-named party in search
  results. A genuinely missing DOB becomes the placeholder plus a
  verify-before-permanent-entry flag; the disposition can still post with the
  placeholder if the order was signed.
- When the portal has the correct identity/counsel and a queue/worksheet has a
  wrong one, correct to the portal value.

## Payment plans & installment math

Read the jurisdiction's **payment policy** row for: monthly min/max band,
down-payment requirement, account fee, `first_due_days`,
`return_to_court_offset_days`, and restitution priority.

- **`total_due` = fines-and-costs balance + restitution balance + any
  policy-supported account fee.** Restitution **is** part of the balance the plan
  pays off. If the policy's account fee is 0 (or the noted fee isn't current
  policy), the applied account-fee amount is **0** and `total_due` excludes it.
- **Approved monthly amount:** approve the requested amount when it is inside the
  policy min/max band **and** affordable from disposable income
  (`income − obligations`). Classify support accordingly (supportable /
  below-minimum / above-maximum / unsupported-by-budget). A plan being set up
  means the petitioner is not "exempt / no payment."
- **Installment breakdown** (see `references/installment_math.md` for a worked,
  value-free template):
  - `full_installments = floor(total_due / monthly)`
  - `remainder = total_due − full_installments × monthly`
  - if `remainder > 0`, there is one extra **final installment** equal to the
    remainder; `total_installments = full_installments + 1` and
    `final_payment_amount = remainder`. If it divides evenly, the final payment
    equals the regular installment and there is no extra one.
- **Payment application order:** if restitution > 0 and policy is
  restitution-first → restitution-before-fines/costs; if there is no restitution
  → fines/costs-only.

## Dates (these patterns are consistent)

- `first_due_date` = **submission/order date + policy `first_due_days`**.
- Installments fall monthly on that same day-of-month.
- `final_due_date` = `first_due_date` + (`total_installments` − 1) months.
- `return_to_court_date` = `final_due_date` + policy `return_to_court_offset_days`
  (a **day** offset, not months).
- A **return-to-court trigger** for a current (non-default) first installment
  order is nonpayment, not a scheduled default review.

## License suspension & probation referral (field-packet forms)

- **License suspension start = the conviction date.** A release-from-confinement
  date is memo context only and does **not** replace the conviction date for the
  suspension consequence. `suspension_end_date = start + suspension_months`. Basis
  is the conviction type (e.g., DUI conviction).
- **Probation referral:** prepare it only if supervised probation was actually
  ordered by a signed referral form. If no referral order was signed, mark it
  not-ordered, term 0, and no report datetime — even if a portal field still
  carries a scheduled report time.
- **Form identity/labels:** use the portal form's `form_id`. For a free-string
  form-label field, use the portal form's **`label`** value (the short official
  label), *not* the long descriptive form name. When the template restricts the
  label to enum/allowed values, use those verbatim. When a "labels used" list is
  requested, include all of the form's structural labels.

## Output discipline

- Emit exactly the required top-level keys and item shapes; use enum values
  **verbatim** (never paraphrase into prose).
- Currency: numbers to two decimals. Dates: ISO `YYYY-MM-DD`. Datetimes: ISO
  local `YYYY-MM-DDTHH:MM:SS`. Times: `HH:MM`.
- Apply the template's sort orders (usually by case/citation/petition identifier
  ascending; sub-lists such as missing-fields or excluded-items alphabetically).
- **Totals sum only the posted/disposed matters.** Held/excluded matters
  contribute 0 to money totals and are counted in the separate held/excluded
  count. Re-derive each total from your per-matter numbers and confirm the
  grand total equals the sum of per-matter totals.

## Pre-submission checklist

- [ ] Every top-level key from the template is present; every enum value is one
      of the allowed values.
- [ ] Identity/counsel/status come from the authoritative record; courtroom facts
      (plea, outcome, sentence, amendments, order-signed) come from the notes.
- [ ] Fee amounts use the schedule row effective on the disposition date; no
      unsupported fees added; PD-user fee only for public defenders; lab fee only
      for a CS conviction that wasn't amended away.
- [ ] Held/continued/unsigned matters: no disposition, no financials, disposition
      date null, excluded from totals, next-setting captured.
- [ ] Missing required identifiers use the exact placeholder string; nothing
      invented or borrowed.
- [ ] `total_due` includes restitution; account fee = policy-supported amount
      (often 0); installment/remainder split and all four derived dates recomputed.
- [ ] Currency 2dp, ISO dates/datetimes, arrays sorted, totals equal the sum of
      per-matter amounts.
