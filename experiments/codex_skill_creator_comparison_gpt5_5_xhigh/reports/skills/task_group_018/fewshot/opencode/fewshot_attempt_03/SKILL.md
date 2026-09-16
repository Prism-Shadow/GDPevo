---
name: court-closeout-json
description: Prepare clerk-ready JSON answers for Court Operations Portal closeout tasks involving criminal dispositions, traffic citations, sentencing/probation/license packets, financial petitions, fee schedules, payment plans, form metadata, register totals, unsupported charge exclusions, and missing-field placeholders. Use when a prompt asks Codex to reconcile local court payloads with portal endpoints and return an answer_template.json-shaped court operations result.
---

# Court Closeout JSON

Use this skill to produce a single schema-valid JSON object for court closeout and post-disposition packet tasks. The task usually provides local payloads plus a Court Operations Portal base URL. Treat the local payloads and portal records as evidence to reconcile, not as text to summarize.

## First Pass

1. Read the prompt, `answer_template.json`, and every local payload before deciding any values.
2. Extract target identifiers, court/jurisdiction, docket or hearing date, requested portal endpoints, output keys, enum values, ordering rules, date rules, currency rules, and placeholder text.
3. Build a small evidence table for each target matter: local final hearing/order facts, worksheet or queue values, portal case/citation/petition rows, charge rows, docket rows, current fee schedules, payment policy, and form metadata.
4. Return JSON only. Do not include markdown, citations, comments, or explanatory prose.

## Portal Queries

Use the task base URL from the prompt or `environment_access.md`. Query only target identifiers and their jurisdictions.

From the skill root, `scripts/court_packet_math.py` can pretty-print allowed portal responses:

```bash
python scripts/court_packet_math.py query --base-url "$BASE_URL" --endpoint cases --param case_number=CASE_NUMBER
python scripts/court_packet_math.py query --base-url "$BASE_URL" --endpoint charges --param case_number=CASE_NUMBER
python scripts/court_packet_math.py query --base-url "$BASE_URL" --endpoint citations --param citation_number=CITATION_NUMBER
python scripts/court_packet_math.py query --base-url "$BASE_URL" --endpoint financial-petitions --param petition_id=PETITION_ID
python scripts/court_packet_math.py query --base-url "$BASE_URL" --endpoint fee-schedules --param jurisdiction_code=JURISDICTION
python scripts/court_packet_math.py query --base-url "$BASE_URL" --endpoint payment-policies --param jurisdiction_code=JURISDICTION
python scripts/court_packet_math.py query --base-url "$BASE_URL" --endpoint forms --param jurisdiction_code=JURISDICTION
python scripts/court_packet_math.py query --base-url "$BASE_URL" --endpoint search --param q=TARGET_ID
```

Useful query order:

1. Query target matters by their typed endpoint: `cases`, `citations`, or `financial-petitions`.
2. For case numbers, query `charges` and `docket-entries`.
3. Once a `jurisdiction_code` is known, query `fee-schedules`, `payment-policies`, and `forms`.
4. Use `search` only as a fallback or corroboration source when typed endpoints do not locate the target.

## Evidence Precedence

Use the schema to decide shape and allowed values, then reconcile facts by source quality:

- Final signed hearing notes, disposition notes, judicial statements, and local closeout notes control the actual courtroom outcome when they directly describe accepted pleas, findings, amendments, continuances, final orders, or holds.
- Portal case/citation rows are usually strongest for identity, DOB, counsel classification, jurisdiction, case status, citation facts, and canonical form/policy identifiers.
- Current portal fee schedules and payment policies control money amounts, mandatory/current fees, policy bands, account-fee treatment, first-due rules, and return-to-court offsets.
- Local audit or supervisor memos explain known conflicts and can corroborate counsel or status corrections.
- Finance queues, worksheets, scratchpads, intake cover sheets, old local forms, and legacy charge rows are suspect when contradicted by final hearing notes, current portal policy, or current fee schedules.
- If no source resolves a required identifier or contact field, use the exact placeholder required by the payload or form metadata. Do not invent identifiers, addresses, phone numbers, office locations, attorney details, or license numbers.

Portal `charges` rows can carry legacy values. Do not blindly copy a charge disposition, departure flag, fine, or assessment from a charge row if final local notes record a different accepted plea, conviction count, amendment, dismissal, continuance, or judge-directed departure treatment.

## Disposition Rules

- Enter a disposed/register matter only when there is a final disposition or signed order for the target date.
- Hold or exclude a matter with no signed final order, continued status, deferred final disposition, or unresolved required verification. Set financial postings to zero or empty according to the schema.
- Use the schema's null rule for missing disposition dates. If the template allows null for pending matters, use null; otherwise use the hearing/status date only when the task expects a dated hold entry.
- Map pleas and findings to the exact enum spelling in the template. For example, use `no_contest` when the enum uses underscores and `no contest` when the enum uses spaces.
- For bench-trial or no-plea situations, prefer `not_applicable` if available; otherwise use the closest allowed value supported by the case record.
- Determine departure status from explicit judge statements and current final sentence posture. Legacy departure labels do not control if final notes say no departure or top-of-range. Use not-applicable misdemeanor or pending values when the schema provides them.

## Financial Rules

- Current fee schedules supersede stale schedules, old worksheets, and queued import amounts.
- Posted criminal dispositions usually include mandatory court cost when the current schedule supports it and the case is closed.
- Apply drug, lab, or controlled-substance assessments only to final convicted counts that trigger the assessment. Do not assess them when the controlled-substance count was amended away, dismissed, pending, or not the conviction count.
- Apply public-defender user fees only when counsel is classified as public defender and no source says the fee was waived or inapplicable. Exclude the fee for retained counsel and appointed-private county-pay counsel.
- Do not add late, collection, DMV, traffic-school, returned-check, account-management, restitution, court-appointed-attorney, court-reporter, copy, certification, or miscellaneous fees unless a current order, current policy, current schedule, or petition balance directly supports the item.
- For traffic citations, match the current standard-fine schedule to the citation violation code/tier, then add mandatory per-citation surcharges. Do not substitute statutory maximum notes or stale schedule amounts for the current standard fine.
- For petitions, total due is the supported fines/costs balance plus supported restitution plus any policy-supported account fee, less any down payment only for schedule-balance math when the schema distinguishes it.
- Totals and register counts include posted/disposed matters only. Held or pending matters should have zero financial totals unless the schema explicitly asks for a separate held total.

## Payment And Date Math

Use exact cents internally and output numeric JSON values rounded to two decimal places.

For installment schedules:

1. Use the approved/requested monthly amount only if it fits the current policy band and the budget supports it.
2. Monthly disposable income is monthly income minus monthly obligations.
3. Mark support according to the schema's enum: supported/supportable when the selected amount is within policy and not above disposable income; below or above policy when outside the policy band; unsupported when the budget cannot support it.
4. `total_installments` is `ceil(balance_after_down_payment / regular_installment_amount)`.
5. `full_installment_count` or `full_payment_count` is the number of regular full payments before any smaller final remainder. If the balance divides evenly, all installments are full payments and the final payment equals the regular amount.
6. `final_due_date` is the first due date plus `total_installments - 1` calendar months.
7. If the task gives a candidate return-to-court date, verify it against policy. Otherwise compute it from the final due date plus the policy offset when the schema asks for it.

The helper script can compute these values:

```bash
python scripts/court_packet_math.py installments --total TOTAL_DUE --amount MONTHLY_AMOUNT --down DOWN_PAYMENT --first YYYY-MM-DD --return-offset-days DAYS
python scripts/court_packet_math.py add-months --date YYYY-MM-DD --months MONTH_COUNT
```

For license suspensions, use the start basis stated in the task materials. In these packet tasks the usual basis is the conviction date unless a note or policy says release date or petition date. The suspension end date is the start date plus the stated number of calendar months.

## Forms And Placeholders

- Query current form metadata for form IDs, labels, required fields, and placeholder instructions.
- Use local form excerpts for visible labels, account-reference rules, and form sections when portal metadata is brief.
- If no separate account number exists for a citation and the local form says to use the citation number, use the citation number as the account reference.
- Use placeholders only for missing identifiers, addresses, phone numbers, driver license numbers, probation officer/office details, and similar form-required contact/party details.
- Do not use placeholders for legal outcomes, fee amounts, policy choices, or dates that can be derived from the evidence.
- When the schema asks for placeholder lists, include every missing field required by the packet and sort fields exactly as instructed.

## Output Assembly

- Start from the template, not from an example answer.
- Preserve required top-level keys, nested keys, enum spelling, nullability, date formats, and array ordering.
- Sort each array according to the template. If no rule is stated, sort target matters by their primary identifier.
- Use JSON numbers for money, not strings. Keep calculations to cents even if JSON rendering shows one decimal place.
- Recompute all case totals and batch/register totals from the fee items included in the output.
- Include excluded charges or financial items when stale/unsupported values appear in source materials and the schema asks for exclusions.
- Before finalizing, check that every enum value appears exactly in the template, every required key is present, every unsupported fee total included is zero unless supported, and the output parses as JSON.
