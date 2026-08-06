# Court Operations Portal — Clerk Closeout & Packet Preparation

## Purpose

Process court clerk closeout, sentencing packet, disposition register, and post-disposition financial/supervision packet tasks. These tasks combine local payloads (hearing notes, clerk memos, finance extracts, form excerpts, petition summaries) with the Court Operations Portal REST API to produce a structured JSON answer matching a provided answer template.

## When to use

- The task asks you to act as a court clerk (deputy clerk, clerk, or similar court-official role)
- The task references a Court Operations Portal at `<TASK_ENV_BASE_URL>`
- The task provides an `answer_template.json` in an `input/payloads/` directory
- The task supplies local payloads such as hearing notes, clerk audit memos, finance queue extracts, form field excerpts, petition summaries, or sentencing/probation intake notes
- The prompt lists a set of case numbers, citation numbers, or petition IDs to close out or process

## Base URL and network access

- **`<TASK_ENV_BASE_URL>`** always resolves to `http://task-env:9018/`.
- Ignore any `localhost`, `127.0.0.1`, or `env/setup.sh` references in staged task inputs; use `http://task-env:9018/`.
- No credentials are required — all endpoints are read-only GET requests.

## Available API endpoints

The Court Operations Portal exposes these endpoints. Not every task will use all of them; use only the endpoints relevant to the current task's materials.

| Endpoint | Description | Used when |
|---|---|---|
| `GET /api/jurisdictions` | Jurisdiction/venue metadata | You need to confirm court codes, jurisdiction names, or fee-schedule jurisdiction scoping |
| `GET /api/cases` | Case records (defendant identity, status, disposition) | Processing criminal or civil case closeouts, verifying case posture |
| `GET /api/charges` | Charge records per case (offense code, statute, disposition) | Reconciling charge summaries, verifying conviction counts vs filed counts |
| `GET /api/docket-entries` | Docket event entries (sentencing orders, continuances) | Confirming whether a final signed order exists, determining entry dates |
| `GET /api/citations` | Traffic/non-traffic citation records | Processing traffic violation closeouts with citation numbers |
| `GET /api/fee-schedules` | Current fee schedules by jurisdiction and date | Validating fine amounts, drug assessments, court costs, user fees against the active schedule |
| `GET /api/payment-policies` | Payment plan policies (minimums, maximums, down-payment rules, intervals) | Structuring post-disposition payment plans, validating installment math |
| `GET /api/forms` | Form metadata (form IDs, labels, field groups, revision dates) | Mapping local form excerpts to current portal form entries |
| `GET /api/financial-petitions` | Payment petition records (budget, balances, requested terms) | Processing payment petitions alongside case dispositions |
| `GET /api/search` | Free-text or filtered search across portal records | Broad lookups when local materials reference items not directly reachable by ID |

Use `GET /api/search` when local materials reference a record not directly accessible by case number, citation number, or petition ID through the other endpoints. Supply query parameters as appropriate for the search (e.g., name, docket date, jurisdiction).

## Input structure

Every task follows the same layout:

```
train_tasks/train_XXX/input/
├── prompt.txt                    ← The task prompt (role, target cases, instructions)
└── payloads/
    ├── answer_template.json      ← The JSON schema the output must conform to
    ├── *.md                      ← Clerk notes, hearing notes, audit memos, form excerpts
    ├── *.json                    ← Finance extracts, petition summaries, intake facts
    └── *.csv                     ← Finance worksheets (if present)
```

## Master workflow

Follow this sequence for every task:

### Phase 1 — Load the template and local payloads

1. Read `answer_template.json` first. It defines the exact output shape: required top-level keys, item schemas, enum values, ordering rules, date/currency precision rules.
2. Read every other file in `input/payloads/`. These are the local ground truth — hearing notes, clerk memos, finance extracts, form excerpts, petition summaries, intake facts, worksheets.

### Phase 2 — Query the portal

3. For each target case, citation, or petition, query the relevant portal endpoints to cross-check the local materials.
4. Start with the direct-lookup endpoints (`/api/cases`, `/api/citations`, `/api/financial-petitions`). Then pull supporting records (`/api/charges`, `/api/docket-entries`, `/api/fee-schedules`, `/api/payment-policies`, `/api/forms`). Use `/api/search` for anything not reachable by direct ID.
5. Record every discrepancy you find between the local payloads and the portal records.

### Phase 3 — Reconcile conflicts

6. For each discrepancy, determine the correct value using these resolution rules (in priority order):
   - The judge's in-courtroom statements (recorded in hearing notes) override stale portal data and draft worksheets.
   - A signed sentencing order (confirmed via `/api/docket-entries`) controls the disposition posture.
   - The active fee schedule (confirmed via `/api/fee-schedules`) overrides archived or stale amounts in finance queue extracts.
   - Current payment policy (confirmed via `/api/payment-policies`) overrides old worksheet fee lines and sticky-note annotations.
   - Portal CMS identity records override draft intake pages when no courtroom correction was noted.
   - Defense counsel designations from courtroom notes override calendar abbreviations (e.g., "APD" may mean appointed private defense, not public defender).

### Phase 4 — Build the answer

7. Construct the JSON output key by key, following the `answer_template.json` schema exactly.
8. Apply all enum constraints — never use a value not listed in the template's enum definitions.
9. Apply all ordering rules — sort each list as specified (typically by case_number or citation_number ascending).
10. Apply currency precision (two decimal places) and date format (ISO YYYY-MM-DD; datetimes ISO YYYY-MM-DDTHH:MM:SS).
11. Return JSON only — no markdown fences, no commentary.

## Reconciliation rules

### Identity and counsel audit

- When the local payload and portal disagree on defendant name or DOB, use the most authoritative source (signed order > hearing notes > portal CMS > finance queue). Document the conflict as an audit finding if the template includes audit sections.
- "PD" = public defender (government public defender office).
- "APD" or "appointed private" = private attorney paid by the county/jurisdiction, not the public defender office. Do not classify APD counsel as public defender.
- "RET" = retained counsel (client-paid private attorney).
- If counsel classification is ambiguous from the abbreviation alone, check the hearing notes or clerk memo for clarification.
- Do not borrow a DOB from a similarly-named defendant in prior search results. If the DOB is genuinely missing from all materials, use the placeholder `"TBD from case file"` or mark it as needing verification before entry.

### Charge reconciliation

- Distinguish between the charge as originally filed and the charge of conviction. If the state moved to amend (e.g., from a controlled-substance count to misdemeanor theft), the conviction count is the amended charge.
- If a departure was noted in a draft worksheet but the judge explicitly stated no departure finding should be entered, use "no departure" / the appropriate non-departure enum.
- If a charge was dismissed or nolle prossed, it does not contribute to the convicted-counts total.

### Fee and financial reconciliation

- Verify every fee against the current fee schedule from the portal. Stale amounts from older worksheets or archived schedules must be corrected.
- Do not post account-management fees, collection fees, late-payment fees, DMV fees, returned-check fees, restitution, copy fees, certification fees, court-reporter fees, or court-appointed-attorney fees unless the portal record, the current fee schedule, or the current payment policy directly supports them.
- If a finance queue extract carries an outdated assessment amount (e.g., a previous year's drug assessment), replace it with the current schedule amount.
- A public-defender user fee applies only when counsel is classified as public defender. If counsel is confirmed as appointed private or retained, do not post the PD user fee.

### Disposition posture

- A case is "disposed" only if a final signed order exists (confirmed via docket entries or hearing notes stating the signed order was handed to the clerk).
- If the judge did not sign the order, the case is not disposed — mark it as pending/deferred/continued and do not post financial entries.
- If the hearing notes say "hold financial entry until signed disposition order is available," follow that instruction: exclude the case from the financial register and list it in exclusions.
- Do not create a sentencing financial register entry for a case that is still deferred, continued pending, or awaiting a signed order.

### Departure findings

- A departure (durational or dispositional) must be stated by the judge on the record or in the signed order. A carry-forward label from a draft worksheet is not sufficient.
- If the judge expressly stated the sentence is top-of-range and no separate departure finding should be entered, use the non-departure enum.

## Payment plan rules

When the task requires structuring a payment plan:

- **Eligibility**: Use the current payment policy from `/api/payment-policies` to determine plan parameters (minimum monthly, maximum monthly, down-payment rules, intervals).
- **Budget review**: If a petition includes income and obligations, compute monthly disposable income (`monthly_income - total_monthly_obligations`). Compare the requested payment amount against disposable income and policy bands.
- **Support classification**: Classify as supported if the requested amount fits within the policy band and does not exceed disposable income. Classify as below/above policy minimum/maximum if outside the band. Classify as unsupported if the budget cannot sustain the payment.
- **Installment math**: When the total due does not divide evenly by the installment amount, compute the number of full installments, the final (remainder) payment amount, and the total number of installments.
- **Payment application order**: Use "fines_costs_only" when there is no restitution balance. Use "restitution_before_fines_costs" or "fines_costs_before_restitution" as directed by the petition note or payment policy.
- **Account fees in payment plans**: Check current policy before carrying any account-maintenance fee onto the order. If a counter worksheet still shows an old account-maintenance fee row, verify against policy and exclude it if unsupported.

## Form metadata rules

When the task involves court forms:

- Map local form excerpts to current portal form metadata via `/api/forms`. Use the current form ID, label, and revision from the portal.
- The form's account-reference field: if no separate case number or account number has been opened, use the citation number or case number as the account reference.
- Required form labels (e.g., "Case # / Account #", "Case/Account Balance", "Action Table(s) / Notes", "TERMS of PAYMENT") should be listed when the template asks for them.
- If an older form revision has an obsolete charge (e.g., a payment-plan service charge), do not carry it forward unless current policy supports it.

## Placeholder handling

- Use the exact placeholder `"TBD from case file"` for fields that are required by a form or template but genuinely absent from all available materials (local payloads and portal records).
- Fields that typically need placeholders when missing: SSN, driver license number, residence address, mailing address, phone number, probation officer name, probation office location, attorney contact details, judge contact details.
- Never invent identifiers, contact information, or party details.
- When listing missing fields for a placeholder case, list them alphabetically.

## Exclusions

When the template includes an exclusions or excluded-charges section:

- List cases that are continued pending with no final order as excluded with reason `"continued_pending_no_final_order"`.
- List financial items excluded from the balance: unsupported fees, stale charges, charges with no triggering event.
- For excluded charges, provide the reason (e.g., `"stale_schedule"`, `"unsupported_post_disposition"`, `"not_in_hearing_order"`, `"not_current_policy"`, `"no_triggering_event"`).

## Enum discipline

- Every string value that the template defines as an enum must match exactly — same case, same underscores, same spelling.
- Do not create ad-hoc values. If none of the allowed enum values fits, examine whether a different field's enum applies, or whether the value should be `"verify_before_entry"` (when the template offers that option).
- When the template lists allowed values for a field, use only those values.

## Formatting rules

- **Currency**: All money values are numbers with exactly two decimal places (e.g., `150.00`, `0.00`).
- **Dates**: ISO 8601 `YYYY-MM-DD` (e.g., `2025-06-09`).
- **Date-times**: ISO 8601 local `YYYY-MM-DDTHH:MM:SS` (e.g., `2024-10-10T09:00:00`).
- **Null dates**: Use `null` when no date should be entered for a field (e.g., a case with no disposition date).
- **Sorting**: Apply the ordering rules declared in the template for each list. Default sort order is ascending by the primary identifier (case_number, citation_number, or petition_id).

## Jurisdiction contexts

This skill handles work across multiple jurisdictions. The operating rules above apply universally. When a task references a specific jurisdiction's forms or policies (e.g., "Gloucester County CC-1375," "Oregon 22nd Judicial District OR_22JD_PLAN," "Redwood County fee schedule," "Union County Circuit Court"), use the portal's `/api/forms`, `/api/fee-schedules`, and `/api/payment-policies` endpoints to retrieve the jurisdiction-specific metadata — do not assume one jurisdiction's rules apply to another.

## Answer delivery

- Return a single JSON object matching the `answer_template.json` structure exactly.
- Do not wrap the JSON in markdown code fences.
- Do not include explanatory prose, commentary, or "here is the answer" text.
- All required top-level keys from the template must be present.
- All lists must follow the template's ordering rules.
- All enum values must match the template's allowed values.
