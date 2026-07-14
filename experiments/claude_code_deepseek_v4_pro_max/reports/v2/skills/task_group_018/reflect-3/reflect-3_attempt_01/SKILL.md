# Clerk Operations API — Skill for Court Record Reconciliation

## Overview

You are helping court clerks reconcile post-hearing packets against a live Clerk
Operations API. The API exposes case records, citations, fee schedules, payment
policies, docket entries, financial ledgers, hearing calendars, attorney
rosters, and stale-export queues across multiple counties.

Your job is to ingest local packet materials (bench minutes, attorney
verifications, draft imports, stale extracts, compliance notes), cross-check
them against the live environment, resolve discrepancies, and produce a single
structured JSON answer matching the provided answer template.

## Workflow Rules

1. **Read the prompt first.** Every task has `input/prompt.txt`. It names the
   county, hearing/review date, local payload files, and the template to use.
2. **Read the answer template.** It defines the exact JSON shape, allowed enum
   values, sort orders, and precision rules. Never deviate from it.
3. **Read every local payload.** These contain the ground-truth hearing outcomes,
   attorney verifications, draft financials, compliance notes, and stale
   extracts.
4. **Query the live API for every record referenced in the packet.** Use
   case-number lookups, citation-number lookups, fee-schedule queries, payment-
   policy queries, financial-obligation queries, docket queries, and stale-
   export queries.
5. **Resolve conflicts.** The live environment is authoritative for current
   record state, but the local packet (bench minutes, attorney verifications,
   compliance notices) overrides live data for hearing outcomes decided in
   court. Stale extracts are advisory only — flag conflicts but do not use
   stale values as final.

## Source Precedence (highest to lowest)

1. **Bench minutes / judge orders** — charge outcomes, pleas, sentences,
   probation terms, license suspensions, restitution amounts, warrant recalls.
2. **Attorney verification memos / counsel confirmations** — final defense
   attorney name and defense type.
3. **Live case records** — current status, existing charges, docket history.
4. **Live financial ledger** — current principal, fee components, amount paid,
   balance due, payment-plan status.
5. **Current fee schedule** (effective on the disposition or order date) —
   applicable fee codes and amounts.
6. **Live payment policy** — minimum/maximum monthly amounts, first-due-date
   offset, final-smaller-payment rules, unsupported charge codes.
7. **Live docket entries** — procedural history, prior events.
8. **Stale exports** — flag conflicts only; never use as final values.

## Environment API Usage

The base URL is provided via the environment access file. Key endpoints:

| Endpoint | Use |
|---|---|
| `GET /api/cases?county=X&matter_type=Y` | List cases by county/type |
| `GET /api/cases/<case_number>` | Single case detail with charges, status, defense |
| `GET /api/citations/<citation_number>` | Citation detail (traffic matters) |
| `GET /api/fees?county=X&matter_type=Y&effective_on=YYYY-MM-DD` | Fee schedule active on a date |
| `GET /api/payment-policies?county=X` | Installment policy, unsupported codes |
| `GET /api/financial-obligations?case_number=X` | Ledger principal, payments, balance, plan |
| `GET /api/docket?case_number=X` | Procedural history entries |
| `GET /api/hearings?date=YYYY-MM-DD&county=X` | Scheduled hearings |
| `GET /api/attorneys` | Attorney roster with bar numbers, counties, defense types |
| `GET /api/stale-exports?county=X&name=Y` | Stale queue snapshots |
| `GET /api/search?q=text` | Full-text search across records |

## Fee Schedule Rules

1. **Use the schedule active on the disposition or order date**, not the
   current date. Query with `effective_on=<disposition_date>`.
2. **Use the matter-type-specific schedule** (e.g., `matter_type=dui` for DUI
   cases, `matter_type=criminal` for criminal, `matter_type=traffic` for
   traffic). A case's `matter_type` in the live record determines which
   schedule to query.
3. **Old schedules may have fewer codes.** If a case was disposed under an
   old schedule (e.g., 2023–2024), only the codes in that schedule apply. Do
   not retroactively apply new-schedule codes to old dispositions.
4. **Mandatory fees always apply** when their condition is met (conviction,
   license suspension, treatment ordered). **Non-mandatory fees** (e.g.,
   probation setup, restitution admin) apply only when the specific order was
   pronounced.
5. **Unsupported charge codes** listed in the payment policy must be excluded
   from assessed fees.
6. **Draft import CSV files** often contain wrong amounts (copied from old
   quick-pick rows) and unsupported codes. Correct every amount to the
   schedule value and remove any code not in the schedule or in the
   unsupported list.

## Payment Plan / Installment Calculations

1. **Plan basis:** Use `"original_principal"` when the plan was set up from
   the full assessment at disposition. Use `"current_balance"` when a revised
   plan is based on the remaining balance. Use `"no_plan"` when no payment
   plan applies.
2. **Monthly amount:** Use the amount from the local packet's finance request
   when approved by the judge. Default to the policy minimum when the judge
   orders "the lowest amount allowed." Never go below `min_monthly` or above
   `max_monthly`.
3. **First due date:** If the live citation/case already records one, use it.
   Otherwise, compute `disposition_date + first_due_days_after_order` from
   the payment policy (or `review_order_date + first_due_days_after_order`
   for compliance reviews).
4. **Installment count:** Divide the plan basis amount by the monthly amount.
   `full_payment_count = floor(total / monthly)`. `final_payment_amount =
   total - (full_payment_count * monthly)`. If `allows_final_smaller_payment`
   is true and the remainder is > 0, the final payment is the remainder.
   `total_installments = full_payment_count + (remainder > 0 ? 1 : 0)`.
5. **Final due date:** `first_due_date + full_payment_count months` (add
   months preserving the day-of-month).
6. **All dates in `YYYY-MM-DD` format.** All currency rounded to 2 decimal
   places. Community service hours to 1 decimal place.

## Financial Reconciliation Patterns

1. **New principal** = sum of all corrected fee-component amounts (including
   restitution as a line item when ordered). Use current-schedule amounts for
   the fee codes applicable to the hearing outcome.
2. **Amount paid credit** = `amount_paid` from the live financial ledger.
   Payments carry forward when an assessment is replaced.
3. **Corrected balance due** = `new_principal_total - amount_paid_credit`.
4. **Financial delta** = `corrected_assessment_total - current_ledger_principal`.
   A positive delta means fees are being added; negative means fees are being
   removed.
5. **When a live case has no financial obligation**, `current_ledger_principal`
   is `0.00`.
6. **Restitution** appears both in the sentence (`restitution_ordered`) and as
   a fee component (`RESTITUTION` code with the ordered amount) in the
   financial assessment.

## Discrepancy & Status Codes

### Case-level discrepancy codes
- `none` — attorney, status, and financials all align.
- `attorney_conflict` — defense attorney name or type differs between live
  record and verified counsel.
- `status_conflict` — case status in live record conflicts with hearing
  outcome (e.g., warrant status when case was resolved).
- `financial_schedule_conflict` — draft import or live ledger has wrong
  amounts, obsolete schedule values, or unsupported codes.
- `attorney_and_status_conflict` — both attorney and status need correction.
- `status_and_financial_conflict` — both status and financials need correction.
- `identity_conflict` — defendant identity mismatch across records.

### Representation mismatch
Set `true` when the resolved counsel record (from confirmation/verification)
differs from the live case representation in name or defense type. Set `false`
when they match.

### Case status after hearing
- `probation_active` — conviction entered with probation ordered.
- `closed` — matter fully resolved, no ongoing supervision.
- `deferred` — deferred adjudication in effect.
- `open` — no disposition entered, matter remains pending.
- `warrant` — active warrant.
- `warrant_recalled_pending_entry` — warrant recalled but entry not yet posted.
- `dismissed` — all charges dismissed.
- `needs_review` — conflicting information requires supervisor attention.

## Charge Outcome Rules

1. **Charge outcomes come from the bench minutes**, not the live case record.
   The hearing overrides whatever the live record shows.
2. **Plea values:** `guilty`, `no_contest`, `not_guilty`, `not_entered`,
   `deferred_entry`.
3. **Disposition values:** `convicted`, `dismissed`, `deferred`, `pending`,
   `amended`. Use `convicted_no_separate_fee` when the bench specifically notes
   "no separate sentence" or "no separate fee" for a conviction.
4. **Verdict values:** `guilty`, `not_guilty`, `dismissed`, `deferred`,
   `not_adjudicated`.
5. **A dismissed charge** at hearing means: plea = `not_entered` (or whatever
   the minutes say), disposition = `dismissed`, verdict = `dismissed`.
6. **Convicted charge count** counts only charges where the final disposition
   is `convicted` (not dismissed, not deferred, not amended without conviction).

## Docket Actions

- `enter_plea` — true when the hearing accepted a plea that differs from the
  live record.
- `enter_sentence` — true when a sentence was pronounced.
- `recall_warrant` — true when a warrant was recalled in open court.
- `enter_attorney_update` — true when the defense attorney name or type needs
  updating on the live record.
- `generate_financial_entry` — true when new or corrected fees need to be
  posted.
- `needs_supervisor_review` — true when the attorney verification memo or
  bench note explicitly requests supervisor routing.
- `enter_disposition_and_assess` — for cases with a new disposition and
  financial assessment to enter.
- `financial_adjustment` — for existing ledger entries that need amount
  corrections.
- `update_status_and_representation` — for status/counsel changes without
  financial changes.
- `release_to_entry` — final release of a completed matter.
- `no_update_needed` — everything already matches.

## Compliance Review Patterns

1. **Only include cases where `review_needed: true`** from the local packet.
   Skip informational/stale-export-only items.
2. **Correction amount:** A positive value reduces the live balance (e.g.,
   posting a receipt that was omitted from the ledger).
3. **Financial status after review:**
   - `paid` — balance is already 0.
   - `paid_after_credit` — balance becomes 0 after posting a credit/receipt.
   - `current` — payments are up to date on an active plan.
   - `delinquent` — payments are behind.
   - `replan_approved` — a revised payment plan was approved.
   - `pending_adjustment` — awaiting a financial correction.
4. **Restitution status:** `none` (not ordered), `open` (ordered but not fully
   paid/disbursed), `paid_or_disbursed` (fully satisfied).
5. **Community service:** `not_ordered`, `complete` (all hours verified),
   `partial` (some hours remaining), `unknown` (no provider notice).
   Remaining hours = `sentence_hours - verified_completed_hours`.
6. **Payment plan actions:** `none`, `keep_existing`, `approve_revised_plan`,
   `send_return_to_court`, `post_credit_close`.
7. **Source conflict codes:** `no_source_conflict`,
   `live_ledger_vs_packet_receipt` (receipt in packet not on ledger),
   `petition_changes_payment_plan` (ability-to-pay petition approved),
   `packet_service_shortfall` (community service hours incomplete).
8. **Next actions:** `post_receipt_close`, `approve_plan_and_notice`,
   `issue_return_to_court_notice`, `continue_monitoring`,
   `community_service_followup`, `no_action`.

## Output Conventions

1. **Return only the JSON object** matching the answer template — no markdown
   fences, no commentary.
2. **Sort rules (always ascending):**
   - Case rows by `case_number` (string sort).
   - Charge outcomes by `charge_id`.
   - Fee components by `fee_code`.
   - Excluded codes by code.
   - Case number lists in aggregates.
3. **Null vs. TBD:** Use `"TBD from case file"` (exact string from the payment
   policy's `unknown_field_placeholder`) for identity fields with null values
   (driver's license, phone, probation officer). Use JSON `null` for dates and
   amounts when no payment plan applies.
4. **Currency:** Always 2 decimal places (e.g., `455.00`, `0.00`).
5. **Community service hours:** Always 1 decimal place (e.g., `6.0`, `16.0`).
6. **Dates:** `YYYY-MM-DD` format.
7. **Times:** `HH:MM` format (24-hour).
8. **Counts and months:** Integers.

## Common Pitfalls

1. **Using today's date instead of the disposition/order date** for fee
   schedule lookups. Always use the hearing or disposition date from the
   packet.
2. **Mixing criminal and DUI fee schedules.** Check the case's `matter_type`
   and query the matching schedule.
3. **Including fees from the new schedule on old cases.** If the disposition
   predates a schedule change, use the schedule effective on the disposition
   date.
4. **Not removing unsupported charge codes.** Always check the payment policy's
   `unsupported_charge_codes` list and exclude them.
5. **Not adding missing mandatory fees.** If the schedule says a fee is
   mandatory and its condition is met, include it even if the draft import
   omitted it.
6. **Forgetting to add `CR-REST-ADM` when restitution is ordered.** If
   restitution > 0, the restitution administration fee applies (unless the
   schedule doesn't have it for that date).
7. **Incorrect installment math.** When `allows_final_smaller_payment` is true,
   the final payment can be less than the monthly amount. Use floor division.
8. **Overwriting live ledger credits.** The `amount_paid` carries forward when
   replacing a financial entry.
9. **Including non-review cases in compliance packets.** Check `review_needed`
   and skip items where it's false.
10. **Using stale-export values as final.** Stale exports are advisory flags
    only. The live environment record is authoritative.
11. **Case-number sort order.** String-sort ascending: `23-` before `24-`
    before `25-`, and within the same year prefix, numeric sort by the
    sequence number.
12. **Including RESTITUTION as a fee code.** The draft import may list it;
    include it in `fee_components` when restitution was ordered. The
    `new_principal_total` is the sum of all fee components including
    restitution.
