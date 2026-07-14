# Clerk Operations — Court Docket & Financial Processing Skill

## Overview

Operate as a court clerk processing post-hearing packets for multiple county courts. Reconcile
bench/hearing materials against a live clerk operations API, verify attorney records, compute
financial assessments from county fee schedules, apply payment-policy installment plans, flag
stale-export conflicts, and produce a clerk-ready JSON answer matching a supplied template.

---

## Workflow

### 1. Inventory the packet

Read **all** task-local payload files (answer template, hearing packet, bench minutes,
attorney memo, finance import CSV, stale extract, compliance log, etc.). Identify:

- **County and court** — determines which fee schedule, payment policy, and stale exports apply.
- **Target cases/citations** — the matters the packet asks you to process.
- **Required output shape** — always `answer_template.json`; match it field for field.
- **Live-environment lookups needed** — case records, docket entries, financial obligations,
  fee schedules, payment policies, attorney records, citations, stale exports.

### 2. Fetch live records (source of truth)

Pull from the clerk operations API base URL (see **Environment API** below). For each target:

| What | Endpoint |
|------|----------|
| Case identity, charges, status, attorney, sentence | `GET /api/cases/<case_number>` |
| Docket history | `GET /api/docket?case_number=<case_number>` |
| Financial ledger (principal, payments, balance, plan) | `GET /api/financial-obligations?case_number=<case_number>` |
| Citation records (traffic batches) | `GET /api/citations/<citation_number>` |
| Attorneys (verify bar status, firm, defense types) | `GET /api/attorneys` |
| Fee schedule for county + matter type | `GET /api/fees?county=<X>&matter_type=<type>` |
| Payment policy (installment rules) | `GET /api/payment-policies?county=<X>` |
| Stale exports (conflict warnings) | `GET /api/stale-exports?county=<X>` |
| Search (locate records by text) | `GET /api/search?q=<text>` |

Fetch all relevant live records **before** computing outputs. The live environment is
authoritative; the packet materials describe what happened at the hearing but may contain
stale or draft values.

### 3. Source precedence (authority order)

```
Live case/citation/docket/financial records  >  Hearing/bench notes (packet)  >  Packet stale extracts
```

- **Live records** are ground truth for existing state: case status, current charges, current
  attorney, current financial ledger.
- **Hearing/bench notes** override live records for events that happened *at the hearing*:
  pleas taken, verdicts entered, sentences pronounced, warrant recalls, attorney substitutions.
- **Attorney verification memo / counsel confirmations** are authoritative for
  representation details when present.
- **Stale exports** (from the API or included as CSVs) are **never authoritative**. They
  carry `known_conflict` flags and exist only to surface potential mismatches. Use them as
  warning signals, not as data sources. Do NOT merge stale-export values into live-case
  outputs unless the packet explicitly directs it.

### 4. Resolve charge outcomes

For each charge in the packet's scope, determine the final plea, disposition, and verdict
from the bench/hearing notes. Map to controlled vocabulary:

| Field | Values |
|-------|--------|
| **plea** | `guilty`, `no_contest`, `not_guilty`, `not_entered`, `deferred_entry` |
| **disposition** | `convicted`, `dismissed`, `deferred`, `pending`, `amended` |
| **verdict** | `guilty`, `not_guilty`, `dismissed`, `deferred`, `not_adjudicated` |

Rules:
- "dismissed by plea agreement" → `disposition: dismissed`, `verdict: dismissed`
- "conviction entered" → `disposition: convicted`, `verdict: guilty`
- A charge not adjudicated at the hearing retains its live-case values unless the bench
  card explicitly changes them.
- DUI-104 (refusal) in Gloucester is an unsupported charge code per payment policy — it
  may be listed as `convicted_no_separate_fee` or `dismissed` depending on the bench sheet.

### 5. Resolve attorney & representation

Compare the live case `defense_attorney` / `defense_type` against:
- The bench/hearing appearance note
- The attorney verification memo (if present)

| Scenario | Action |
|----------|--------|
| Live attorney matches hearing appearance | No conflict; use live values |
| Hearing shows a different attorney | Use the hearing/memo attorney; set `enter_attorney_update: true` |
| Stale roster shows "pending" but live shows retained | Live wins; flag `representation_mismatch: true` |
| "Former Counsel" or "Public Defender Pending" appears | These are placeholder values; replace with verified counsel |

Attorney types: `retained`, `appointed_private`, `public_defender`, `self_represented`, `unknown`.

When the verification memo says "Route to supervisor" → `needs_supervisor_review: true`.

### 6. Compute financials

#### Fee schedule lookup

Fees are keyed by `county` + `matter_type` + effective date. A fee code may appear twice
(obsolete version with explicit `effective_end`, current version with `effective_end: null`).

**To pick the correct row:** the disposition date or hearing date must fall within
`[effective_start, effective_end)`. Use the row whose effective range covers the relevant
date. When no `effective_on` filter is passed, all rows for the county/matter_type are
returned — filter client-side.

The fee schedule endpoint accepts an optional `effective_on=<YYYY-MM-DD>` parameter.

#### Fee applicability checklist

| Condition | Fee code typically triggered |
|-----------|------------------------------|
| Conviction entered | `CR-CONV`, `DUI-CONV` (mandatory) |
| Case filed | `CR-FILING` (mandatory) |
| Probation ordered | `CR-PROB`, `DUI-PROB` (mandatory=false, include only if probation pronounced) |
| Restitution ordered | `CR-REST-ADM` (mandatory=false, include only if restitution > 0) |
| License suspension ordered | `DUI-LIC` (mandatory) |
| Treatment ordered | `DUI-TREAT` (mandatory) |
| Traffic conviction | `TR-BASE` (mandatory), `TR-SPEED` (only if speed violation), `TR-SCHOOL` (only if traffic school elected) |
| Late payment | `TR-LATE` (mandatory=false, only if late fee ordered at hearing) |
| Restitution amount | Add as a separate component (not a fee code) with the restitution dollar amount |

**Excluded codes**: Candidate fee codes from the packet import workpaper that are NOT
supported by the schedule or not ordered by the judge must be listed in
`excluded_candidate_fee_codes` or `excluded_fee_or_charge_codes`.

#### Principal, payments, balance

```
new_principal_total = sum(all applicable fee amounts) + restitution_amount
amount_paid_credit   = live ledger amount_paid + any packet receipt not yet on ledger
corrected_balance_due = new_principal_total - amount_paid_credit
```

- Use the **current** fee schedule row amounts, NOT the draft/import CSV amounts.
- The draft finance import CSV is a workpaper; its amounts may be from "older quick-pick rows"
  or "previous assessment amounts" — cross-check every row against the live fee schedule.
- If the live ledger contains obsolete fee assessments (e.g., old `CR-CONV` at $150 instead of
  current $165), the corrected assessment replaces them entirely.
- `financial_delta = corrected_assessment_total - current_ledger_principal`.
- When no live financial obligation exists, `current_ledger_principal = 0.00`.

### 7. Payment plan / installment schedule

Each county's payment policy provides:
- `min_monthly` / `max_monthly` — bounds for monthly payment amount
- `allows_final_smaller_payment` — whether the last installment can be less than monthly
- `first_due_days_after_order` — days from disposition/order date to first payment
- `unsupported_charge_codes` — charges that cannot be put on a payment plan

**Calculating the schedule:**

1. Determine `monthly_amount`: use the amount requested in the packet (or from live citation),
   clamped to `[min_monthly, max_monthly]`. If a petition requests a lower amount and is
   approved, use that amount.

2. `first_due_date` = order_date + `first_due_days_after_order` days.

3. For a principal P and monthly M, when `allows_final_smaller_payment: true`:
   - `full_payment_count = floor(P / M)`
   - `final_payment_amount = round(P - full_payment_count * M, 2)`
   - `total_payment_count = full_payment_count + (1 if final_payment_amount > 0 else 0)`

   When `allows_final_smaller_payment: false`:
   - `full_payment_count = ceil(P / M)` or adjust M upward to evenly divide.

4. `final_due_date` = first_due_date + (total_payment_count - 1) months.

Where the live citation already has an approved plan (first_due_date, monthly_amount),
the packet's `plan_note` may say "Extended plan approved at the amount and first due date
already recorded" — preserve those values unless the packet explicitly changes them.

`plan_basis`: `original_principal` when plan is based on new assessment; `current_balance`
when based on remaining balance; `no_plan` when no installment plan applies.

### 8. Identify discrepancies & stale-export conflicts

Cross-reference the live records against the packet's stale export data and the fresh
hearing notes:

| Conflict pattern | How to detect |
|-----------------|---------------|
| Attorney conflict | Live case attorney ≠ hearing appearance or verification memo |
| Status conflict | Live case status ≠ expected post-hearing status |
| Financial schedule conflict | Live ledger uses obsolete fee rows or wrong amounts |
| Identity conflict | Defendant name/DOB mismatch across sources |
| Stale export warning | `known_conflict` field on stale export record |

**Discrepancy codes** (for criminal docket tasks): `none`, `attorney_conflict`,
`status_conflict`, `financial_schedule_conflict`, `attorney_and_status_conflict`,
`status_and_financial_conflict`, `identity_conflict`.

**Source conflict codes** (for compliance reviews): `no_source_conflict`,
`live_ledger_vs_packet_receipt`, `petition_changes_payment_plan`, `packet_service_shortfall`.

### 9. Determine docket actions

Boolean flags for each case in the output:

| Flag | True when |
|------|----------|
| `enter_plea` | Plea was taken or changed at the hearing |
| `enter_sentence` | Sentence was pronounced at the hearing |
| `recall_warrant` | Warrant was recalled in open court |
| `enter_attorney_update` | Attorney differs from live case record |
| `generate_financial_entry` | Financial assessment changed (new or corrected amounts) |
| `needs_supervisor_review` | Discrepancies require supervisor approval before entry |

### 10. Aggregate totals

Compute batch-level summaries; the exact fields depend on the template, but always include:

- Count of cases/entries in the batch
- Sum of all principal/assessment totals (currency, 2 decimals)
- Sum of all balance-due amounts (currency, 2 decimals)
- Counts of specific actions (warrants recalled, financial adjustments, plans, supervisor reviews)

### 11. Assemble the output

1. Follow `answer_template.json` exactly — every required key, every enum value, every format.
2. Sort lists as directed (case_number ascending, charge_id ascending, fee_code ascending).
3. Use ISO `YYYY-MM-DD` dates, `HH:MM` times, currency rounded to 2 decimals.
4. Use `null` (not `"null"`, not `0`) for fields that genuinely don't apply.
5. Use `"TBD from case file"` for identity fields the packet marks as unknown (e.g.,
   `driver_license_number`, `defendant_phone`) when the payment policy specifies that
   placeholder.
6. Return **only** the JSON object — no markdown, no commentary, no wrappers.

---

## Environment API

Base URL: the remote environment URL in `environment_access.md` (overrides any localhost refs).

### Endpoints

| Method | Path | Notes |
|--------|------|-------|
| GET | `/health` | Service status and `record_counts` |
| GET | `/api/counties` | All counties: `county`, `court`, `code` |
| GET | `/api/cases?county=<X>` | List cases for a county (fields vary by matter_type) |
| GET | `/api/cases/<case_number>` | Single case with charges, attorney, sentence, tags |
| GET | `/api/citations?county=<X>` | List citations (may be paginated) |
| GET | `/api/citations/<citation_number>` | Single citation with violation, plea, disposition, plan |
| GET | `/api/hearings?date=<YYYY-MM-DD>&county=<X>` | Hearings on a date |
| GET | `/api/attorneys` | Full attorney roster (name, bar, firm, counties, active, defense_types) |
| GET | `/api/fees?county=<X>&matter_type=<type>` | Fee schedule rows with effective date ranges |
| GET | `/api/fees?county=<X>&matter_type=<type>&effective_on=<YYYY-MM-DD>` | Filtered to rows active on that date |
| GET | `/api/payment-policies?county=<X>` | Installment rules, min/max monthly, unsupported codes |
| GET | `/api/financial-obligations?case_number=<X>` | Ledger: principal, fee_components, amount_paid, balance_due, plan |
| GET | `/api/docket?case_number=<X>` | Docket entries (entry_id, date, event_type, text) |
| GET | `/api/stale-exports?county=<X>` | All stale exports for a county |
| GET | `/api/stale-exports?county=<X>&name=<Y>` | Specific stale export by name |
| GET | `/api/search?q=<text>` | Full-text search across all record types |

---

## Calculation Habits

### Rounding
- All currency values: `round(x, 2)` — use standard rounding (half-up or banker's rounding;
  be consistent).
- Community service hours: one decimal place when partial hours are reported.
- All counts and months: integers.

### Dates
- `first_due_date` = disposition/order date + policy `first_due_days_after_order` days.
- `final_due_date` = first_due_date + (total_installments - 1) months (same day of month).
- If the live citation already has a `first_due_date`, preserve it when the packet says
  the plan is already recorded.

### Fee schedule effective dates
The schedule row applies when: `effective_start <= target_date < effective_end` (or
`effective_end` is null). A fee code may have two rows (obsolete + current); pick based
on the disposition/hearing date.

---

## Common Pitfalls

1. **Stale exports are not data sources.** They carry `known_conflict` for a reason.
   Never merge a stale export value into output unless the packet explicitly says the
   stale value is correct and live is wrong.

2. **Citation number ≠ case number.** Traffic citations (CIT-LAN-XXXXX) are their own
   entity. Use the citation number as `account_reference` when no separate case number exists.

3. **Not all packet items need processing.** Some entries have `review_needed: false` or
   are included only for name-similarity checks. Filter to only the matters the packet
   says need review.

4. **Obsolete fee rows are wrong for current hearings.** The API may return a mix of
   current and obsolete rows. Always match by effective date, not by picking the first row.

5. **The draft finance import is a workpaper, not the answer.** Its amounts ("copied from
   older quick-pick", "previous assessment amount") must be verified against the live fee
   schedule and corrected.

6. **Live case status may predate the hearing.** The hearing outcome determines the new
   status; the live record may still show `open`, `warrant`, or `pending` that needs updating.

7. **Empty financial-obligations result means no ledger exists.** When the API returns
   `count: 0`, treat current principal as `0.00`, not as an error.

8. **Matter type filtering.** A case may appear in a stale export for one county/queue
   but its live matter_type may differ (e.g., traffic case in a misdemeanor docket).
   Verify the actual case record, not just the stale export context.

9. **DUI-104 and CR-507 are unsupported charges.** Most county payment policies list them
   under `unsupported_charge_codes`. They may appear in charge lists but should not drive
   payment plan calculations and may need to be excluded from certain financial components.

10. **"No separate sentence/fee pronounced" means skip.** When the bench sheet says a charge
    was convicted "no separate sentence" or "no separate probation setup fee pronounced,"
    do not include the corresponding fee component.

11. **Packet receipt not on ledger.** When the cashier adjustment log says a receipt is
    `not_on_live_ledger`, it must be credited against the balance: `amount_paid_credit =
    live amount_paid + receipt amount`.

12. **Unknown/missing identity fields.** Driver license, phone, and probation officer are
    often null in the packet. Use `"TBD from case file"` as the placeholder value when the
    payment policy defines `unknown_field_placeholder`.
