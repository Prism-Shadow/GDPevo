# Court Disposition Closeout & Financial Packet Skill

## Purpose

Prepare a clerk-ready structured JSON closeout or post-sentencing packet for a court docket by reconciling local hearing notes, audit memos, finance queue extracts, petitions, and case file payloads against a Court Operations Portal. The output identifies audit conflicts, corrected case dispositions, fee reconciliation, docket/register actions, payment schedules, license and probation form entries, and excluded or unsupported charges — all following strict schema rules and jurisdiction-specific policy.

## Prerequisites

- Access to the Court Operations Portal (GET endpoints: `/api/jurisdictions`, `/api/cases`, `/api/charges`, `/api/docket-entries`, `/api/fee-schedules`, `/api/payment-policies`, `/api/forms`, `/api/citations`, `/api/financial-petitions`, `/api/search`).
- Local payload files supplied with each task (hearing notes, audit memos, finance queue extracts, worksheets, form excerpts, petition summaries, sentencing intake facts, etc.).
- The answer template JSON that defines the required output structure, enums, and ordering rules.

## Step-by-Step Process

### Step 1: Gather All Source Materials

1. Read every file in the task's `input/payloads/` directory.
2. From each payload, note which values are **final/hearing-confirmed** and which are **draft, stale, carry-forward, or unverified**. Labels like "draft", "archived", "old", "stale", "omit", "verify", and "TBD" signal non-final data.
3. Identify the target case numbers, citation numbers, or petition IDs.

### Step 2: Query the Portal for Each Target

For every case, citation, or petition in scope, fetch:

| Portal Endpoint | Use For |
|---|---|
| `GET /api/cases` or `/api/search?q=<case>` | DOB, counsel type, attorney name, status, disposition date |
| `GET /api/charges?case_number=<case>` | Count, offense code, plea, disposition, fine, jail, probation, departure, assessment code |
| `GET /api/fee-schedules` | Current fees by jurisdiction; note `effective_date` / `end_date` to pick active schedule |
| `GET /api/payment-policies` | Min/max monthly, first-due-days, restitition priority, account-fee rules, return-to-court offset |
| `GET /api/forms` | Form IDs, labels, placeholder instructions, required fields |
| `GET /api/citations` | Violation code, speed/zone, plea, plan status, monthly payment |
| `GET /api/financial-petitions` | Petition sequence, income, obligations, balances, requested monthly |
| `GET /api/docket-entries` | Existing docket entries (filing, hearing, disposition, financial, clerk_note types) |

Always use the search endpoint to locate cross-referenced records when the direct endpoint returns too much noise.

### Step 3: Reconcile — Identify Conflicts

Compare every local value against the portal record. Flag conflicts using these conflict categories:

| Conflict Category | Typical Indicators |
|---|---|
| **Identity** | DOB mismatch, name spelling difference between queue and CMS/hearing notes |
| **Counsel** | Queue labels "PD" or "APD" but hearing/portal confirms appointed-private or retained |
| **Status** | Queue says "disposed" but no signed order exists; CMS disposition contradicts hearing outcome |
| **Fee Schedule** | Stale/archived fee amount (check `end_date` on schedule), missing fee lines, fees that should not apply (e.g., PD user fee when counsel is appointed-private) |
| **Departure** | Draft worksheet carries departure language that judge explicitly rejected or corrected |

Resolution source priority (for each conflict):
- **use_cms** — portal/CMS record is authoritative for identity data (DOB, name spelling)
- **use_hearing_notes** — courtroom notes or bench sheet override draft/queue values for disposition, counsel clarification, departure status
- **use_corrob_memo** — corroborating audit memo confirms correction
- **use_fee_schedule** — current fee schedule (not archived) governs fee amounts
- **hold_unsigned_order** — no signed order exists; hold financial entry

### Step 4: Determine Final Disposition for Each Matter

For each case or citation:

1. **Entry status**: If signed sentencing order exists → `disposed_enter` / `enter_disposition`. If no signed order or matter continued → `pending_exclude` / `hold_unsigned_order`.
2. **Primary outcome**: Map from hearing notes — `guilty_plea`, `no_contest_guilty`, `bench_trial_guilty`, or `continued_pending`.
3. **Plea**: Use the hearing or citation record. If no plea was accepted, use `none` or `not_applicable`.
4. **Charge disposition**: Override CMS with hearing notes when they conflict. A CS count amended to theft gets `guilty` on the amended count, not `nolle_prosequi` (which is the old count's status).
5. **Departure status**: Set `no_departure` or `none` when judge explicitly stated no departure finding. Use `not_applicable` for deferred/pending matters. Use `not_evaluated_misdemeanor` where misdemeanor sentencing doesn't require a departure analysis.
6. **Disposition date**: Use the hearing date when a signed order was entered. Use `null` for continued/pending matters with no final order.

### Step 5: Fee Reconciliation

For each disposed case:

1. **Start from the current fee schedule** for the jurisdiction (check `effective_date` has no `end_date` or `end_date` is null).
2. Include mandatory fees: court costs, fines (as pronounced), drug/crime lab assessments (only when conviction count has the matching `assessment_code`).
3. Include PD user fee **only** when `counsel_type` is `public_defender`. Exclude when appointed-private or retained.
4. Exclude every unsupported charge: stale fee amounts, account-management fees not in current policy, late/collection/DMV fees with no triggering event documented in hearing minutes, restitution with no court order.
5. For deferred/pending cases: set fee status to `hold` or `do_not_post_pending` with zero totals.

### Step 6: Payment Plan Construction (When Applicable)

1. Pull the jurisdiction's payment policy (`/api/payment-policies`).
2. Determine **petition classification**: `initial_installment`, `subsequent_review`, `deferred_payment`, or `exempt_no_payment`.
3. Compute **disposable income**: monthly income minus monthly obligations.
4. Set **support classification**: `supportable` if the approved amount is within policy min–max band AND fits disposable income; `below_policy_minimum`, `above_policy_maximum`, or `unsupported_by_budget` otherwise.
5. Determine **payment application order** from policy: `fines_costs_only`, `restitution_before_fines_costs`, or `fines_costs_before_restitution`.
6. Check **account fee treatment**: If the jurisdiction policy has `account_fee = 0.00`, use `excluded_by_policy`. Otherwise verify whether policy includes it.
7. Compute schedule:
   - `total_due` = fines_and_costs + restitution (per policy application order).
   - `regular_installment_amount` = approved/requested monthly amount.
   - `total_installments` = ceil(total_due / installment_amount). The last installment may be smaller.
   - `full_payment_count` = floor(total_due / installment_amount).
   - `final_payment_amount` = total_due − (full_payment_count × installment_amount). If zero, set equal to installment_amount and reduce total_installments by 1.
   - `first_due_date` = petition submitted_date + `first_due_days` from policy.
   - `final_due_date` = first_due_date + (total_installments − 1) months.
   - `return_to_court_date` = final_due_date + `return_to_court_offset_days` from policy.
8. For traffic citations: use the citation number as `account_reference` when no separate court account number exists.

### Step 7: Form and Probation/License Entries

1. **CC-1375 (Probation Referral)**: Prepare when supervised probation was ordered. Set `cc1375_status` = `prepare_referral`. Use `not_ordered` when no probation referral order was signed.
2. **CC-1379 (License & Installment Order)**: Always required when license suspension is part of the sentence.
   - `license_start_basis`: `conviction_date`, `release_date`, or `petition_date` per jurisdiction practice and notes.
   - Compute `suspension_end_date` = start date + `suspension_months`.
   - `agreement_type`: `initial_installment` for first petitions, `deferred_payment` or `subsequent_review` for others.
3. **Oregon traffic forms**: Use `OR_22JD_PLAN` (22nd JD) or `OR_27JD_PLAN` (27th JD) per jurisdiction code. Map `form_label` from the portal form record.

### Step 8: Placeholder and Exclusion Handling

1. **Placeholders**: For any required form field where the case file lacks a value (SSN, DL#, addresses, phone, probation officer/office), use the exact placeholder text specified in the form's `placeholder_instruction` — typically `"TBD from case file"`. List all such fields with their `reason_code` (`missing_identifier`, `missing_contact`, `missing_office_detail`, `missing_party_detail`).
2. **Excluded charges/items**: List every fee or charge that appears in intake/scratchpad data but must NOT be entered:
   - `stale_schedule` — old fee schedule amounts with an `end_date` before disposition
   - `unsupported_post_disposition` — no hearing order or policy supports the charge
   - `not_in_hearing_order` — item never ordered at hearing
   - `not_current_policy` — item removed from current policy revision
   - `no_triggering_event` — e.g., late fee when no default, collection fee with no referral
   - `no_order_or_policy_support` — generic exclusion for items without order or policy backing
   - `not_part_of_balance` — e.g., restitution of $0 with no restitution order

### Step 9: Batch Totals and Register

1. Count **assessed/disposed** cases (those with `fee_status: post`) and **held/excluded** cases (those with `fee_status: hold`/`do_not_post_pending`).
2. Sum fees by category (fine_total, court_cost_total, assessment_total, user_fee_total, crime_lab_fee_total).
3. Compute **grand_total** = sum of all fee categories for disposed cases only.

### Step 10: Sort and Format

1. Sort all arrays per the answer template's `ordering_rules` or `instructions`.
2. All currency values to two decimal places.
3. All dates in ISO `YYYY-MM-DD`; datetimes in `YYYY-MM-DDTHH:MM:SS`.
4. Use exact enum values from the template — never substitute prose for an enum.
5. Return one JSON object matching the template structure.

## Common Pitfalls

- **Stale fee amounts**: Always verify the fee schedule's `end_date` before using an amount. The finance queue often carries forward older figures.
- **Counsel mislabeling**: "PD" and "APD" abbreviations on intake sheets frequently misidentify appointed-private counsel as public defenders, which affects PD user fee eligibility.
- **Draft disposition entries**: A worksheet showing "guilty / fine $X" is NOT authoritative if the judge did not sign the order. Hold the financial entry.
- **Amended charges**: When a count is amended from one offense to another, the original count's CMS disposition may show `nolle_prosequi` or `dismissed`. The audit must reflect that the conviction count is the amended one, and any assessment tied to the original count (e.g., drug lab fee) may no longer apply.
- **Missing identifiers**: Never invent SSN, DL#, addresses, or contact details. Always use the specified placeholder text.
- **Account fees in counter notes**: Petition counter worksheets sometimes carry stale account-maintenance fee rows. Verify against the current jurisdiction policy before including.
- **Payment application order**: Follow the jurisdiction policy (e.g., Gloucester uses `restitution_before_fines_costs`). The petitioner's preference does not override policy.
- **DOB verification**: When DOB is null in the CMS and blank on the bench card, use the placeholder (`TBD from case file`), not a DOB from a similarly-named defendant in a prior search.
- **Return-to-court date calculation**: This is typically `final_due_date + return_to_court_offset_days` from policy, not the candidate date in the petition summary.

## Decision Table: Fee Exclusion Quick Reference

| Charge Type | Keep If | Exclude If |
|---|---|---|
| Court cost | Mandatory, always keep for disposed cases | Pending/deferred case |
| Fine | Pronounced at hearing, signed order | Draft/no signed order |
| Drug/crime lab assessment | Conviction count has `assessment_code` | Count was amended to non-drug offense |
| PD user fee | `counsel_type` = `public_defender` | `counsel_type` = `appointed_private` or `retained` |
| Account management fee | Policy `account_fee > 0` and policy includes it | Policy `account_fee = 0` or excluded by policy |
| Late/collection/DMV fees | Hearing minutes document triggering event | No hearing mention of default/referral/DMV |
| Restitution | Court order in sentencing intake or notes | No restitution order ($0 balance, no order) |
| Stale schedule amounts | Current schedule (`end_date` is null) | Archived amounts (`end_date` before disposition) |

## Payment Plan Math Reference

```
total_installments = ceil(total_due / installment_amount)
full_payment_count = floor(total_due / installment_amount)
final_payment_amount = total_due - (full_payment_count * installment_amount)

# Edge case: if final_payment_amount == 0
#   final_payment_amount = installment_amount
#   total_installments -= 1

first_due_date = submitted_date + first_due_days
final_due_date = first_due_date + (total_installments - 1) months
return_to_court_date = final_due_date + return_to_court_offset_days
```
