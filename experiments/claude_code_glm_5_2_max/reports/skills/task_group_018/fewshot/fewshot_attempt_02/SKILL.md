# Court Operations Closeout & Reconciliation Skill

## Purpose

Perform court-clerk closeout tasks: reconcile hearing notes, finance extracts, and petition data against the Court Operations Portal, resolve audit conflicts, compute fee and payment schedules, and produce a structured JSON answer matching the supplied answer template.

## Environment Access

The Court Operations Portal is reached over the network using the details in `environment_access.md` at the repository root. Read that file for the base URL, credentials, and allowed endpoint list. **Never** attempt to read server-side files; use only the documented HTTP GET endpoints.

## Procedure

### Step 1 — Read all input payloads

Read every file inside `input/payloads/` without exception. Typical payloads include:

- **answer_template.json** — the JSON schema the final answer must match. It defines required top-level keys, field types, enum values, ordering rules, currency precision, and date format. Treat it as the authoritative contract.
- **Hearing / bench notes** (`.md`) — clerk or judge notes from the courtroom session. May contain shorthand, carry-forward values, or draft figures that need verification.
- **Finance / queue extracts** (`.json`, `.csv`) — financial import data that often contains stale, draft, or erroneous carry-forward values requiring reconciliation.
- **Audit memos** (`.md`) — pre-identified exceptions listing specific fields that are known to be wrong in the finance queue.
- **Petition summaries** (`.json`) — defendant payment-petition intake data including budget, requested payment amounts, and balances.
- **Sentencing / probation notes** (`.json`) — conviction details, sentence terms, probation referral info, and missing-identifier lists.
- **Local form excerpts** (`.md`, `.json`) — form field definitions, placeholder rules, and form-label metadata.
- **Form field excerpts** (`.json`) — structured form family definitions (e.g., CC-1375, CC-1379) with field groups and placeholder rules.

Each task may use a different subset of these payload types. Read them all; ignore only those that are absent.

### Step 2 — Identify target cases/citations

Extract the list of target case numbers or citation numbers from `input/prompt.txt`. These are the matters the closeout must cover.

### Step 3 — Query the Court Operations Portal

For every target case, query the relevant portal endpoints to obtain authoritative records. Typical endpoint usage:

| Endpoint | Used for |
|---|---|
| `GET /api/jurisdictions` | Confirm jurisdiction codes |
| `GET /api/cases` | Case records, defendant identity, status |
| `GET /api/charges` | Charge details, offense codes, dispositions |
| `GET /api/docket-entries` | Docket history and entry types |
| `GET /api/citations` | Traffic citation details |
| `GET /api/fee-schedules` | Current fee amounts (resolves stale/archived figures) |
| `GET /api/payment-policies` | Payment plan rules, policy bands, return-to-court triggers |
| `GET /api/forms` | Form IDs, labels, revision metadata |
| `GET /api/financial-petitions` | Petition records, balances, classification |
| `GET /api/search` | General lookup when other endpoints don't cover the need |

Use query parameters (e.g., `?case_number=...`, `?jurisdiction_code=...`) to scope responses when the endpoint supports them.

**Portal data is authoritative** over local payload values when they conflict, unless the answer template or audit memo instructs otherwise (e.g., "use hearing notes" as a resolution source).

### Step 4 — Reconcile conflicts

For every field where local materials disagree with portal data or where the audit memo flags an exception:

1. Identify the **issue type** (identity, counsel, status, fee_schedule, departure, etc.) using the enum from the answer template.
2. Record the **conflicted value** (the stale/wrong value from local materials).
3. Determine the **corrected value** using the authoritative source.
4. Assign a **resolution source** (e.g., `use_cms`, `use_hearing_notes`, `use_corrob_memo`, `use_fee_schedule`, `hold_unsigned_order`, `verify_before_entry`, `exclude_pending`).

Common reconciliation patterns:

| Issue | Typical resolution |
|---|---|
| Defendant name/DOB mismatch | CMS/portal record overrides local unless hearing notes provide a courtroom correction |
| Counsel mislabeled (e.g., "PD" vs. appointed private) | Hearing notes or corroboration memo overrides calendar abbreviation |
| Stale fee amount (archived schedule) | Current fee schedule from portal |
| Draft departure on worksheet | Hearing notes or judge's stated intent controls |
| Unsigned order / continued status | Hold or exclude from financial posting; no disposition entry |

### Step 5 — Determine disposition and status for each matter

For each target case/citation:

- If a signed sentencing order or final disposition exists → **enter disposition** (status: `disposed`, `disposed_enter`, etc.).
- If the order is unsigned, the matter was continued, or no plea was accepted → **hold or exclude** (status: `deferred`, `pending`, `pending_exclude`; fee status: `hold` or `do_not_post_pending`).
- Set the **closeout action** or **register action** accordingly.
- Set disposition date to the hearing/signing date when disposed; use `null` when no disposition date exists.
- Classify the primary outcome (guilty_plea, no_contest_guilty, bench_trial_guilty, continued_pending, etc.).

### Step 6 — Compute financial entries

For each disposed case, compute fee items using **current** portal fee schedules, not stale local amounts:

- Include only fees supported by the fee schedule or a specific order.
- Exclude public defender user fees when counsel is classified as appointed private (not a PD office attorney).
- Include crime/drug/lab assessment fees when triggered by the conviction type and confirmed by the current schedule.
- For held/deferred cases, set all financial amounts to zero and fee status to hold/do-not-post.

For payment plans:

- Use the petition's requested monthly amount, but validate against the payment policy band (minimum/maximum).
- Classify support as `supported_by_budget`, `supportable`, `below_policy_minimum`, `above_policy_maximum`, or `unsupported_by_budget` based on disposable income and policy limits.
- Compute schedule: `full_installment_count = floor(total_due / installment_amount)`, `final_payment_amount = total_due - (full_installment_count × installment_amount)`, `total_installments = full_installment_count + (1 if final_payment_amount > 0 else 0)`.
- Set first due date from petition or policy; compute final due date by advancing months.
- Set return-to-court date from policy (typically 2 months after final due date).

### Step 7 — Handle placeholders

When a required form field cannot be completed from available materials:

- Set the value to **"TBD from case file"** (the standard placeholder).
- Catalog each placeholder with the field name, placeholder value, and reason code (e.g., `missing_identifier`, `missing_contact`, `missing_office_detail`, `missing_party_detail`).
- Sort placeholder entries by field name ascending.

**Never invent** identifiers, SSNs, addresses, phone numbers, driver license numbers, or contact details.

### Step 8 — Exclude unsupported financial items

Identify and list any financial items that appear in local worksheets but lack support from an order, policy, or current fee schedule:

- Common exclusions: restitution (when no order), account-management fees, late fees, DMV fees, court-appointed-attorney fees, court-reporter fees, collection fees, traffic-school fees, stale schedule amounts.
- For each, record the item name, the amount (0.00 if not actually assessed), and the reason code (e.g., `no_order_or_policy_support`, `not_part_of_balance`, `not_current_policy`, `no_triggering_event`, `not_in_hearing_order`, `stale_schedule`, `unsupported_post_disposition`).

### Step 9 — Compile docket/register entries

For each disposed case, create a docket entry or register action:

- Entry type: `sentencing_order` / `SENTENCING_ORDER_ENTERED` for disposed cases; `disposition_hold` / `CONTINUED_NO_DISPOSITION` for held/excluded cases.
- Assign a summary code reflecting the disposition (e.g., `conviction_no_departure`, `conviction_no_pd_fee`, `conviction_drug_assessment`, `hold_unsigned_order`).
- Set the financial total equal to the case's total fees (zero for held cases).

### Step 10 — Compute batch/register totals

Aggregate across all target matters:

- Count of disposed/assessed cases and held/excluded cases.
- Sum of each fee category (fine total, court cost total, assessment total, user fee total, etc.).
- Grand total = sum of all assessed fee amounts.
- For traffic closeouts: combined amount due, matter count, unsupported charge total included.

### Step 11 — Assemble and format the final answer

1. Build the JSON object with all required top-level keys from the answer template.
2. **Sort** every list according to the ordering rules in the answer template (typically by `case_number` ascending, then by sub-fields).
3. **Currency**: all monetary values as numbers rounded to two decimal places.
4. **Dates**: ISO `YYYY-MM-DD`. Datetimes: ISO `YYYY-MM-DDTHH:MM:SS`. Use `null` for absent dates where the template allows it.
5. **Enums**: use only the exact values listed in the answer template's enum definitions. Never substitute prose for an enum value.
6. Return a single JSON object with no markdown formatting.

## Output Checklist

Before finalizing, verify:

- [ ] Every required top-level key from the answer template is present.
- [ ] All lists are sorted per the template's ordering rules.
- [ ] All currency values have exactly two decimal places.
- [ ] All dates use ISO format; null used where no date should be entered.
- [ ] All enum values match the template's allowed set exactly.
- [ ] No invented identifiers or contact details — missing values use the designated placeholder.
- [ ] Unsupported fees are excluded from balances and listed in the exclusion section.
- [ ] Held/deferred cases have zero financial entries and appropriate hold/exclude status.
- [ ] Batch totals are the arithmetic sum of the individual case entries.
- [ ] The answer is valid JSON with no markdown wrappers.
