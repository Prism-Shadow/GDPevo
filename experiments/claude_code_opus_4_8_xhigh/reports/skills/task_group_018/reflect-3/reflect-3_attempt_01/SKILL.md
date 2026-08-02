---
name: court-closeout-reconciliation
description: >-
  Prepare a court clerk closeout / field packet by reconciling local draft
  documents (finance-queue extracts, worksheets, hearing/closeout notes, intake
  sheets, petitions, form excerpts) against an authoritative Court Operations
  Portal, then emit ONE strict JSON object that matches a provided
  answer_template.json. Use for criminal sentencing closeouts, traffic-violation
  dispositions with payment plans, and financial/installment-petition packets
  (probation-referral, license-suspension, installment-order forms). Trigger
  whenever the inputs pair local "draft/carry-forward/queued" values with a
  portal/CMS plus an answer_template that lists required keys, enums, ordering
  rules, and currency/date formats.
---

# Court closeout reconciliation

You are a deputy/finance clerk producing a closeout package. The inputs always
have the same shape and the same trap: **local documents carry stale, draft, or
mis-labeled values, and your job is to reconcile them against the authoritative
court records and the current fee/policy schedules, then write one strict JSON
answer.** The score is decided by getting the reconciled *decisions* right and by
matching the answer template exactly — not by prose.

## Method (do these in order)

1. **Read the answer_template first, completely.** It is the contract. Note every
   `required_top_level_keys`, every enum list, the `ordering_rules`, and the
   currency/date/datetime formats. Your output must use enum values *verbatim*
   (never substitute prose), numbers to two decimals, ISO dates `YYYY-MM-DD` and
   ISO local datetimes `YYYY-MM-DDTHH:MM:SS`, and each list sorted exactly as the
   template's ordering rule says.

2. **Inventory the inputs.** Separate them into (a) *local/draft* material
   (finance queue, clerk worksheet/CSV, hearing or closeout notes, intake sheet,
   petition summary, form excerpts) and (b) the *authoritative portal* the task
   points you at (cases, charges, docket-entries, citations, fee-schedules,
   payment-policies, forms, financial-petitions, and a search facility). Treat
   the portal as the system of record; treat local material as claims to verify.

3. **Pull the portal record for every target matter.** For each case/citation/
   petition id, retrieve its authoritative row and its associated charges,
   docket entries, current fee schedule, payment policy, and form metadata for
   that jurisdiction. Use the search facility when a direct list does not key on
   the id. The docket disposition line ("recorded with status …", "matter
   continued; no final order signed") is the ground truth for case status.

4. **Reconcile each field with the authority hierarchy** (next section), compute
   any money/date math, and drop anything unsupported.

5. **Assemble, sort, and validate** against the template before finishing. Verify
   every enum value is spelled exactly as listed, every list is sorted, item
   *sets* are neither over- nor under-populated, and totals equal the sum of the
   per-item values you actually posted.

See `references/field_playbook.md` for a field-by-field playbook and
`references/payment_math.md` + `scripts/installments.py` for the installment math.

## Authority hierarchy — who wins a conflict

- **Identity (name, DOB), counsel classification, and case status → the portal/CMS.**
  A queued/worksheet DOB, name spelling, or counsel label that disagrees with the
  portal is corrected to the portal value. A label like `APD`/`PD` on a calendar
  or worksheet does **not** determine counsel type — use the portal's
  `counsel_type` (and the on-record clarification), e.g. "appointed private,
  county pay" is `appointed_private`, not public defender.

- **What happened in the courtroom (plea, adjudication/conviction, sentence terms,
  departures, and whether a final order was signed) → the hearing/closeout notes
  and the docket.** These override a stale structured value in the portal charge
  record. Example: if the bench adjudicated guilt and imposed jail + an
  assessment, that is a conviction even if a charge row still reads
  "nolle prosequi"; if the notes say no referral/order was signed, the
  corresponding datetime/term is empty even if a portal field still carries a
  tentative value.

- **Fee and fine AMOUNTS → the schedule effective on the disposition date.**
  Ignore archived/stale amounts (any schedule row with an `end_date` in the past),
  "old worksheet" amounts, and "statutory maximum" notes. Use the current
  standard/scheduled amount.

When you record a reconciled conflict, pick the `resolution_source` enum that
matches which authority resolved it (portal/CMS, hearing notes, corroborating
memo, current fee schedule, or "hold because the order is unsigned").

## Fees — post only what is supported

- Post a fee only if the current schedule, a policy, or a signed order supports it.
  **Never add** account-management, collection, late-payment, DMV/reinstatement,
  returned-check, restitution, copy/certification, traffic-school,
  court-appointed-attorney, or court-reporter charges unless a portal record /
  current schedule / policy / order directly calls for it. Sticky-note or
  "do-not-add" reminders are exclusions, not charges.
- A public-defender **user fee** applies only when counsel is `public_defender`
  (not `appointed_private`, not `retained`), and only if not waived.
- Mandatory assessments attach to their trigger: a controlled-substance / drug
  conviction triggers the jurisdiction's current drug-assessment or crime-lab fee;
  a charge that was amended away to a non-drug offense does **not**.
- Traffic: add the county surcharge once per citation; use the current standard
  fine for the tier.
- The register/batch totals are sums over the matters you actually posted;
  held/excluded matters contribute zero.

## Departures, status, and holds

- Record a sentencing **departure** only when the judge expressly made a departure
  finding. "Top of the range", "plea agreement cap", or an empty departure reason
  is **not** a departure. For misdemeanors, use the template's
  "not evaluated / not applicable" departure value; for a pending matter, the
  "not entered / pending" value.
- If a matter has **no signed final order** (status deferred / continued /
  pending, or the docket says the order was not signed): do not post financials.
  Put it in the hold/exclude bucket, use the hold/exclude enum values, set the
  disposition date to null, and record the next status-check date if the notes
  give one.

## Placeholders — never invent

For a required form field whose value is genuinely absent from all case materials
(SSN, driver-license number, address, phone, probation officer/office contact),
use the **exact** placeholder string the materials specify (commonly
`TBD from case file`). Do not guess, and do not borrow a value from a
similarly-named party or from search results. List each placeholdered field where
the template asks for it, sorted as instructed.

## Money math — payment plans / installment orders

Compute, never eyeball. Anchors come from the **policy** (min/max monthly,
first-due offset, down payment, restitution priority, account-fee flag,
return-to-court offset) and the **balance** to be paid:

- `total_due = fines_costs_balance + restitution_balance` (account fee only if the
  policy flags it; otherwise excluded and 0).
- `full_installments = floor(total_due / monthly)`;
  `remainder = total_due - full_installments * monthly`.
- If `remainder > 0`: there is one extra final installment equal to `remainder`,
  so `total_installments = full_installments + 1` and
  `final_payment_amount = remainder`. If it divides evenly,
  `total_installments = full_installments` and `final_payment_amount = monthly`.
- `first_due_date = submitted/disposition date + policy first-due days` (some
  policies pin it to "the 15th of the next month").
- `final_due_date = first_due_date + (total_installments - 1) months` (same day).
- `return_to_court_date = final_due_date + policy return-to-court offset days`.
- Keep the approved monthly within `[min_monthly, max_monthly]`; classify support
  by comparing it to disposable income (`income - obligations`) and the band.
- **Payment application order:** if restitution > 0 and policy prioritizes it, use
  "restitution before fines/costs"; if restitution is 0, use "fines/costs only".
- License suspension starts on the conviction date (unless a policy/order names
  release or petition date); `end = start + months`.

`scripts/installments.py` implements this; verify your dates with it.

## Output discipline (this is where points are lost)

- Emit exactly the `required_top_level_keys`, nothing more, nothing less.
- Enum fields: copy the allowed value character-for-character.
- Item *sets* must match reality: list every matter/charge/exclusion that belongs
  and **omit ones that do not** — over-listing an exclusion set or a placeholder
  set is scored as wrong as omitting one.
- Two-decimal currency numbers; ISO dates/datetimes; `null` only where allowed.
- Apply every ordering rule (usually sort by case/citation/petition number, and
  sub-lists alphabetically).
- Cross-check: per-case totals = sum of that case's posted line items; batch
  totals = sum over posted cases; counts (assessed vs held/excluded) add up.
