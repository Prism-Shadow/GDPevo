---
name: court-clerk
description: Court clerk closeout, reconciliation, and post-sentencing packet preparation. Use this skill whenever the user is preparing a criminal or traffic case closeout, reconciling audit conflicts against court records, preparing post-sentencing field packets with probation referral and license suspension orders, reconciling payment petitions against court policy, producing a structured register-ready JSON answer from local case materials and a court operations portal, or performing any court-clerk workflow that involves cross-referencing hearing notes, finance extracts, and intake sheets against an authoritative case-management API. Do NOT use for general legal analysis, drafting legal briefs, or interpreting statutes outside the clerk closeout context.
---

# Court Clerk Closeout and Reconciliation

This skill covers the recurring clerk workflow: read local case materials, cross-reference against a court operations portal API, reconcile discrepancies, and produce a structured JSON answer matching a supplied answer template.

## Core workflow

Every clerk closeout task follows the same four-phase pattern. Execute these phases in order.

### Phase 1 --- Absorb the output contract

Read the `answer_template.json` (or equivalent schema payload) first. It defines the exact JSON shape you must produce, including required top-level keys, field-level enums, sorting rules, currency precision, and date format. Internalize these constraints before you touch any case data. Treat the template as the contract --- every key name, enum value, and ordering rule is mandatory.

### Phase 2 --- Gather all sources

Read every local payload the task provides. Common payload types and what they contribute:

- **Hearing notes / courtroom notes**: authoritative for what happened in open court --- plea, finding, sentence, departures, judge remarks. Hearing notes override draft worksheets and carry-forward finance import values when they conflict.
- **Audit / clerk memos**: identify specific reconciliation issues to resolve --- wrong counsel labels, stale fees, incorrect DOBs, unsigned orders, departure misclassifications.
- **Finance queue extracts / worksheets**: carry tentative financial totals and fee line items. These are provisional and must be verified against current fee schedules from the portal.
- **Form field excerpts / local form references**: define which fields a local court form requires and which labels it uses (Case # / Account #, TERMS of PAYMENT, etc.). Use these for form-level metadata.
- **Sentencing intake facts**: hold the conviction date, sentence parameters, probation details, and defendant identifiers. Treat intake facts as the baseline for the case memo and form pre-population.
- **Petition / budget summaries**: provide petition classification (first, subsequent), budget arithmetic (income, obligations, disposable income), and requested payment amounts. Use these plus the portal's payment policy to compute the approved payment schedule.

### Phase 3 --- Query the portal

The task environment provides a Court Operations Portal at the base URL given in the prompt. Query only the endpoints the task lists or those that are needed to resolve uncertainties in the local materials. Common endpoints and when to query them:

- `GET /api/cases` --- confirm case status, defendant identity, counsel of record. Prefer portal case records over finance-queue labels.
- `GET /api/charges` --- verify offense codes, statutes, amendment history.
- `GET /api/docket-entries` --- check whether a final order was entered or a case is still deferred/pending.
- `GET /api/citations` --- confirm citation records for traffic matters.
- `GET /api/fee-schedules` --- the single source of truth for current fee amounts. Override any stale or archived fee values from local worksheets.
- `GET /api/payment-policies` --- the authority for whether fees like account-management, collection, late, or DMV fees apply by default.
- `GET /api/forms` --- confirm current form IDs, labels, and field groups for the jurisdiction.
- `GET /api/financial-petitions` --- verify petition status, balances, and prior payment history.
- `GET /api/jurisdictions` --- confirm jurisdiction codes when building batch-level entries.
- `GET /api/search` --- resolve ambiguous identifiers (defendant names, DOBs) when local materials disagree.

Query in parallel when the results are independent. Batch case-level queries by case number.

### Phase 4 --- Reconcile and build the answer

Work through each target case/citation/petition in order --- the template's sort rule determines the final ordering, but reconciliation logic works case by case.

#### Reconciliation rules

When local materials conflict, apply these precedence rules:

1. **Hearing notes override everything else** for what was pronounced in court: plea, finding, sentence, departures, costs, and whether a final order was signed.
2. **Current fee schedule (portal) overrides stale local amounts.** If a local worksheet carries an archived or older-year fee, use the portal's current schedule.
3. **Portal case record overrides finance-queue labels** for identity (DOB, name spelling) and counsel type. If the portal and local materials disagree, note the conflict in the audit section with `resolution_source: "use_cms"` and the corrected value.
4. **Audit/corroboration memos are tiebreakers.** When the hearing notes are ambiguous and the portal record is unclear, the clerk audit memo or defense cover memo provides the resolution.
5. **Pending/unsigned orders block financial posting.** If a case has no signed final order, classify it as deferred, held, or continued. Do not post sentencing financial entries. Set fee_status to "hold" or "do_not_post_pending" and financial totals to 0.00.

#### Audit findings

For each discrepancy between the initial state (finance queue, draft worksheet, legacy screen) and the corrected state, add an audit_findings entry with:
- `case_number` --- the case where the conflict was found
- `issue_type` --- one of: identity, counsel, status, fee_schedule, departure
- `conflicted_value` --- what the pre-reconciliation record showed
- `corrected_value` --- the reconciled value
- `resolution_source` --- how the conflict was resolved: use_cms, use_hearing_notes, use_corrob_memo, use_fee_schedule, hold_unsigned_order

#### Fee reconciliation

For each case, build the fee_items list from what was ordered in court (from hearing notes) plus what the current fee schedule mandates. Use `fee_code` enums (fine, court_cost, drug_assessment, public_defender_user_fee, crime_lab_fee, etc.) exactly as the template defines them.

Do not add fees that:
- The hearing notes did not order
- The current payment policy excludes (account-management, collection, late, DMV, returned-check, traffic-school, copy, certification)
- Have no triggering event (e.g., a late-payment fee when nothing is late)
- Are stale schedule values from a prior year

List all such excluded charges in the excluded_charges or excluded_financial_items section with a reason_code explaining why each is excluded.

#### Payment plan math

When the template requires a payment schedule, compute it from the approved monthly payment and total due:

1. `total_installments` = ceil(total_due / monthly_payment)
2. `full_payment_count` = `total_installments` - 1 (the number of full-size payments)
3. `final_payment_amount` = total_due - (full_payment_count * monthly_payment)
4. `final_due_date` = first_due_date + (total_installments - 1) months
5. If `final_payment_amount` computes to 0 (balance divides evenly), set it to the monthly_payment amount and adjust full_payment_count down by 1 --- the last payment is never zero.

For petition-driven payment plans, also check budget support:
- `monthly_disposable_income` = monthly_income - total_monthly_obligations
- `support_classification`: "supported_by_budget" if the requested monthly payment falls within the policy band; otherwise "below_policy_minimum" or "above_policy_maximum" or "unsupported_by_budget"

#### Placeholder handling

When a form requires a field that cannot be completed from the case file (missing SSN, driver license number, mailing address, phone, probation officer name, probation office location):

- Use the exact placeholder value **`TBD from case file`**
- Record the missing fields in the placeholder_fields or placeholder_cases section with a reason_code: missing_identifier, missing_contact, missing_office_detail, missing_party_detail
- Never invent identifiers, addresses, phone numbers, or contact details

#### Batch totals

Aggregate across all disposed cases:
- Count of disposed (enterable) cases vs. held/pending/excluded cases
- Sums for each fee type across all posted cases
- The grand total across all posted financial entries
- Held or excluded cases contribute 0.00 to all totals

## Output rules

Follow these rules for every answer:

- **JSON only.** No markdown wrapping, no explanatory prose.
- **ISO dates.** All dates in YYYY-MM-DD format. Date-times in YYYY-MM-DDTHH:MM:SS.
- **Currency to two decimal places.** Every money value is a number with exactly two decimal places (e.g., 150.00, not 150).
- **Use enum values exactly as supplied** in the template. Do not substitute prose descriptions for enum values.
- **Sort per template ordering_rules.** Sort array items by the key the template specifies (typically case_number, citation_number, petition_id, or field name ascending).
- **Required keys must be present.** The template defines required_keys lists --- every key in those lists must appear in your output, even if the value is 0, 0.00, null, or an empty array.
- **Use null for absent dates.** When a disposition date or entry date does not apply (e.g., a continued/pending case), use `null`, not an empty string or a placeholder.
- **Case matching.** Match case numbers, citation numbers, and petition IDs exactly as they appear in the local materials and portal records. Do not reformat or normalize them.

## Quick reference: reconciliation decision table

| Conflict type | Default resolution | Source to cite |
|--------------|-------------------|----------------|
| DOB mismatch (finance queue vs. portal/hearing) | Use portal CMS | use_cms |
| Counsel label wrong (APD not PD, wrong attorney name) | Use corroborating memo or portal | use_corrob_memo or use_cms |
| Stale/archived fee amount | Use current portal fee schedule | use_fee_schedule |
| Disposition status: draft vs. unsigned | Hold if no signed order | hold_unsigned_order |
| Departure classification conflict | Use hearing notes (judge's pronouncement) | use_hearing_notes |
| Amended charge (different from filed count) | Use hearing notes for actual conviction | use_hearing_notes |
| Missing DOB --- genuinely absent from all sources | Placeholder; verify before entry | verify_before_entry |
| Pending/continued case --- no final order | Exclude from financial posting | exclude_pending |
| Fee not supported by current policy | Exclude with reason code | not_current_policy or no_order_or_policy_support |
| Payment plan for a traffic citation | Portal fee schedule + hearing-approved monthly amount | use_fee_schedule |

## Common portal query patterns

Query in parallel where the endpoints are independent. Example sequence for a multi-case batch:

1. Query `/api/cases` for all target case numbers simultaneously
2. Query `/api/charges` for all target cases (can run in parallel with cases)
3. Query `/api/fee-schedules` for the jurisdiction (one query covers all cases)
4. Query `/api/payment-policies` for the jurisdiction (one query covers all cases)
5. Query `/api/forms` for the jurisdiction
6. Query `/api/docket-entries` for cases with uncertain status
7. Query `/api/search` only for genuinely ambiguous identifiers --- prefer direct case/citation lookups

For petition-driven tasks, also query `/api/financial-petitions` by petition ID.

## Verification checklist

Before finalizing, verify:
- [ ] All required top-level keys from the template are present
- [ ] Every array item has all its required keys
- [ ] Enums match the template's allowed values exactly
- [ ] Sort order matches the template's ordering rules
- [ ] ISO date format on every date field
- [ ] Two decimal places on every currency field
- [ ] No invented identifiers or contact details --- use "TBD from case file" where needed
- [ ] Held/pending cases have 0.00 financials and no posted fee items
- [ ] Excluded charges enumerated with reason codes
- [ ] Batch totals add up correctly from the posted-case subtotals
