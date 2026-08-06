# Court Operations Closeout Skill

## Purpose

Produce a structured, clerk-ready JSON closeout package for a court docket by reconciling local hearing/audit/petition materials with the Court Operations Portal. The output must follow the answer-template schema exactly—using the specified enums, currency precision, date formats, and sort orders.

## Prerequisites

- **Portal access**: Base URL and allowed endpoints from `environment_access.md`.
- **Local payloads**: Hearing notes, audit memos, clerk worksheets, petition/budget forms, and form excerpts provided with each task.
- **Answer template**: JSON schema defining required keys, field types, enums, ordering, and precision rules.

## Step-by-Step Process

### 1. Read All Inputs

1. Read the prompt to identify: target jurisdiction, docket date, target case/citation numbers, and which local payload files are provided.
2. Read every local payload file completely before touching the portal.
3. Read the answer template to understand the exact output shape, required enums, and ordering rules.

### 2. Query the Portal

Use the portal endpoints to fetch authoritative records for each target identifier:

| Endpoint | When to use |
|---|---|
| `GET /api/jurisdictions` | Confirm jurisdiction code, policy reference |
| `GET /api/cases` | Case status, disposition date, counsel, defendant identity |
| `GET /api/charges` | Offense codes, plea, disposition, fine, jail, probation, departure, assessment codes |
| `GET /api/docket-entries` | Existing docket text and entry types |
| `GET /api/fee-schedules` | Current fee amounts, effective dates, stale amounts (check `end_date`) |
| `GET /api/payment-policies` | Monthly min/max, account fee, first-due-days, return-to-court offset, restitution priority |
| `GET /api/forms` | Form IDs, labels, placeholder instructions, required fields |
| `GET /api/financial-petitions` | Petition sequence, balances, income/obligations, restitution |
| `GET /api/citations` | Traffic citation details, speed, zone, violation code |
| `GET /api/search?q=<id>` | Best way to look up a specific case, citation, or petition |

**Tip**: Use `/api/search?q=<case_number>` to find a specific case and its related docket entries / petitions in one call.

### 3. Reconcile Local Materials Against Portal

For every target case/citation, compare each data point across three sources in this priority order:

| Priority | Source | When it controls |
|---|---|---|
| 1 (highest) | Hearing notes / bench notes | Courtroom facts: plea, finding, sentence, departure, unsigned-order status |
| 2 | Audit memo / corroboration memo | Corrections to identity, counsel type, stale values |
| 3 | Payment petition / budget | Balances, income, obligations, requested payment amounts |
| 4 | Portal (CMS) | Authoritative identity (DOB, name spelling), case status, fee schedule current amounts |
| 5 | Fee schedule (current, non-expired) | Current amounts override stale/archived amounts from finance queue or old worksheets |
| 6 (lowest) | Finance queue / worksheet carry-forward | Default values only if no conflict; these frequently contain stale data |

**Key reconciliation rules**:

- **Identity conflicts**: If CMS has a different DOB or name spelling than the finance queue, use CMS. Record the conflict as an audit finding.
- **Counsel type conflicts**: If the bench notes or a defense memo says "appointed private" but the queue says "PD", use the hearing notes/memo. This affects whether a public-defender user fee applies.
- **Stale fee amounts**: If the finance queue or worksheet uses an older fee amount (check `end_date` on the fee schedule), replace with the current amount from `/api/fee-schedules` that has `effective_date ≤ disposition_date` and `end_date` is null.
- **Departure conflicts**: If the CMS/legacy charge screen carries a departure label but the judge stated on the record "no departure" or "top of the range," use the hearing notes. Record as an audit finding.
- **Status conflicts**: If the worksheet says "disposed" but the docket note says unsigned order / continued, defer to the portal status and the hearing notes. If no final order was signed, the case is deferred or pending — do NOT post financial entries.
- **Amended charges**: If the original charge was amended (e.g., controlled substance → misdemeanor theft), the original count is "dismissed_or_amended_away." Use the hearing notes for the actual convicted count.

### 4. Build Each Output Section

#### Audit Findings / Case Audit
- List every conflict found between sources.
- For each: `case_number`, `issue_type`, `conflicted_value`, `corrected_value`, `resolution_source`.
- Sort by case_number, then issue_type.

#### Dispositions
- Use hearing notes for plea, finding, outcome.
- Use CMS for identity (name, DOB) unless corrected by memo.
- Set `closeout_action` / `entry_status` based on whether the sentencing order was signed.
- For cases with no signed order: status = deferred/pending, action = hold/no closeout, financial = hold.

#### Fee Reconciliation / Fee Entries
- Start from the current fee schedule for the jurisdiction.
- Include: court costs (mandatory), fines (from sentencing), assessments (if `assessment_code` on the charge), public-defender user fee (only if counsel_type = public_defender, NOT appointed_private).
- **Exclude** all of the following unless the hearing order or current policy explicitly includes them:
  - Account-management fees
  - Collection fees
  - Late-payment fees
  - DMV fees
  - Restitution (if no order)
  - Court-appointed-attorney fees
  - Court-reporter fees
  - Copy/certification fees
  - Crime-lab fees on non-conviction/amended-away counts
- Use fee schedule amounts effective on the disposition date; ignore stale/expired amounts.
- For deferred/pending cases: set fee_status = "hold" / "do_not_post_pending", total = 0.00.

#### Payment Plans / Installment Orders
- Use the payment policy from the portal for the jurisdiction.
- **Approved monthly amount**: from hearing minute or petition request, as long as it falls within the policy band `[min_monthly, max_monthly]`.
- **Support classification**:
  - `supportable` / `supported_by_budget`: requested amount is within policy band AND ≤ disposable income.
  - `below_policy_minimum`: disposable income < policy minimum.
  - `above_policy_maximum`: requested amount > policy maximum.
  - `unsupported_by_budget`: for edge cases where budget clearly cannot support.
- **Payment schedule math**:
  - `total_due` = fines + costs + assessments + user_fees + restitution (as applicable per policy).
  - `first_due_date` = petition/submission date + `first_due_days` from policy.
  - `regular_installment_amount` = approved monthly amount.
  - `full_payment_count` = floor(total_due / installment_amount).
  - `final_payment_amount` = total_due − (full_payment_count × installment_amount).
  - `total_installments` = full_payment_count + (1 if final_payment_amount > 0 else 0).
  - `final_due_date` = first_due_date + full_payment_count months.
  - `return_to_court_date` = final_due_date + `return_to_court_offset_days` from policy.
- **Account fee**: Check the jurisdiction's payment policy. If `account_fee` = 0.00 in the policy, set `account_fee_treatment` = "excluded_by_policy" and `account_fee_amount` = 0.00. Do NOT carry counter-petition or worksheet account-fee rows onto the order unless the policy supports them.
- **Restitution priority**: Follow the policy's `restitution_priority` field. If "Restitution before fines and costs," set `payment_application_order` = "restitution_before_fines_costs".
- **Agreement type**: "initial_installment" for first petitions; "deferred_payment" for deferred; "subsequent_review" for later petitions.

#### License / Probation / Docket Entries
- CC-1375 (probation referral): Prepare only if supervised probation was ordered. Set `cc1375_status` = "not_ordered" if no supervised probation. Include report_datetime from hearing/portal.
- CC-1379 (license + payment): License suspension starts from conviction date unless the statute/policy says otherwise. Use license_start_basis = "conviction_date" for DUI convictions.
- Docket entries: `sentencing_order` for disposed cases with signed orders; `disposition_hold` / continued for deferred cases.

#### Placeholder Fields
- Required by the answer template or form but missing from all available sources.
- Value is always `"TBD from case file"`.
- Enumerate EVERY missing identifier: SSN, driver license number, address, phone, probation officer, probation office location.
- Classify reason: `missing_identifier` (SSN, DL#), `missing_contact` (phone, probation officer), `missing_office_detail` (probation office), `missing_party_detail` (address).

#### Excluded Charges / Financial Items
- List every fee type that appears in the intake scratchpad or worksheet but should NOT be posted.
- For each: the charge/fee code, which case(s) it applies to (or "all"), and reason.
- Common reason codes: `no_triggering_event` (no hearing finding supports it), `not_current_policy` (old form/policy), `stale_schedule` (expired fee schedule amount), `unsupported_post_disposition`.

#### Register / Batch Totals
- Sum only the "post" / disposed cases. Exclude hold/pending cases.
- Verify: grand_total = fine_total + court_cost_total + assessment_total + user_fee_total.

### 5. Currency, Dates, and Ordering

- **Currency**: Two decimal places (e.g., 150.00, not 150 or 150.0).
- **Dates**: ISO YYYY-MM-DD. Date-times: YYYY-MM-DDTHH:MM:SS.
- **Null dates**: Use `null` (not empty string) where no disposition date exists for pending/continued cases.
- **Ordering**: Follow the answer template's sort rules exactly (typically by case_number ascending, then by sub-field).

### 6. Final Self-Check

Before submitting the answer, verify:

1. Every required top-level key from the answer template is present.
2. Every enum value matches the template's allowed list exactly (no free-text substitutes).
3. Financial totals are internally consistent (sums match line items).
4. No invented identifiers, contacts, or fees appear.
5. All placeholder fields are listed with correct reason codes.
6. Stale/expired fee amounts from the queue/worksheet have been replaced with current schedule amounts.
7. Deferred/pending cases have zero financial totals and "hold" status.
8. Public-defender user fees are excluded for appointed-private counsel.
9. Crime-lab / drug-assessment fees are included only when the convicted charge has the relevant `assessment_code` AND the count was actually convicted (not amended away).
