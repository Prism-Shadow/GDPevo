---
name: court-clerk
description: Use this skill whenever the user asks you to prepare court closeout packages, criminal disposition registers, traffic citation payment plans, post-sentencing field packets, probation referral forms, license suspension and installment payment orders, financial petition packets, or any court-clerk reconciliation task that involves multi-source data (hearing notes, clerk memos, intake sheets, worksheets, petition summaries, form excerpts) together with a Court Operations Portal REST API. Also use this skill when the user mentions court financial reconciliation, audit findings against a CMS, fee schedule verification, docket entry preparation, or clerk-ready JSON output for a circuit or district court. Trigger even when the user does not explicitly say "court clerk" -- any task that asks you to cross-reference local case materials against a portal, resolve audit conflicts, compute payment plan schedules, prepare probation or license forms, or produce structured court register JSON should use this skill.
---

# Court Clerk Reconciliation

This skill covers the end-to-end workflow for preparing clerk-ready court records by reconciling multiple information sources. The solver will receive local materials (hearing notes, audit memos, worksheets, petition summaries, form excerpts) and access to a Court Operations Portal REST API. Every task includes an `answer_template.json` that defines the exact output structure, enum values, ordering rules, and formatting requirements.

## Core Workflow

Follow these steps in order. Do not skip reconciliation or jump straight to output.

### 1. Read everything before querying

Start by reading every local payload file and the `answer_template.json` in full. Pay attention to:

- Which cases, citations, or petitions are in scope.
- Which jurisdiction and what date the task covers.
- What the answer template requires at the top level and in each nested section.
- Every enum value the template defines -- these are the only allowed values for those fields.
- Sorting and ordering rules stated in the template.
- Currency precision (always two decimal places) and date format (always ISO `YYYY-MM-DD`).

The answer template is the authoritative spec for output shape. You will fill its structure with reconciled data, not invent a new format.

### 2. Query the Court Operations Portal

The portal runs at the base URL provided in the task prompt (typically `<TASK_ENV_BASE_URL>`). All endpoints are read-only `GET`. Available endpoints are listed in the prompt; use only the ones the task mentions.

Common query patterns:

```
GET /api/cases?case_number={CASE_ID}
GET /api/cases?jurisdiction_code={JURISDICTION}
GET /api/citations?citation_number={CITATION_ID}
GET /api/charges?case_number={CASE_ID}
GET /api/docket-entries?case_number={CASE_ID}
GET /api/fee-schedules?jurisdiction_code={JURISDICTION}
GET /api/payment-policies?jurisdiction_code={JURISDICTION}
GET /api/forms?jurisdiction_code={JURISDICTION}
GET /api/financial-petitions?petition_id={PETITION_ID}
GET /api/search?q={SEARCH_TERMS}
```

Responses are JSON with a `count` and `results` array. For single-case lookups, use the case-specific parameter. For batch tasks, the `/api/search` endpoint with a case-number prefix often returns cases, charges, and docket entries in one response -- check the `result_type` field in each result.

The portal is the system of record for:
- **Identity** (defendant name, date of birth, external party ID): the CMS record (`source_system` starting with "AOC-CMS") is authoritative.
- **Case status** (`disposed`, `deferred`, `pending`, `closed`): the portal status field controls whether a case enters the register.
- **Current fee schedules**: filter by `jurisdiction_code`, then prefer the record with the most recent `effective_date` and no `end_date` (or the latest `end_date` that is after the task date). Ignore records with `end_date` before the disposition date.
- **Docket entries**: use entry types and text to verify that orders were signed and hearings recorded.

### 3. Cross-reference and identify conflicts

Compare every fact across all available sources. The typical sources, in rough authority order for most facts:

| Fact type | Most authoritative source |
|-----------|--------------------------|
| Defendant identity (name, DOB) | Portal CMS record |
| Counsel type and attorney name | Portal CMS record, corroborated by clerk memo |
| Case status | Portal `status` field |
| Plea, finding, sentence terms | Hearing notes / courtroom record |
| Departure findings | Judge's stated position in hearing notes |
| Fees and amounts | Current portal fee schedule for the jurisdiction |
| Payment plan terms | Court-approved order in hearing notes or petition |
| Missing identifiers | Accept as missing; see placeholder rules |

When sources conflict, record the conflict as an audit finding and resolve it by citing which source controls. Never average or split the difference.

### 4. Resolve by applying these rules

**Identity conflicts**: When a local worksheet or finance queue has a different name or DOB than the portal CMS record, the portal CMS record wins. However, if a corroborating memo (clerk audit memo, supervisor note) provides verified corrections that supersede even the portal, use the corroborating memo and flag it.

**Counsel classification**: The raw label on a worksheet or queue ("PD", "APD", "APPT PRIVATE") may be abbreviated or stale. Check the portal `counsel_type` field and any corroborating memo. Key distinction: `appointed_private` counsel paid by the county is NOT a public defender -- do not apply the PD user fee. `retained` means private counsel paid by the defendant.

**Departure status**: The judge's own words in the hearing notes control. If the judge called a sentence "top of the range" and said no departure finding, record `no_departure` even if a legacy worksheet shows a departure label.

**Fee schedule currency**: Always use the fee schedule entry that is current for the disposition date. A fee with an `end_date` before the disposition date is stale -- exclude it. When the portal has both an old and current version of the same fee type for the same jurisdiction, use the current one and flag the stale one in audit findings.

**Amended charges**: When the state moved to amend a charge (e.g., controlled substance amended to misdemeanor theft), the original charge wording is not the conviction count. The conviction is the amended charge. A lab fee that is mandatory for controlled-substance counts does not apply when the conviction is for a non-drug amended charge.

**Missing DOB**: If the bench card/worksheet has no DOB and the portal also returns `null` for DOB, use `"TBD from case file"`. Never borrow a DOB from a similarly named defendant in search results.

**Unsigned / pending / continued cases**: A case with no signed final order does not enter the disposition register. Its status is `deferred` or `pending`, its closeout action is `hold_unsigned_order` or `exclude_pending`, its fee status is `hold` or `do_not_post_pending`, and its financial totals are `0.00`. Its docket entry type should reflect the hold, not a sentencing order.

### 5. Apply the fee schedule

For each disposed case, collect the mandatory fees from the current portal fee schedule:

- **Court costs**: almost always mandatory (`mandatory: true`), one per case.
- **Fines**: the amount stated by the judge in the hearing notes.
- **Assessments**: mandatory assessments tied to the conviction offense (e.g., drug assessment for controlled-substance convictions, crime lab fee for controlled substances).
- **User fees**: public defender user fee only when counsel is `public_defender` (not `appointed_private` or `retained`).
- **Surcharges**: apply per citation if the schedule includes one.

Do not add fees that are:
- Stale (superceded by a newer schedule entry).
- Unsupported by the current schedule or hearing order.
- Trigger-based without a triggering event (no late payment → no late fee; no collection referral → no collection fee; no returned check → no returned-check fee; no DMV referral → no DMV fee; no traffic school ordered → no traffic school fee).
- Account-management fees unless current policy explicitly requires them.

Excluded fees/charges should be listed explicitly in the output with a reason code (`stale_schedule`, `unsupported_post_disposition`, `not_in_hearing_order`, `not_current_policy`, `no_triggering_event`, `no_order_or_policy_support`, `not_part_of_balance`).

### 6. Payment plan mathematics

When the court has approved an extended payment plan (installment agreement), compute the schedule as follows:

```
full_payment_count = floor(total_due / monthly_payment)
final_payment_amount = total_due - (full_payment_count * monthly_payment)
total_installments = full_payment_count + (final_payment_amount > 0 ? 1 : 0)
final_due_date = first_due_date + (total_installments - 1) months
```

All amounts in dollars to two decimal places. The down payment is `0.00` unless the order states otherwise. The return-to-court date is a separate field from the final due date and is provided in the task materials; do not compute it from the payment schedule.

For budget-supported reviews: `monthly_disposable_income = monthly_income - monthly_obligations`. If the requested installment is less than or equal to disposable income, it is `supported_by_budget` or `supportable`. The policy band minimum and maximum come from the local payment policy.

### 7. Placeholder handling

When a form field is required by the template but the value is absent from all available sources (portal, local materials, hearing notes), use the exact placeholder string `"TBD from case file"`. Never invent identifiers, addresses, phone numbers, license numbers, officer names, or office locations.

The placeholder is appropriate for:
- SSN, driver's license number, mailing address, residence address, phone number.
- Probation officer name, probation office location.
- Any contact or identifier field where no source provides the value.

Do not use the placeholder for facts that can be derived (e.g., compute a suspension end date from start date and months, or compute a final payment amount from the schedule math). Do not use it for optional fields that the template does not require.

### 8. Produce the output

Build the JSON object by filling the answer template structure with reconciled data:

- Use **exactly** the enum values defined in the template. Do not substitute prose like "no departure was found" for `no_departure`.
- Follow the template's **ordering rules** (typically sort by case number or citation number ascending).
- Apply the **currency** and **date** formatting rules.
- Every key listed as `required` must be present.
- For optional or conditional sections (e.g., payment plans for held cases), use the null/empty pattern shown in the template.
- List excluded items in sorted order as directed by the template.

## Common portal field reference

| Portal field | Meaning |
|-------------|---------|
| `case_number` | Unique case identifier |
| `citation_number` | Traffic citation identifier |
| `defendant_first` / `defendant_last` | Defendant name from CMS |
| `defendant_dob` | Date of birth (may be null) |
| `counsel_type` | `public_defender`, `appointed_private`, `retained`, or `unknown` |
| `attorney_name` | Attorney of record |
| `status` | `disposed`, `deferred`, `pending`, `closed` |
| `disposition_date` | Date of disposition |
| `jurisdiction_code` | Court jurisdiction (e.g., `AR-RC`, `OR22-JEFF`, `VA-GLO`, `AR-UC`) |
| `source_system` | `AOC-CMS` is most authoritative; `Intake queue`, `Legacy-CMS` are less reliable |
| `fee_id` | Unique schedule entry ID |
| `fee_type` | `court_cost`, `fine`, `assessment`, `user_fee`, `standard_fine`, `county_surcharge`, `account_fee` |
| `mandatory` | `true` means always apply for qualifying cases |
| `effective_date` / `end_date` | Schedule currency window; `end_date: null` means currently active |
| `violation_code` | Links fee to specific offense code |

## Quick reference: output section patterns

These are the most common top-level output sections seen across court-clerk tasks. The answer template tells you exactly which apply.

**Audit / reconciliation sections** (`audit_findings`, `case_audit`): For each conflict found, record `case_number`, the issue type, the conflicted value, the corrected value, and which source resolved it. Sort by case number then issue type.

**Disposition sections** (`case_dispositions`, `dispositions`, `matters`): One entry per target case. Include defendant identity, plea, finding, sentence terms, and status. Disposed cases get a disposition date and financial entry. Held/pending cases get a null date and zero financials.

**Fee reconciliation** (`fee_reconciliation`, `fee_entries`): List each fee by code with amount. `case_total` is the sum. Use fee status `post` for disposed cases and `hold` or `do_not_post_pending` for deferred/pending cases.

**Docket / register entries** (`docket_entries`, `docket_register`): One entry per case. Disposed cases get a sentencing order entry with the entry date and financial total. Held cases get a hold/continuance entry with no financial total.

**Totals** (`register_totals`, `batch_totals`, `docket_register.totals`): Sum the individual case amounts. Count disposed vs held cases separately. The grand total only includes disposed cases.

**Exclusions** (`excluded_charges`, `excluded_financial_items`, `exclusions`): List every charge, fee, or case excluded from the register with a reason code. Sort as directed.

**Payment plans** (`payment_plan`, `payment_order`, `payment_schedule`): Compute from the approved monthly amount and total due using the formulas in section 6.

**Form entries** (`form_entry`, `cc1375`, `cc1379`): Fill every field the form requires from available sources. Use placeholders for missing identifiers.

**Placeholder tracking** (`placeholder_fields`, `placeholder_cases`): List every field that uses the `TBD from case file` placeholder, organized by case or form section.
