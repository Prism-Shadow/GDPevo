# Clerk Operations Skill

## Workflow Rules

1. **Read all local payloads first.** The task directory contains `input/payloads/` with
   bench/hearing packets, attorney memos, stale exports, draft finance imports, and an
   `answer_template.json` — read every file before querying the environment.

2. **Identify target cases.** The packet or prompt identifies which case numbers or citation
   numbers are in scope. Stale exports may list additional records — only act on the targets
   named in the packet or bench notes.

3. **Query the remote environment for each target.** Look up the live case record, docket
   history, financial obligations, fee schedule, payment policy, stale exports, and attorney
   records. Use the endpoints listed in `environment_access.md`.

4. **Cross-reference packet claims against live data.** If the packet says a warrant was
   recalled or an attorney substituted, verify against the live case. Resolve discrepancies
   in favour of the more recent verified source (bench minutes + attorney verification memo
   override stale exports).

5. **Compute corrected financials.** Use the fee schedule **effective on the disposition or
   order date**, not today's date. Only include fee codes present in the applicable schedule
   and supported by the county's payment policy. Exclude codes listed in
   `unsupported_charge_codes`.

6. **Fill the answer template exactly.** Return only JSON conforming to the schema in the
   local `answer_template.json`. Sort lists as directed (case numbers ascending, fee codes
   ascending, citation numbers ascending).

## Source Precedence

| Priority | Source | When to use |
|----------|--------|-------------|
| 1 (highest) | Bench minutes / hearing packet | Plea, disposition, sentence pronounced in court |
| 2 | Attorney/counsel verification memo | Final defense attorney and defense type |
| 3 | Live environment case record | Current status, charges, docket entries |
| 4 | Live environment financial ledger | Principal, payments, balance due, fee components |
| 5 | Fee schedule (effective on order date) | Correct fee codes and amounts |
| 6 | Payment policy | Installment plan rules, unsupported charge codes |
| 7 (lowest) | Stale exports / draft finance imports | Contextual hints only — do not use as authoritative |

## Fee Schedule Usage

- Query `/api/fees?county=<county>&matter_type=<type>&effective_on=<YYYY-MM-DD>`.
  Use the **order date or disposition date** as `effective_on`, not the current date.
- Fee schedules have `effective_start` and `effective_end` ranges. A schedule row applies
  only when the effective date falls within its range.
- `mandatory: true` codes always apply when the triggering condition is met.
- `mandatory: false` codes apply only when the specific condition (probation, restitution,
  traffic school, etc.) was ordered.
- **RESTITUTION is not a fee code** — do not list it in `fee_components` or
  `assessed_fee_codes`. It is tracked separately via `restitution_ordered` or
  `restitution_amount` in the live ledger. Include its amount in `new_principal_total`
  but do not list it as a fee component.

## Financial Calculations

```
new_principal_total = sum(applicable fee amounts) + restitution_amount
corrected_balance_due = new_principal_total - amount_paid_credit
financial_delta = corrected_assessment_total - current_ledger_principal
```

- `amount_paid_credit` comes from the live ledger's `amount_paid` field.
- When the live environment has no financial obligation for a case, treat
  `current_ledger_principal` as `0.00`.
- Round all currency values to 2 decimal places.

## Installment Plan Calculations

From payment policy: `min_monthly`, `max_monthly`, `allows_final_smaller_payment`,
`first_due_days_after_order`.

```
monthly_amount = approved monthly amount (from packet, citation, or policy minimum)
full_payment_count = floor(balance / monthly_amount)
final_payment_amount = balance - full_payment_count * monthly_amount
total_payment_count = full_payment_count + (final_payment_amount > 0 ? 1 : 0)
first_due_date = order_date + first_due_days_after_order (calendar days)
final_due_date = first_due_date + (full_payment_count) months
```

- When `allows_final_smaller_payment` is `false`, the final payment must be ≥ `min_monthly`.
  If it would be smaller, absorb it into the last full payment or add another installment.
- When the payment plan already exists on the live citation or ledger, use the existing
  `first_due_date` and `monthly_amount` if the packet says the plan was "already recorded."

## Common Pitfalls

1. **Wrong effective date on fee schedule.** Always match `effective_on` to the order or
   disposition date. Using today's date may return a different schedule with different rates.

2. **Listing restitution as a fee code.** RESTITUTION is not a schedule fee. Put it in
   `new_principal_total` but not in `fee_components`/`assessed_fee_codes`.

3. **Using stale export values as authoritative.** Stale exports may have outdated status,
   defense info, principal amounts, or license dates. The live environment is the authority.

4. **Misclassifying case status.** After a conviction with probation ordered, the status is
   `probation_active` (not `warrant_recalled_pending_entry` even if a warrant was also
   recalled). `warrant_recalled_pending_entry` is for cases where only a warrant recall
   occurred without other disposition.

5. **Wrong disposition class.** `disposition_class` reflects the actual case outcome
   (`convicted`, `deferred`, `dismissed`, `pending_no_disposition`), not the type of
   review being conducted (`ledger_review_only` is only for cases where no disposition
   was ever entered and only financial cleanup occurs).

6. **Including unsupported charge codes.** Check the county's payment policy
   `unsupported_charge_codes` list. Codes like `CR-507`, `TR-231`, `DUI-104` may be
   unsupported in certain counties. Exclude them from assessed components.

7. **Forgetting mandatory fees.** `CR-FILING` is mandatory in criminal schedules even if
   the draft import omitted it. For cases filed under the current schedule, include it.

8. **Mixed fee code granularity.** DUI cases use DUI-specific codes (`DUI-CONV`, `DUI-LIC`,
   `DUI-TREAT`, `DUI-PROB`), not generic criminal codes (`CR-CONV`, etc.). Traffic cases
   use `TR-*` codes. Always query the right `matter_type` for the schedule.

9. **Plan calculation errors.** Use `floor()`, not `ceil()`, for `full_payment_count`.
   The remainder becomes the `final_payment_amount`. `total_payment_count` = full + 1
   (if final > 0).

10. **Sorting violations.** Answer templates specify ordering: case numbers ascending,
    fee codes ascending, charge IDs ascending, citation numbers ascending. Follow these
    exactly.

## Output Conventions

- All dates in ISO `YYYY-MM-DD` format.
- All currency amounts rounded to 2 decimal places.
- `null` for optional fields that do not apply (e.g., plan fields when there is no plan).
- `"TBD from case file"` for identity fields where the value is unknown (per payment policy
  `unknown_field_placeholder`).
- Boolean fields: `true`/`false` (not strings).
- Empty lists `[]` when no items exist (not omitted).
