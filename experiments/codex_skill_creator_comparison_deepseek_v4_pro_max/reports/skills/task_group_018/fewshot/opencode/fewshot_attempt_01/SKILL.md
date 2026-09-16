---
name: court-clerk-closeout
description: Court docket closeout, sentencing reconciliation, and financial posting for criminal, traffic, and civil citation matters. Use when the user asks about court docket closeout, sentencing packages, financial reconciliation for court cases, post-disposition packets, traffic citation closeout with payment plans, or any task that involves cross-referencing local hearing notes, audit memos, finance worksheets, or petition summaries against a Court Operations Portal API. Trigger on mentions of circuit court, county court, docket closeout, sentencing order, fee reconciliation, court financial entry, payment plan for fines/costs, probation referral forms, license suspension orders, or placeholder handling for missing court identifiers. Even if the user does not use the exact phrase closeout, use this skill whenever they need to reconcile court case records with multiple conflicting local sources and produce structured financial or disposition JSON output.
---

# Court Clerk Docket Closeout

Reconcile court case materials (hearing notes, audit memos, finance worksheets, petitions) against an authoritative Court Operations Portal API and produce structured JSON closeout packages.

## Core principle

Every closeout task is an exercise in **cross-source reconciliation**. Local materials (hearing notes, clerk memos, finance queue extracts, petition summaries) contain draft values, carry-forward errors, and bench shorthand that must be validated against the authoritative portal. The portal is the system of record for identity, fees, and case metadata. Local notes provide courtroom context that helps detect and resolve conflicts, but they never override portal fee schedules or payment policies.

## When to use this skill

Use this skill when the task involves:

- Multiple case numbers needing disposition and financial entries posted to a register
- Local payloads with conflicting or draft data (audit memos, hearing notes, finance worksheets, petition summaries, sentencing intake facts)
- A Court Operations Portal API with endpoints like `/api/cases`, `/api/charges`, `/api/citations`, `/api/fee-schedules`, `/api/docket-entries`, `/api/payment-policies`, `/api/forms`, `/api/financial-petitions`, `/api/search`
- An `answer_template.json` that defines the expected output schema with required keys, enums, ordering rules, currency precision, and date formats
- The need to detect audit conflicts, correct case status, reconcile fees against current schedules, produce register totals, and optionally compute payment plans, probation referrals, or license suspension orders

Do not use this skill for tasks that involve only a single clean data source with no conflicts to resolve, or tasks that do not produce structured JSON output against a provided answer template.

## Workflow

Follow this five-phase process for every closeout task. Do not skip phases.

### Phase 1: Ingest the contract

Read the task prompt fully. Note which case numbers or citation numbers are in scope.

Read every file under the payloads directory. Pay special attention to:

- **answer_template.json** — This is your output contract. Note every required top-level key, enum set, ordering rule, currency precision (two decimal places), and date format (ISO YYYY-MM-DD). The template defines the exact shape of correct output.
- **Hearing notes, audit memos, finance extracts, petition summaries, sentencing intakes** — These are your local evidence. They contain bench shorthand, draft values, carry-forward errors, and courtroom facts that the portal may not yet reflect.

Read the environment access document (typically `environment_access.md` or the task prompt itself) to get the portal base URL and available endpoints.

### Phase 2: Query the portal

Query the portal for every relevant data domain. Parallelize independent queries.

At minimum, query for each case or citation in scope. Use `/api/cases`, `/api/citations`, or `/api/search` with case-number parameters. Then expand to related domains:

- `/api/charges` — charge records for each case
- `/api/docket-entries` — existing docket entries for each case
- `/api/fee-schedules` — current fee amounts for the jurisdiction
- `/api/payment-policies` — which fees are allowed and how payments apply
- `/api/forms` — form metadata when the task involves probation referrals, license orders, or installment agreements
- `/api/financial-petitions` — existing petitions when applicable
- `/api/jurisdictions` — jurisdiction metadata when needed

The portal data is authoritative. When portal data and local data conflict:
- Portal wins for identity (name spelling, DOB), fee amounts, and case metadata — unless local hearing notes or a corroborating memo provide a specific correction backed by paper-file evidence
- Local hearing notes win for judge statements about pleas, findings, sentences, and departure rulings
- Local corroborating memos win when they specifically correct a portal record based on evidence the portal does not yet reflect (e.g., a defense cover memo confirming counsel type)

### Phase 3: Detect and classify conflicts

For every case, compare portal records against local materials. Classify each conflict:

| Conflict type | What to look for |
|---|---|
| **identity** | Name spelling differs between sources; DOB differs; finance queue carries a typo |
| **counsel** | Attorney classification wrong (e.g., "PD" label used for appointed private counsel, "APD" abbreviation used for non-public-defender) |
| **status** | Case marked "disposed" in a finance queue but the judge withheld signature, or a case is continued pending with no final order |
| **fee_schedule** | Fee amounts from a legacy or draft worksheet that do not match the current portal fee schedule; fee omitted from a worksheet that should be posted |
| **departure** | A departure finding (dispositional or durational) on a draft worksheet that the judge did not adopt in open court |

For each conflict, determine three things:
1. The **conflicted value** — what the draft/queue/worksheet currently says
2. The **corrected value** — what should be posted based on the best evidence
3. The **resolution source** — the evidence that settles the conflict

Use the resolution source enums from the answer template. Common sources:
- `use_cms` — portal case management system is authoritative
- `use_hearing_notes` — judge's spoken ruling or bench note controls
- `use_corrob_memo` — corroborating memo corrects a stale or incorrect record
- `use_fee_schedule` — current portal fee schedule corrects a legacy amount
- `hold_unsigned_order` — no signed order exists, so hold
- `verify_before_entry` — data cannot be resolved from available sources; flag for manual verification

### Phase 4: Build the structured output

Use the `answer_template.json` as the exact contract. Build each section in the order the template specifies.

#### Audit findings

List every conflict found, sorted by case number then by conflict type (per template ordering rules). Each entry identifies the case, the issue type, what was wrong, what is correct, and which source resolved it.

#### Case dispositions

For every case in scope, record the final disposition state:

- **Disposed cases** — enter the disposition date (the hearing date), defendant name (corrected spelling), DOB (from portal unless corrected), counsel classification and attorney name, case status, and a charge summary for each count. The charge summary includes: count number, offense code, plea, charge disposition, fine, jail days imposed/suspended, probation months, and departure status.
- **Deferred/continued/held cases** — mark their closeout action as hold or no-closeout. Do not create a sentencing financial entry. Charge summaries for held cases reflect the pre-disposition state (plea not entered, pending, zero fines, zero jail).

Counsel classification: use the template's enum values (typically `public_defender`, `appointed_private`, `retained`, `unknown`). Do not trust a "PD" or "APD" label on a calendar or worksheet without checking hearing notes and corroborating memos.

#### Fee reconciliation

For each case, determine the fee status:

- **post** — the case is disposed, fees are ready to post to the register
- **hold** — the case is deferred/continued and a final order is not yet signed; post nothing
- **exclude** — specific fees are excluded by payment policy even though the case is disposed

Rules for fee amounts:
- Base all fee amounts on the current portal fee schedule, never on a legacy worksheet or memo amount
- When the portal schedule says a fee amount is different from what a local worksheet carries, use the portal amount and flag the discrepancy in audit findings
- Account-management, collection, late, DMV, copy, certification, and similar administrative fees are excluded unless the portal payment policy or fee schedule explicitly authorizes them
- Public defender user fees post only when counsel is confirmed as a public defender (not appointed private)
- Crime lab or drug assessment fees post only for controlled-substance or lab-eligible convictions
- Restitution posts only when a restitution order exists in the record
- For cases with amended charges where the conviction offense is not lab-eligible, do not post lab fees

The case total is the sum of all fee items being posted.

#### Docket entries

Each disposed case gets a sentencing-order docket entry. Held cases get a disposition-hold entry. The entry date is the hearing date. The financial total on the docket entry must match the case total from fee reconciliation.

Summary codes (from the template) describe the key feature of the case for register scanning: no PD fee, drug assessment applied, no departure, hold for unsigned order, etc.

#### Register totals

Sum across all **disposed (posted)** cases only. Do not include held/pending cases in financial totals. Count them separately.

- `assessed_case_count` or `disposed_case_count` — number of cases with posted financials
- `held_case_count` or `excluded_pending_count` — number of cases held or excluded
- Fee totals per fee code (fine_total, court_cost_total, assessment_total, user_fee_total)
- `grand_total` or `batch_total_due` — sum of all posted financials

#### Payment plans (when applicable)

For cases with financial petitions requesting installment payments:

1. Classify the petition (e.g., `initial_installment` for a first-time petition)
2. Classify supportability by comparing the requested monthly amount against disposable income and policy thresholds
3. Compute the schedule:
   - `total_installments = ceil(total_due / regular_installment_amount)`
   - `final_payment_amount = total_due - regular_installment_amount * (total_installments - 1)`
   - `final_due_date` — first due date advanced by (total_installments - 1) months
   - `return_to_court_date` — typically 1-2 months after the final due date
4. Set the payment application order: restitution before fines/costs when the petitioner requests it or policy mandates it; fines/costs first otherwise
5. Exclude account-maintenance and other administrative fees from the balance unless portal policy explicitly includes them

#### Probation referrals and license orders (when applicable)

- **Probation referral (CC-1375 style)**: Prepare the referral only when supervised probation was actually ordered. If no probation order was signed, mark as `not_ordered` with zero months.
- **License suspension (CC-1379 style)**: Suspension runs from the conviction date (not the release date). Compute the end date by adding suspension months to the start date.
- For both form types, use `TBD from case file` for any required field (SSN, address, phone, driver license number, probation officer contact) that is absent from all available sources.

### Phase 5: Validate and output

Before finalizing:

1. Every required top-level key from the template is present
2. Sort order matches the template's ordering rules (by case_number ascending, by citation_number ascending, etc.)
3. All currency values are numbers to two decimal places (e.g., `150.00`, not `150` or `150.0`)
4. All dates are ISO 8601 YYYY-MM-DD
5. All enum values match the template's allowed sets — do not replace enums with prose
6. Held/pending cases have zero or excluded financial totals and are not summed into register totals
7. Register/batch totals sum correctly: verify each fee-code total and the grand total against the individual case totals
8. No invented values — every field is sourced from the portal, local payloads, or the template's placeholder value
9. The final output is a single JSON object matching the template's structure

## Conflict resolution hierarchy

When sources disagree about a value, resolve in this priority order:

1. **Judge's spoken ruling** (from hearing notes) — controls disposition outcome, sentence, departure findings, and whether an order was signed
2. **Corroborating clerk memo** — controls when the memo specifically corrects a portal record based on paper-file evidence (e.g., a defense cover memo confirming private appointed counsel)
3. **Portal CMS record** — controls identity (name spelling, DOB), case metadata, charge records, and is the default authority for anything not overridden above
4. **Portal fee schedule** — controls all fee amounts; overrides any local worksheet, legacy amount, or memo note
5. **Portal payment policy** — controls which fees are allowed and the order in which payments apply

A value from a local finance queue or worksheet that matches none of these sources is an error to correct, not a value to carry forward.

## Fee handling rules

- Every posted fee must be traceable to the current portal fee schedule or to the judge's spoken sentence (for fines)
- A fee that appears in a local worksheet but not in the current portal schedule is excluded, with the discrepancy flagged
- A fee that appears in the current portal schedule but was omitted from a local worksheet is added
- Public defender user fees: post only when counsel is confirmed as a public defender; do not post when counsel is appointed private or retained
- Crime lab / drug assessment fees: post only for controlled-substance or other lab-eligible convictions; do not post for amended-away charges or non-lab offenses
- Court costs: post for every disposed criminal case unless the judge waived costs; verify the amount against the portal schedule
- Restitution: post only when a restitution order exists; zero otherwise
- Administrative fees (account management, collection, late, DMV, copy, certification): exclude unless portal policy explicitly includes them

## Identity and placeholder rules

- DOB defaults to the portal CMS record. Override only when a hearing note or corroborating memo provides a correction with a specific paper-file source.
- Never borrow a DOB from a similarly named defendant in a different case or a prior search result.
- When DOB is blank in all sources, use the template's placeholder (commonly `TBD from case file` or a verify-before-entry marker).
- Missing identifiers (SSN, address, phone, driver license number, probation officer/office contact) always become placeholders when they are required form fields but absent from every available source.
- Do not invent contact information, office locations, or officer names.

## Payment plan computation

For installment plans derived from a total due and a monthly payment amount:

```
total_installments = ceil(total_due / monthly_amount)
final_payment_amount = total_due - monthly_amount * (total_installments - 1)
```

The first due date comes from the petition or template candidate date. Advance by one month per installment for the final due date. The return-to-court date should be set after the final due date (typically 1-2 months later per local practice).

Supportability check: compare the requested monthly payment against the petitioner's disposable income (monthly income minus listed obligations, per household size). Policy thresholds determine whether the amount is supportable, below the minimum, or above the maximum.

## Common pitfalls

**Posting fees for held cases.** If a case is deferred, continued, or has an unsigned order, its financial total must be zero. The register counts it separately as held, not assessed.

**Carrying forward legacy fee amounts.** An audit memo saying "old worksheet says 125 — verify current schedule" is a red flag, not a source of truth. Always fetch and use the current portal fee schedule.

**Trusting calendar abbreviations for counsel type.** "PD" and "APD" on a calendar or finance worksheet can be wrong. Check hearing notes and corroborating memos for the actual attorney and appointment type.

**Including held cases in batch totals.** Only disposed, posted cases contribute to register financial totals. Held cases are counted discretely.

**Misclassifying departure findings.** A judge saying "no separate departure finding" or "top of the range" means no departure, regardless of what a draft worksheet shows. Only adopt a departure when the judge expressly pronounced one.

**Inventing missing data.** Never make up a DOB, SSN, address, phone number, or license number. Use the placeholder value from the template.

**Mixing up release date and conviction date for license suspensions.** License suspension runs from the conviction date. A release-from-confinement date is for memo context; it does not replace the conviction date.

**Posting fees for amended-away charges.** When the conviction offense differs from the filed offense and the conviction offense is not lab-eligible, do not post lab fees even if the original charge was lab-eligible.

**Overlooking omitted fees.** When the portal schedule shows a fee that a local worksheet omitted (e.g., lab assessment on a controlled-substance conviction, PD user fee on a PD-represented case), add it and flag the omission.

## Reference material

For detailed endpoint descriptions, fee handling examples, payment plan edge cases, and form-specific patterns, read [references/court_ops_guide.md](references/court_ops_guide.md) when the task domain matches and you need deeper guidance.
