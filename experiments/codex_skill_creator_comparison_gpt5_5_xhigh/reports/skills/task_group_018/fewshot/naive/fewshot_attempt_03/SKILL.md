---
name: court-closeout-reconciliation
description: Reconcile court closeout, disposition register, payment-plan, and post-sentencing packet tasks using local payloads plus the read-only Court Operations Portal, returning schema-exact JSON.
---

# Court Closeout Reconciliation

Use this skill when a task asks for a clerk-ready court JSON package involving criminal dispositions, traffic citation closeout, fee/register reconciliation, payment petitions, probation referrals, license suspension orders, or form packet fields. The typical task gives local files under `input/payloads/`, an `answer_template.json`, and a read-only Court Operations Portal base URL.

## Boundary

- Use only the task prompt, files in the task input directory, and the read-only portal endpoints named by the prompt or environment instructions.
- Do not call write, judge, or submit endpoints. If the environment lists a disabled endpoint, treat it as forbidden.
- Return the final answer as JSON only, with no markdown, commentary, or extra wrapper.
- Do not invent identifiers, contact details, account numbers, officer/probation-office details, fees, charges, conditions, or triggering events.

## One-Pass Workflow

1. Read the prompt and every payload file before reasoning. Parse `answer_template.json` first enough to learn required keys, enums, ordering rules, date formats, currency precision, placeholder values, and whether `null` is allowed.
2. Extract all target identifiers: case numbers, citation numbers, petition IDs, hearing dates, jurisdictions, and form families.
3. Query portal records only for relevant evidence. Use `/api/search` for case and petition identifiers when useful, and query direct collection endpoints such as `/api/cases`, `/api/charges`, `/api/docket-entries`, `/api/citations`, `/api/fee-schedules`, `/api/payment-policies`, `/api/forms`, and `/api/financial-petitions` as needed. Filter broad endpoint results down to the targets before using them.
4. Build a source table per matter: local hearing or sentencing notes, local worksheets or petition summaries, portal case/citation record, charges, docket entries, active fee schedules, active payment policy, financial petition, and form metadata.
5. Resolve conflicts using the rules below, then fill the answer template exactly. Preserve template key names, enum strings, list ordering, numeric types, dates, and `null` values.
6. Validate arithmetic and schema shape before final output: totals equal line sums, held or excluded matters contribute zero where required, payment schedules amortize the stated balance, sorted lists obey the template, and every enum value appears exactly as allowed.

## Source Priority

- Signed/final courtroom disposition, sentencing, or hearing notes control the legal outcome when they conflict with stale worksheets, queue imports, or scratchpads.
- Portal case/citation identity fields control party spelling, DOB, jurisdiction, counsel classification, and status when they are direct target records.
- Current effective-dated fee schedules control fee amounts. Ignore archived or stale schedule rows unless the template asks to list them as excluded/stale charges.
- Payment policies control account-fee treatment, minimum/maximum installments, down payments, first-due offsets, return-to-court offsets, and restitution priority.
- Portal form metadata controls form IDs, labels, and placeholder instructions. Local form excerpts can supply visible field labels and account-reference handling when the portal does not contain those details.
- If a required value is genuinely absent, use the exact placeholder enum or text required by the template/materials. Do not fill missing data from similarly named non-target records.

## Criminal Disposition Registers

For each target case:

- Enter a disposition only when the materials establish a final disposition or signed order. If the matter was continued, lacks a signed order, or remains pending/deferred without a final order, hold or exclude it according to the template and post no financials.
- Use hearing notes to determine plea, finding, convicted counts, dismissed/amended-away counts, sentence, fine, probation, jail, and departure status. Do not preserve imported departure labels when the hearing record rejects them.
- Use portal case records for verified defendant name, DOB, counsel type, attorney name, jurisdiction, and CMS status. If the DOB is missing and the template allows a placeholder/verify action, use that rather than borrowing from search results.
- Treat appointed-private counsel separately from public defender counsel. Do not assess public-defender user fees for appointed-private counsel unless a current policy explicitly says to do so.
- Court costs post only for matters that the register should assess. Fine amounts come from the pronounced sentence or charge record after reconciliation.
- Drug, lab, and other conviction-linked assessments post only when the convicted or adjudicated count qualifies under the current fee schedule. Do not assess them on charges that were amended away, dismissed, nolle prossed, pending, or merely present in an old worksheet.
- Exclusions, holds, audit flags, and conflict findings should explain stale worksheets, identity/counsel corrections, omitted mandatory fees, unsupported fees, and pending/no-final-order matters using the template enums.

## Traffic Citation Closeout

For each target citation:

- Use the citation record for jurisdiction, defendant, plea, disposition/finding, violation code, speed facts, hearing date, payment-plan approval, monthly payment, and first due date when available.
- Match the violation code and jurisdiction to the current fee schedule effective for the disposition. Use the standard fine tier, not a statutory maximum or old schedule, unless the template explicitly requires a verification/exclusion entry.
- Add only mandatory current surcharges or fees supported by the fee schedule and hearing order.
- Exclude late, collection, DMV, returned-check, account-management, traffic-school, or similar charges unless the materials show the triggering event and current policy supports the charge.
- When no separate case/account number exists and the form or policy says to do so, use the citation number as the account reference.

## Payment Petition And Schedule Math

For each petition or approved plan:

- Classify the petition from the petition sequence and default status: first/current petitions are generally initial installment requests; default or later petitions may require subsequent-review handling if the template provides that enum.
- Compute disposable income as monthly income minus monthly obligations. Compare the requested/approved installment with the policy minimum, policy maximum, and disposable income to choose the template's support classification.
- Total due is fines-and-costs plus restitution plus any account fee that the active policy actually includes. Exclude stale counter notes or old account fees when the active policy amount is zero or the policy says not to include them.
- If restitution is present and the policy says restitution has priority, use the restitution-priority application order; otherwise use the fines/costs-only or template-equivalent value.
- Schedule balance equals total due minus down payment. For regular installments, count full installments of the regular amount, then add one final installment for any remainder. If the balance divides evenly, the final payment amount is the regular installment and total installments equals the exact quotient.
- First due date comes from the approved plan, petition, local note, or policy offset in that priority order.
- Final due date is the first due date plus `total_installments - 1` calendar months for monthly plans, preserving the due-day when possible.
- Return-to-court date comes from an explicit candidate date if supplied; otherwise add the active policy return-to-court offset to the final due date when the schema asks for it.

## Probation, License, And Form Packets

- Prepare probation referral fields only when sentencing/probation materials show supervised probation or an ordered referral. If no referral order exists, use the template's not-ordered status and zero/null fields as appropriate.
- Use conviction date, not release date or petition date, as the license-suspension start when the sentencing note or template basis calls for conviction-date suspension.
- Compute suspension end dates by adding the stated suspension months to the start date.
- Use portal form IDs and labels matching the jurisdiction and form family. Do not substitute a different jurisdiction's form if the correct one exists.
- Add placeholder tracking for missing required identifiers, contact details, driver-license numbers, addresses, phone numbers, and probation office/officer details. Sort placeholder fields/cases as directed by the template.

## Final JSON Checks

- Required top-level keys are present and no extra top-level sections are added unless the template allows them.
- Lists are sorted by the template's rule, commonly by case number, citation number, petition ID, field name, item name, or charge code.
- Dates are ISO strings; datetimes are ISO local strings; times use the template's requested format.
- Currency values are JSON numbers rounded to cents, not strings.
- `null` is used only where the template permits no date/datetime or no value.
- Batch/register totals exactly match included line items and exclude held or unsupported items.
