# Reconciliation playbook — by task type

Three task shapes recur. All follow the same method (read template → gather →
apply authority hierarchy → compute → conform to template). The template names
and enums vary per task; copy them from the current `answer_template.json`.

Illustrative values below are placeholders (`F`, `C`, `M`, `B`) — never hardcode
amounts; look them up live from the portal for the actual jurisdiction and date.

---

## Type A — Criminal sentencing / disposition register
(Answer sections resemble: audit findings, case dispositions, fee
reconciliation, docket entries, register/batch totals, exclusions.)

Per target case:
1. Pull `/api/cases`, `/api/charges`, `/api/docket-entries` (search by
   case_number). Note `status` and the `disposition` docket entry's recorded
   status.
2. **Identity**: correct name spelling + DOB from CMS (memo corroborates). Flag
   the local queue's wrong spelling/DOB as an identity audit finding resolved to
   CMS.
3. **Counsel**: use CMS `counsel_type`. A calendar/queue abbreviation ("APD",
   "PD") that conflicts with the judge's on-record clarification / memo is a
   counsel audit finding — the label is not the classification. Appointed-private
   (county pay) is **not** public-defender-fee eligible.
4. **Status / hold**: if CMS status is `deferred`/`pending`/`continued` or the
   order was not signed → hold. No disposition, no fee entry; docket action =
   the "no final order / continued" code; put it in exclusions with
   `financial_posting_allowed = false`; keep it out of totals.
5. **Charge summary**: plea, charge disposition, sentence terms, and **departure**
   from the signed record. If the charge screen shows a departure but the judge
   called it "top of range, not a departure", the departure status is
   none/no_departure (resolution = use_hearing_notes). If the screen shows
   `nolle prosequi` but guilt was adjudicated, the disposition is guilty.
6. **Fees** (only if disposed): court_cost (current schedule) + pronounced fine +
   assessment (only if the conviction triggers it, at the current amount) +
   public_defender_user_fee (only if counsel_type == public_defender and not
   waived). Rebuild the finance queue's totals from current-schedule amounts;
   drop omitted-but-required fees back in and stale amounts out.
7. Docket entry = sentencing-order-entered (disposed) or the hold/continued code.
8. Totals: count disposed vs held; sum each posted fee category and the grand
   total across disposed cases only.

Common audit `issue_type`s: identity, counsel, status, fee_schedule, departure.

---

## Type B — Traffic-violation payment-plan closeout
(Answer sections resemble: matters[disposition, financial_entry, payment_plan,
form_entry], excluded_charges, batch_totals.)

Per citation:
1. Verify the citation via `/api/citations` (plea, disposition, speed/zone,
   `violation_code`, plan_approved, first_due_date).
2. **Speed tier**: from `speed_mph` vs `zone_mph` (e.g. 100+ mph, 31–40 over,
   21–30 over) → map to `violation_code`; confirm against the citation record.
3. **Financial entry**: `standard_fine` = current `standard_fine` fee for
   jurisdiction + violation_code, effective on the disposition date (ignore the
   old ended tier and any "statutory maximum up to $X" note). `county_surcharge`
   = current surcharge fee. `amount_due = standard_fine + county_surcharge`.
   `unsupported_charge_total_included = 0` unless a stale/unsupported amount was
   actually in the starting balance (then report it).
4. **Payment plan**: use §7 math with the approved monthly `M` and approved
   first-due date from the minute note; validate `M` against
   `/api/payment-policies` band. `agreement_sequence` = post_disposition when the
   plan was approved after the disposition entry.
5. **Form entry**: form_id/label from `/api/forms`; if no separate case/account
   number, `account_reference` = citation number; `required_labels_used` = the
   labeled sections present in the local form excerpt.
6. **Excluded charges**: every sticky-note fee with no triggering hearing minute
   (late, collection, DMV, returned-check, account-management, traffic-school),
   plus stale-schedule amounts and statutory-maximum substitutions — each with
   its reason code (`no_triggering_event`, `stale_schedule`, `not_current_policy`,
   `unsupported_post_disposition`, `not_in_hearing_order`).
7. Batch totals: matter_count, combined_amount_due, unsupported_charge_total.

---

## Type C — Post-sentencing financial & supervision packet (VA / Gloucester)
(Answer sections resemble: case memo, CC-1375 probation referral, CC-1379
license + installment order, budget review / support, petitions, placeholders,
excluded financial items.)

Per matter:
1. **Sentence facts** from the sentencing/probation intake: conviction date,
   offense/statute, jail imposed/suspended, fine, court costs, supervised
   probation months, license suspension months. Release-from-confinement date is
   memo context only — it does **not** replace the conviction date for the
   license suspension basis.
2. **Balances**: fines_and_costs and restitution from the petition/counter,
   reconciled with `/api/financial-petitions`. Court costs at the current
   `/api/fee-schedules` amount.
3. **Budget & support** (§8): disposable = income − obligations; classify against
   the policy band and disposable income; set the support enum from the template.
4. **Account fee**: include only if `policy.account_fee > 0` and permitted; a
   counter "account-maintenance" row against a `0` policy fee (or public
   assistance) ⇒ excluded_by_policy.
5. **Payment application order**: restitution first if policy says so and
   restitution > 0 (or requested and allowed); else fines_costs_only.
6. **Installment schedule** (§7): interval, first_due_date, regular amount,
   total_installments, final amount/date, return_to_court_date.
7. **CC-1375**: prepare_referral only if supervised probation ordered and a
   referral signed (report_datetime from intake); else not_ordered /
   report_datetime null.
8. **CC-1379**: license_start_basis = conviction_date (default);
   suspension_start_date = conviction_date; suspension_end = start + months;
   driver_license_number = placeholder if unknown.
9. **Placeholders**: for each missing identifier/contact (SSN, DL number,
   addresses, phone, probation-office details) use the exact placeholder string
   with the template's reason code; sort per template.
10. **Excluded financial items**: restitution (if unordered), account-management,
    late, DMV reinstatement, court-appointed-attorney, court-reporter fees — each
    with its reason code.

---

## Cross-cutting reminders
- The template's enum for "when unsure" (`verify_before_entry`,
  `needs_judge_review`, `not_evaluated_*`, `not_entered_pending`) beats a guess.
- Placeholder value is the exact string the materials require (usually
  `"TBD from case file"`) — never a blank, `null`, or invented value unless the
  template says so.
- Recompute all totals from the per-matter posted amounts as a final check.
