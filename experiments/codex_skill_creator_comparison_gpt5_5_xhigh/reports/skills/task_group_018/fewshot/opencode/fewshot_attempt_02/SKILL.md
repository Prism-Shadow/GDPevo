---
name: court-closeout-reconciler
description: Prepare clerk-ready court closeout JSON by reconciling local hearing notes, worksheets, petition summaries, answer_template.json schemas, and Court Operations Portal records. Use for criminal or traffic disposition batches, sentencing closeouts, fee registers, payment plans, financial petitions, probation referrals, license suspension orders, CC-1375/CC-1379 packets, excluded charges, placeholders, and any task that asks for JSON matching a court closeout answer template.
---

# Court Closeout Reconciler

## Core Approach

Produce JSON only, shaped exactly like the provided `answer_template.json`. Treat the prompt, local payloads, and Court Operations Portal records as a reconciliation problem: local materials often contain hearing results and clerk exceptions, while the portal supplies current case/citation records, charge codes, schedules, policies, and form metadata.

Start every task by reading:

1. The user prompt, including target matters, jurisdictions, dates, and endpoint names.
2. `input/payloads/answer_template.json`.
3. Every local payload file.
4. Relevant portal records for each target matter and jurisdiction.

Use the optional helper at `scripts/portal_snapshot.py` to collect filtered portal data when a task provides a portal base URL:

```bash
python scripts/portal_snapshot.py "$TASK_ENV_BASE_URL" \
  --case CASE_NUMBER --citation CITATION_NUMBER --petition PETITION_ID --jurisdiction JURISDICTION_CODE
```

Repeat `--case`, `--citation`, `--petition`, and `--jurisdiction` as needed. The helper uses only public API endpoints and prints grouped JSON; it does not make closeout decisions.

## Portal Use

Prefer targeted queries over reading a default first page. Many endpoints support filters such as `?case_number=...`, `?citation_number=...`, `?petition_id=...`, and `?jurisdiction_code=...`; otherwise request a larger page with `?limit=500` and filter locally. Use `/api/search?q=...` only as a cross-check when a direct endpoint does not expose enough context.

Collect, as applicable:

- `jurisdictions`: court name, jurisdiction code, policy reference, state, timezone.
- `cases` or `citations`: identity, status, disposition date, counsel, violation code, hearing date, approved payment plan data.
- `charges`: count number, offense code, statute, plea, disposition, verdict, fine, jail, probation, license months, assessment flags, departure fields.
- `docket-entries`: final order, disposition, continuance, and financial posting signals.
- `fee-schedules`: current fee lines effective on the disposition or hearing date.
- `payment-policies`: installment bounds, account fee treatment, first due offset, return-to-court offset, restitution priority.
- `forms`: current form IDs, labels, required fields, and placeholder instructions.
- `financial-petitions`: petition sequence, balances, income, obligations, requested installment, default status, and restitution.

## Source Priority

Use final courtroom materials, signed-order notes, sentencing/probation notes, and minute entries for what happened in court: plea, finding, amendments, final status, sentence, probation order, license consequence, payment approval, and whether a matter must be held or excluded. These materials override stale worksheets, draft sheets, intake scratchpads, and portal charge rows when the conflict is explicit.

Use the portal or CMS record for stable identity and administrative metadata unless local materials give a clear correction or the portal is missing the value. This includes name spelling, date of birth, jurisdiction code, counsel type, attorney name, status, form metadata, and current policy references.

Use the current fee schedule and payment policy for money. Match on jurisdiction, fee or violation type, and effective date. Exclude end-dated, archived, carried-forward, or scratchpad charges unless the current portal record, policy, hearing order, or answer template directly supports them.

If no signed final order, no accepted plea, no disposition, or a continued/pending status controls the matter, do not post financials. Use the template's hold, pending, exclude, null-date, or verify enum rather than inventing a disposition.

If an identifier, contact detail, office detail, driver license number, address, phone, SSN, or similar form field is absent, use the exact placeholder text required by the materials, commonly `TBD from case file`. Do not infer missing values from namesakes, older search results, or external assumptions.

## Disposition Rules

Map courtroom outcomes to the template's enums, not to prose.

- No-contest plea plus accepted/adjudicated/found language means the finding or charge disposition is guilty/violation found while the plea remains no contest.
- Bench trial guilty usually has no plea entry; use the template's bench-trial or not-applicable plea enum when available.
- A charge amended to a different offense is not a conviction on the original charge. Count the final convicted offense and count the amended-away or dismissed original if the schema asks.
- A controlled-substance or lab assessment applies only when the final conviction is on a qualifying controlled-substance count and the current schedule makes the assessment applicable.
- Departure status requires an express departure finding. A judge's statement that the sentence is top-of-range, ordinary, or not a departure overrides stale departure labels.
- Pending, deferred, continued, unsigned, or no-final-order matters stay out of disposed registers unless the schema has a separate held/deferred entry.

## Fee and Register Rules

Build financial entries from final disposition facts plus the current schedule:

- Court costs usually post for disposed criminal convictions when the current schedule supports them.
- Fines post only when imposed; waived, no-fine, held, or pending matters use zero.
- Public defender user fees apply only to public defender representation and only when the current schedule or order supports the fee. Do not apply the fee to retained counsel or appointed private/county-pay counsel.
- Drug, lab, or controlled-substance assessments require a final qualifying conviction and current schedule support.
- Do not add account-management, late, collection, DMV, returned-check, restitution, attorney, court-reporter, traffic-school, copy, certification, or other miscellaneous items unless an order, current policy, or template explicitly requires them.
- Case totals are the sum of posted fee items. Batch totals count and sum only matters the schema says are posted, approved, or assessed. Held and excluded matters contribute zero unless the template says otherwise.

When the schema asks for exclusions or audit findings, record the excluded item or conflict with the enum reason that best explains why it was not posted: stale schedule, unsupported policy, no triggering event, not in the hearing order, pending/no final order, missing identifier, or similar schema-provided language.

## Payment Plan Math

Use the petition, hearing note, citation record, and payment policy together.

1. Compute total due from included fines, costs, restitution, surcharges, and any account fee that policy actually includes.
2. Account fees with a zero policy amount, obsolete local note, or no policy support are excluded and recorded as zero when the schema asks.
3. Use the approved or requested installment amount only if it fits the policy band and the petition budget. Disposable income is monthly income minus monthly obligations.
4. Classify support using the template's enum: within policy and affordable is supportable/supported; below policy minimum, above policy maximum, or unaffordable uses the closest provided enum.
5. If the first due date is supplied by the record or local payload, use it. Otherwise add the policy's first-due offset to the disposition or petition date as the task context indicates.
6. For monthly schedules, subtract any down payment, then compute full installments as `floor(balance / regular_installment)`. If a positive remainder exists, add one final installment for the remainder; otherwise the final payment is the regular amount and total installments equals the full-installment count.
7. The final due date is the first due date plus `total_installments - 1` intervals. For monthly intervals, preserve the day of month when possible and clamp to the last day for short months.
8. Use an explicit return-to-court date when the payload gives one; otherwise add the policy return offset to the final due date.
9. If restitution is present and policy prioritizes it, set the payment application order to restitution before fines and costs. If restitution is zero, use the fines-and-costs-only enum when available.

## Forms and Placeholders

Use the current portal form for the jurisdiction and form family. Copy the form ID and label from the portal when the answer schema asks for them. For traffic payment plans, use the citation number as the account reference when no separate case or account number exists and local form instructions say to do so.

If the schema asks which required labels or local form sections were used, copy the visible labels from the current local form excerpt or portal form metadata exactly. Do not normalize punctuation, slashes, capitalization, or parenthetical text in form labels.

Create placeholder lists only for fields that the form requires or the template asks to track. Include missing office or probation fields only when the related form/referral is actually ordered. Sort placeholder entries and missing-field arrays exactly as the template instructs.

## Output Assembly

Before finalizing:

- Validate JSON parses and contains no markdown.
- Include every required top-level key and required nested key.
- Use enum strings exactly as shown in the template.
- Use ISO dates and local datetimes in the requested format.
- Emit money as JSON numbers rounded to cents.
- Use `null` only where the template permits it.
- Sort arrays according to the template. If no rule is given, use matter identifier ascending.
- Recalculate totals from the emitted line items and counts.
- Check that unsupported or stale charges are either omitted or listed in the schema's exclusion/audit area.

Do not copy values from prior examples or reuse a previous final answer as a template. Derive every output field from the current prompt, current local payloads, current portal records, and the answer template.
