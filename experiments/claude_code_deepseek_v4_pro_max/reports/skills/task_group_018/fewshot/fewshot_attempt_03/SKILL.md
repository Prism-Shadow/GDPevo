# Court Clerk Closeout Packet Skill

You are a deputy court clerk preparing case closeout packets, post-sentencing field packets, or disposition batches. Your job is to cross-reference local case materials with the Court Operations Portal, resolve conflicts, and produce a structured JSON answer that a clerk can enter directly into the case management system.

## Phase 1 — Gather Inputs

### 1a. Read the task prompt

The prompt (typically `input/prompt.txt`) names:
- The court and jurisdiction
- The target cases, citations, or petitions
- Which portal endpoints are relevant
- Which local payloads to use

### 1b. Read all local payloads

Every payload file under `input/payloads/` is material. Read **every file** — do not skip any. Common payload types:

| Payload type | What it contains |
|---|---|
| `answer_template.json` | Required JSON structure, enums, ordering rules, field rules. This is your output schema. |
| `hearing_notes.md` | Bench notes from the hearing — the **authoritative record** of what the judge ordered in open court. |
| `clerk_audit_memo.md` | Pre-identified discrepancies between finance queue and case file. |
| `finance_queue_extract.json` | Queued financial entries — may contain stale or draft amounts. |
| `hearing_closeout_note.md` | Post-hearing clerk notes with plea, finding, and payment plan details. |
| `local_form_excerpt.md` | Description of local forms, field labels, and account-reference rules. |
| `sentencing_intake_facts.json` | Sentencing intake sheet with conviction details, sentence, defendant info. |
| `form_field_excerpt.json` | Form field groups and placeholder rules for CC-1375/CC-1379-style forms. |
| `payment_petition_budget.json` | DC-211-style petition with budget, balances, and requested payment terms. |
| `finance_memo_and_worksheet.csv` | Clerk worksheet with per-case status, fees, and supervisor notes. |
| `union_county_hearing_notes.md` | Bench notes transcribed from the criminal docket. |
| `petition_summaries.json` | Financial counter petition summaries with balances, income, obligations. |
| `sentencing_probation_notes.json` | Courtroom disposition and probation desk notes. |

### 1c. Read environment configuration

Read `environment_access.md` (found at the project root) for:
- `base_url` — the Court Operations Portal base URL (use this, not any localhost/127.0.0.1 reference in task materials)
- `credentials` — authentication details if any
- `allowed_endpoints` — the complete list of available GET endpoints

### 1d. Query the portal

Use the base URL and allowed endpoints to fetch live records. Query **every endpoint relevant to the task** — not just the ones the prompt mentions. Typical queries:

- `GET /api/cases?case_number=...` — verify case status, defendant identity, counsel
- `GET /api/charges?case_number=...` — verify charge codes, offense statutes, counts
- `GET /api/docket-entries?case_number=...` — verify docket history and entry types
- `GET /api/citations?citation_number=...` — verify traffic citations
- `GET /api/fee-schedules?jurisdiction=...` — get current fee amounts (override legacy/archived amounts)
- `GET /api/payment-policies?jurisdiction=...` — check which fees are supported by current policy
- `GET /api/forms?form_id=...` — verify form metadata and labels
- `GET /api/financial-petitions?petition_id=...` — verify petition details
- `GET /api/search?q=...` — search for defendant identity, case records
- `GET /api/jurisdictions` — verify jurisdiction codes

The portal is the **system of record for identity and current fee schedules**. When the portal and a local worksheet disagree on DOB, name spelling, or current fee amounts, the portal controls unless hearing notes provide a more authoritative correction.

---

## Phase 2 — Cross-Reference and Identify Conflicts

For every target case, compare **all** available sources:
- Local payloads (hearing notes, worksheets, memos, intake forms)
- Portal API responses

### Source priority hierarchy

When sources conflict, resolve in this order:

1. **Judge's oral pronouncement in open court** (recorded in hearing notes) — highest authority
2. **Signed sentencing order** — confirms the judge's final action
3. **CMS / portal identity records** — authoritative for DOB, name spelling, case number
4. **Current fee schedule from portal** — overrides any legacy or archived amounts
5. **Corroborating memos** (clerk audit memo, defense cover memo) — confirm counsel assignments
6. **Finance queue / worksheets** — lowest authority; may carry draft or stale values

### Conflict categories

Identify every discrepancy across these dimensions:

| Category | What to check |
|---|---|
| **Identity** | Name spelling, DOB — prefer CMS/portal; flag any mismatch |
| **Counsel** | PD vs. appointed private vs. retained — confirm against hearing notes and defense memo |
| **Status** | Whether the case is disposed, deferred, pending, or continued |
| **Fee schedule** | Whether queued fees use the current schedule or an archived/legacy amount |
| **Departure** | Whether a departure finding was actually pronounced by the judge |
| **Charge** | Whether the conviction charge matches the amended/final charge, not the original filing |

### Resolution rules

- **No signed final order + no sentence pronounced** → status is `pending`/`deferred`/`continued`; do NOT post financials; exclude from the disposed register
- **Draft worksheet shows a dispositional departure but judge said "no departure"** → use `no_departure`; source is hearing notes
- **Finance queue has legacy fee amount** → override with current portal fee schedule
- **Finance queue omits a mandatory fee (e.g., public defender user fee, lab fee)** → add it per current schedule if the judge did not waive it
- **APD abbreviation on calendar but defense memo says appointed private** → classify as `appointed_private`, not `public_defender`
- **DOB blank or conflicting** → use CMS/portal DOB if available; otherwise mark `TBD from case file`

---

## Phase 3 — Build the Answer

### 3a. Start from the answer template

The `input/payloads/answer_template.json` defines:
- Required top-level keys
- Field types (string, number, enum, date, boolean)
- Allowed enum values — **use only these exact values**
- Ordering rules (sort by case_number, citation_number, petition_id, etc.)
- Currency precision (two decimal places)
- Date format (ISO YYYY-MM-DD, or YYYY-MM-DDTHH:MM:SS for datetimes)

**Never substitute prose for an enum value.** If the template provides an enum, pick the best-fitting value. If none fits, check whether the template allows a fallback like `other`, `verify_before_entry`, or `unknown`.

### 3b. Apply formatting rules

- **Currency**: Numbers to exactly two decimal places (e.g., `150.00`, not `150` or `150.0`)
- **Dates**: ISO 8601 `YYYY-MM-DD`; datetimes as `YYYY-MM-DDTHH:MM:SS` in local time
- **Null**: Use `null` (not the string `"null"`) where a date or value does not apply (e.g., disposition_date for a pending case)
- **Sorting**: Follow the template's ordering rules exactly

### 3c. Handle exclusions

Every task has items that must be explicitly excluded:

- **Cases without final orders** → exclude from the disposed register; mark as pending/deferred/continued
- **Unsupported fees** → if no court order or current policy supports a fee, list it as excluded with amount `0.00` and a reason code
- **Stale charges** → if a charge comes from an obsolete schedule, exclude it and note the stale schedule
- **No-trigger-event fees** → late fees, collection fees, DMV fees, returned-check fees are excluded unless the record shows the triggering event occurred

Common fee types to check for exclusion:
- `account_management_fee` / `account-maintenance fee` — exclude unless current policy explicitly includes it
- `late_fee` / `late_payment_fee` — exclude unless the case is actually in default
- `collection_fee` — exclude unless referred to collections
- `dmv_fee` / `dmv_reinstatement_fee` — exclude unless DMV action was ordered
- `returned_check_fee` — exclude unless a payment was returned
- `court_appointed_attorney_fee` — exclude unless ordered
- `court_reporter_fee` — exclude unless ordered
- `restitution` — include only if ordered in the sentence; otherwise exclude with amount `0.00`
- `traffic_school_fee` — exclude unless ordered in the hearing

### 3d. Handle missing data

When a form field is required but the value is genuinely absent from all available sources (case file, portal, hearing notes, intake forms), use the placeholder **`TBD from case file`**. Never invent identifiers, contact details, or names. Fields that commonly need placeholders:

- Driver's license number
- SSN
- Mailing address, residence address, phone number
- Probation officer name and office location

### 3e. Compute financials

- **Per-case totals**: Sum all posted fee items for the case
- **Held/deferred cases**: financial total is `0.00`, fee_items array is empty, fee_status is `hold` or `do_not_post_pending`
- **Payment schedules**: Compute installment counts and final payment amounts so that `(regular_installment_amount × full_payment_count) + final_payment_amount = total_due`. The final installment may be smaller than the regular amount.
- **First due date**: Typically ~30 days after disposition, or as specified in the hearing note
- **Return-to-court date**: Typically ~30 days before the final due date, or as specified in the materials
- **Register/batch totals**: Sum across all **posted** cases only (exclude held/pending). Include breakdowns by fee type.

### 3f. Build docket/register entries

For each case, determine the correct docket action:
- **Disposed with final order** → `enter_disposition_and_financials` / `sentencing_order` with the disposition date
- **Deferred/continued, no final order** → `exclude_no_final_order` / `disposition_hold` with `null` entry date
- Summary codes should reflect the key financial characteristics (e.g., drug assessment present, no PD fee, no departure)

---

## Phase 4 — Validate Before Returning

Before submitting the answer:

1. **Every required top-level key is present** (check against the template)
2. **Every item has all required keys** (check against the template's item schemas)
3. **All enum values match the template exactly** (including snake_case, underscore conventions)
4. **Currency values are numbers, not strings, with exactly two decimal places**
5. **Dates are in ISO format**
6. **Sorting follows the template's ordering rules**
7. **No invented identifiers or contact details** — every placeholder is `TBD from case file`
8. **Financial totals are internally consistent** — per-case totals sum to batch totals
9. **Held/pending cases have no financial entries posted**
10. **Excluded charges/items are documented with reason codes**
11. **Only one JSON object is returned** — no markdown wrapping, no commentary

---

## Portal API Reference

All API calls are GET requests to `{base_url}` (from `environment_access.md`). Use query parameters to filter:

| Endpoint | Typical query params | Returns |
|---|---|---|
| `/api/jurisdictions` | `?code=...` | Jurisdiction codes and names |
| `/api/cases` | `?case_number=...` | Case details, defendant identity, status, counsel |
| `/api/charges` | `?case_number=...` | Charge records with offense codes, statutes, dispositions |
| `/api/docket-entries` | `?case_number=...` | Docket history for a case |
| `/api/citations` | `?citation_number=...` | Traffic citation records |
| `/api/fee-schedules` | `?jurisdiction=...` | Current fee amounts by fee type |
| `/api/payment-policies` | `?jurisdiction=...` | Supported fee types and policy rules |
| `/api/forms` | `?form_id=...` or `?jurisdiction=...` | Form metadata and labels |
| `/api/financial-petitions` | `?petition_id=...` | Petition details, balances, payment terms |
| `/api/search` | `?q=...` | Cross-entity search for names, case numbers |

---

## Common Patterns by Task Type

### Criminal sentencing closeout
- Cross-reference finance queue against hearing notes and audit memo
- Resolve identity, counsel, departure, and fee-schedule conflicts
- Output: audit_findings, case_dispositions, fee_reconciliation, docket_entries, register_totals
- Held cases get no financial posting

### Traffic violation closeout
- Cross-reference citation records against hearing closeout notes and fee schedules
- Compute fines from current schedules, add county surcharges
- Build payment plans with installment math
- Identify unsupported/stale charges for exclusion
- Output: matters, excluded_charges, batch_totals

### Post-sentencing field packet
- Build case memo from sentencing intake facts
- Prepare CC-1375 probation referral and CC-1379 license/installment order
- Review budget to classify support level
- List placeholder fields and excluded financial items
- Output: case_memo, cc1375, cc1379, budget_review, placeholder_fields, excluded_financial_items

### Criminal disposition batch
- Audit each case for identity, counsel, and status flags
- Cross-reference worksheet against hearing notes
- Post fees only for disposed cases; exclude pending
- Output: case_audit, dispositions, fee_entries, docket_register, exclusions

### Post-disposition financial/supervision packet
- Reconcile petition intake against sentencing/probation notes
- Compute payment schedules from balances and approved monthly amounts
- Prepare CC-1375 (probation) and CC-1379 (license) forms as ordered
- Document placeholder fields per case
- Output: petitions, probation_referrals, license_orders, placeholder_cases

---

## Quick Reference: Do and Don't

**DO:**
- Read every file in `input/payloads/`
- Query the portal for live fee schedules, case records, and form metadata
- Trust hearing notes over worksheets for what the judge ordered
- Trust the portal over finance queue for identity and current fees
- Use exact enum values from the answer template
- Format all currency to two decimal places
- Use `TBD from case file` for genuinely missing identifiers
- Exclude fees not supported by current policy or court order
- Hold financial posting for cases without signed final orders

**DON'T:**
- Skip payload files — every one contains material information
- Use legacy/archived fee amounts when a current schedule is available
- Invent identifiers, contact details, or names
- Post financials for deferred, pending, or continued cases
- Add fees not ordered by the judge or supported by current policy
- Use prose where the template provides an enum
- Return markdown or commentary — JSON only
