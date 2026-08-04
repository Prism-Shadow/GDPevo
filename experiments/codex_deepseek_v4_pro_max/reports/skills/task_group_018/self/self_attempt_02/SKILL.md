---
name: court-clerk-closeout
description: Reconcile court docket data from local payloads and a Court Operations Portal to produce structured JSON closeout, disposition, and financial-packet answers. Use when a task supplies an answer_template.json, supporting payloads, and references a Court Operations Portal with GET-only API endpoints.
---

# Court Clerk Closeout Skill

This skill covers reconciling criminal and traffic docket data across multiple sources—local case materials and a remote Court Operations Portal—to produce structured JSON closeout packages, disposition registers, and post-sentencing field packets.

## When to Use

- The task includes an `answer_template.json` that defines the output schema, enums, and sort rules.
- Payloads provide raw case data: hearing notes, audit memos, finance queue extracts, budget forms, petition summaries, probation notes.
- The task references `<TASK_ENV_BASE_URL>` or a Court Operations Portal with GET endpoints.
- The goal is to produce a single JSON object (never prose or Markdown) for clerk entry.

## Operating Rules

### 1. Read All Inputs First

Before any portal queries or output construction, read every file in the input directory:
- The `prompt.txt` for target cases, jurisdiction, and applicable portal endpoints.
- The `answer_template.json` for the required output shape, enums, field types, sorting rules, currency precision, and date formats.
- Every payload file in `input/payloads/` for case facts, audit notes, financial extracts, form excerpts, and clerk review reminders.

### 2. Query the Portal Systematically

The Court Operations Portal at `<TASK_ENV_BASE_URL>` provides GET-only endpoints. Always query the portal to:
- Verify case/docket/citation records against local payload data.
- Retrieve current fee schedules, payment policies, and form metadata.
- Resolve conflicts between local payloads and the authoritative portal record.

Common endpoints across tasks:
- `GET /api/jurisdictions` — jurisdiction metadata and codes
- `GET /api/cases` — case records (defendant details, charges, status)
- `GET /api/charges` — charge detail, offense codes, amended counts
- `GET /api/docket-entries` — docket history and entry types
- `GET /api/citations` — traffic citation records
- `GET /api/fee-schedules` — current fee amounts for the jurisdiction
- `GET /api/payment-policies` — payment-plan rules, minimums, account-fee handling
- `GET /api/forms` — form metadata (IDs, labels, field requirements)
- `GET /api/financial-petitions` — petition records and status
- `GET /api/search` — lookup by case number, citation, defendant name, or petition ID

Query parameters should mirror the patterns visible in the payloads (case number, citation number, jurisdiction code).

### 3. Reconcile Conflicts Across Sources

Compare data across local payloads and portal responses. For each discrepancy found:
- Identify the `issue_type` (identity, counsel, status, fee_schedule, departure).
- Determine the corrected value from the most authoritative source:
  - `use_hearing_notes` — courtroom bench notes carry the judge's actual ruling.
  - `use_cms` — portal/case-management system holds the official record.
  - `use_corrob_memo` — audit memo or defense cover memo corroborates the correction.
  - `use_fee_schedule` — current portal fee schedule overrides stale local amounts.
  - `hold_unsigned_order` — no final order was signed; financial entry must be held.
- Record both the conflicted value and the corrected value.

Common audit conflict patterns:
- **Identity**: DOB mismatch between finance queue and defense memo/hearing notes.
- **Counsel**: PD label on finance queue vs. appointed private counsel per courtroom record.
- **Status**: Queue shows disposed but docket note says no final order signed.
- **Fee schedule**: Stale assessment amounts from prior years' schedules.
- **Departure**: Draft worksheet carries a departure label the judge did not announce.

### 4. Follow the Answer Template Exactly

The `answer_template.json` is the authoritative schema. Obey every constraint:

- **Top-level keys**: Include every key in `required_top_level_keys`. Omit none.
- **Enums**: Use only values listed in each enum. Never substitute prose or free text for an enum value.
- **Field types**: Match the declared type (string, number, integer, boolean, date, datetime).
- **Sorting**: Apply the `ordering_rules` or `sort` instructions from the template.
- **Currency**: Numbers representing money must be numeric values (not strings) rounded to two decimal places. Use `0.00` not `0`.
- **Dates**: ISO 8601 `YYYY-MM-DD`. Datetimes: `YYYY-MM-DDTHH:MM:SS`. Use `null` when no date should be entered.
- **Nested structures**: Match every required key in nested objects (charge_summary, fee_items, payment_schedule, sentence_summary).

### 5. Handle Missing Data with Placeholders

When a field is required by the form/template but genuinely absent from all sources:
- Use the canonical placeholder `"TBD from case file"` for missing identifiers (SSN, driver license number, addresses, phone numbers).
- Do not invent, guess, or borrow values from similarly named defendants.
- Record each placeholder field in the designated output section, with a `reason_code` (missing_identifier, missing_contact, missing_office_detail).
- Sort placeholder entries as specified by the template.

### 6. Exclude Unsupported Charges and Fees

Do not post a charge or fee to the register unless it is supported by:
- The judge's oral pronouncement captured in hearing notes.
- The signed sentencing/disposition order.
- The current portal fee schedule.
- Current payment policy (not an obsolete form revision).

Fees to scrutinize before inclusion:
- Account-management / account-maintenance fees — verify current policy; do not carry from an old counter worksheet.
- Late-payment fees, collection referral fees, DMV notice fees, returned-check fees — exclude unless the hearing record confirms a triggering event.
- Traffic-school fees — exclude unless ordered on the record.
- Restitution — exclude unless a restitution order exists.
- Court-appointed-attorney fees, court-reporter fees — exclude unless ordered.
- Public defender user fee — do not post if counsel is classified as appointed private or retained.
- Crime lab fee — post only for controlled-substance convictions with the judge's express inclusion.

Record each excluded item with its charge_code/item, amount, and a reason_code (stale_schedule, no_triggering_event, not_in_hearing_order, not_current_policy, no_order_or_policy_support, unsupported_post_disposition).

### 7. Determine Case Status and Closeout Actions

For each target matter, decide the register action:
- **Disposed / enter**: A final order was signed, a plea was accepted, and a sentence was pronounced. Post the disposition and financials.
- **Continued / pending / exclude**: No final order was signed, plea not accepted, or matter continued for status. Do not create a financial register entry. Record in exclusions with the next status check date.
- **Hold / deferred**: The draft suggests disposition but the order was not signed. Hold until signed order is available. Use `hold_unsigned_order`.

### 8. Verify Counsel Classification

Classify counsel correctly because it affects fee eligibility:
- `public_defender` — the public defender's office appeared; eligible for PD user fee.
- `appointed_private` — private attorney paid by the county, not the PD office; not eligible for PD user fee.
- `retained` — privately retained counsel; not eligible for PD user fee.
- Abbreviations in worksheets (e.g., APD) must be checked against courtroom/hearing notes. The judge's on-record clarification controls.

### 9. Construct Payment Plans from Policy and Budget

When a post-disposition payment plan is needed:
- **Retrieve the current payment policy** from the portal to get minimum monthly amounts, maximum terms, and account-fee treatment.
- **Review the budget** from the petition or intake: monthly income minus listed obligations = disposable income.
- **Classify the requested payment**: `supportable` (within policy band), `below_policy_minimum`, `above_policy_maximum`, `unsupported_by_budget`.
- **Compute the schedule**: total due divided by monthly payment = full installments; compute the final remainder payment amount.
- **Payment application order**: Follow the policy or petition note for whether payments apply to restitution before fines/costs or vice versa.
- **Return-to-court date**: Set per the petition candidate date or policy rule.

### 10. Build the Final JSON Output

After reconciliation is complete, construct the output:
1. Build each top-level section by iterating through target matters in the specified sort order.
2. Populate every required field for each item. Use `null` only for genuinely inapplicable/nullable fields (e.g., report_datetime when no probation referral exists).
3. Compute register/batch totals by summing applicable financial fields from the items being posted (exclude held/pending matters).
4. Validate that all enum values match the template's allowed values exactly.
5. Output raw JSON only — no Markdown fences, no prose, no commentary.

## Quality Checklist

Before delivering the answer, verify:
- Every required_top_level_key from the template is present.
- Every item includes all required_keys from the template.
- All sort orders match the template's ordering_rules.
- All currency values are numeric with exactly two decimal places.
- All dates are ISO YYYY-MM-DD format.
- No enum value appears outside its declared set.
- Audit findings include conflicted_value and corrected_value for every conflict.
- Pending/continued cases appear in exclusions, not in financial totals.
- Unsupported fees/charges are listed with reason codes.
- No identifier, contact detail, or party information was invented.
- Portal query results were used to confirm current schedules and policies (not stale local copies).
