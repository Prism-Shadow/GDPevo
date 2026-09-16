---
name: court-closeout-reconciliation
description: Reconcile local court documents against a read-only Court Operations Portal API to produce structured closeout packets, financial entries, payment plans, probation referrals, and license orders. Covers audit conflict identification, cross-source identity and counsel resolution, fee-schedule date matching, installment math, placeholder discipline, and unsupported-charge exclusions.
---

# Court Closeout & Reconciliation

Use this skill when the task involves reconciling local court materials against the Court Operations Portal to produce structured clerk-ready JSON closeout packets, disposition registers, post-sentencing form packets, or payment-plan orders.

## The Core Workflow

Every task in this family follows the same three-stage pipeline:

1. **Ingest local payloads** -- Read every file in `input/payloads/` and the prompt text.
2. **Cross-check the portal** -- Query the Court Operations Portal API for the target cases/citations, their charges, docket entries, fee schedules, payment policies, forms, petitions, and jurisdiction metadata.
3. **Reconcile and produce the answer** -- Compare local claims against portal records, identify and resolve conflicts, compute financials, and output a single JSON object matching the provided `answer_template.json`.

## Portal API Reference

The Court Operations Portal is a read-only REST API. Allowed endpoints:

| Endpoint | Query params | Returns |
|---|---|---|
| `GET /api/jurisdictions` | `jurisdiction_code` (optional) | Court metadata: code, state, county, policy_ref |
| `GET /api/cases` | `case_number`, `jurisdiction_code` | Case records: defendant name/DOB, counsel_type, status, dates |
| `GET /api/charges` | `case_number` | Charge records: count_no, statute, plea, disposition, fines, jail, probation, departure |
| `GET /api/docket-entries` | `case_number` | Docket text, entry_date, entry_type |
| `GET /api/citations` | `citation_number`, `jurisdiction_code` | Traffic citation records: speed, zone, plea, plan_approved, etc. |
| `GET /api/fee-schedules` | `jurisdiction_code` | Fee amounts with effective_date and end_date ranges |
| `GET /api/payment-policies` | `jurisdiction_code`, `policy_id` | Min/max monthly, first_due_days, account_fee, restitution_priority, return_to_court_offset_days |
| `GET /api/forms` | `jurisdiction_code`, `form_id` | Form labels, required fields, placeholder instructions |
| `GET /api/financial-petitions` | `case_number`, `petition_id` | Petition details: balances, income, obligations, requested payment |
| `GET /api/search` | `q` (case or citation number) | Cross-resource search returning matching cases, docket_entries, charges |

**Querying conventions:**

- Use `?case_number=` for single-case lookups.
- Use `?jurisdiction_code=` to filter to one court's records (cases, fee schedules, policies, forms).
- The `/api/search?q=` endpoint returns results of multiple `result_type` values (`cases`, `docket_entries`, `charges`). Use it as a first pass when you need a broad view.
- Fee schedules have `effective_date` and `end_date` (null means still active). A schedule entry is current when `effective_date <= disposition_date` and (`end_date` is null or `end_date >= disposition_date`).
- Citations have `violation_code` values like `ORS_811_109_100PLUS`, `ORS_811_109_31_40`, `ORS_811_109_21_30` which map to fee schedule entries.

## Multi-Source Reconciliation

Every task requires reconciling at least two information sources. The sources and their relative authority:

| Source | Authority |
|---|---|
| Portal CMS records (cases, charges, docket_entries) | **Authoritative for identity, counsel classification, case status** |
| Portal fee schedules, payment policies, forms | **Authoritative for financial amounts and policy rules** |
| Local hearing notes / bench sheets | **Authoritative for judge's oral pronouncements (departure, plea, fine)** |
| Local audit memos / clerk notes | **Corroborating; flag conflicts but defer to portal + hearing notes** |
| Local finance extracts / worksheets | **Legacy data; often stale or draft -- always verify against current portal** |

### Audit Conflict Resolution

When sources disagree, create an audit finding with:

- `case_number` -- the matter
- `issue_type` -- one of: `identity`, `counsel`, `status`, `fee_schedule`, `departure`
- `conflicted_value` -- what the stale/wrong source says
- `corrected_value` -- the resolved correct value
- `resolution_source` -- which source settled the conflict

**Resolution priority by issue type:**

- **identity** (name/DOB mismatch): Portal CMS wins. Use `resolution_source: use_cms`.
- **counsel** (PD vs. appointed private): Portal `counsel_type` field wins over local abbreviations. Use `resolution_source: use_corrob_memo` when a defense memo or judge clarification resolves it. Never treat appointed private counsel as public defender for fee purposes.
- **status** (disposed vs. deferred/pending): If the judge did not sign a final order, the case is deferred/pending regardless of draft worksheets. Use `resolution_source: hold_unsigned_order`. Do not post financials for cases without signed orders.
- **fee_schedule** (stale amounts): Current portal schedule with null `end_date` wins over legacy worksheet amounts. Use `resolution_source: use_fee_schedule`.
- **departure** (departure vs. no departure): Judge's oral pronouncement in hearing notes wins over legacy carry-forward labels. Use `resolution_source: use_hearing_notes`.

### Counsel Classification

The portal `counsel_type` field is canonical. Common pitfalls:

- `"APD"` in legacy labels often means **appointed private counsel**, not public defender. Check the portal `counsel_type` and any defense cover memo.
- Public defender user fees attach **only** when `counsel_type` is `public_defender`. They are excluded for `appointed_private` and `retained`.
- When the portal has an `attorney_name`, use it; otherwise use the name from local hearing notes.

### Identity Verification

- The portal CMS is the authoritative source for defendant name spelling and DOB.
- When the portal DOB is `null`, do **not** borrow a DOB from similarly named defendants in prior search results. Use `"TBD from case file"` and flag with `identity_action: use_placeholder_verify`.
- When local materials have a slightly different name spelling (e.g., "Simons" vs "Simmons"), use the CMS spelling.

## Fee Reconciliation

### Selecting the Correct Fee Schedule

For every fee type, query `/api/fee-schedules?jurisdiction_code=<CODE>`. Then filter:

1. `effective_date <= disposition_date`
2. `end_date` is `null` or `end_date >= disposition_date`

Use the entry with a `null` end_date (current). Entries with a past end_date are stale and should be excluded.

### Fee Types and Their Application Rules

- **court_cost** -- Almost always mandatory. Post unless the case is held/deferred.
- **fine** -- Amount comes from the hearing notes or charge record. Zero if fine waived.
- **assessment** (drug assessment, crime lab fee) -- Post only when:
  - The conviction is for the relevant offense type (controlled substance for drug assessment and lab fee).
  - The current portal schedule supports the amount.
  - The charge was not amended away from the triggering offense.
- **public_defender_user_fee** -- Post only when `counsel_type` is `public_defender`. Do not post for appointed_private or retained.
- **county_surcharge** -- For traffic citations, add exactly once per citation if the portal schedule has one.

### Unsupported Charges to Exclude

Never add these fees unless a specific court order or current portal policy explicitly supports them:

- Late payment fees
- Collection/referral fees
- DMV notice/reinstatement fees
- Returned check fees
- Account-management / account-maintenance fees (unless portal policy `account_fee` > 0)
- Restitution (unless a restitution order exists)
- Court-appointed attorney fees
- Court reporter fees
- Traffic school fees
- Statutory maximum substitutions

When excluding, provide a `reason_code`: `stale_schedule`, `unsupported_post_disposition`, `not_in_hearing_order`, `not_current_policy`, `no_triggering_event`, `no_order_or_policy_support`, or `not_part_of_balance`.

## Payment Plan and Installment Math

When a payment plan is ordered, compute the schedule from the total due and the approved monthly payment.

### Standard Installment Calculation

```
full_payment_count = floor(total_due / monthly_payment)
final_payment_amount = total_due - (monthly_payment * full_payment_count)
total_installments = full_payment_count + (1 if final_payment_amount > 0 else 0)
```

**Example (VA-GLO, POL-VA-GLO-FIRST):** `total_due = 1260.00`, `monthly_payment = 75.00`
- `full_payment_count = floor(1260 / 75)` = 16
- `final_payment_amount = 1260 - (75 * 16)` = 60.00
- `total_installments = 16 + 1` = 17

**Example (OR22-JEFF, POL-OR22-EPP):** `total_due = 1155.00`, `monthly_payment = 50.00`
- `full_payment_count = floor(1155 / 50)` = 23
- `final_payment_amount = 1155 - (50 * 23)` = 5.00
- `total_installments = 23 + 1` = 24

### First Due Date

The first due date comes from one of these sources, in priority order:
1. Explicit date in the hearing closeout note or petition (e.g., "first due 2026-12-15")
2. Policy `first_due_days` + disposition date (or petition submitted date): add `first_due_days` days
3. For OR22-JEFF, the policy note says "usually the 15th of the next month if set after disposition"

### Final Due Date

Add `(total_installments - 1)` months to the first due date. If the first due date is on the 15th, the final is on the 15th of the computed month.

### Return to Court Date

Add `return_to_court_offset_days` days to the final due date.

### Budget Support Classification

When a petition includes income and obligations:

```
monthly_disposable_income = monthly_income - total_monthly_obligations
```

- `supported_by_budget` / `supportable` -- the approved monthly payment is within the policy band (`min_monthly` to `max_monthly`) AND within disposable income.
- `below_policy_minimum` -- approved amount is below `min_monthly`, but budget justifies it.
- `unsupported_by_budget` -- disposable income is insufficient.

### Payment Application Order

The portal policy `restitution_priority` field controls the payment application order:
- `"Restitution before fines and costs"` maps to `restitution_before_fines_costs`
- `"Not applicable"` maps to `fines_costs_only` (no restitution balance)
- When restitution exists and policy says restitution first, use `restitution_before_fines_costs`.

## Placeholder Discipline

When a form requires a field that cannot be completed from the available case materials, use the exact string `"TBD from case file"`. Never invent:

- SSNs
- Driver's license numbers
- Mailing or residence addresses
- Phone numbers
- Probation officer names or office locations
- Attorney contact details not in the record

The portal form records include `placeholder_instruction` fields that confirm this rule. Forms with IDs `VA_CC1375` or `VA_CC1379` explicitly require `"TBD from case file"` for unknown identifiers.

## Answer Format Rules

These rules apply to all tasks in this family:

- **Currency**: All monetary values are numbers with exactly two decimal places (e.g., `1260.00`, not `1260`).
- **Dates**: ISO 8601 `YYYY-MM-DD` format. Date-times use `YYYY-MM-DDTHH:MM:SS`.
- **Null dates**: Use `null` (not a string) when no date should be entered (e.g., pending cases without a disposition date).
- **Sorting**: Sort by case_number or citation_number ascending, unless the template specifies a different order.
- **Enums**: Use only enum values provided in the answer template. Do not substitute prose or custom strings.
- **Lists**: Sort placeholder_fields and excluded_financial_items by field/item name ascending unless otherwise specified.

## Task-Specific Patterns

### Criminal Sentencing Closeout (train_001 pattern)

Identify audit conflicts first, then build case_dispositions, fee_reconciliation, docket_entries, and register_totals. The register grand_total sums only cases with `fee_status: "post"`. Held cases contribute zero.

### Traffic Violation Closeout (train_002 pattern)

Match the `violation_code` from the citation to the correct fee schedule entry. Compute `amount_due = standard_fine + county_surcharge`. Build payment_plan with installment math. Use the citation number as the `account_reference` when no separate case number exists.

### Post-Sentencing Packet (train_003 pattern)

Build the case_memo from sentencing intake facts. Populate CC-1375 (probation referral) and CC-1379 (license suspension + installment order) forms. Compute payment schedule from petition data against the jurisdiction's payment policy. List all placeholder fields and excluded financial items.

### Disposition Register (train_004 pattern)

Audit each case for identity, counsel, and financial flags. Separate disposed cases from pending/continued ones. Post fees only for disposed cases with signed orders. Build docket_register entries and totals. List exclusions for pending matters with a next_status_check_date.

### Multi-Matter Financial and Supervision Packet (train_005 pattern)

Process multiple petitions and cases together. For each: classify the petition, compute budget support, build the payment schedule, determine CC-1375 and CC-1379 form entries. Group placeholder cases by case_number with their missing fields lists.

## Quick Reference: Portal Policy Fields

When reading a payment policy object:

- `min_monthly` / `max_monthly` -- the allowed monthly payment band
- `first_due_days` -- days from disposition/petition to first payment
- `account_fee` -- 0 means no account fee allowed; > 0 means check if applicable
- `restitution_priority` -- controls payment application order
- `return_to_court_offset_days` -- added to final_due_date for return-to-court date
- `down_payment_required` -- 0 means no down payment required
- `subsequent_petition_rule` -- what happens on default
