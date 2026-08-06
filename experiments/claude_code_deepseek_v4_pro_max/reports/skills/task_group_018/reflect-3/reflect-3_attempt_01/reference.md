# Conflict Resolution Quick Reference

## Source Authority Hierarchy

When multiple sources disagree on a fact, resolve in this order:

```
1. Hearing/Courtroom Notes         ← highest authority
2. Audit/Corroborating Memos
3. CMS Portal Identity Fields
4. Finance Queue / Worksheets      ← lowest authority
```

## Specific Conflict Types

### Identity (name, DOB)
- **CMS portal** is the default authority for name spelling and DOB.
- **Audit memo** overrides CMS when it provides a verified correction.
- **Hearing notes** may record bench shorthand (nicknames, approximations); prefer CMS or audit correction.
- When DOB is genuinely missing from ALL sources → `"TBD from case file"`.

### Counsel Classification
- **Hearing notes** record who actually appeared.
- **Audit memo** may clarify labels (e.g., "APD" = appointed private, not public defender).
- Calendar abbreviations (APD, PD, RET) are unreliable shortcuts — verify against portal `counsel_type`.
- Only `public_defender` triggers a PD user fee.

### Charge / Offense
- **Hearing notes** control what offense the court adjudicated.
- Portal charge records may be stale (pre-amendment, pre-appeal).
- Amended charges: the convicted offense is the amended one; the original charge was "amended away."

### Case Status
- **Hearing notes** control whether a final order was signed.
- **Portal `status` field** reflects the CMS record — trust it over finance-queue status.
- "Deferred" or "pending" in CMS + no signed order in hearing notes = case is NOT disposed.

### Departure Findings
- **Hearing notes / judge's stated findings** control departure status.
- Portal departure labels may be draft artifacts from plea worksheets.
- If the judge said "no departure" or hearing notes are silent → `no_departure`.

### Fee Amounts
- **Current fee schedule** (check `effective_date` and `end_date`) controls every dollar.
- Stale schedules (expired `end_date`) are retained for audit history only — never apply them.
- Counter worksheets and old form footers may reference obsolete amounts.

### Financial Entries
- **Hearing notes + CMS status** control whether financials post at all.
- Fee schedule + payment policy control the amounts.
- Queue-extract totals are draft figures — recompute from the current schedule.
```

## Fee Application Decision Tree

```
Is the case disposed with a signed final order?
├── NO → fee_status: "hold" / "do_not_post_pending", case_total: 0.00
└── YES → For each potential fee:
    ├── Is there a current fee schedule (end_date is null or > disposition_date)?
    │   └── NO → Do not apply (stale schedule)
    ├── Is the fee mandatory?
    │   ├── YES → Apply if triggering condition is met
    │   └── NO → Apply only if triggering condition is met AND confirmed by record
    ├── Does the offense trigger this fee?
    │   ├── Drug assessment → controlled-substance conviction
    │   ├── Crime lab fee → controlled-substance conviction
    │   ├── PD user fee → public_defender counsel type
    │   └── Court costs → virtually all disposed criminal cases
    └── Does current policy set this fee to $0.00?
        └── YES → Exclude (amount: 0.00)
```

## Payment Schedule Formula

```
Given: amount_due, monthly_payment, first_due_date, return_to_court_offset_days

full_installment_count = floor(amount_due / monthly_payment)
final_payment_amount   = amount_due - (full_installment_count * monthly_payment)
total_installments     = full_installment_count + (1 if final_payment_amount > 0 else 0)
final_due_date         = first_due_date + (total_installments - 1) months
return_to_court_date   = final_due_date + return_to_court_offset_days

Validate:
  min_monthly ≤ monthly_payment ≤ max_monthly  (from payment policy)
  monthly_payment ≤ monthly_disposable_income   (from petition budget)
```
