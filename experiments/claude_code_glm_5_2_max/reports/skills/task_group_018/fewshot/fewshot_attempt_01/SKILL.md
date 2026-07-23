# Court Operations Closeout Skill

Reusable method for producing clerk-ready **closeout packages** — structured JSON that reconciles a batch of court matters after disposition. The inputs are always: (1) a prompt naming the batch and target cases/citations/petitions, (2) local clerk payloads (hearing notes, audit memos, finance extracts, worksheets, form excerpts), and (3) a live **Court Operations Portal** reachable over the network. The output is always one JSON object matching the per-task `answer_template.json`.

Use this skill whenever you must reconcile courtroom notes or finance extracts against a court portal, resolve audit conflicts (identity, counsel, status, fee schedule, departures), post or hold financial entries, build payment plans, or fill referral/license/installment forms — and return a single schema-shaped JSON object.

## What you need from the task directory

For each run, locate and read, before doing anything else:

1. `input/prompt.txt` — the batch, the court, the target case/citation/petition identifiers, and which portal endpoints are useful.
2. `input/payloads/answer_template.json` — **the authoritative output schema**. It declares the required top-level keys, per-item required keys, enums, ordering rules, and the currency/date conventions. Every field you emit must be valid against this template. Treat it as the contract.
3. Every other file under `input/payloads/` — clerk notes, audit memos, finance queue extracts, worksheets, form/form-field excerpts, petition summaries. Read all of them; conflicts between them are the point of the task.

Reach the environment **only** through `environment_access.md` (base URL and the allowed `GET /api/...` endpoint list). Do not attempt to read server-side files. The portal is open within the network — no credentials.

## The reconciliation method

Work the same six steps on every matter in the batch. Do not skip ahead; the steps are ordered because later steps depend on decisions made earlier.

### 1. Inventory the batch against the schema
Parse `answer_template.json` first. Write down: the required top-level keys, the per-item required keys, every enum and its allowed values, the sorting rules, and the currency/date rules (currency = dollars to two decimals; dates = ISO `YYYY-MM-DD`; datetimes = `YYYY-MM-DDTHH:MM:SS`; use `null` only where the template explicitly allows it). List the target identifiers from the prompt. Every matter the prompt names must appear in the relevant output sections; nothing the prompt does not name should appear.

### 2. Pull the authoritative record from the portal
For each target identifier, query the case-management source of truth:
- `GET /api/cases?...` or `GET /api/search?q=<identifier>` for the canonical case/citation/petition record (defendant DOB, counsel classification and attorney name, status, jurisdiction code, disposition date).
- `GET /api/charges`, `GET /api/docket-entries`, `GET /api/citations`, `GET /api/financial-petitions` to confirm charges, docket text, citation detail, and petition metadata as relevant to the batch type.
- `GET /api/fee-schedules` for the **current** fee/court-cost/assessment amounts effective **on the disposition date** (filter by `jurisdiction_code`, `fee_type`, and effective dates; reject entries whose `end_date` has passed).
- `GET /api/payment-policies` for the jurisdiction's installment rules: `min_monthly`/`max_monthly`, `first_due_days` offset, `return_to_court_offset_days`, `account_fee`, restitution priority, and subsequent-petition rules.
- `GET /api/forms` for form metadata: `form_id`, label, placeholder instruction, and required fields.

The portal is the authority for identifiers, DOB, current fee amounts, and policy. Local payloads only describe what the clerk has on paper — they are the *values to be reconciled*, not the source of truth.

### 3. Resolve each conflict to a single corrected value
Compare local payloads against the portal and the signed on-the-record notes. For every conflicted field, record an audit finding (when the schema has an audit section) and pick the corrected value using this **source hierarchy**:

| Field conflicted | Authoritative source | Notes |
|---|---|---|
| Defendant DOB / identity | Portal (CMS) | Use the case file DOB. Never borrow a DOB from a similarly-named party in search results. If genuinely missing and required, use the placeholder and a verify flag. |
| Counsel classification / attorney name | Corroborating record (defense memo, on-record clarification) | Calendar labels like "APD" or "PD" are often wrong — "APD" can mean appointed-*private*, not public defender. The defense/cover memo or judge's on-record statement controls. |
| Charge count / amendment / departure | Hearing notes (bench record) | Amendments to a lesser count replace the filed count; a judge saying "top of the range, no departure" overrides a draft worksheet's departure label. |
| Fee / assessment / court-cost amount | Current fee schedule effective on disposition date | Stale amounts ("archived", prior-year worksheets, old local tables) are rejected. A prior-year disposition uses that year's schedule; a current-year disposition uses the current schedule. |
| Final status / order signed | Signed final order | If no sentencing/disposition order was signed in open court, the matter is **deferred/continued/pending**, not disposed. Do not enter a final disposition or post financials. |

Record findings using the schema's enum `resolution_source` (e.g. `use_cms`, `use_hearing_notes`, `use_corrob_memo`, `use_fee_schedule`, `hold_unsigned_order` / `verify_before_entry` / `exclude_pending` — use whichever enum the template defines).

### 4. Gate financial posting on finality
For each matter decide the posting status *before* computing amounts:
- **Final order signed → post.** Build the disposition, charge summary, and fee items from supported amounts only.
- **No signed final order → hold or exclude.** Emit the hold/exclude status with zero financials (`fee_status` hold/exclude, empty fee items, `total_due`/`total` `0.00`, docket entry type `disposition_hold`/`CONTINUED_NO_DISPOSITION`, etc.). Never post a financial register entry for a deferred/continued matter, even if a draft worksheet lists fines.

### 5. Build financial entries and payment plans from supported amounts only
**Amount due at disposition** = supported fine + supported court cost + supported statutory assessments (drug/crime-lab) + supported user fees. Drop every unsupported line:
- Stale/prior-year schedule amounts → replace with the current effective amount.
- Account-management, collection, late-payment, returned-check, DMV, restitution, copy, certification, traffic-school, court-appointed-attorney, court-reporter fees → **exclude** unless a portal schedule, policy, or signed order directly supports them. Carry excluded items in the schema's `excluded_charges` / `excluded_financial_items` / `exclusions` section with the matching reason code (e.g. `not_current_policy`, `no_triggering_event`, `stale_schedule`, `unsupported_post_disposition`, `not_in_hearing_order`, `no_order_or_policy_support`, `not_part_of_balance`). Where the schema requires an excluded item amount, use `0.00`.

Do not let the unsupported-charge leakage into the balance: `unsupported_charge_total_included` is `0.00` when everything stale has been correctly excluded.

**Payment plans** (when the schema has a plan/installment section): compute from the corrected amount due and the policy, not from round numbers in the notes.
- `monthly_payment` / `installment_amount` = the approved amount.
- `full_payment_count` / `full_installment_count` = number of full installments = `floor(amount_due / installments amount)`.
- Remainder `= amount_due - (full count × installment amount)`; if remainder > 0, the final payment is that remainder (a small last installment) and `total_installments = full count + 1`; if remainder == 0, final payment equals a normal installment and `total_installments = full count`.
- `first_due_date` = the policy/approved start date (policy `first_due_days` after disposition, or the specified anchor).
- `final_due_date` = the last installment date (count forward from first due by the interval). When computing the same-day-next-month cadence for monthly intervals, advance month-by-month.
- `down_payment` = policy-applicable amount (often `0.00`).
- `return_to_court_date` = the candidate return date given, or disposition date plus `return_to_court_offset_days` per policy; set the trigger (e.g. `nonpayment`) per policy.
- Classify budget support: installment within `[min_monthly, max_monthly]` and ≤ disposable income (income − obligations) → `supported`/`supportable`; below minimum → `below_policy_minimum`; above maximum → `above_policy_maximum`; over disposable income → `unsupported_by_budget`.

**Payment application order**: when restitution exists, follow the policy's restitution-priority rule (`restitution_before_fines_costs`, or `fines_costs_only` / `restitution_before_fines_costs`/`fines_costs_before_restitution` per the schema's enum) and the petitioner's request when the policy permits.

### 6. Fill forms with placeholders, never inventions
For referral/license/installment orders, populate fields from the case file and portal. For any field a form **requires but the materials do not supply** — identifiers (SSN, driver license number), contact details (addresses, phone), office details (probation officer name/location), party details — use the **exact placeholder string the materials define** (the standard is `TBD from case file`) and record the field in the schema's `placeholder_fields` / `placeholder_cases` section with the matching reason code (`missing_identifier`, `missing_contact`, `missing_office_detail`, `missing_party_detail`). Sort placeholders as the template specifies (usually by field name ascending, or by case number then field).

Hard rules:
- **Never invent** an identifier, address, phone, license, attorney, judge, or probation-office contact.
- **Never borrow** a value from a different party or a similarly-named search hit.
- One placeholder *string* per the materials; one *reason code* per the schema enum.
- License suspension effective date follows the basis the record or policy names (conviction date unless the schema/record says release date or petition date); suspension end = start + months.

## Formatting and ordering — every output

- One JSON object. No markdown, no prose, no trailing text. Valid JSON.
- Currency: numbers, two decimals (e.g. `150.00`). `0.00` for excluded/empty, never `0` or `null` unless the template allows `null`.
- Dates: ISO `YYYY-MM-DD`. Datetimes: ISO local `YYYY-MM-DDTHH:MM:SS`. Use the template's allowed `null` only for genuinely-absent disposition dates on held/excluded matters.
- Enums: emit the **exact** allowed token from `answer_template.json`. Never substitute prose for an enum value, and never invent a token not in the list.
- Lists sorted exactly as the template's `ordering_rules` / `instructions` specify (typically by case_number/citation_number/petition_id ascending; excluded items by their code ascending; placeholders by field name ascending). When several sort keys apply, apply in the order given.
- Totals (register/batch) **sum only the posted matters**. Held/excluded matters contribute zero. Re-derive every total from the items you emitted — do not trust worksheet batch totals, which often still contain stale lines.

## Gate before you finish

Run this checklist against the emitted JSON:
1. Every required top-level key present; no extra keys the template does not allow.
2. Every item carries every required key; every enum field is an allowed token.
3. Every matter the prompt named appears where it should; no extra/unprompted matters.
4. Every stale, unsupported, or drafted value from the local payloads is either corrected to the portal/record value or moved to an exclusion section with a reason code — none survives into a posted total.
5. Held/excluded matters have zero financials and the hold/exclude docket action; nothing posted for them.
6. Every total equals the sum of its components (recompute, don't copy).
7. No invented identifiers or contacts; every genuinely-missing required field uses the exact placeholder string and is recorded in the placeholder section.
8. Dates ISO; currency two-decimal; lists sorted per template.

## Reference files in this skill

- `references/portal_endpoints.md` — the allowed portal endpoints, what each returns, and the query patterns that resolve the most common conflicts.
- `references/reconciliation_playbook.md` — worked decision rules for each conflict type (identity, counsel, charge/amendment, departure, fee schedule, status/finality) with the authoritative source and the enum to emit.
- `references/financial_and_plan_math.md` — the exact arithmetic for amount-due, installment counts, remainder last payment, due dates, totals, and budget-support classification.
- `references/validation_checklist.md` — the pre-submit checklist as a copyable ordered list, plus the common failure modes (stale leakage into totals, posting on a deferred matter, invented placeholders, enum prose substitution).

## When the inputs don't match this shape

If the task directory lacks `answer_template.json`, or `environment_access.md` names a different base URL / endpoint set, or you find material in `/work` that is not the expected `train_tasks/`, `train_answers/`, and `environment_access.md` — **stop**, do not emit an answer, and write `contamination_report.txt` at the work root describing the unexpected material.
