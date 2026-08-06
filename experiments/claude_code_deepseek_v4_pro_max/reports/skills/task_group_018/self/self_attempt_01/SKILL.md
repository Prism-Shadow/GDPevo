# Court Clerk Operations — Closeout and Financial Reconciliation

## Purpose

Prepare court closeout, disposition, and financial-reconciliation packets by cross-referencing local case materials against the Court Operations Portal API and producing a structured JSON answer that follows an answer-template schema.

## When to use

The user is acting as a deputy clerk or court officer and needs to:

- Reconcile hearing notes, audit memos, finance queue extracts, or petition summaries against the live case-management system.
- Produce a clerk-ready JSON output matching a provided answer-template schema.
- Identify audit conflicts, stale fee amounts, unsupported charges, and missing identifiers.
- Decide which cases should be **posted** (disposed with signed orders) and which must be **held** (pending, continued, deferred, or unsigned).

## Workflow

### Step 1 — Read the prompt

From the user's prompt extract:

- **Role context** — which court, which docket type (criminal sentencing, traffic violation, post-sentencing field packet, etc.).
- **Target identifiers** — case numbers, citation numbers, or petition IDs to be processed.
- **Relevant portal endpoints** — the prompt lists which `GET /api/*` endpoints are useful for this task. Only use endpoints the prompt names.
- **Local payload files** — every referenced payload under `input/payloads/` that the prompt mentions. Read every one of them.

### Step 2 — Read every local payload

Read each payload file completely. These are the local materials the clerk assembled before portal reconciliation. Typical payload types:

| Payload | Typical content |
|---|---|
| `hearing_notes.md` | Bench notes with defendant names, DOBs, counsel, pleas, sentences, and judge remarks. May contain shorthand, nicknames, or carry-forward errors. |
| `clerk_audit_memo.md` | Exceptions flagged by the audit clerk — identity mismatches, stale fee amounts, departure disputes, unsigned orders. |
| `finance_queue_extract.json` | Pre-loaded financial records from the queue. May contain draft amounts, incorrect counsel labels, or stale fee schedules. |
| `sentencing_intake_facts.json` | Conviction details, sentence components, probation terms, release dates. |
| `form_field_excerpt.json` | Form field groups and placeholder rules for jurisdiction-specific forms. |
| `payment_petition_budget.json` | Petitioner income, obligations, requested payment terms, intake limits. |
| `petition_summaries.json` | Multi-petition intake summaries with balances, requested terms, and counter notes. |
| `sentencing_probation_notes.json` | Disposition notes, charge details, probation report dates, missing identifier lists. |
| `hearing_closeout_note.md` | Traffic/citation closeout notes with plea, finding, payment-plan approvals. |
| `local_form_excerpt.md` | Local form labels, account-reference rules, and fee-policy notes. |
| `finance_memo_and_worksheet.csv` | Row-per-case worksheet with name, DOB, counsel code, outcome, costs, fines, and supervisor notes. |

### Step 3 — Read the answer template

Every task includes `input/payloads/answer_template.json`. Read it before querying the portal. It defines:

- **`required_top_level_keys`** — the sections you must return.
- **`ordering_rules`** — sort order for each section (typically by case number ascending).
- **Enums** — every constrained value the output may use. **Never output a value outside the declared enums.**
- **Field types** — currency (two-decimal number), dates (ISO YYYY-MM-DD), datetimes (ISO YYYY-MM-DDTHH:MM:SS), strings, integers, booleans.
- **`placeholder_rule`** — the exact placeholder string to use for missing values (e.g. "TBD from case file").

The answer template **is** the output contract. Construct every key and value exactly as it prescribes.

### Step 4 — Query the Court Operations Portal

Connect to the portal using the base URL from the environment configuration. Reference `portal-api-reference.md` for the full endpoint catalog. For each target case, citation, or petition, fetch the authoritative records.

**Query strategy:**

1. Fetch jurisdiction metadata if the prompt lists `/api/jurisdictions` and you need to confirm court codes or fee-schedule links.
2. Fetch each target case from `/api/cases` (or `/api/citations` for traffic matters).
3. For each case, fetch `/api/charges` to get the current charge records — these are authoritative for what was actually filed, amended, or dismissed.
4. Fetch `/api/docket-entries` to confirm whether final orders were signed and entered.
5. Fetch `/api/fee-schedules` to get **current** fee amounts — do not rely on stale amounts from local worksheets.
6. Fetch `/api/payment-policies` when the task involves payment plans, installment orders, or account-fee decisions.
7. Fetch `/api/forms` when form IDs, labels, or field mappings need to match current portal versions.
8. Fetch `/api/financial-petitions` when petition IDs need cross-referencing.
9. Use `/api/search` as a fallback for verifying defendant identity, DOB, or counsel when the direct record is ambiguous.

**Important:** The portal is the **source of truth** for case status, charge records, current fee schedules, and form metadata. Local payloads are evidence but may carry stale, draft, or erroneous values.

### Step 5 — Reconcile and resolve conflicts

For each target matter, compare the local payloads against the portal records. Apply these rules in order:

#### Conflict resolution hierarchy

1. **Portal record (CMS)** — authoritative for: case status, current charges, fee schedule amounts, form IDs and labels, docket entry dates.
2. **Hearing notes / bench record** — override pre-loaded queue values when the judge's oral pronouncement contradicts a draft worksheet. A judge's statement in open court controls the sentence, plea, and disposition.
3. **Corroborating memo** — resolves identity mismatches (name, DOB, counsel) and flags stale departure labels or draft status entries.
4. **Unsigned orders** — if the final disposition order was **not signed**, do not post financial entries. Mark the case as `hold_unsigned_order`, `exclude_pending`, or the equivalent enum from the answer template.

#### Specific conflict categories

| Conflict | Resolution |
|---|---|
| **Identity mismatch** (name spelling, DOB difference) | Use the portal CMS identity. Flag in audit findings. |
| **Counsel mislabel** (e.g. "APD" copied as public defender but defense memo says appointed private) | Classify per the corroborating memo or judge's on-record clarification. Do not post a public-defender user fee for non-PD counsel. |
| **Stale fee amount** (e.g. drug assessment from an old schedule) | Replace with the current fee schedule amount from the portal. Flag the stale value in audit findings. |
| **Departure dispute** (draft says "departure" but judge said "top-of-range, no departure") | Remove the departure label. Mark `no_departure` or equivalent enum. |
| **Amended charge** (original count amended to a different offense) | Use the amended conviction charge from the hearing notes, not the original filed charge. |
| **DOB genuinely missing** (bench card blank, not in portal) | Use the placeholder exactly as specified in the answer template (e.g. "TBD from case file"). Do **not** borrow a DOB from similarly named defendants. |

### Step 6 — Financial reconciliation

For each disposed case, build the fee reconciliation using **current portal fee schedules**, not local worksheet amounts:

1. Start from the sentence pronounced in the hearing notes (fine, costs, assessments).
2. Cross-check each fee line against the current portal fee schedule.
3. Replace any stale amount with the current schedule value.
4. **Exclude** fees that have no support in the hearing record, current policy, or portal schedule — common unsupported fees include:
   - Late-payment fees (no triggering event in the record)
   - Collection referral fees (no referral in the record)
   - DMV notice/reinstatement fees (no DMV referral in the record)
   - Returned-check fees (no returned payment in the record)
   - Account-management / service charges (not in current policy)
   - Restitution (no restitution order)
   - Court-appointed-attorney fees (not ordered)
   - Traffic-school program fees (not ordered)
5. **Hold** financial entry for any case without a signed final order.

### Step 7 — Assemble the output

Build the JSON output to match the answer template exactly:

- **Section order**: Follow `required_top_level_keys` in order.
- **Item order**: Sort by the field specified in `ordering_rules` (typically `case_number` or `citation_number` ascending).
- **Enums only**: Every constrained field must use one of the allowed enum values. Do not substitute prose, free text, or invented values.
- **Currency**: Numbers, not strings, rounded to exactly two decimal places. Use `0.00` not `0` or `"0.00"`.
- **Dates**: ISO 8601 `YYYY-MM-DD`. Use `null` where the template allows null for dates (e.g. no disposition date for pending cases).
- **Datetimes**: ISO 8601 local `YYYY-MM-DDTHH:MM:SS`.
- **Placeholders**: Use the exact placeholder string (e.g. `"TBD from case file"`) for genuinely missing identifiers — SSN, driver's license number, addresses, phone numbers, probation officer names, office locations. Never invent these values.
- **Register totals**: Sum across disposed cases only. Exclude held/pending cases from financial totals.

### Step 8 — Verify completeness

Before returning the output, check:

- [ ] Every target case/citation appears in the output.
- [ ] Every `required_top_level_key` section is present.
- [ ] Every required field within each item is populated.
- [ ] All enum-constrained fields use declared values.
- [ ] Sort order matches the template's `ordering_rules`.
- [ ] Currency values are numbers with two decimal places.
- [ ] Dates are ISO format or null where allowed.
- [ ] No invented identifiers — missing fields use the declared placeholder.
- [ ] Held/pending cases are not included in register/financial totals.
- [ ] Unsupported fees are listed in the exclusions section with reason codes.

## Operating principles

### Always

- Use the portal as the source of truth for case status, charges, fee schedules, and form metadata.
- Use hearing notes to override draft/queue values when the judge's oral pronouncement differs.
- Use the exact enum values from the answer template — never invent, paraphrase, or substitute.
- Hold financial entry for any case without a signed final order.
- Exclude fees that lack support in the hearing record, current policy, or portal schedule.
- Use the declared placeholder for genuinely missing identifiers.

### Never

- Never invent a DOB, name, SSN, address, phone number, driver's license number, probation officer, or office location.
- Never borrow a DOB or identifier from a similarly named defendant.
- Never post a public-defender user fee when counsel is confirmed as appointed-private or retained.
- Never carry forward a stale fee amount when a current portal schedule is available.
- Never add late fees, collection fees, DMV fees, account-management fees, restitution, or other charges unless the hearing record or current portal policy explicitly supports them.
- Never output a value outside the answer template's declared enums.
- Never wrap the JSON output in markdown code fences unless the template explicitly allows it.

## Supporting files

- `portal-api-reference.md` — Full catalog of Court Operations Portal endpoints and their behavior.
