# Financial math: reconciliation, installments, budget, dating

All money is a number rounded to **two decimals**. All dates ISO `YYYY-MM-DD`;
date-times `YYYY-MM-DDTHH:MM:SS`; times `HH:MM`.

## 1. Fee reconciliation (what to post)

- Start from the **supported** lines only: the fine actually imposed, the current
  mandatory court cost (schedule row effective on the disposition date), plus any
  mandatory conviction-linked assessment or PD user fee that the counsel type and
  schedule support.
- Drop every stale/archived amount and every unsupported add-on (see
  `reconciliation-and-fees.md`); each dropped item is reported in the exclusion list.
- `fines_and_costs_total` (or `case_total`) = sum of the supported posted lines. If a
  clerk-stated balance is given, confirm it equals your supported sum; if the portal /
  schedule contradicts it, the supported sum wins.
- Batch/register totals = sums across **posted** matters only, split by the category
  fields the template names (e.g., `fine_total`, `court_cost_total`, `assessment_total`,
  `user_fee_total`, `grand_total`), with separate `assessed`/`held`/`excluded` counts.

## 2. Installment / payment-plan schedule

Inputs: `total_due` (the supported balance to be paid on the plan), the approved/
requested `monthly_amount`, and `first_due_date`. Optional: `down_payment`.

Let `base = total_due − down_payment` (down payment is usually 0 unless the policy or
order sets one).

- **Even division** (`base` is an exact multiple of `monthly_amount`):
  - `total_installments = base / monthly_amount`
  - every installment (including the final) = `monthly_amount`
  - `final_payment_amount = monthly_amount`
- **Uneven division** (there is a remainder):
  - `full_installment_count = floor(base / monthly_amount)` payments of `monthly_amount`
  - `final_payment_amount = base − (full_installment_count × monthly_amount)`  ← the
    smaller remainder payment
  - `total_installments = full_installment_count + 1`
- `first_due_date`: use the date approved/stated in the notes or petition. If none is
  stated, derive it from the policy: disposition date + `first_due_days`.
- `final_due_date = first_due_date + (total_installments − 1) months` (monthly interval;
  adjust for the actual interval enum — monthly/biweekly/weekly).
- Report both `full_installment_count`/`regular_installment_amount` and the
  `final_payment_amount` when the template separates them; when the plan divides evenly,
  the final payment equals the regular installment.

_Worked example (illustrative, not a task answer): base 1260, monthly 75 → floor(1260/75)
= 16 full payments of 75.00 (= 1200.00), remainder 60.00 as a 17th final payment;
total_installments 17._

## 3. Budget / support classification

- `monthly_disposable_income = monthly_income − total_monthly_obligations`.
- Read the policy band: `[min_monthly, max_monthly]` from the jurisdiction's
  payment-policy row.
- Classify the requested/approved monthly against the band and disposable income using
  the template enum, e.g.:
  - within band and ≤ disposable → supportable / `supported_by_budget`;
  - below `min_monthly` → `below_policy_minimum`;
  - above `max_monthly` → `above_policy_maximum`;
  - exceeds disposable income → `unsupported_by_budget` / `needs_judge_review`.
- `policy_band.minimum_monthly` / `maximum_monthly` come straight from the policy row.

## 4. Account fee & payment-application order

- **Account fee:** include only if the jurisdiction policy's `account_fee > 0`; if it is
  0, treat as `excluded_by_policy` regardless of a counter/worksheet row that still
  carries one. If the policy is ambiguous, use `verify_before_entry`.
- **Payment application order:** follow the policy's restitution priority and the
  template enum (`restitution_before_fines_costs`, `fines_costs_before_restitution`,
  `fines_costs_only`). Honor a petitioner's request (e.g., restitution first) **only if
  the policy supports it**. When there is no restitution balance, use `fines_costs_only`.

## 5. Petition classification

- Use the intake sequence + default status: a current first petition (no prior default)
  is an `initial_installment`; a default/subsequent review uses the
  `subsequent_review`/`default_review` enum. A deferred single-due arrangement uses the
  deferred enum. Do not treat a current first petition as a default review.

## 6. License suspension dating

- License suspension **runs from the conviction date**, not the release-from-confinement
  date (a release date is memo context only) — unless the template's
  `license_start_basis` explicitly selects another basis.
- `suspension_end_date = suspension_start_date + suspension_months`.
- Take `suspension_months` from the signed order / sentence (or the worksheet entry the
  packet is built on); if a note carries a different figure, use the one the order/packet
  supports.

## 7. Return-to-court setting

- Set the return-to-court `date`/`time`/`trigger` from the order or policy. If not
  stated, derive the date from the policy `return_to_court_offset_days`. The trigger is
  typically nonpayment/default review; use `none` when no return is set.
