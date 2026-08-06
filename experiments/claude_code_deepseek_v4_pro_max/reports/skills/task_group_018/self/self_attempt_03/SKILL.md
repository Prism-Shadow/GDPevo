# Court Clerk Disposition Closeout Skill

## Purpose

Perform court clerk disposition-closeout tasks for criminal and traffic dockets. Given local case materials and API access to a Court Operations Portal, produce a single JSON answer conforming to the provided answer template schema. Reconcile hearing notes, clerk memos, intake sheets, finance extracts, and portal records into a clerk-ready register entry.

## Environment Setup

### Base URL

All API calls use `http://task-env:9018/` as the base URL. Never use `localhost`, `127.0.0.1`, or any URL from an `env/setup.sh` script — the base URL from the task environment always takes precedence.

### Authentication

No credentials are required. All endpoints are unauthenticated GET requests.

### Available Endpoints

The task prompt enumerates which endpoints are usable. The full set of possible endpoints includes:

- `GET /api/jurisdictions`
- `GET /api/cases`
- `GET /api/charges`
- `GET /api/docket-entries`
- `GET /api/citations`
- `GET /api/fee-schedules`
- `GET /api/payment-policies`
- `GET /api/forms`
- `GET /api/financial-petitions`
- `GET /api/search`

Only call endpoints listed in the task prompt as useful or relevant.

## Input Materials

Every task supplies:

1. **A prompt** — describes the court, docket date, target cases/citations, and which endpoints to consult.
2. **Local payloads** — hearing notes, clerk audit memos, finance queue extracts, intake sheets, form excerpts, petition summaries, sentencing/probation notes, and/or worksheets. These are in the `input/payloads/` directory.
3. **An answer template** — `input/payloads/answer_template.json`. This defines the exact output schema, required keys, enums, ordering rules, and formatting rules.

## Output Rules

### Schema Compliance

Return exactly one JSON object matching the answer template schema. Do not include markdown fences, commentary, or extra top-level keys beyond those in the template's `required_top_level_keys`.

### Enum Discipline

When the answer template defines an enum for a field, use one of the allowed values exactly as written. Never substitute a prose description for an enum value. If no enum value fits the evidence, use `verify_before_entry` (when available) or the closest applicable value.

### Formatting

- **Currency**: All monetary values are numeric, rounded to two decimal places (cents). No currency symbols or commas in the JSON values.
- **Dates**: ISO 8601 `YYYY-MM-DD`.
- **Date-times**: ISO 8601 local datetime `YYYY-MM-DDTHH:MM:SS`.
- **Null**: Use `null` where a date, datetime, or value is genuinely not applicable or not available (not `"N/A"`, not `""`).

### Ordering

Follow the ordering rules specified in the answer template. Typical patterns:
- Sort entries by case number or citation number ascending.
- Sort within sub-arrays (excluded charges, placeholder fields, missing fields) by the designated key ascending.

## Core Operating Rules

### 1. Evidence Hierarchy

When sources conflict, resolve using this priority order:

1. **Courtroom hearing notes / bench orders** — what the judge actually pronounced and signed in open court. This is the highest authority.
2. **Portal records** — authoritative for current fee schedules, payment policies, case records, form metadata. Use the portal to validate or override stale/archived local figures.
3. **Clerk audit memos** — identify known conflicts and provide resolution guidance. Follow the memo's resolution instruction when it cites a specific source.
4. **Finance queue extracts / draft worksheets** — these are queued or draft data subject to override. Never treat a draft as a final order. Always cross-check against hearing notes and portal.

### 2. Identity Verification

For every target case or citation:

- Cross-check defendant name and date of birth across all available sources (hearing notes, finance queue, intake sheets, portal records).
- When a DOB is missing or blank, use the placeholder `"TBD from case file"` — never borrow a DOB from a similarly-named defendant in search results.
- When the answer template offers an `identity_action` enum, select the action that matches the verification status: use the CMS/portal value when confirmed, use the placeholder when genuinely missing, and exclude/pend when unverified.
- If the hearing notes correct a name (e.g., a bench sheet has a slash or alternate spelling), the hearing notes' correction prevails.

### 3. Counsel Classification

Classify counsel using these rules:

| Label in source | Classification | PD user fee applies? |
|---|---|---|
| PD, Public Defender office | `public_defender` | Yes |
| APD (when record shows appointed private, not PD office) | `appointed_private` | No |
| RET, retained counsel named | `retained` | No |
| Unknown or ambiguous | `unknown` | Verify before applying |

- The abbreviation "APD" on a calendar or worksheet is ambiguous. Check the hearing notes and defense memos: if the judge or memo states the attorney is appointed private counsel paid by the county (not the public defender office), classify as `appointed_private`, not `public_defender`.
- A public defender user fee is only postable when counsel is confirmed as the public defender office.
- If a finance queue labels counsel as PD but a defense cover memo or hearing clarifies appointed private, the hearing/memo overrides the queue.

### 4. Case Status and Draft Detection

- A case is only `disposed` if the judge signed a final sentencing or disposition order in open court.
- A case that was continued, had no plea accepted, had no sentence pronounced, or had its order explicitly not signed is `pending` or `continued` — do not post financial entries for it.
- A draft disposition worksheet is not a final order. If the hearing notes say the judge did not sign, or the order was held, exclude the case from the disposed register.
- Status actions map as follows:
  - Final signed order + sentence pronounced → `enter_disposition` / `disposed_enter`
  - No final signed order → `hold_unsigned_order` / `exclude_no_final_order`
  - Matter continued → `no_closeout` / `pending_exclude`

### 5. Fee Reconciliation

#### Verify Schedule Currency

- Fee schedules have revision dates. A case disposed in a given year must use the schedule active at disposition time, not an older/archived amount.
- If the finance queue or a local worksheet carries an amount labeled "archived" or from a prior year, replace it with the current portal schedule amount.
- Drug assessment fees, court costs, and fine tiers must all be verified against the current schedule.

#### Fee Posting Rules

For each case, classify every fee item as `post`, `exclude`, or `hold`:

- **Post**: The fee is supported by the sentencing order, the applicable statute, and the current fee schedule.
- **Exclude**: The fee has no basis in the hearing record, no triggering event, no current policy support, or belongs to a category the task materials explicitly prohibit. Common excluded categories:
  - Account-management / account-maintenance fees (unless current policy explicitly supports them)
  - Collection referral fees
  - Late-payment fees
  - DMV notice / reinstatement fees
  - Returned-check fees
  - Restitution (when no restitution order exists)
  - Copy / certification fees
  - Court-appointed-attorney fees (when counsel was not court-appointed, or when no such fee is ordered)
  - Court-reporter fees
  - Traffic-school program fees
- **Hold**: The fee is contingent on a future event (e.g., a pending signed order).

#### Specific Fee Triggers

- **Public defender user fee**: Post only when counsel is confirmed as the public defender office and the court did not waive the fee.
- **Drug assessment**: Post on controlled-substance convictions when the current schedule supports it. The judge's oral instruction to include it in open court is binding.
- **Lab fee**: Post on controlled-substance convictions when the worksheet, hearing notes, or judge's instruction supports it. If a worksheet omitted it but the judge mentioned it on the record, the judge's instruction prevails.
- **Fine**: Post the amount announced by the judge. If the judge waived the fine, post zero.
- **Court costs**: Post the current schedule amount. Costs are generally mandatory unless the judge expressly waived them.

### 6. Charge and Disposition Handling

#### Charge Amendments

- If the state moved to amend a charge before plea (e.g., from a controlled-substance felony to a misdemeanor theft), the conviction is on the amended charge, not the original filing. The original charge wording is not the conviction count.
- When classifying the departure status for an amended-to-misdemeanor conviction, use `not_evaluated_misdemeanor` or the equivalent enum from the answer template.

#### Plea to Charge Mapping

- Each count needs: plea entered, charge disposition, fine, jail days (imposed and suspended), probation months, and departure status.
- A guilty plea results in a `guilty` charge disposition.
- A no-contest plea with the court finding guilt also results in a `guilty` charge disposition.
- A dismissed count has plea `none` and disposition `dismissed` or `nolle_prosequi`.

#### Departure Status

- The departure status must match what the judge actually pronounced, not what a legacy screen or draft worksheet carried forward.
- If the judge expressly stated "no departure finding" or "top of the range," use `no_departure` or `none`.
- If a draft worksheet or legacy screen labeled the case as a departure but the judge said otherwise, the hearing record overrides.
- For misdemeanor convictions where departure evaluation is not applicable, use `not_evaluated_misdemeanor` or the equivalent enum.

### 7. Docket Entry Construction

Each disposed case produces at least one docket entry with:
- Entry date (the disposition date)
- Entry type (e.g., `sentencing_order`, `disposition_hold`)
- Summary code reflecting the key actions on the case
- Financial total matching the sum of posted fees for that case

Use summary codes that capture the material characteristics:
- `conviction_no_pd_fee` — conviction entered, no PD fee applicable (appointed private or retained counsel)
- `conviction_drug_assessment` — conviction includes a drug assessment fee
- `conviction_no_departure` — conviction with no departure finding
- `hold_unsigned_order` — case held pending signed order

A case with no signed final order gets a `disposition_hold` entry with no financial total.

### 8. Payment Plan Construction

When the task requires a payment plan or installment order:

#### Budget Supportability

- Compute monthly disposable income: `monthly_income - total_monthly_obligations`.
- Compare the requested monthly payment to the disposable income.
- Compare the requested amount to any policy band (minimum and maximum monthly amounts from the payment policy).
- Classify support:
  - `supported_by_budget` / `supportable` — requested amount ≤ disposable income and within policy band.
  - `below_policy_minimum` — requested amount is below the policy minimum.
  - `above_policy_maximum` — requested amount exceeds the policy maximum.
  - `unsupported_by_budget` — disposable income is negative or insufficient.

#### Schedule Calculation

Given: total due, down payment, regular installment amount, first due date.

- Compute the balance after down payment: `total_due - down_payment`.
- Full installments: `floor((total_due - down_payment) / regular_installment_amount)`.
- Final payment: `(total_due - down_payment) - (full_installments * regular_installment_amount)`. If this is zero, the last full installment is the final payment and there is no reduced final amount.
- Total installments: `full_installments + (final_payment > 0 ? 1 : 0)`.
- Compute the final due date by incrementing the first due date by `(total_installments - 1)` months. Use same-day-of-month; if that day doesn't exist in the target month, use the last day of the target month.

#### Payment Application Order

When both restitution and fines/costs are present:
- `restitution_before_fines_costs` — restitution paid first.
- `fines_costs_before_restitution` — fines and costs paid first.
- `fines_costs_only` — no restitution balance.
- Follow the petitioner's stated preference or local policy if specified in the materials.

#### Return-to-Court

- Set the return-to-court date as provided in the petition or local materials.
- Set the return-to-court trigger based on the petition's review type: `nonpayment` for initial installment agreements with a review date, `default_review` for subsequent reviews, `none` if no return date is set.

### 9. Placeholder Handling

The placeholder value is always `"TBD from case file"`. Use it for fields that are required by a form or template but whose value is genuinely absent from all available materials.

Fields that commonly require placeholders when missing:
- SSN
- Driver's license number
- Residence address
- Mailing address
- Phone number
- Probation officer name
- Probation office location
- Attorney contact details
- Judge name (when not in the record)

**Never invent**: identifiers, contact details, names, office locations, or any value not found in the case file, hearing notes, petition, or portal records.

When the template provides a `placeholder_fields` or `placeholder_cases` section, list every field that requires the placeholder, with the reason code:
- `missing_identifier` — SSN, driver's license, case/account number
- `missing_contact` — address, phone
- `missing_office_detail` — probation office location
- `missing_party_detail` — attorney name, judge name, probation officer

### 10. Exclusion Rules

#### Unsupported Financial Items

Exclude any fee, charge, or balance item that:
- Has no basis in the sentencing order or hearing record.
- Has no triggering event (e.g., a late fee with no late payment; a collection fee with no referral to collections; a DMV fee with no DMV action ordered).
- Belongs to a category the intake materials explicitly prohibit.
- Is from a stale/archived fee schedule that does not apply to the disposition year.
- Is an account-maintenance or administrative charge unless the current payment policy explicitly authorizes it.

#### Cases Excluded from Disposition Register

A case is excluded from the disposed register when:
- No final order was signed.
- The matter was continued to a future date.
- No plea was accepted and no sentence was pronounced.

For excluded cases, record:
- The case number.
- The exclusion reason (use the enum from the template).
- A next status check date (the continued hearing date, if known).
- `financial_posting_allowed: false`.

### 11. Batch and Register Totals

At the end of every closeout, compute aggregate totals:

- **Case counts**: Number of cases disposed vs. held/pended.
- **Financial totals**: Sum of fines, court costs, assessments, user fees, lab fees — each as a separate subtotal — across all posted cases.
- **Grand total**: Sum of all posted financial amounts across all disposed cases.

Every dollar in the register totals must reconcile to the sum of individual case fee entries. If the template provides separate total fields for each fee category, report each category's sum separately.

### 12. Form Metadata Verification

When the task references specific forms (by form family, ID, or local label):

- Use the portal's `/api/forms` endpoint to retrieve current form metadata.
- Cross-check the form ID, form label, and field requirements against both local form excerpts and portal data.
- The portal provides the authoritative current revision; a local form excerpt may be an older copy.
- For form field references (e.g., account reference fields, balance labels, terms labels), confirm the required labels are present in the current portal form metadata.
- If a local excerpt describes an obsolete fee or charge in an older revision, verify against current court policy before including it.

### 13. Cross-Source Reconciliation

For each target case or citation, perform these checks:

| Check | Sources to compare | Action on conflict |
|---|---|---|
| Identity (name, DOB) | Hearing notes vs. finance queue vs. portal | Hearing notes prevail; use placeholder if all sources lack a value |
| Counsel type | Hearing notes vs. finance queue vs. defense memo | Hearing notes and defense memos prevail over queue labels |
| Charge conviction | Hearing notes vs. portal charges | Amended charge per hearing notes is the conviction charge |
| Fee amounts | Hearing notes vs. finance queue vs. portal fee schedule | Current portal schedule overrides stale/archived local amounts |
| Departure status | Hearing notes (judge's statement) vs. queue/draft labels | Judge's oral pronouncement prevails over draft labels |
| Case status | Hearing notes (signed order?) vs. queue status | Signed order = disposed; no signed order = pending/hold |
| Form metadata | Local form excerpt vs. portal forms | Portal has current revision; local excerpt may be stale |

### 14. API Query Patterns

When querying the portal:

- **By case number**: Use `/api/search` with the case number as a query parameter, or use `/api/cases` with a filter.
- **By jurisdiction**: Use `/api/jurisdictions` to confirm the jurisdiction code and retrieve jurisdiction-level settings.
- **Fee schedules**: Query `/api/fee-schedules` for the jurisdiction to get current amounts. Match the schedule to the disposition year.
- **Payment policies**: Query `/api/payment-policies` for the jurisdiction to get policy bands (min/max monthly), account fee rules, and payment application order defaults.
- **Forms**: Query `/api/forms` with the form family or ID to get current labels and field requirements.
- **Citations (traffic)**: Use `/api/citations` for citation-specific records.
- **Financial petitions**: Use `/api/financial-petitions` for petition records and status.
- **Charges and docket entries**: Use `/api/charges` and `/api/docket-entries` for per-case charge detail and procedural history.

### 15. Common Pitfalls

- **Do not** post financial entries for a case whose final order was not signed, even if the finance queue shows draft amounts.
- **Do not** apply a public defender user fee when counsel is appointed private (even if the queue or calendar abbreviates as "APD").
- **Do not** use an archived/stale fee schedule amount when a current schedule is available from the portal.
- **Do not** carry forward a departure finding from a draft worksheet when the judge explicitly stated no departure.
- **Do not** borrow identity data (DOB, name) from search results for a different defendant.
- **Do not** add unsupported administrative fees (account management, collection, late, DMV, copy, certification) unless the portal record or current policy directly supports them.
- **Do not** invent missing identifiers or contact details — use the placeholder.
- **Do not** treat a continued/draft matter as disposed.
- **Do not** include markdown or commentary in the JSON output — return pure JSON matching the template.
