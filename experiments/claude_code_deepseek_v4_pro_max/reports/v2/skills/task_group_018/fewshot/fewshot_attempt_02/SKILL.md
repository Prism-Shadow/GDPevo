# Court Clerk Operations — Docket Processing Skill

## Overview

Process post-hearing court docket packets for a county clerk. Cross-reference local
packet materials (judge minutes, attorney memos, stale extracts, hearing notes) against
the live clerk operations API to resolve case status, charge outcomes, attorney
representation, financial assessments, and docket-entry actions.

You will receive a task prompt naming the county, hearing/docket date, matter type, and
local payload files. Produce a single JSON answer matching the supplied answer template.

---

## Environment

The clerk operations API runs at the URL given in `environment_access.md` — **that URL
overrides any localhost or `env/setup.sh` reference** found in task text. All API calls
are read-only `GET` requests.

### Endpoints

| Endpoint | Parameters | Returns |
|---|---|---|
| `/api/counties` | — | County registry: `county`, `court`, `code` |
| `/api/cases` | — | All case records (charges, status, attorney, sentence) |
| `/api/cases/<case_number>` | — | Single case by number |
| `/api/citations` | — | All citation records |
| `/api/citations/<citation_number>` | — | Single citation |
| `/api/hearings` | `date` (YYYY-MM-DD), `county` | Hearing docket entries for date+county |
| `/api/attorneys` | — | Attorney registry (bar number, firm, counties, active flag, defense types) |
| `/api/fees` | `county`, `matter_type`, optional `effective_on` | Fee schedule rows for county+matter |
| `/api/payment-policies` | `county` | Installment plan rules and unsupported charge codes |
| `/api/financial-obligations` | `case_number` | Financial ledger: principal, components, paid, balance, payment plan |
| `/api/docket` | `case_number` | Docket event history (entries with dates and event types) |
| `/api/stale-exports` | `county`, `name` | Stale case-management extracts queued for processing |
| `/api/search` | `q` | Full-text search across all record types |

### Key data shapes

**Case record**: `case_number`, `county`, `court`, `matter_type`, `defendant_name`,
`status`, `filing_date`, `charges[]` (charge_id, statute, description, severity,
offense_date, plea, verdict, disposition), `defense_attorney`, `defense_type`,
`disposition_date`, `sentence` (jail_days, suspended_days, community_service_hours,
treatment_ordered), `probation_months`, `license_suspension_months`, `restitution_ordered`,
`tags[]`.

**Fee schedule row**: `county`, `matter_type`, `fee_code`, `description`, `applies_when`,
`amount`, `effective_start`, `effective_end` (null = current), `mandatory`.

**Payment policy**: `county`, `min_monthly`, `max_monthly`, `allows_final_smaller_payment`,
`first_due_days_after_order`, `return_to_court_days_after_missed_payment`,
`unknown_field_placeholder` (value `"TBD from case file"`), `unsupported_charge_codes[]`.

**Financial obligation**: `case_number`, `order_date`, `principal_amount`,
`fee_components[]` (fee_code, description, amount, source_effective_start),
`restitution_amount`, `amount_paid`, `balance_due`, `payment_plan`, `monthly_amount`,
`next_due_date`, `missed_payments`, `status`, `source`.

**Attorney**: `attorney_id`, `name`, `bar_number`, `firm`, `counties[]`, `phone`,
`email`, `active`, `defense_types[]`.

---

## Workflow

### Step 1 — Read local materials

Read every file in `input/payloads/`:
- **Packet / hearing notes**: the primary source of truth for judge rulings, plea
  entries, sentence terms, attorney confirmations, and receipt amounts.
- **Stale extract** (if provided): may contain older case-management values; use only
  when live data is missing or as corroboration when a conflict needs flagging.
- **Answer template**: dictates the exact JSON shape, key order, and controlled
  vocabularies you must produce.

### Step 2 — Identify the matters

From the task prompt and local packet, determine:
- **County** — drives fee schedule, payment policy, court name.
- **Hearing / docket / review date** — the effective date for fee schedule selection.
- **Matter type** (`criminal`, `traffic`, `dui`, or per the case record's `matter_type`).
- **List of case numbers or citation numbers** to process.

If the task says "use the citation number as the case/account reference," do exactly
that when the live citation has no separate case number.

### Step 3 — Pull live records

For each case/citation in scope, fetch from the API:
1. **Case** at `/api/cases/<case_number>` (or `/api/citations/<citation_number>`).
2. **Docket** at `/api/docket?case_number=<case_number>`.
3. **Financial obligations** at `/api/financial-obligations?case_number=<case_number>`.
4. **Fee schedule** at `/api/fees?county=<county>&matter_type=<matter_type>`.
   - If a matter_type-specific schedule exists (e.g., `dui` for Gloucester), fetch that
     separately.
5. **Payment policy** at `/api/payment-policies?county=<county>`.
6. **Attorneys** at `/api/attorneys` (full list; filter by name/county).

Query `/api/hearings?date=<date>&county=<county>` and `/api/stale-exports?county=<county>&name=<name>`
when the task references a hearing docket or stale export queue.

### Step 4 — Cross-reference and resolve

Compare local packet data against live API records for each field:

**Charges**: The judge's minute card / hearing notes are the final word on plea,
disposition, and verdict per charge. When the live case record disagrees, the local
judge ruling wins.

**Case status**: Determine from the combined picture. Common statuses: `open`, `closed`,
`probation_active`, `deferred`, `warrant`. If the live record shows `warrant` but the
hearing resolved the case, the status should reflect the resolved posture.

**Attorney**: Compare the attorney named in local counsel confirmations against the live
case's `defense_attorney` field. Also verify the attorney is active and authorized for
the county and defense type. Flag mismatches. Defense types: `retained`,
`appointed_private`, `public_defender`.

**Sentence**: Judge minutes override the live case record. Fields: `jail_days`,
`suspended_days`, `probation_months`, `community_service_hours`, `treatment_ordered`,
`restitution_ordered`. If no sentence was ordered, use 0/false.

**Financial ledger**: The live `/api/financial-obligations` may reflect an older,
incorrect assessment. Your corrected assessment uses the current fee schedule (see
Step 5). Compare corrected vs. live principal to compute financial deltas.

### Step 5 — Assess fees

Select fee schedule rows where:
- `effective_start <= event_date` AND (`effective_end IS NULL OR effective_end >= event_date`)
- Ignore rows marked obsolete (those with `effective_end` before the event date).

Apply fees conditionally:

| Fee code pattern | Condition to assess |
|---|---|
| `CR-CONV`, `DUI-CONV`, `TR-BASE` | At least one charge has a conviction disposition |
| `CR-FILING` | Always (mandatory filing fee) |
| `CR-PROB`, `DUI-PROB` | Probation was ordered (`probation_months > 0`) |
| `CR-REST-ADM` | Restitution was ordered (`restitution_ordered > 0`) |
| `DUI-LIC` | License suspension ordered (`license_suspension_months > 0`) |
| `DUI-TREAT` | Treatment was ordered (`treatment_ordered: true`) |
| `TR-LATE` | Payment delinquency (check ledger for missed payments) |
| `TR-SPEED` | Citation has a speed value (check `speed_mph` / `posted_speed_mph`) |
| `TR-SCHOOL` | Traffic school elected (check plea/citation notes) |

**Deferred dispositions**: A deferred case does NOT get a conviction fee. Only the
filing fee applies.

**Excluded codes**: Check the payment policy's `unsupported_charge_codes` list. Do not
assess a fee for a charge whose statute appears in that list. Likewise, a charge with
disposition `convicted_no_separate_fee` generates no separate fee row.

**Charge-level vs. case-level fees**: Filing fees (CR-FILING) and conviction assessments
are case-level (once per case). Conditional fees like probation, restitution admin,
treatment are also case-level — don't multiply by charge count.

### Step 6 — Compute financials

```
new_principal = sum(applicable mandatory fee amounts) + sum(applicable conditional fee amounts) + restitution_ordered
corrected_balance_due = new_principal - amount_paid_credit
```

- `amount_paid_credit` comes from the live financial ledger (`amount_paid`).
- Round all amounts to 2 decimal places.
- When the task asks for "final approved principal amounts before payments," report
  `new_principal`, not balance due, and compare against the live ledger principal.

### Step 7 — Build payment plan (when ordered)

Use the county payment policy:

```
monthly_amount: between policy.min_monthly and policy.max_monthly
                 (choose a reasonable round number that divides the principal efficiently)
first_due_date: order_date + policy.first_due_days_after_order
regular_payment_count: floor(principal / monthly_amount)
final_payment_amount: principal - (regular_payment_count * monthly_amount)
total_installments: regular_payment_count + (1 if final_payment_amount > 0 else 0)
final_due_date: add (total_installments - 1) months to first_due_date
```

- If `allows_final_smaller_payment` is false, adjust `monthly_amount` so the final
  payment equals the regular monthly amount (or use a different split).
- Null out plan fields when no payment plan exists.

### Step 8 — Determine docket actions

Mark which docket updates are needed:
- **`enter_plea`**: true when the live record's plea differs from the judge's accepted plea.
- **`enter_sentence`**: true when sentence fields need entry/update.
- **`recall_warrant`**: true when the live case status is `warrant` and the hearing resolved it.
- **`enter_attorney_update`**: true when attorney or defense type differs from live record.
- **`generate_financial_entry`**: true when a new or corrected financial assessment is needed.
- **`needs_supervisor_review`**: true when discrepancies exist that need human sign-off.

### Step 9 — Assemble the answer

Follow the answer template's structure exactly:
- Match key names, nesting, and array ordering.
- Order case rows by case number (ascending).
- Use only the controlled enum values present in the template.
- Fill `"TBD from case file"` for identity fields the API/packet cannot resolve.
- Compute aggregate totals as defined by the template (sums, counts, lists).

---

## Output Conventions

| Rule | Example |
|---|---|
| Dates | `"2025-06-20"` (ISO 8601, YYYY-MM-DD) |
| Currency | `822.50` not `822.5` (exactly 2 decimals, but trailing zero optional) |
| Nulls | Use `null` for absent values, `0.0` for zero amounts, `false` for booleans |
| Empty arrays | `[]` not omitted |
| Case ordering | Ascending by case number / citation number |

---

## Source Precedence (highest to lowest)

1. **Judge minute card / hearing notes** (local packet) — final word on plea, verdict,
   disposition, sentence.
2. **Attorney verification memo** (local packet) — final word on counsel of record.
3. **Live API case record** (`/api/cases/<case_number>`) — current case-management
   state, charge detail, defendant identity.
4. **Live API financial ledger** (`/api/financial-obligations`) — payments received.
5. **Live API fee schedule** (`/api/fees`) — authoritative fee amounts for the
   effective date.
6. **Live API payment policy** (`/api/payment-policies`) — installment rules.
7. **Stale export** (local packet) — use only as corroboration; live data wins when
   they conflict.

---

## Controlled Vocabularies

**Plea**: `guilty`, `not_guilty`, `no_contest`, `not_entered`, `deferred_entry`

**Disposition**: `convicted`, `dismissed`, `amended`, `deferred`, `satisfied`,
`convicted_no_separate_fee`, `pending_no_disposition`

**Verdict**: `guilty`, `not_guilty`, `dismissed`, `not_adjudicated`

**Case status**: `open`, `closed`, `probation_active`, `deferred`, `warrant`

**Defense type**: `retained`, `appointed_private`, `public_defender`

**Discrepancy codes** (criminal docket): `status_and_financial_conflict`,
`attorney_conflict`, `status_conflict`, `attorney_and_status_conflict`

**Discrepancy codes** (compliance): `live_ledger_vs_packet_receipt`,
`petition_changes_payment_plan`, `packet_service_shortfall`, `no_source_conflict`

**Financial status**: `paid`, `paid_after_credit`, `current`, `delinquent`,
`replan_approved`

**Docket actions**: `no_update_needed`, `update_status_and_representation`,
`financial_adjustment`, `enter_disposition_and_assess`

**Follow-up actions**: `enter_probation_license_payment_order`, `post_receipt_close`,
`approve_plan_and_notice`, `issue_return_to_court_notice`, `continue_monitoring`,
`community_service_followup`

---

## County Quick Reference

| County | Code | Court | Matter types |
|---|---|---|---|
| Benton | BEN | Benton County Circuit Court | criminal, traffic |
| Lane | LAN | Lane County Justice Court | traffic |
| Gloucester | GLO | Gloucester County Superior Court | criminal, dui |
| Marion | MAR | Marion County Circuit Court | criminal |
| Wasco | WAS | Wasco County District Court | criminal |
| Columbia | COL | Columbia County Circuit Court | (varies) |
| Jefferson | JEF | Jefferson County Municipal Court | (varies) |
| Middlesex | MID | Middlesex County Superior Court | (varies) |

---

## Common Pitfalls

1. **Using obsolete fee rows**. Always filter by `effective_start <= event_date` and
   `effective_end IS NULL OR effective_end >= event_date`. A row with `effective_end`
   in the past is obsolete and its amount must not be used.

2. **Date confusion**. The "effective date" for fee selection is the disposition/order
   date, not today's date and not the filing date. Use the hearing/disposition date
   from the task prompt or packet.

3. **Applying conviction fees to deferred cases**. A deferred disposition is not a
   conviction — do not assess `CR-CONV`, `DUI-CONV`, or similar conviction-triggered
   fees.

4. **Missing the restitution in principal**. `restitution_ordered` is part of the
   financial obligation total, in addition to fee components.

5. **Ignoring charge-level exclusions**. Check `unsupported_charge_codes` in the
   payment policy and the disposition value `convicted_no_separate_fee` — both
   suppress fee assessment for specific charges.

6. **Forgetting to apply ledger credits**. The live ledger's `amount_paid` must be
   subtracted from the corrected principal to compute `corrected_balance_due`.

7. **Case vs. citation lookup**. For traffic matters, if the citation has no
   associated case number, use the citation number as the account reference and
   look up `/api/citations/<citation_number>` instead of `/api/cases/...`.

8. **Attorney cross-county authorization**. An attorney may be listed on a case but
   not authorized for that county or defense type. Verify against the attorney record.

9. **Stale extract traps**. A stale export reflects older case-management state.
   Always prefer the live API record. Use stale extracts only to flag discrepancies,
   not as the authoritative source.

10. **Answer template fidelity**. Match the answer template's structure exactly —
    key names, nesting depth, array element ordering, enum spelling. Do not add
    extra keys or omit required keys even if null/empty.

11. **Payment plan date arithmetic**. `first_due_date` is `order_date +
    first_due_days_after_order` (from the county payment policy). Each subsequent
    due date is one month later (same day of month). When the day exceeds the
    month's length, use the last day of that month.
