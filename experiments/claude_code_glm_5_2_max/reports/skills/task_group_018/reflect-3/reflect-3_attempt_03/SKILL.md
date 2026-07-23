# Court Operations Closeout Skill

## Purpose

Prepare a structured JSON closeout packet for a court criminal or traffic docket by reconciling local hearing notes, finance worksheets, and petition materials against the Court Operations Portal. The output matches the answer template supplied with each task and captures audit conflicts, corrected dispositions, fee reconciliation, docket/register entries, payment plans, probation referrals, and license orders.

## Entry Instructions

### 1. Read all local payload files

Read every file in the `input/payloads/` directory for the current task. These typically include:
- Hearing or closeout notes (bench shorthand, party corrections, carry-forward warnings)
- Finance queue extracts or clerk worksheets (may contain stale or draft values)
- Petition budget summaries or payment petition records
- Form field excerpts (CC-1375 / CC-1379 / local plan metadata, placeholder rules)
- The answer template (defines required keys, enums, ordering, and currency/date rules)

Treat local payloads as the primary narrative of what happened in the courtroom. Flag any value that conflicts with the portal.

### 2. Look up every target case, charge, and docket entry in the Court Operations Portal

Base URL: `http://task-env:9018/`

Required endpoint lookups per task:
- **GET /api/cases?case_number=…** — identity (name spelling, DOB), counsel type, case status, disposition date, jurisdiction code
- **GET /api/charges?case_number=…** — offense code, statute, plea, disposition, fine, jail/probation, departure, assessment code
- **GET /api/docket-entries?case_number=…** — entry dates and types for register actions
- **GET /api/fee-schedules?jurisdiction_code=…** — current amounts, effective dates, end dates, stale/archived rows. The URL uses the plural form `fee-schedules` (not `fee-schedule`)
- **GET /api/payment-policies** — policy bands, account fees, first-due-day offsets, return-to-court offset days, restitution priority rules. Filter by jurisdiction_code query param
- **GET /api/forms?jurisdiction_code=…** — form IDs, labels, placeholder instructions, required fields
- **GET /api/financial-petitions?petition_id=…** — petition balances, income/obligations, default status, license suspension months
- **GET /api/citations?citation_number=…** — traffic violation specifics, speed, zone, violation code, plan status
- **GET /api/jurisdictions** — jurisdiction codes, policy references (useful for determining the correct code)

Fetch **all** of these before constructing the answer so every value can be cross-checked.

### 3. Reconcile: resolve every conflict between local payloads and portal records

Common conflict patterns and resolution rules:

| Conflict type | Typical resolution source | Rule |
|---|---|---|
| **Identity** (name spelling, DOB) | Portal CMS (`use_cms` / `use_cms_identity`) | Portal case record is authoritative unless the hearing notes contain an explicit correction affirmed on the record |
| **Counsel type label** | Portal CMS + hearing notes | If the portal says `appointed_private` but the worksheet says "PD", trust the portal. If the judge clarified on the record (e.g., "APD means appointed private, county pay"), use hearing notes |
| **Stale fee amounts** | Fee schedule (`use_fee_schedule`) | Always use the fee schedule row with `end_date = null` and the earliest `effective_date` on or before the disposition date. Rows with an `end_date` are archived and must not be posted |
| **Draft or unsigned disposition** | Hold (`hold_unsigned_order` / `exclude_pending`) | If no signed order exists, set status to `deferred` or `pending_exclude`, hold or exclude all financial entries, and do not post to the register |
| **Departure flag from draft** | Hearing notes | If the courtroom audio/note says "top of range, not a departure," override the draft departure flag. Enter `no_departure` or equivalent |
| **Charge amendment** | Hearing notes | If the state amended a count (e.g., from controlled substance to misdemeanor theft), the original count is amended away. The conviction count and fee applicability follow the amended charge |
| **Lab / assessment fee omission** | Fee schedule + judge instruction | Mandatory assessments (e.g., crime lab fee for controlled-substance convictions) apply when the assessment_code matches and the fee schedule marks it mandatory. Judge reminders on the record reinforce this |
| **Missing DOB / identifiers** | Placeholder (`verify_before_entry`) | If DOB is genuinely absent from both the portal and notes, use the placeholder value (typically "TBD from case file") and flag for verification. Never borrow a DOB from a different defendant |
| **Account-management or stale local fees** | Policy (`excluded_by_policy` / `no_order_or_policy_support`) | Exclude any fee not supported by the current fee schedule or payment policy. Old account-management fees, obsolete plan service charges, and stale fee rows are excluded |
| **Payment application order** | Payment policy restitution_priority | If the policy says "Restitution before fines and costs," set `restitution_before_fines_costs`. Otherwise `fines_costs_only` |

### 4. Compute payment schedules

When the answer template requires a payment plan:

1. **Determine total due**: fines_and_costs_balance + restitution_balance. Do NOT add any unsupported fees
2. **Select installment amount**: use the amount from the petition request, clamped to the policy band [min_monthly, max_monthly]
3. **Classify support**: if the requested amount is within the policy band and disposable income supports it → `supportable`. If at the minimum → still `supportable` if the policy permits it
4. **Count installments**: `full_count = floor(total_due / installment)`, `remainder = total_due - (full_count * installment)`. If remainder > 0, there is a final smaller payment; `total_installments = full_count + 1`, otherwise `total_installments = full_count`
5. **First due date**: petition submitted_date + policy.first_due_days
6. **Final due date**: first_due_date + (total_installments - 1) months
7. **Return to court date**: final_due_date + policy.return_to_court_offset_days
8. **Down payment**: use `policy.down_payment_required` (typically 0)

### 5. Build the output JSON

- Follow the answer template's required keys, enum values, ordering rules, date format, and currency precision exactly
- Use ISO dates (YYYY-MM-DD) and datetimes (YYYY-MM-DDTHH:MM:SS)
- Use currency numbers to two decimal places (e.g., 150.00 not 150)
- Sort arrays per the template's ordering_rules (usually by case_number ascending)
- For traffic citations: use citation_number as account_reference when no separate case/account number exists (per local form excerpt rule)

### 6. Placeholder handling

- When a required form field (SSN, driver license, address, phone, probation officer) is absent from all sources, use the exact placeholder text specified by the materials — typically `"TBD from case file"`
- Do NOT invent or fabricate identifiers, contact details, or account numbers
- List all placeholder fields with the appropriate reason code (missing_identifier, missing_contact, missing_office_detail, missing_party_detail)

### 7. Excluded financial items

For every fee or charge that appears in a worksheet but should not be posted:
- Record the excluded item with its amount (0.00 if not applicable) and a reason code
- Common excluded items: account-management fees, collection fees, DMV fees, late-payment fees, returned-check fees, traffic-school fees, stale fee-schedule amounts, statutory-maximum substitutions, restitution (when no order exists)
- Reason codes: `no_order_or_policy_support`, `not_current_policy`, `no_triggering_event`, `stale_schedule`, `not_in_hearing_order`, `unsupported_post_disposition`, `not_part_of_balance`

### 8. Register/batch totals

- Sum only the cases with `post` or `disposed_enter` status. Exclude `hold` / `pending_exclude` cases
- Include all fee categories in the totals (fines, court costs, assessments, user fees, lab fees)
- The grand total must equal the sum of all included fee items
- The batch_total_due must equal the sum of all disposed-case total_due values

## Common Pitfalls

- **Plural endpoint names**: The fee-schedule endpoint is `/api/fee-schedules` (plural). The citation endpoint is `/api/citations` (plural). Other endpoints use singular cases/charges/docket-entries
- **Archived fee rows**: Always check `end_date` on fee schedule rows. A stale row (end_date in the past) must not be used for current dispositions, even if the amount appears in a worksheet
- **Counsel type drives fee eligibility**: Public Defender User Fee only applies when counsel_type is `public_defender`. It does NOT apply for `appointed_private` or `retained` counsel
- **No signed order = no register entry**: If the hearing notes state the judge did not sign the order, the status is deferred/pending and no financial entry should be posted
- **Worksheet "draft" values are unreliable**: Any worksheet value flagged as draft, carried forward, or from an older import must be verified against the portal before posting
- **Amended charges change fee applicability**: If a controlled-substance count is amended to a non-drug charge, the drug-crime assessment fee and lab fee no longer apply, even if the worksheet still shows them
- **Payment plan installments must sum correctly**: Verify that `(full_installment_count × regular_amount) + final_payment_amount = total_due`
