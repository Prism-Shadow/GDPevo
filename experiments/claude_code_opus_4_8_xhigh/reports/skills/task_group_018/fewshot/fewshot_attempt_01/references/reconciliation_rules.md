# Reconciliation & computation rules

These rules are the generalizable "clerk judgment" behind every task in this
family. They describe *how* to decide values, not the values themselves — always
recompute from the current task's payloads + portal.

## 1. Source-of-authority hierarchy

Different sources are authoritative for different fields. When they conflict,
resolve in favour of the source that actually governs that field:

| Field kind | Authoritative source | Notes |
|---|---|---|
| Defendant identity (name, DOB) | Portal **CMS** (`/api/cases`, `/api/citations`), confirmable via `/api/search?q=<name>` | Finance-queue/worksheet spellings and DOBs are frequently wrong carry-forwards. |
| Counsel classification (retained / public_defender / appointed_private) | Corroborating **memo / defense cover note** when it clarifies a raw label; portal `counsel_type` confirms | A raw `attorney_label_raw`/calendar abbreviation like "PD" or "APD" can mean appointed-private county-pay — the memo/on-record clarification controls. |
| Offense code, statute, severity, count structure | Portal **`/api/charges`** | |
| Numeric sentence (jail days/months imposed & suspended, fine, probation months, license months) | Portal **`/api/charges`** / order / petition | |
| Plea | Portal charge/citation `plea` | |
| **What happened in open court** — plea accepted & guilt adjudicated, count amendment (which count is the conviction), departure pronounced *or expressly rejected*, whether a final/signed order exists | **Hearing notes / minute order** | Open-court reality overrides a stale CMS field: a legacy "departure" the judge rejected → `no_departure`; a charge `disposition` of "nolle prosequi"/draft that the court adjudicated guilty → guilty; a "disposed" status with no signed order → held. |
| Current money amounts (court cost, assessments, surcharge, user fee, standard fine) | Portal **`/api/fee-schedules`**, current-window row | Never the stale/archived amount carried in a worksheet. |
| Installment policy (bands, offsets, restitution priority, account fee) | Portal **`/api/payment-policies`** | |
| Form id / label / placeholder wording | Portal **`/api/forms`** | |
| Balances, budget, petition sequence, default status | Portal **`/api/financial-petitions`** (and/or petition payload) | |

**Draft / stale / carry-forward / "old worksheet" / finance-queue / archived
values are never authoritative** — treat them as candidates to verify and
replace with the authoritative value.

When the schema records a `resolution_source` / `recommended_resolution` per
finding, name the source that actually settled *that* conflict (identity → CMS;
counsel label → corroborating memo; departure/finding/signature → hearing notes;
amount → fee schedule; unsigned/deferred → hold/verify).

## 2. Hold / exclude a matter with no signed final order

If a target is deferred, continued, pending, or the order "was not signed":
- Do **not** post financials or a sentencing disposition.
- Set its status/action to the schema's held/excluded/pending enum, financial
  totals to 0, `disposition_date`/entry_date to `null` where the schema allows.
- Exclude it from disposed/assessed counts; count it under held/excluded.
- Record the next status-check/setting date if the materials give one.
- Its charge disposition is pending / not entered, departure not evaluated.

## 3. Fee reconciliation

1. Resolve the `jurisdiction_code`, then pull current fee-schedule rows for it
   whose window covers the disposition/event date (see portal_api.md §fee-schedules).
2. **Include** mandatory rows: court cost / filing fee; county surcharge (once
   per citation); a mandatory assessment **only when its trigger applies** (e.g.
   a drug/crime-lab assessment only on the qualifying controlled-substance
   conviction count — check the charge's `assessment_code`).
3. **Include conditional rows only when the condition holds**: a public-defender
   user fee only when counsel is `public_defender` (not appointed-private or
   retained); a charge-specific assessment only when that charge is the actual
   conviction count.
4. **Include a fine only if actually imposed** by the order/charge
   (`fine_amount` > 0) — not a draft/waived fine.
5. **Exclude everything not supported by an order or the current schedule**, e.g.
   account-management/maintenance, collection/referral, late-payment,
   DMV/reinstatement, returned-check, copy/certification, traffic-school,
   restitution (unless ordered), statutory-maximum substitutions, archived/
   "noise"/stale local fees. When the schema itemizes exclusions, list each with
   the schema's `reason_code` (stale schedule, no triggering event, not in
   hearing order, not current policy, unsupported post-disposition, etc.).
6. Case total = sum of included items. Register/batch totals = per-category sums
   and counts over **posted** matters only (held matters contribute 0 and count
   as held/excluded).

## 4. Installment / payment-plan math

Use `scripts/installments.py` to avoid arithmetic and calendar mistakes.

- **Amount to schedule** = total balance due (fines/costs + restitution as the
  policy applies) minus any down payment. Account fee included only if the
  current policy's `account_fee` > 0 (else amount 0, treatment excluded_by_policy).
- **Regular installment** = the approved/requested monthly amount. Validate it:
  - Against the policy band: `min_monthly <= amount <= max_monthly`
    → below → below_policy_minimum; above → above_policy_maximum.
  - Against budget: `monthly_disposable = income_monthly - obligations_monthly`
    must cover the installment → else unsupported_by_budget. Otherwise
    supportable / supported_by_budget.
- **Breakdown**: `full = floor(total / monthly)`, `remainder = total - full*monthly`.
  If remainder > 0: `total_installments = full + 1`, `final_payment_amount =
  remainder`, `full_installment_count = full`. If remainder == 0: no smaller
  final payment (`total_installments = full`, final payment = a regular one).
- **first_due_date**: use the explicitly approved/ordered/candidate date from the
  materials when given; otherwise `anchor_date + policy.first_due_days`
  (anchor = submitted/disposition date). Follow any policy note (e.g. "15th of
  next month").
- **final_due_date** = first_due advanced by `(total_installments - 1)` intervals.
- **return_to_court_date** = final_due + `policy.return_to_court_offset_days`
  (only when the schema has this field). Trigger per policy (nonpayment / default
  review). Some schemas (traffic EPP) omit return-to-court entirely.
- **payment_application_order**: if restitution > 0 and the policy prioritizes
  restitution → restitution_before_fines_costs; if restitution == 0 →
  fines_costs_only; else per policy.

## 5. Traffic fine tiers

Read the citation's `violation_code` (authoritative), then select the current
`standard_fine` fee-schedule row with the matching `violation_code` for the
jurisdiction. Add the mandatory county surcharge once. `amount_due = standard
fine + surcharge`. Do not substitute a statutory-maximum note or a stale
(end-dated) tier for the current SOF/standard fine.

## 6. License suspension (e.g. VA CC-1379)

Status suspended when the conviction carries one. `start_basis` is the
**conviction date** (not the release-from-confinement date) unless the schema
says otherwise; `months` from the order/charge/petition; `end_date = start +
months`. `basis` = dui_conviction for a DUI, else other. Driver license number
is a placeholder if unknown.

## 7. Probation referral (e.g. VA CC-1375)

Prepare the referral only when supervised probation was actually ordered/signed:
status prepare_referral, use conviction date, probation term months, and report
datetime from the order/petition. If no referral order was signed → not_ordered,
term 0, report datetime null.

## 8. Placeholders — never invent

For a form-required field that cannot be filled from any authoritative source
(SSN, address, phone, driver license number, probation officer/office contact,
account number), use the **exact placeholder string the materials specify**
(commonly `TBD from case file`). List such fields where the schema asks
(placeholder_fields / placeholder_cases / missing_fields), sorted as directed,
each with the correct reason code. Do not fabricate identifiers, contacts,
amounts, or conditions.
