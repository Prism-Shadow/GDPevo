# Clerk Operations Reconciliation Skill

## Overview

Reconcile local court-clerk packet data (bench minutes, attorney verifications, stale
exports, draft finance imports) against a live Clerk Operations API to produce
clerk-ready JSON outputs. The API serves shared case records, docket history,
financial ledgers, fee schedules, payment policies, attorney directories, and
stale-export queues for multiple counties.

## Environment

The base URL is provided per task (e.g., `TASK_ENV_BASE_URL` or a concrete IP).
Key public endpoints:

| Endpoint | Purpose |
|---|---|
| `GET /api/cases/<case_number>` | Live case record: status, charges, defense, sentence |
| `GET /api/cases?county=&matter_type=&status=` | Filtered case list |
| `GET /api/citations/<citation_number>` | Live citation record (traffic matters) |
| `GET /api/fees?county=&matter_type=&effective_on=YYYY-MM-DD` | Fee schedule rows active on a date |
| `GET /api/payment-policies?county=` | Installment-plan policy (min/max, due-date rules) |
| `GET /api/financial-obligations?case_number=` | Live ledger: principal, components, paid, balance |
| `GET /api/docket?case_number=` | Live docket entries |
| `GET /api/hearings?date=YYYY-MM-DD&county=` | Scheduled hearings |
| `GET /api/attorneys` | Attorney directory with defense types and active status |
| `GET /api/stale-exports?county=&name=` | Stale export snapshots (known conflicts) |
| `GET /api/search?q=` | Full-text search across all record types |
| `GET /api/counties` | County/court reference list |

## Workflow

1. **Read the answer template** (`answer_template.json`) first — it defines the exact
   output shape, required keys, enum values, ordering rules, and precision requirements.
2. **Read all local payloads** (bench minutes, hearing packets, attorney memos, stale
   extract CSVs, draft finance imports) to understand what the clerk needs.
3. **Query the live environment** for every case/citation referenced in the local
   materials — case details, financial obligations, docket, fee schedules (with the
   correct `effective_on` date), payment policies, and relevant stale exports.
4. **Resolve conflicts** between local data, stale exports, and live records using
   the source-precedence rules below.
5. **Compute financials** from the live fee schedule (not draft imports), apply
   payment-policy rules, and compute corrected totals.
6. **Output JSON only** matching the template shape exactly. No explanatory text.

## Source Precedence

1. **Live environment records** (cases, citations, financial obligations, fee
   schedules) are the authoritative source for current state.
2. **Local packet materials** (bench minutes, hearing notes, attorney verification
   memos) describe what happened at the hearing and override live records for the
   *outcome* of the proceeding.
3. **Stale exports** are snapshots with known problems — every stale record carries a
   `known_conflict` field that tells you what is unreliable:
   - `"attorney may be prior assignment"` → don't trust the export's attorney
   - `"balance is from a prior ledger batch"` → don't trust the export's balance
   - `"charge text may predate amendment"` → don't trust the export's charges
   - `"status may be older than live docket"` → don't trust the export's status
   - `"citation export may not include later plea or payment-plan action"` → stale
4. **Draft finance imports** (CSV/JSON workpapers) are working notes only —
   recalculate all amounts from the current live fee schedule.
5. **When live and local disagree on counsel**: the attorney verification memo (or
   the appearance note from the bench minutes) controls, but flag the discrepancy.

## Fee Schedule Rules

- Always query with `effective_on=<date>` where the date is the **hearing date**,
  **disposition date**, or **bench order date** from the local packet.
- A fee is active if `effective_on` falls within `[effective_start, effective_end]`
  (null `effective_end` means still active).
- `"Obsolete"` in the description means the fee is expired — don't use it for new
  assessments; use the current schedule row instead.
- `mandatory: true` → always apply when the trigger condition is met.
- `mandatory: false` → apply only when the trigger condition is explicitly met
  (e.g., probation ordered, restitution ordered, traffic school elected).
- Fees apply based on their `applies_when` condition — match against what the bench
  actually ordered:
  - `"conviction entered"` → at least one charge resulted in conviction
  - `"case filed"` → always applies for filed cases
  - `"probation ordered"` → judge pronounced probation
  - `"restitution ordered"` → judge ordered restitution > $0
  - `"traffic school elected"` → defendant elected traffic school
  - `"speed over posted limit"` → speeding violation
  - `"payment more than 30 days late"` → late-fee trigger
- **Never** enter fee codes listed in the payment policy's `unsupported_charge_codes`.
- **Never** enter fee codes not on the active fee schedule.
- Only enter fees supported by **both** the schedule and the hearing/bench order.
  Candidate fee codes from draft workpapers that don't meet this test go into
  `excluded_candidate_fee_codes` or `excluded_fee_or_charge_codes`.

## Financial Calculations

### Principal and Balance
- **principal_amount** = sum of all fee_component amounts on the live ledger.
- **balance_due** = principal_amount − amount_paid.
- **New assessment total** = sum of fees from the *current* schedule (not the old
  ledger), computed by applying the fee-schedule rules above.
- **financial_delta** = corrected_assessment_total − current_ledger_principal.
- **correction_amount** (compliance tasks): positive values reduce the live balance;
  compute as ledger_balance_before_adjustment − corrected_balance_due.

### Payment Plan Calculations
- **monthly_amount**: must be within `[min_monthly, max_monthly]` from the county
  payment policy. When the defendant requests a specific amount, clamp it to those
  bounds.
- **first_due_date**: order_date + `first_due_days_after_order` days.
- **Installment breakdown** (when `allows_final_smaller_payment: true`):
  - `full_payment_count` = floor(total / monthly_amount)
  - `final_payment_amount` = total − (full_payment_count × monthly_amount)
  - `total_payment_count` = full_payment_count + (final_payment_amount > 0 ? 1 : 0)
- When `allows_final_smaller_payment: false`: the total must be evenly divisible by
  the monthly amount; adjust the monthly amount if needed.
- **final_due_date**: first_due_date + (total_payment_count − 1) months.
- If no payment plan applies, use `0`, `null`, or `"no_plan"` per the template.

### Restitution
- Restitution is part of the total principal but tracked as a separate line item.
- The `CR-REST-ADM` fee applies only when restitution > $0 was ordered.
- Live ledger `restitution_amount` is authoritative.

## Discrepancy Codes and Conflict Resolution

Common discrepancies and how to resolve them:

| Situation | Resolution |
|---|---|
| Live case shows attorney A; memo/bench says attorney B appeared | Use memo/bench attorney; flag `attorney_conflict` |
| Live case shows warrant; bench recalled warrant | Status becomes `warrant_recalled_pending_entry` |
| Stale export status ≠ live case status | Trust live case; stale export has `known_conflict` |
| Draft finance has wrong amounts | Recalculate from current fee schedule |
| Live case shows retained; attorney is public defender | Use memo/confirmation; flag the mismatch |
| Two cases with similar names or numbers | Check DOB/SID; don't merge |
| Citation has no case number | Use citation number as `account_reference` |

## Output Conventions

- **Dates**: `YYYY-MM-DD` format.
- **Currency**: round to 2 decimal places (Python: `round(x, 2)`).
- **Community service hours**: check template — some use 1 decimal place.
- **Integers**: counts, months, payment counts, hours where specified.
- **Null vs. "TBD from case file"**: when a value is genuinely unknown and the
  policy says `unknown_field_placeholder: "TBD from case file"`, use that string.
  Otherwise use `null`.
- **Empty lists**: use `[]`, not `null`.
- **Booleans**: lowercase `true`/`false` in JSON.
- **Ordering**: follow the template's sort directive (usually ascending by
  case_number, citation_number, or charge_id).
- **Enum values**: use exactly the values listed in the template's
  `allowed_values`/`choices` — do not improvise.

## Common Pitfalls

1. **Wrong effective date on fees** — match `effective_on` to the hearing or
   disposition date from the local packet, not "today's date."
2. **Using draft finance amounts** — always recalculate from the live fee schedule.
3. **Including unsupported fee codes** — check `unsupported_charge_codes` in the
   payment policy for the county.
4. **Merging nearby records** — a stale export citation for `CIT-LAN-2024-00412`
   (Evan Tuner) is NOT the same as `CIT-LAN-2024-00411` (Evan Turner). Similar names
   and numbers are warnings, not matches.
5. **Obsolete schedule rows** — check `effective_start`/`effective_end`; a fee
   labeled "Obsolete" in its description is expired.
6. **Ignoring the `known_conflict` field** on stale exports — it tells you exactly
   what not to trust in that export row.
7. **Forgetting to include restitution in principal** — restitution is part of the
   total the defendant owes, even when tracked separately.
8. **Monthly amount below policy minimum** — clamp requested amounts to
   `min_monthly`.
9. **Null fields in templates** — some fields expect `null` when not applicable
   (e.g., `first_due_date: null` when no payment plan exists).
10. **Not querying all relevant cases** — the local packet may reference cases not
    explicitly listed as "targets" (e.g., stale export rows).

## County-Specific Notes

- **Benton**: Criminal matters. Fee codes `CR-CONV`, `CR-FILING`, `CR-PROB`,
  `CR-REST-ADM`. Unsupported: `CR-507`, `CR-610`. Policy min $20, max $225, no
  final-smaller-payment.
- **Lane**: Traffic matters. Fee codes `TR-BASE`, `TR-SPEED`, `TR-SCHOOL`, `TR-LATE`.
  Unsupported: `CR-507`, `DUI-104`, `TR-231`. Policy min $35, max $200, allows
  final-smaller-payment.
- **Gloucester**: DUI matters. Fee codes `CR-CONV`, `CR-FILING`, `CR-PROB`,
  `CR-REST-ADM` (criminal schedule channel). Unsupported: `CMP-072`, `DUI-104`.
  Policy min $35, max $250, allows final-smaller-payment.
- **Marion**: Criminal/compliance mixture. Fee codes `CR-CONV`, `CR-FILING`,
  `CR-PROB`, `CR-REST-ADM`. Unsupported: `CMP-072`, `CR-507`, `CR-610`. Policy min
  $20, max $150, allows final-smaller-payment.
- **Wasco**: Criminal, DUI, and compliance matters. Fee codes `CR-CONV`, `CR-FILING`,
  `CR-PROB`, `CR-REST-ADM`. Unsupported: `TR-231`. Policy min $30, max $225, allows
  final-smaller-payment.

## Data Retrieval Pattern

```
For each case/citation in the local packet:
  1. GET /api/cases/<case_number> or /api/citations/<citation_number>
  2. GET /api/financial-obligations?case_number=<case_number>
  3. GET /api/docket?case_number=<case_number>
  4. GET /api/fees?county=<county>&matter_type=<type>&effective_on=<hearing_date>
  5. GET /api/payment-policies?county=<county>
  6. GET /api/stale-exports?county=<county>&name=<export_name>  (if referenced)

Compare live records against local packet data:
  - Live case status vs. bench outcome → final_case_status
  - Live defense_attorney/defense_type vs. attorney verification memo → final counsel
  - Live ledger fee_components vs. current fee schedule → corrected assessment
  - Stale export values vs. live values → discrepancy detection
```
