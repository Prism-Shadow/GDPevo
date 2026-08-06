# Reconciliation rules & trap catalog

The local materials are deliberately noisy. Below is the source-of-truth order and
the recurring traps. For every field, ask "which source is authoritative for *this*
kind of fact?" and record conflicts in the audit section with the template's enum.

## Source precedence, by fact type

| Fact | Authoritative source | Notes |
| --- | --- | --- |
| Defendant name, DOB | `/api/cases` / `/api/citations` record for the exact ID | If DOB is `null`, use the placeholder + verify action. Never borrow from search. |
| Counsel type | `/api/cases.counsel_type`, reconciled with on-record note/memo | Raw labels (`APD`, `PD C. Hill`, `APPT PRIVATE`) are unreliable; the note's clarification governs. |
| Plea / finding / counts | Signed order or hearing note for the hearing date | Overrides a stale CMS charge screen or draft worksheet. |
| Fine / jail / probation | Signed order / hearing note | Draft "fine 1000" lines that were never signed do not post. |
| Departure | On-the-record statement | "top of range, no departure finding" ⇒ none, despite a CMS `departure_type`. |
| Fee amounts | Current `/api/fee-schedules` row (`end_date == null`) | Correct any worksheet amount that matches a stale (past `end_date`) row. |
| Installment band / dates | `/api/payment-policies` | `first_due_days`, `return_to_court_offset_days`, `min/max_monthly`, `account_fee`. |
| Balances / budget | `/api/financial-petitions` + petition payload | Exclude counter "account fee" rows unless policy `account_fee > 0`. |
| Form label / placeholder rule | `/api/forms` row | Also gives account-reference rule for traffic plans. |

## Common traps (each seen across the training set)

1. **Stale fee amount.** Worksheet carries a prior-year assessment/fine amount.
   The current fee schedule has a newer row (old row has a past `end_date`). Post
   the current amount; flag `fee_schedule` / `stale_schedule`.
2. **Omitted mandatory/discretionary fee.** Worksheet omits a fee that the current
   schedule or the judge's on-record statement requires (e.g. a lab assessment the
   judge called out, or a public-defender user fee). Add it if its trigger holds.
3. **Discretionary fee applied to the wrong counsel type.** A public-defender user
   fee must NOT post when counsel is `appointed_private` or `retained`.
4. **`APD` ≠ public defender.** "Appointed private counsel, county pay" is
   `appointed_private`. Classify accordingly and suppress the PD user fee.
5. **Amended / dismissed count still on the CMS screen.** The filed count was
   amended (e.g. drug count → misdemeanor theft) or nolle-prosequi'd. Convict on
   the amended count; drop any assessment tied only to the original count; count it
   in the "dismissed/amended-away" tally.
6. **Phantom departure.** A draft worksheet or CMS row shows a departure the judge
   expressly declined. Enter no departure.
7. **Identity typo vs CMS.** Name/DOB in the queue differs from CMS by a letter or
   a day. CMS wins; record an `identity` finding.
8. **DOB genuinely missing.** CMS `defendant_dob` is `null` and the bench card was
   blank. Use the required placeholder + "verify" action. Do NOT borrow a DOB from
   a similarly named `/api/search` hit — that is an explicit trap.
9. **Unsigned / continued order.** Draft disposition exists but no final order was
   signed (matter deferred/continued). Hold: no financial posting, pending/hold
   status, hold docket code, add to exclusions with the next status-check date and
   `financial_posting_allowed = false`.
10. **Sticky-note fees.** Intake asks "add late / collection / DMV / returned-check
    / account-management / traffic-school fee?" with no triggering event. Exclude
    all of them; reason = no triggering event / not in the order.
11. **Obsolete form footer.** An old form copy references a service charge the
    current revision dropped. Follow current policy; do not add it.
12. **Statutory-maximum substitution.** A "up to $X" note is not the standard fine;
    use the current standard-fine schedule row, and exclude the substitution.
13. **Release date ≠ conviction date.** For license suspension, the suspension runs
    from the conviction date; a release-from-confinement date is memo context only.
14. **Account fee by policy only.** Include an account/maintenance fee solely when
    the jurisdiction's payment policy sets `account_fee > 0`; otherwise exclude the
    counter's fee row.
15. **Restitution priority.** When a restitution balance exists, include it in the
    total and set the payment-application order from the policy's
    `restitution_priority`; with zero restitution, order is fines/costs only.

## Deciding "post vs exclude vs hold"

- **Post** a case/fee when there is a signed disposition AND the amount is
  supported by the current schedule or the order.
- **Exclude** an individual fee/item that lacks schedule or order support (record
  it with a reason enum).
- **Hold** an entire matter when no final order was entered — keep it out of the
  disposed register and financial totals entirely.
