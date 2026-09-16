# Reconciliation Rules

## Table of Contents
1. Resolution Hierarchy
2. Audit Finding Construction
3. Identity and Counsel Verification
4. Fee Schedule Reconciliation
5. Payment Plan Math
6. Probation Referrals (CC-1375)
7. License Suspension Orders (CC-1379)
8. Excluded Charges and Financial Items
9. Placeholder Handling
10. Register Total Computation
11. Enum Reference

---

## 1. Resolution Hierarchy

When a conflict exists between sources, resolve using this priority order (highest first):

| Priority | Source | Enum Value | When to Use |
|---|---|---|---|
| 1 | Portal CMS | `use_cms` | Identity (DOB, name spelling) verified from `/api/cases` |
| 2 | Hearing notes | `use_hearing_notes` | Courtroom outcomes, plea, sentence, judge statements |
| 3 | Corroborating memo | `use_corrob_memo` | Defense cover memo confirming counsel type |
| 4 | Fee schedule | `use_fee_schedule` | Current fee amounts from `/api/fee-schedules` |
| 5 | Hold unsigned | `hold_unsigned_order` | No signed order exists; do not post |
| 6 | Verify before entry | `verify_before_entry` | Missing DOB or other critical identity field |

---

## 2. Audit Finding Construction

Every discrepancy between local materials and portal records becomes an audit finding. Each finding requires:

- `case_number` — the affected case
- `issue_type` — one of: identity, counsel, status, fee_schedule, departure
- `conflicted_value` — what the local/finance source says
- `corrected_value` — what the authoritative source says (use enum where applicable)
- `resolution_source` — which source produced the correction

Sort audit findings by case_number, then issue_type.

### Common patterns

**Identity mismatch:** Finance queue has wrong name spelling or DOB. CMS portal `/api/cases` is authoritative. Resolution = `use_cms`.

**Counsel mismatch:** Finance/worksheet says PD but defense memo says appointed private. Hearing notes or corroborating memo wins over worksheet label. Resolution = `use_corrob_memo`.

**Fee schedule mismatch:** Old assessment/fine amount in queue. Portal `/api/fee-schedules` with current effective date controls. Resolution = `use_fee_schedule`.

**Status mismatch:** Draft worksheet says disposed but no signed order. Resolution = `hold_unsigned_order`.

**Departure mismatch:** Legacy charge screen shows a departure that the judge did not order. Hearing notes control. Resolution = `use_hearing_notes`.

---

## 3. Identity and Counsel Verification

### Defendant identity

- The portal CMS (`/api/cases`) is the authoritative source for defendant name (first + last) and DOB.
- When the portal shows a different spelling or DOB than local worksheets, correct to the portal.
- When DOB is genuinely missing from both portal and local materials, use `"TBD from case file"` with `identity_action: "use_placeholder_verify"`.

### Counsel classification

- `public_defender` — Public defender office, PD user fee applies.
- `appointed_private` — Private attorney paid by county, NOT the PD office. PD user fee does NOT apply.
- `retained` — Privately retained by defendant.

The portal's `counsel_type` field is generally correct, but hearing notes and corroborating memos can override it (especially when a calendar abbreviation like "APD" was copied incorrectly).

---

## 4. Fee Schedule Reconciliation

### Basic rules

1. Query `/api/fee-schedules?jurisdiction_code=` for the target jurisdiction.
2. For each fee, check: `effective_date <= disposition_date` AND (`end_date` is null OR `end_date >= disposition_date`).
3. `mandatory: true` fees are always posted for eligible cases.
4. `mandatory: false` fees (like PD user fee) are posted only when the triggering condition is met.

### Fee types

| fee_code | Typical trigger |
|---|---|
| court_cost | All disposed cases (mandatory) |
| fine | As ordered by judge (amount from hearing notes or charges) |
| assessment (drug) | Controlled-substance conviction under Ark. Code 5-64 |
| public_defender_user_fee | Counsel type is `public_defender` |
| county_surcharge | One per traffic citation (OR) |
| standard_fine | Traffic violation by speed tier |

### Stale fee handling

- A fee with `end_date` before the disposition date is stale.
- The stale fee is an audit finding; use the current fee for financial posting.
- Example: 2023 drug assessment of $125 vs. 2025 assessment of $250 → audit finding for fee_schedule, post $250.

### Fee posting decisions

- `fee_status: "post"` — case is disposed with signed order; post all applicable fees.
- `fee_status: "hold"` or `"do_not_post_pending"` — case lacks signed order; post nothing (all amounts 0.00).

---

## 5. Payment Plan Math

### Installment calculation

Given: total_due, monthly_payment, first_due_date

1. `full_installment_count = floor(total_due / monthly_payment)`
2. `final_payment_amount = total_due - (full_installment_count * monthly_payment)`
   - If final_payment_amount == 0: `total_installments = full_installment_count`, no final payment row needed
   - If final_payment_amount > 0: `total_installments = full_installment_count + 1`
3. `final_due_date = first_due_date + (total_installments - 1) months` (same day of month)
4. `return_to_court_date = final_due_date + return_to_court_offset_days` (from payment policy)

### Budget support classification

From the petition budget:
- `monthly_disposable_income = monthly_income - monthly_obligations`
- Compare `selected_installment_amount` to policy band (`min_monthly` to `max_monthly`):
  - Within band AND <= disposable income → `supported_by_budget` / `supportable`
  - Below min_monthly → `below_policy_minimum`
  - Above max_monthly → `above_policy_maximum`
  - Exceeds disposable income → `unsupported_by_budget`

### Payment application order

Determined by the payment policy's `restitution_priority`:
- "Restitution before fines and costs" → `restitution_before_fines_costs`
- "Restitution before discretionary fines" → same
- "Not applicable" or no restitution → `fines_costs_only`
- When restitution_balance > 0 AND policy says restitution first, use `restitution_before_fines_costs`

### Account fee treatment

- If payment policy has `account_fee: 0.00` → `excluded_by_policy`, amount 0.00
- If policy has `account_fee > 0` → check notes for conditions; may be `included_by_policy` or `verify_before_entry`
- The local balance reported by the counter may include an account fee row — always cross-check against the portal policy.

---

## 6. Probation Referrals (CC-1375)

CC-1375 is the "Notice of Referral to Probation Officer" form.

### When to prepare

- `cc1375_status: "prepare_referral"` when supervised probation was ordered (probation_term_months > 0) and a report_datetime is known.
- `cc1375_status: "not_ordered"` when no supervised probation was ordered or no referral was signed.

### Field rules

- `conviction_date` — from sentencing/portal records.
- `probation_term_months` — from sentencing order.
- `report_datetime` — from sentencing intake or petition summary. Use null if not ordered.
- `probation_officer` — `"TBD from case file"` when not available.
- `probation_office_location` — `"TBD from case file"` when not available.
- Do NOT invent officer names or office locations.

---

## 7. License Suspension Orders (CC-1379)

CC-1379 is the "License Suspension and Installment Payment Order" form.

### License suspension

- `license_start_basis: "conviction_date"` — suspension runs from conviction date (default for DUI).
- `suspension_start_date` = conviction_date.
- `suspension_end_date` = suspension_start_date + suspension_months (same day of month).
- `driver_license_number` — `"TBD from case file"` when not available. Do NOT invent.

### Installment payment order

- `agreement_type` — `initial_installment` for first petition, `deferred_payment` for deferred, `subsequent_review` for second+ petitions.
- Use the policy `first_due_days` to compute `first_due_date` from the submission or petition date when not explicitly stated.
- `return_to_court_date` = `final_due_date + return_to_court_offset_days`.
- `return_to_court_trigger` — `nonpayment` (typical) or `default_review` or `none`.

---

## 8. Excluded Charges and Financial Items

### Charges that are excluded by default

Do NOT include these unless the portal policy or an explicit court order supports them:

- `account_management_fee` — exclude when policy account_fee is 0
- `collection_fee` — exclude unless case is in collections
- `dmv_fee` / `dmv_reinstatement_fee` — exclude unless DMV action ordered
- `late_payment_fee` / `late_fee` — exclude unless payment is past due
- `returned_check_fee` — exclude unless returned payment occurred
- `traffic_school_fee` — exclude unless traffic school ordered
- `restitution` — exclude when restitution_balance is 0 or no restitution order exists
- `court_appointed_attorney_fee` — exclude unless specifically ordered
- `court_reporter_fee` — exclude unless specifically ordered
- `statutory_maximum_substitution` — exclude; use current fee schedule amount
- `stale_*` fees (e.g., `stale_2022_standard_fine`) — exclude; current schedule controls

### Reason codes for exclusion

| Reason code | When to use |
|---|---|
| `stale_schedule` | Fee from an expired schedule |
| `unsupported_post_disposition` | Not supported after disposition |
| `not_in_hearing_order` | Not mentioned in hearing outcome |
| `not_current_policy` | Not in current payment policy |
| `no_triggering_event` | No event that triggers this fee (no default, no collection referral, etc.) |
| `no_order_or_policy_support` | No court order or policy basis |
| `not_part_of_balance` | Not part of the current balance |

---

## 9. Placeholder Handling

### When to use "TBD from case file"

Use this exact string for fields that are required by a form but genuinely absent from all available sources (local payloads + portal). Common examples:

- SSN
- Driver license number
- Residence/mailing address
- Phone number
- Probation officer name
- Probation office location
- Attorney/judge contact details not in the record

### When NOT to use placeholders

- Do NOT use placeholder for case numbers, defendant names, DOB (when known), conviction dates, fines, or any value that can be verified from the portal or local materials.
- If the portal returns null for a field AND it is not required by the output schema, omit it rather than placeholding.

### Placeholder field structure

Sort placeholder cases by case_number ascending. Sort missing_fields alphabetically within each case.

---

## 10. Register Total Computation

### Rules

1. Only cases with `fee_status: "post"` (or `register_action: "enter_disposition_and_financials"`) contribute to totals.
2. Cases on hold (`hold`, `do_not_post_pending`, `exclude_no_final_order`) contribute zero to totals.
3. `assessed_case_count` / `disposed_case_count` = number of cases posted.
4. `held_case_count` / `excluded_pending_count` = number of cases not posted.
5. Sum each fee category across posted cases only.
6. `grand_total` / `batch_total_due` = sum of all fee category totals for posted cases.

---

## 11. Enum Reference

### Common enums across task types

**issue_type:** identity, counsel, status, fee_schedule, departure

**resolution_source:** use_cms, use_hearing_notes, use_corrob_memo, use_fee_schedule, hold_unsigned_order, verify_before_entry

**counsel_type / counsel_classification:** retained, public_defender, appointed_private

**case_status:** disposed, deferred, pending, continued

**plea:** guilty, no_contest (or no contest), not_guilty, not_entered, not_applicable, no_plea_recorded

**charge_disposition:** guilty, nolle_prosequi, deferred, pending, dismissed

**departure_status:** no_departure, durational_departure, dispositional_departure, not_applicable, none, not_evaluated_misdemeanor, not_entered_pending

**fee_status:** post, exclude, hold, do_not_post_pending

**docket_entry_type:** sentencing_order, disposition_hold

**register_action:** enter_disposition_and_financials, exclude_no_final_order

**docket_code:** SENTENCING_ORDER_ENTERED, CONTINUED_NO_DISPOSITION

**petition_classification:** initial_installment, subsequent_review, deferred_payment, exempt_no_payment

**support_classification:** supported_by_budget, unsupported_by_budget, needs_judge_review, supportable, below_policy_minimum, above_policy_maximum

**payment_application_order:** fines_costs_only, restitution_before_fines_costs, fines_costs_before_restitution

**account_fee_treatment:** excluded_by_policy, included_by_policy, verify_before_entry

**schedule_interval:** monthly, deferred_single_due

**license_start_basis:** conviction_date, release_date, petition_date

**cc1375_status:** prepare_referral, not_ordered
