# Business Rules Reference

This document captures detailed decision logic for each reconciliation
workflow. Read it when the SKILL.md overview does not give enough detail
for an edge case.

## Claim-to-payment reconciliation flow

```
For each claim in scope:
  1. Read claim record (status, amount, vendor_id, receipt_status, policy_flags)
  2. Find all AP bills where bill.claim_id == claim.claim_id
  3. For each bill, find all payments where payment.bill_id == bill.bill_id
  4. Classify:
     - If any bill is paid AND has a cleared payment for non-zero amount: PAID
     - Else if claim status is approved AND at least one non-void bill exists: PAYABLE
     - Else: BLOCKED (CRM-required)
```

### Paid classification

A claim is paid when there exists at least one bill-payment pair where
bill.status is "paid" AND payment.status is "cleared" AND payment.amount > 0.
A claim with status "paid" in the claims endpoint still needs bill+payment
verification. The claim status alone is not sufficient evidence.

When a claim has two bills and one is paid+cleared while the other is
scheduled, the claim is still paid -- the paid+cleared path confirms the
obligation was satisfied.

### Payable classification

A claim is payable when claim.status is "approved", at least one non-void
bill links to the claim, and no bill-payment pair satisfies the paid
classification. The AP open balance is the sum of (bill.amount minus sum of
cleared payment amounts for that bill) across all non-void bills.

### Blocked / CRM-required classification

A claim is blocked when any of these hold:

- claim.status is not "approved" (rejected, needs_receipt, submitted)
- The claim has no AP bill linked at all
- The only linked bills are void
- receipt_status is "partial" AND policy_flags includes "over_limit" or
  "late_receipt"
- The bill amount diverges substantially from the claim amount AND no
  matching paid/cleared alternative bill exists

## Stale snapshot correction logic

Compare the snapshot CSV row against current ERP data:

| Snapshot situation | Correction type |
|---|---|
| Current data matches snapshot (same bill, amount, status) | current_snapshot_ok |
| Bill is scheduled/approved with pending payment; snapshot shows no payment | mark_in_flight_payment |
| A different bill is the correct paid match | replace_with_matched_paid_bill |
| Bill amount differs from claim, or vendor does not match | exclude_amount_or_vendor_mismatch |
| Snapshot bill is now void in current ERP | ignore_void_bill |
| Claim is not approved in current ERP | block_unapproved_claim |

## Close log flagging

Scan close logs for entries where:

- period matches the batch context period or a recent adjacent period
- area is relevant (AP, Expense, Prepaids, Treasury)
- message contains trigger phrases: "export refresh", "journal entry",
  "support uploaded", "manual journal entry posted"

Only flag close logs whose content materially affects the batch.

## Vendor compliance decision logic

### Decision matrix

| Factor | Release/Approve | Hold/Awaiting_Info | Escalate |
|---|---|---|---|
| Bank account | verified | name_mismatch | closed |
| License vs review date | not expired | -- | expired + other flags |
| PEP | none | possible_pep (alone) | confirmed_pep |
| Sanctions | clear | not_run (alone) | confirmed_match |
| Shell company | false | -- | true |
| Missing docs | none or website only | -- | license or beneficial_owner_id |
| Tax ID | valid numeric | -- | non-numeric (e.g. TIN12X899) |
| Risk score | < 70 | >= 70, PEP/sanctions clear | >= 70 + PEP/sanctions flags |

Default to the highest severity flag present.

### Hard-stop flags mapping

| Compliance finding | Hard-stop flag enum |
|---|---|
| bank_account_status: "closed" | bank_closed |
| bank_account_status: "name_mismatch" | bank_name_mismatch |
| pep_status: "confirmed_pep" | confirmed_pep |
| license_expiry < review_date | expired_license |
| "license" or "beneficial_owner_id" in missing_fields | missing_required_documents |
| sanctions_check_status: "confirmed_match" | sanctions_confirmed |
| sanctions_check_status: "not_run" or pep_status: "not_run" | screening_not_run |
| shell_company_suspected: true | shell_company_suspected |
| vendor status inactive or review_status escalated | vendor_on_hold |

Sort flags alphabetically. Do not include flags not in the template's
allowed enum values.

### UBO counting

Count unique beneficial owner names where ownership_pct >= 25 (the
standard reporting threshold). Individuals appearing multiple times in the
ubo_list count as one unique name.

### Tax ID validation

A valid tax ID matches "TIN" followed by exactly six digits (9 chars total).
Tax IDs like "TIN12X899" (with embedded letters) are invalid.

## Prepaid amortization calculation

For each invoice in the close period:

```
service_start_month = extract YYYY-MM from service_start
close_period_month  = the close period (e.g. "2025-03")
months_elapsed      = (close_year - start_year)*12 + (close_month - start_month) + 1

cumulative_amortization = monthly_amortization * months_elapsed
ending_balance          = original_amount - cumulative_amortization
                           (clamp to 0.00 if negative)
```

### Exception flag triggers

Set exception_flag = true when any of:

- ending_balance == 0.00 AND service_end month == close period month
- data_quality_flags includes "missing_contract_dates"
- data_quality_flags includes "rounded_amount"
- service_start month == close period month (first amortization period)

### Account-level rollup

For each account, sum invoice-level fields, then:

```
variance_amount = schedule_ending_balance - gl_ending_balance
variance_flag   = abs(variance_amount) > variance_threshold_abs (or > 0)
account_status  = reconciled | variance_review | requires_reconciliation
```

## Account-change release decisions

Post-account-change decisions use the same compliance evaluation as
onboarding, with these additional cross-checks:

1. Compare the ticket's requested_bank_last4 against the vendor's
   bank_account_last4. A mismatch adds risk.
2. If compliance bank_account_status is name_mismatch, add to
   bank_mismatch_ids.
3. Tax ID validation uses the same digit-only rule.
4. License expiry is checked against the as_of_date in the prompt.
5. review_queue_ids includes every business that is not a clean release.
6. risk_score_override_flags includes businesses with risk_score >= 70
   regardless of decision outcome.
