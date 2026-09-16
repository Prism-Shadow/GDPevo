# Claims-AP Close Review Patterns

## Workflow

1. Fetch /claims and /api/claims/{id} for every candidate claim ID.
2. Fetch /bills or /api/ap/bills to get all AP bills.
3. Fetch /payments or /api/ap/payments to get all payments.
4. If close-log context is needed, fetch /close/logs or /api/close/logs.

## Cross-Reference Logic

### Matching claims to bills

For each candidate claim, find the bill record where bill.claim_id equals
claim.claim_id. A claim may have zero, one, or multiple bills. When
multiple bills exist, prefer the most recent non-void bill. Treat bills
with status "void" as if no bill exists for that claim.

### Matching bills to payments

For each matched bill, find payment records where payment.bill_id equals
bill.bill_id or payment.claim_id equals claim.claim_id. A bill may have
zero, one, or multiple payments. Use the latest payment for
cleared/in_flight determination.

## Classification Rules

### paid_claim_ids

A claim is **paid** when ALL of:
- Claim status is `approved` or `paid`.
- A non-void bill exists with status `paid` and bill amount matches claim amount.
- A payment exists with status `cleared` and payment amount matches claim/bill amount.

### payable_claim_ids

A claim is **payable** when ALL of:
- Claim status is `approved`.
- A non-void bill exists with status `approved` or `scheduled`.
- No clearing payment exists for that bill.

### blocked_claim_ids

A claim is **blocked** when ANY of:
- No non-void bill exists for the claim.
- Claim status is not `approved` (e.g., `draft`, `void`).
- Bill exists but bill amount does not match claim amount.
- Bill status is `void` (functionally no bill).
- Bill is `paid` but payment is missing or not cleared.

### crm_required_claim_ids (subset of blocked)

A blocked claim requires CRM/owner cleanup when:
- No non-void bill exists (missing AP link).
- Bill is void.
- Claim status is not `approved` (expense case not ready).
- Bill amount mismatches claim amount.

Exclude from crm_required when the only issue is a payment that has not
cleared yet on an otherwise valid bill.

## AP Open Balance

Sum the bill amounts for all **payable** claims only. Use the matched bill
amount, not the claim amount.

## Batch Status

- `blocked`: any claim in the batch is blocked.
- `open_payables`: no blocked claims exist, but at least one payable claim remains.
- `ready_to_close`: no blocked claims and no payable claims (all are paid).

## Stale Snapshot Correction (layered workflow)

When a stale AP snapshot CSV is supplied alongside the claims review,
compare each snapshot row against current API records. The correction
enum values:

- `current_snapshot_ok`: snapshot matches current state; no correction needed.
- `mark_in_flight_payment`: snapshot says no payment, but current API shows
  a payment in `in_flight` status.
- `replace_with_matched_paid_bill`: snapshot has a stale bill ID/status;
  replace with the matched paid bill from current API.
- `exclude_amount_or_vendor_mismatch`: snapshot amount or vendor does not
  match current API records.
- `ignore_void_bill`: snapshot references a bill that is now void.
- `block_unapproved_claim`: snapshot shows approved but current claim
  status is not approved.

### Close Log Check

Fetch close logs and check if any log references the candidate claim IDs.
If so, set close_log_required.required: true and collect the matching
close log IDs in close_log_required.ids sorted ascending.

### Stale Batch Status

- `ready_to_send`: all candidate claims eligible, no corrections needed.
- `needs_ap_refresh`: eligible claims exist but some corrections flagged.
- `blocked`: at least one claim is not ready.
