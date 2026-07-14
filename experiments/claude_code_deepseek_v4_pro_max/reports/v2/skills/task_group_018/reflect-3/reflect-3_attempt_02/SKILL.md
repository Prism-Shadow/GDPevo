# Clerk Operations Skill

## Overview

Resolve court-clerk post-hearing tasks using a shared clerk operations REST API. The environment provides live case records, fee schedules, payment policies, financial obligations, docket entries, citations, hearings, attorneys, and stale export snapshots. Local packets supply bench minutes, verification memos, draft finance imports, and compliance counter items that must be reconciled against the live environment.

## Workflow

1. **Read the task prompt** — identify the county, docket/hearing/review date, and target case numbers/citations.
2. **Read the answer template** — note every required key, enum value, ordering rule, and numeric precision.
3. **Query the live environment for every target record** — at minimum: `/api/cases/<id>` (or `/api/citations/<id>`), `/api/financial-obligations?case_number=<id>`, `/api/docket?case_number=<id>`.
4. **Query fee schedules** with `?county=<C>&matter_type=<T>&effective_on=<YYYY-MM-DD>` — always use the disposition or event date, not today's date.
5. **Query payment policy** with `?county=<C>` — capture min/max monthly, `first_due_days_after_order`, `allows_final_smaller_payment`, and `unsupported_charge_codes`.
6. **Query stale exports** `?county=<C>&name=<N>` when the task references one — treat these as historical conflict warnings, not authoritative.
7. **Reconcile sources** in priority order (see Source Precedence), then build the answer strictly to the template shape.

## Source Precedence

When the live environment, local packet, and stale exports disagree:

1. **Bench/hearing minutes** (in local packet) — final authority for pleas, verdicts, sentences, and what the judge pronounced.
2. **Attorney verification / counsel confirmation memos** (local) — override live case counsel fields for name and defense type.
3. **Live API records** (`/api/cases`, `/api/financial-obligations`, `/api/docket`) — current state of record; the baseline for corrections.
4. **Fee schedule rows** returned by `/api/fees` — authoritative for amounts; discard draft-import amounts that don't match the schedule.
5. **Payment policy** (`/api/payment-policies`) — authoritative for installment rules and unsupported charge codes.
6. **Stale export records** — reference only; flag conflicts but do not copy values from them.
7. **Draft finance CSVs / import workpapers** (local) — unverified; validate every row against the fee schedule and exclude unsupported codes.

## Fee Schedule Rules

- **Date sensitivity**: Fee schedules are versioned by `effective_start` / `effective_end`. Always query with `effective_on` set to the disposition date or event date. Schedules active on that date are the ones that apply. A fee code present in 2025 may not exist in 2024.
- **Matter type matters**: Use the correct `matter_type` query parameter (`criminal`, `traffic`, `dui`, `compliance`). Different matter types have completely different fee codes.
- **Mandatory vs. conditional**: `mandatory: true` fees apply whenever their `applies_when` condition is met. `mandatory: false` fees apply only when the triggering event actually occurred (e.g., probation ordered, restitution ordered, traffic school elected).
- **Filing fees**: CR-FILING and similar filing assessments apply once at case filing. If the case was filed under an older schedule that lacked the fee code, do not retroactively add it.
- **Unsupported codes**: Any charge or fee code listed in the payment policy's `unsupported_charge_codes` array must be excluded from financial assessment. Also exclude candidate codes from draft workpapers that have no matching row in the fee schedule.
- **Obsolete vs. current**: When the task says "current schedule," use rows with no `effective_end`. When replacing obsolete assessments, use current rates for the replacement.

## Financial Calculation Habits

- **Principal = sum of assessed fee components.** Only include fee codes that exist in the active schedule and whose conditions are met.
- **Restitution**: May be tracked as a separate field (`restitution_amount`) alongside `principal_amount` in the live ledger. Whether to include restitution in the `fee_components` list depends on the answer template — check whether the template has a separate restitution field. When in doubt, include RESTITUTION as a line item in `fee_components` so the totals are complete.
- **Balance due**: `corrected_balance_due = new_principal_total (+ restitution if separate) - amount_paid_credit`.
- **Payment plan installment math**:
  - Divide balance by monthly amount.
  - `full_payment_count = floor(balance / monthly_amount)`.
  - `final_payment_amount = balance - (full_payment_count × monthly_amount)` — rounded to 2 decimals.
  - `total_installments = full_payment_count + 1` (or just 1 if balance < monthly).
  - `first_due_date = order_date + policy.first_due_days_after_order` days.
  - `final_due_date = first_due_date + (full_payment_count) months`.
  - Only produce a smaller final payment when `allows_final_smaller_payment: true`.
- **Plan basis**: Use `"original_principal"` when reporting a plan that was established at disposition against the full principal. Use `"current_balance"` when computing a new or revised plan against the remaining balance. Use `"no_plan"` when no payment plan applies.
- **Financial delta**: `corrected_assessment_total - current_ledger_principal`. Positive = new money owed; negative = credit/removal.
- **All currency values**: round to 2 decimal places. Counts and months: integers. Community service hours: 1 decimal place where specified.

## Status and Discrepancy Conventions

- **Use only the enum values from the answer template.** Do not invent statuses.
- A case needs `"needs_review"` status when the attorney verification or bench note explicitly routes it to a supervisor.
- `"warrant_recalled_pending_entry"` — warrant was recalled at hearing, entry is pending, no supervisor required.
- `"probation_active"` — sentence with probation was pronounced and entry can proceed (no warrant involved, or warrant was from a different matter).
- Discrepancy codes reflect what changed between the live record and the resolved outcome: `"attorney_conflict"` for counsel changes only, `"financial_schedule_conflict"` for obsolete/wrong fee schedules, `"attorney_and_status_conflict"` when both change, `"status_and_financial_conflict"` for warrant status + financial issues, `"none"` when everything matches after hearing.

## Attorney and Representation Handling

- The attorney verification memo or counsel confirmation (in the local packet) is the final resolved counsel record. Use its name and defense type even when the live case shows different values.
- Set `representation_mismatch: true` when the stale export OR live case representation details differ from the resolved counsel record.
- Defense type choices: `retained`, `appointed_private`, `public_defender`, `self_represented`, `unknown`.

## Docket Action Flags

- `enter_plea` / `enter_sentence`: true when the hearing produced new pleas or sentences.
- `recall_warrant`: true when the bench minutes explicitly state the warrant was recalled.
- `enter_attorney_update`: true when the resolved counsel differs from the live case record.
- `generate_financial_entry`: true when the corrected assessment differs from the current live ledger principal OR when a draft import needs replacement. False when the live ledger already matches the corrected calculation.
- `needs_supervisor_review`: true only when the verification memo or bench note explicitly requests supervisor routing.

## API Usage Patterns

- Base URL comes from the environment configuration (see `environment_access.md`). All endpoints are GET except the health check.
- Fee schedule: `/api/fees?county=<C>&matter_type=<T>&effective_on=<YYYY-MM-DD>` — always query multiple effective dates when cases span different filing/disposition years.
- Payment policy: `/api/payment-policies?county=<C>` — one per county.
- Financial obligations: `/api/financial-obligations?case_number=<CN>` — returns principal, fee components, restitution, amount paid, balance, and payment plan fields.
- Docket: `/api/docket?case_number=<CN>` — entry history.
- Stale exports: `/api/stale-exports?county=<C>&name=<N>` — optional `name` filter.
- Case and citation detail endpoints return the live record including charges, defense counsel, status, and sentence.

## Common Pitfalls

- **Using the wrong effective date for fees.** A 2024 disposition uses the 2024 fee schedule, not the 2025 one. Fees that only exist in 2025 (e.g., CR-FILING, TR-SPEED, DUI-PROB in some counties) cannot be assessed on pre-2025 events.
- **Forgetting matter_type in fee queries.** `matter_type=criminal` and `matter_type=dui` return different fee codes. Check the live case's `matter_type` field and match it.
- **Including unsupported charge codes.** Cross-check every candidate fee code against both the fee schedule (must exist) and the payment policy's `unsupported_charge_codes` list (must not appear).
- **Copying draft finance amounts without validation.** Draft CSVs often carry wrong amounts from old quick-picks. Always replace with current schedule amounts.
- **Treating stale exports as authoritative.** Stale exports are labeled with a known_conflict field — use them only to flag potential issues, never as the source of truth.
- **Mixing up plan_basis.** A plan established at original disposition uses `"original_principal"`; a plan recalculated from the remaining balance uses `"current_balance"`.
- **Including non-review items in the output.** When a packet lists items with `review_needed: false`, exclude them — even if they appear in the same local JSON array.
- **Using the wrong ordering.** Sort case rows, charge outcomes, fee components, and excluded codes as specified in the answer template (usually ascending by number or code).
- **Incorrect installment math.** Only include a smaller final payment when the policy `allows_final_smaller_payment`. When the remaining balance is less than the monthly amount, produce exactly 1 installment.
- **Omitting CR-FILING for pre-2025 cases.** If the filing occurred under an old schedule that lacked the CR-FILING code, do not add it now — the filing event already passed under different rules.
