---
name: finance-erp-reconciliation
description: Reusable patterns for reconciling finance operations (claims, AP bills, payments, vendor compliance, prepaid amortization) against the task_group_005 shared ERP API.
---

# ERP Finance Reconciliation Skill

Use the shared task_group_005 ERP API at `<TASK_ENV_BASE_URL>` for every
finance reconciliation task. Never rely on snapshot or local payload data as
the system of record; always pull current state from the API. Report currency
amounts in USD with two-decimal precision and sort claim-id, business-id, and
invoice-id lists in ascending order unless the task payload prescribes a
different ordering.

## Environment

The runner provides the API base URL. All endpoints support exact-match query
parameters by field name and `limit`/`offset` pagination. API paths are
available both with and without the `/api` prefix:

| Domain          | Endpoints (use /api/ prefix)                                      |
|-----------------|-------------------------------------------------------------------|
| Claims          | `/api/claims`                                                     |
| AP Bills        | `/api/ap/bills`                                                   |
| AP Payments     | `/api/ap/payments`                                                |
| AP Aging        | `/api/ap/aging`                                                   |
| Vendors         | `/api/vendors`                                                    |
| Compliance      | `/api/compliance/objects`                                         |
| Prepaid invoices| `/api/prepaids/invoices`                                          |
| GL Balances     | `/api/prepaids/gl-balances` (also `/gl/balances`)                 |
| Close Logs      | `/api/close/logs`                                                 |

## Common Data Shapes

### Claim records (`/api/claims`)

```json
{
  "claim_id": "string",
  "amount": "number (USD)",
  "status": "approved | paid | rejected | needs_receipt | ...",
  "approved_date": "YYYY-MM-DD | null",
  "vendor_id": "string | null",
  "category": "string",
  "department": "string",
  "policy_flags": ["list of strings"],
  "receipt_status": "attached | partial | missing",
  "notes": "string",
  "employee_name": "string",
  "currency": "USD"
}
```

Filter by: `claim_id`

### AP Bill records (`/api/ap/bills`)

```json
{
  "bill_id": "string",
  "claim_id": "string | null",
  "amount": "number (USD)",
  "status": "scheduled | approved | paid | void | ...",
  "vendor_id": "string",
  "account": "string (GL account)",
  "invoice_number": "string",
  "memo": "string"
}
```

Filter by: `bill_id`, `claim_id`

### AP Payment records (`/api/ap/payments`)

```json
{
  "payment_id": "string",
  "bill_id": "string",
  "amount": "number (USD)",
  "status": "cleared | processing | scheduled | ...",
  "method": "string",
  "vendor_id": "string",
  "payment_date": "YYYY-MM-DD"
}
```

Filter by: `bill_id`, `payment_id`

### Vendor records (`/api/vendors`)

```json
{
  "vendor_id": "string",
  "vendor_name": "string",
  "legal_name": "string",
  "status": "active | on_hold | ...",
  "tax_id": "string",
  "bank_account_last4": "string",
  "industry": "string",
  "payment_terms": "string"
}
```

Filter by: `vendor_id`

### Compliance objects (`/api/compliance/objects`)

```json
{
  "business_id": "string",
  "business_name": "string",
  "vendor_id": "string",
  "bank_account_status": "verified | name_mismatch | closed",
  "pep_status": "none | possible_pep | confirmed_pep | not_run",
  "sanctions_check_status": "clear | not_run | sanctions_confirmed",
  "license_expiry": "YYYY-MM-DD",
  "missing_fields": ["list of strings"],
  "shell_company_suspected": "boolean",
  "review_status": "string",
  "risk_score": "integer (0-100)",
  "ubo_list": [{"name": "string", "ownership_pct": "number"}],
  "tax_id": "string"
}
```

Filter by: `business_id`

### Prepaid invoices (`/api/prepaids/invoices`)

```json
{
  "prepaid_invoice_id": "string",
  "account": "string (GL account, e.g. 1250, 1251)",
  "original_amount": "number (USD)",
  "monthly_amortization": "number (USD)",
  "recognition_method": "straight_line",
  "service_start": "YYYY-MM-DD",
  "service_end": "YYYY-MM-DD",
  "data_quality_flags": ["list of strings"],
  "vendor_id": "string",
  "description": "string",
  "invoice_number": "string",
  "source_document": "string"
}
```

Filter by: `prepaid_invoice_id`

### GL Balances (`/api/prepaids/gl-balances`)

```json
{
  "account": "string",
  "account_name": "string",
  "period": "YYYY-MM",
  "ending_balance": "number (USD)",
  "entity": "string"
}
```

Filter by: `account`, `period`

### Close Logs (`/api/close/logs`)

```json
{
  "log_id": "string",
  "area": "AP | Expense | Prepaids | Compliance | Treasury",
  "period": "YYYY-MM",
  "status": "closed | open | ready_for_review",
  "message": "string",
  "owner": "string",
  "created_at": "ISO-8601"
}
```

## Task Pattern: Claims Batch Close Review

Used when a batch of expense claims must be classified as paid, payable, or
blocked for AP release. The input includes a list of claim IDs and an answer
template defining the output schema.

### Data Gathering

For each claim ID in the batch:
1. Fetch the claim from `/api/claims?claim_id=<id>`.
2. Fetch all AP bills for the claim from `/api/ap/bills?claim_id=<id>`.
3. For each bill, fetch payments from `/api/ap/payments?bill_id=<id>`.

### Classification Rules

**paid_claim_ids**: A claim is **paid** when ALL of the following hold:
- Claim `status` is `"paid"`.
- At least one bill linked to the claim has `status` `"paid"` and its `amount`
  matches a cleared payment for that bill.
- The cleared payment `amount` equals the bill `amount`.

Apply the strictest reading: if the claim amount differs from the matched paid
bill amount, treat the claim as blocked (amount mismatch) instead of paid. When
multiple bills exist for the same claim, prefer the bill whose amount is
closest to the claim amount and whose payment has actually cleared.

**payable_claim_ids**: A claim is **payable** when ALL of the following hold:
- Claim `status` is `"approved"`.
- Exactly one valid (non-void) AP bill exists for the claim, the bill `status`
  is not `"paid"` or `"void"`, and the bill `amount` matches the claim `amount`.
- Any associated payment has not cleared (status is `"processing"` or
  `"scheduled"`); this is acceptable but means the bill is still open.

**blocked_claim_ids**: A claim is **blocked** when ANY of the following hold:
- Claim `status` is not `"approved"` and not `"paid"` (e.g. `"needs_receipt"`,
  `"rejected"`, `null` approved_date).
- No AP bill exists for the claim.
- The only bill linked to the claim is `"void"`.
- The bill `amount` differs from the claim `amount` by more than a trivial
  rounding tolerance (amount mismatch = blocked).
- The bill `account` is inappropriate for a reimbursement (e.g. raw materials
  or fixed-asset accounts) combined with a large amount mismatch.
- The claim has unresolved policy flags (`over_limit`, `late_receipt`) and
  the receipt status is `"partial"` or `"missing"` with no matching AP bill.
- The claim `notes` indicate legacy import or cleanup flags.

**crm_required_claim_ids**: All blocked claims that require expense-case owner
cleanup or AP-link remediation. In practice this equals the full
`blocked_claim_ids` list unless specific blocked claims are purely AP-side
issues resolvable without owner action.

**ap_open_balance_total**: Sum of the bill `amount` for each **payable** claim.
Do not include blocked claims (their AP links are invalid) or paid claims
(their bills are settled).

**batch_status**:
- `"blocked"` when any claim in the batch is blocked.
- `"open_payables"` when no claims are blocked but at least one payable claim
  remains.
- `"ready_to_close"` when all claims are paid (no payable or blocked claims).

**reviewed_claim_count**: Total number of claim IDs in the requested batch.

## Task Pattern: Vendor Compliance Review

Used for vendor onboarding or account-change release decisions. Given a set of
business IDs, evaluate each against compliance and vendor API data and assign
a decision: `approve`/`release`, `awaiting_information`/`hold`, or `escalate`.

### Data Gathering

For each business ID:
1. Fetch from `/api/compliance/objects?business_id=<id>`.
2. Fetch the linked vendor from `/api/vendors?vendor_id=<vendor_id>`.

### Hard-Stop Flag Derivation

Evaluate every business against these flags. A flag applies when the condition
is true; use an empty list when none apply. Sort flags alphabetically.

| Flag                        | Condition                                                        |
|-----------------------------|------------------------------------------------------------------|
| `bank_closed`               | `bank_account_status` == `"closed"`                              |
| `bank_name_mismatch`        | `bank_account_status` == `"name_mismatch"`                       |
| `confirmed_pep`             | `pep_status` == `"confirmed_pep"`                                |
| `expired_license`           | `license_expiry` < as_of_date AND `"license"` NOT in `missing_fields` |
| `missing_required_documents`| `missing_fields` is non-empty                                    |
| `sanctions_confirmed`       | `sanctions_check_status` == `"sanctions_confirmed"`              |
| `screening_not_run`         | `sanctions_check_status` == `"not_run"` OR `pep_status` == `"not_run"` |
| `shell_company_suspected`   | `shell_company_suspected` == `true`                              |
| `vendor_on_hold`            | vendor `status` == `"on_hold"`                                   |

Suppress `expired_license` when `"license"` appears in `missing_fields`
because the expiry date is unreliable when the license document itself is
missing.

### UBO Reporting

Count unique beneficial-owner **names** whose `ownership_pct` is **>= 25%**.
If the same name appears multiple times, count the name once. If no UBO meets
the threshold, report 0.

### Tax ID Validation

A tax ID is **invalid** when:
- The compliance `tax_id` does not match the vendor `tax_id`.
- The tax ID contains non-numeric characters in positions where only digits
  are expected (e.g. `TIN12X899`).
- The tax ID is a known placeholder (e.g. `TIN999999`).

### Decision Assignment

The decision framework depends on the task domain:

**Onboarding / new vendor access** (e.g. vendor onboarding release calls):

- `escalate`: ANY of `confirmed_pep`, `sanctions_confirmed`, `vendor_on_hold`,
  `shell_company_suspected`, or `bank_closed`.
- `approve`: No hard-stop flags at all.
- `awaiting_information`: Has hard-stop flags but none of the escalation
  triggers listed above.

**Account-change / payment release** (e.g. after bank account changes):

- `escalate`: ANY of `confirmed_pep`, `sanctions_confirmed`, `vendor_on_hold`,
  `shell_company_suspected`, or invalid tax ID.
- `release`: No hard-stop flags AND no invalid tax ID AND risk_score < 70.
- `hold`: Has hard-stop flags but none of the escalation triggers, OR
  risk_score >= 70 even without other flags.

Note: in account-change contexts, `bank_closed` and `bank_name_mismatch` are
expected (the change ticket exists to resolve them) so they do NOT escalate
on their own. They produce a `hold` decision instead.

### Derived Lists

- `follow_up_business_ids` / `review_queue_ids`: All business IDs whose
  decision is not `approve`/`release`.
- `risk_score_override_flags`: Business IDs with `risk_score` >= 70.
- `bank_mismatch_ids`: Business IDs with `bank_account_status` ==
  `"name_mismatch"`.
- `invalid_tax_ids`: Business IDs with an invalid tax ID.
- `expired_license_ids`: Business IDs where `license_expiry` < as_of_date.
- `overall_release_ready`: `true` only when every business decision is
  `approve`/`release`.

Sort all ID lists ascending by business ID.

## Task Pattern: Prepaid Expense Close Reconciliation

Given a list of prepaid invoice IDs, an entity, a close period, GL accounts,
and a variance threshold, reconcile scheduled amortization against GL balances.

### Prepaid Amortization Math

Straight-line monthly amortization is used for all invoices. The invoice
record provides `monthly_amortization` directly. For a close period `YYYY-MM`:

- **months_elapsed**: Count of calendar months from `service_start` through
  the close period, inclusive. A service starting 2025-01-01 has 3 elapsed
  months by March 2025 (Jan, Feb, Mar). A service starting 2025-03-15 has 1
  elapsed month (March only). Do not apply partial-month proration beyond what
  the API already encodes in `monthly_amortization`.

- **period_amortization** = `monthly_amortization` (always one full month
  for the close period itself unless the invoice starts after the close period,
  in which case it is 0).

- **cumulative_amortization** = `months_elapsed` × `monthly_amortization`.

- **ending_balance** = `original_amount` - `cumulative_amortization`.
  Round to two decimals; small rounding residues (e.g. 0.01) are expected and
  acceptable.

### Exception and Default/Missing-Term Flags

- **default_missing_term_flag**: `true` when `data_quality_flags` contains
  `"missing_contract_dates"`.
- **exception_flag**: `true` when `data_quality_flags` is non-empty OR the
  `ending_balance` is anomalous for a non-natural close (e.g. exactly 0.00
  mid-contract, negative balance, or balance exceeding original amount).

### Account Rollup

For each GL account, aggregate across its selected invoices:

| Field                              | Computation                                      |
|------------------------------------|--------------------------------------------------|
| `selected_invoice_count`           | Count of invoices in the account                 |
| `original_amount_total`            | Sum of `original_amount`                         |
| `march_amortization_total` (etc.)  | Sum of period amortizations                      |
| `cumulative_amortization_through_{period}` | Sum of cumulative amortizations          |
| `schedule_ending_balance`          | `original_amount_total` - `cumulative` total     |
| `gl_ending_balance`                | From `/api/prepaids/gl-balances` for that account and period |
| `variance_amount`                  | `schedule_ending_balance` - `gl_ending_balance`  |
| `variance_flag`                    | `true` when abs(variance) > variance_threshold   |
| `has_default_missing_term_flag`    | `true` when any invoice in account has it         |

**account_status**:
- `"reconciled"`: `variance_flag` is `false`.
- `"variance_review"`: `variance_flag` is `true` but `has_default_missing_term_flag`
  is `true` (missing terms may explain the variance).
- `"requires_reconciliation"`: `variance_flag` is `true` and
  `has_default_missing_term_flag` is `false`.

### Output Lists

- `default_missing_term_invoice_ids`: All invoice IDs with
  `default_missing_term_flag` == `true`, sorted ascending.
- `exception_invoice_ids`: All invoice IDs with `exception_flag` == `true`,
  sorted ascending.
- `selected_invoice_ids`: The complete scope list, in the order provided by
  the task payload.
- `invoice_results`: One object per invoice, in payload order, with keys:
  `prepaid_invoice_id`, `account`, `period_amortization`,
  `cumulative_amortization_through_{period}`, `ending_balance`,
  `default_missing_term_flag`, `exception_flag`. All amounts to two decimals.

## Task Pattern: Stale AP Export Reconciliation

Given a stale AP snapshot CSV and a list of claim IDs, reconcile the snapshot
against current API data and determine which claims can stay in the AP batch.

### Data Gathering

For each claim ID:
1. Fetch the claim from `/api/claims`.
2. Fetch all bills for the claim from `/api/ap/bills`.
3. For each bill, fetch all payments from `/api/ap/payments`.
4. Compare current state with the stale snapshot row.

### Classification

**eligible_claim_ids**: Claims where current API evidence shows a valid open
payable or a correctly settled paid bill. Specifically:
- Claim is `"approved"` or `"paid"`.
- A matching non-void bill exists with `amount` matching the claim `amount`
  (or a paid bill with matching cleared payment).
- No amount mismatch, no void bill, and no unapproved claim status.

**not_ready_claim_ids**: Claims that should not remain in the batch. Includes:
- Claim `status` is not `"approved"` or `"paid"`.
- Bill is `"void"`.
- Bill `amount` does not match claim `amount`.
- Claim has no valid AP bill.

**ap_balance_by_claim**: For each claim, the open AP balance. Compute as:
- If claim is eligible and has an open (non-paid, non-void) bill: the bill `amount`.
- If claim has a paid bill with cleared payment: 0.00.
- If claim is not ready (void bill, amount mismatch, unapproved): 0.00.

### Stale Snapshot Corrections

Assign one correction per claim by comparing the snapshot row to current API
state:

| Correction                        | When to apply                                                  |
|-----------------------------------|----------------------------------------------------------------|
| `current_snapshot_ok`             | Snapshot matches current API state exactly                     |
| `mark_in_flight_payment`          | Snapshot shows no payment but API shows payment in `processing`|
| `replace_with_matched_paid_bill`  | Snapshot bill differs from the bill that is actually paid/cleared |
| `exclude_amount_or_vendor_mismatch`| Bill amount differs substantially from claim amount           |
| `ignore_void_bill`                | Snapshot bill is now `void` in the API                         |
| `block_unapproved_claim`          | Claim `status` is not `"approved"` or `"paid"` in API         |

### Close Logs

Check `/api/close/logs` for a log entry with `area` `"AP"` or `"Expense"`,
`period` matching the relevant close period, and `message` indicating a
manual journal entry, AP export refresh, or variance review. When such a log
exists, set `close_log_required.required` to `true` and include the `log_id`
in `close_log_required.ids`. When no relevant log exists, set `required` to
`false` and `ids` to `[]`.

### Batch Status

- `"ready_to_send"`: All claims eligible and all open balances are zero.
- `"needs_ap_refresh"`: At least one eligible claim has a positive open balance
  OR at least one not-ready claim exists.
- `"blocked"`: All claims are not-ready (no eligible claims).

## General Rules

1. **Amount matching**: When comparing claim amounts to bill amounts, treat
   any difference beyond 0.01 as a mismatch. Do not attempt to rationalize
   mismatches with exchange rates or partial payments unless the task payload
   explicitly directs it.

2. **Multiple bills**: When a claim has more than one bill, prefer the bill
   whose amount matches the claim amount and whose payment has cleared. Treat
   other bills as stale, legacy, or duplicate entries.

3. **Payment status**: A payment in `"processing"` confirms the bill is valid
   but does not settle it. A payment in `"cleared"` means the bill is settled.

4. **Void bills**: A `"void"` bill invalidates the AP link for that claim
   regardless of the claim's own status.

5. **Currency**: All amounts are in USD. Return amounts with exactly two
   decimal places.

6. **Sorting**: Sort all string ID lists in ascending natural order. Preserve
   payload ordering for invoice/payload-scope lists that the template
   explicitly ties to input ordering.

7. **Close logs**: When a task references close logs, always query the full
   set (use a high `limit` to avoid missing entries) and filter by the
   relevant `area`, `period`, and message content.

8. **UBO counting**: Use unique names at >= 25% ownership. Do not count the
   same name twice even if it appears in multiple UBO entries.
