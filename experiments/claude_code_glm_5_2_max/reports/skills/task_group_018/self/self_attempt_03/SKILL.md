# Court Operations Closeout & Financial Packet Skill

## Purpose

Produce a structured JSON closeout, disposition register, or post-sentencing packet for a court clerk by reconciling local hearing materials against a Court Operations Portal. The output always matches a provided `answer_template.json` schema.

## Scope

This skill covers criminal-sentencing closeouts, traffic-violation closeouts, post-sentencing field packets, and disposition-batch registers for circuit and district courts. It applies whenever the task asks the clerk to:

- Reconcile hearing notes / clerk worksheets with portal data
- Resolve audit conflicts between local drafts and authoritative sources
- Compute fee schedules, payment plans, and batch totals
- Prepare CC-1375 / CC-1379 style referral and license-suspension forms
- Exclude unsupported or stale charges from financial entries

---

## Operating Rules

### 1. Source Hierarchy — Resolving Conflicts

When local payload values conflict with each other or with the portal, resolve in this priority order:

| Priority | Source | When to Use |
|----------|--------|-------------|
| 1 | Hearing notes / bench notes / courtroom transcript | Authoritative for what happened in court (plea, finding, sentence pronounced, order signed or not signed) |
| 2 | Audit memo / clerk worksheet corrections | Authoritative for identifying carry-forward or draft errors in finance queues |
| 3 | Portal live data (fee schedule, payment policy, forms, case records) | Authoritative for current schedule amounts, policy terms, and formal case metadata |
| 4 | Finance queue extract / intake worksheet | Presumptively stale — only use values that survived reconciliation |

**Key principle:** A draft or carry-forward value from a finance queue, intake sheet, or legacy worksheet is **never** authoritative over a hearing note or portal record. Always flag and correct it.

### 2. Fee Reconciliation Rules

1. **Verify every fee against the current portal schedule.** Do not use archived, expired, or "old local worksheet" amounts. If the portal gives a different amount for the same fee code, use the portal amount.
2. **Only post fees directly supported by the hearing order or current schedule.** The following fee types are *never* added unless the hearing record or portal confirms them:
   - Account-management / account-maintenance fee
   - Collection referral fee
   - Late-payment fee
   - DMV / DMV reinstatement fee
   - Returned-check fee
   - Court-appointed-attorney fee (unless ordered)
   - Court-reporter fee
   - Restitution (unless an order appears)
   - Traffic-school program fee
   - Certification / copy fee
3. **Public defender user fee** is only appropriate when counsel classification is confirmed as public defender. If counsel is reclassified (e.g., appointed private), exclude the PD user fee.
4. **Drug / controlled-substance assessment** amounts must match the current schedule for the disposition year, not a prior-year archived amount.

### 3. Counsel Classification

| Queue Label | Possible Correction | Rule |
|-------------|---------------------|------|
| `PD` / `PD C. Hill` | May be appointed private counsel | If hearing notes or defense memo clarify that the attorney is appointed private (county-paid, not PD office), reclassify as `appointed_private` and exclude PD user fee |
| `APD` | May be appointed private counsel | Calendar abbreviations are unreliable; resolve from the record |
| `RET` | Retained | Generally correct unless contradicted |
| Blank / unknown | Use best available evidence | If unverifiable, use `unknown` |

### 4. Disposition-Status Decisions

1. **Only enter a disposition if a signed order or on-the-record finding exists.** If the judge did not sign the order or the matter was continued, the case status is `deferred` / `continued` / `pending` — never `disposed`.
2. A case that is deferred/continued must **not** receive a financial register entry. Mark it as `hold` or `exclude` in the fee section.
3. Draft plea lines, draft disposition sheets, and unsigned order references are not final — treat them as non-authoritative.

### 5. Departure and Sentencing Entry

- A "top of the range" sentence is **not** a departure. Only enter a departure finding if the judge made an explicit departure finding on the record.
- If a draft worksheet carried a departure label but the judge stated "no departure finding," correct it to `no_departure` / `none`.

### 6. Identity and DOB Handling

- If the hearing notes correct a DOB or name spelling, use the corrected value.
- If DOB is genuinely missing and must be verified from the case file before permanent entry, use the placeholder `TBD from case file`. Do **not** borrow a DOB from a similarly named defendant or a prior search result.
- If the finance queue and hearing notes disagree on identity (name spelling, DOB), the hearing notes prevail; record the conflict as an audit finding.

### 7. Payment Plans and Budget Review

1. **Petition classification** must follow the intake sequence label (first petition, subsequent, deferred, exempt).
2. **Support classification** compares the petitioner's requested monthly amount against the jurisdiction's payment-policy band (minimum and maximum). Classify as:
   - `supportable` — within policy band
   - `below_policy_minimum` — below minimum
   - `above_policy_maximum` — above maximum
   - `unsupported_by_budget` — disposable income cannot sustain it
3. **Account-fee treatment**: Check current jurisdiction policy. If the policy excludes the fee, classify as `excluded_by_policy`; if included, `included_by_policy`; if uncertain, `verify_before_entry`. Counter worksheets and old fee rows are **not** authoritative for whether the fee is due.
4. **Payment application order**: Follow what the record or policy states (e.g., fines/costs first vs. restitution first). If a petitioner asks for a different order but no policy or order supports it, use the default jurisdictional policy.
5. **Installment math**: Compute `total_installments = ceil((total_due - down_payment) / installment_amount)`. Compute `final_payment_amount = total_due - down_payment - (full_installment_count × installment_amount)`. If the balance divides evenly, `final_payment_amount` equals the regular installment.

### 8. CC-1375 (Probation Referral) and CC-1379 (License Suspension / Installment Order)

1. **CC-1375** is prepared only when supervised probation is ordered. If no supervised probation referral order was signed, status is `not_ordered`.
2. **CC-1379 license suspension** start date follows the applicable basis (conviction date, release date, or petition date per the answer template). End date = start date + suspension months.
3. **Placeholder handling**: For any required form field that cannot be completed from the petition, sentencing note, or portal — including SSN, driver license number, addresses, phone numbers, probation officer name, or probation office location — enter the placeholder `TBD from case file`. Never invent or fabricate identifiers or contact details.
4. **Return-to-court trigger**: Set based on the payment agreement terms. If no default or review is triggered, use `none`.

### 9. Form and Account-Reference Handling

- If no separate case number or account number has been opened (e.g., traffic citations), use the citation number as the account reference.
- Use the correct form ID and label from the portal or local excerpt. Obsolete footer charges or old form revisions do not override current policy.

### 10. Output Formatting

| Rule | Standard |
|------|----------|
| Currency | Numeric, two decimal places (e.g., `150.00`) |
| Dates | ISO `YYYY-MM-DD` |
| Datetimes | ISO local `YYYY-MM-DDTHH:MM:SS` |
| Missing / null dates | Use `null` where the schema allows, or omit if the schema requires a string |
| Enum values | Use **exactly** the values from the answer template's enum lists — never prose, never approximations |
| Sorting | Follow the ordering rules in the answer template (typically ascending by case_number, citation_number, or petition_id) |
| JSON only | Return a single JSON object; no markdown fencing, no commentary |

### 11. Excluded Charges / Unsupported Items

List every charge or fee that was considered but excluded, with:
- The charge or item identifier
- Which matter(s) it applies to (or `all`)
- A reason code drawn from the answer template's enum (e.g., `stale_schedule`, `unsupported_post_disposition`, `not_in_hearing_order`, `not_current_policy`, `no_triggering_event`, `no_order_or_policy_support`, `not_part_of_balance`)

### 12. Batch / Register Totals

- Sum only the amounts for cases with `post` / `disposed_enter` status. Cases on hold or excluded do not contribute to totals.
- Verify that `grand_total` / `batch_total_due` equals the sum of all included fee categories.
- Count cases accurately: `assessed_case_count` / `disposed_case_count` includes only posted cases; `held_case_count` / `excluded_pending_count` includes only held/excluded ones.

---

## Workflow

When executing a court closeout or packet task, follow this sequence:

1. **Read all local payloads** — hearing notes, audit memos, finance extracts, clerk worksheets, sentencing intake facts, petition summaries, probation notes, form excerpts.
2. **Query the portal** for each relevant endpoint (jurisdictions, cases, charges, docket-entries, citations, fee-schedules, payment-policies, forms, financial-petitions, search). Use only the endpoints documented in `environment_access.md` at `<base_url>`.
3. **Identify conflicts** between local materials and portal data. For each conflict, determine the correct value using the source hierarchy (Rule 1).
4. **Classify each case** — disposed vs. deferred/pending. Only disposed cases with signed orders receive financial entries.
5. **Reconcile fees** — verify each fee line against the current portal schedule, correct stale amounts, exclude unsupported charges, and recompute totals.
6. **Prepare form sub-objects** (CC-1375, CC-1379, payment plans, budget reviews) using the corrected data. Use placeholders for missing identifiers.
7. **Build the answer JSON** matching the answer template exactly — correct enums, correct sorting, correct precision.
8. **Validate** — check that batch totals sum correctly, all required keys are present, and no invented values exist.

---

## Portal Access Reference

- **Base URL**: From `environment_access.md` (network-only; no server-side file access)
- **Credentials**: None required within the network
- **Allowed endpoints**:
  - `GET /api/jurisdictions`
  - `GET /api/cases`
  - `GET /api/charges`
  - `GET /api/docket-entries`
  - `GET /api/citations`
  - `GET /api/fee-schedule`
  - `GET /api/fee-schedules`
  - `GET /api/payment-policies`
  - `GET /api/forms`
  - `GET /api/financial-petitions`
  - `GET /api/search`

Do not attempt to read server-side files or access undocumented endpoints.
