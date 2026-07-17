---
name: erp-finance-control-review
description: Use this skill for task_group_005-style ERP finance control work: reimbursement-to-AP close batches, stale AP reimbursement exports, vendor onboarding or account-change release reviews, and prepaid close reconciliations that require reading local scope/template payloads and current shared JSON API records. Trigger whenever the user asks for finance-risk release decisions, AP payment posture, claim close status, prepaid schedule versus GL variance, compliance hard stops, or JSON answers against the task_group_005 ERP environment.
---

# ERP Finance Control Review

Use this skill to turn scoped local payloads plus current ERP API evidence into a strict JSON answer. The recurring trap in these tasks is trusting a local snapshot or source status too much. Treat local files as scope, stale context, or schema, and treat the shared API as the system of record.

## Start With Scope And Schema

1. Read the prompt, every local payload under the task input, and the answer template before fetching API data.
2. Identify the requested population exactly: claim IDs, business IDs, prepaid invoice IDs, accounts, period, entity, review date, and any variance threshold.
3. Copy the response shape from the answer template. Respect required keys, allowed enum values, precision, and ordering notes.
4. Use the shared API described in `environment_access.md` or the runner-provided base URL. Prefer `/api/...` endpoints when both legacy and `/api` paths exist.
5. Do not read local environment source or hidden data directories. Local CSV/JSON files in the task input are allowed only as task inputs.

Useful API habits:

- Check `/health` or `/api/health` and `/endpoints` if the base URL or path set is uncertain.
- Object list endpoints use exact-match query parameters by field name, plus `limit` and `offset`.
- For each scoped ID, fetch the record directly rather than relying on broad samples.
- Keep a small evidence table while working: ID, source records fetched, blocking facts, numeric amounts, and final classification.

## Reimbursement And AP Close

Use this flow for claim close, AP reimbursement batches, and stale AP export reviews.

Fetch current evidence:

- Claim: `GET /api/claims/{claim_id}`
- AP bills: `GET /api/ap/bills?claim_id=...`
- Payments for each bill: `GET /api/ap/payments?bill_id=...`
- Close logs when requested: `GET /api/close/logs` with filters such as `status=open`, `status=ready_for_review`, `period=...`, `area=...`, or `related_account=...`

Classify claim and AP evidence with these rules:

- A valid reimbursement bill must match the scoped claim ID, amount, currency, and vendor evidence. A bill with the right `claim_id` but wrong amount or wrong vendor is stale or mislinked evidence.
- Treat `void` bills as unusable. Ignore stale AP snapshot rows when current API bills contradict them.
- A claim is settled only when a matching AP bill is `paid` and cleared payments for that bill support the claim amount. Scheduled or processing payments are not settled.
- Valid open payables are matching, non-void, unpaid AP reimbursement bills for approved claims. Open balance is the valid bill amount minus cleared payments only.
- Keep reimbursement case problems separate from AP/payment evidence problems. Case cleanup includes unapproved claims, missing/partial support when the task treats support as gating, missing vendor or AP-link remediation, and no valid reimbursement bill. AP/payment evidence problems include amount/vendor mismatches, void or stale bills, and payments that are scheduled or processing rather than cleared.
- Paid, payable, blocked, eligible, and not-ready ID lists should be sorted ascending by claim ID unless the template says otherwise.
- For batch status, use the template's precedence. Commonly: any blocked/not-ready item makes the batch `blocked`; otherwise valid open payables make it open or refresh-needed; otherwise it is ready/closed.

When a stale AP snapshot is supplied:

- Compare each snapshot row to current claim, bill, and payment API records. Do not use the snapshot as the final truth.
- Map corrections from current evidence:
  - `current_snapshot_ok`: current API evidence still supports the snapshot posture.
  - `mark_in_flight_payment`: the bill is valid but payment is scheduled or processing, so it is not cleared.
  - `replace_with_matched_paid_bill`: the snapshot points at a stale row but another current bill/payment pair correctly settles the claim.
  - `exclude_amount_or_vendor_mismatch`: the AP row does not match the reimbursement claim amount or vendor evidence.
  - `ignore_void_bill`: the AP row is voided in the current API.
  - `block_unapproved_claim`: the claim itself is not approved or lacks required owner cleanup.
- For `close_log_required`, include unresolved close-log IDs only when the prompt asks for them and the log content/status is relevant to the stale export or close issue. Sort log IDs ascending.

## Vendor Compliance Release

Use this flow for vendor onboarding, finance-risk release calls, and payment release after account-change events.

Fetch current evidence for every scoped business ID:

- `GET /api/compliance/profile/{business_id}`
- `GET /api/compliance/ownership/{business_id}`
- `GET /api/compliance/registry/{business_id}`
- `GET /api/compliance/screening/{business_id}`
- `GET /api/compliance/bank/{business_id}`
- `GET /api/compliance/risk/{business_id}`
- `GET /api/vendors?vendor_id=...` using the profile's `vendor_id`

Do not copy `review_status` directly into the answer. Synthesize release control from the full evidence set.

Common hard-stop and flag mapping:

- `bank_closed`: bank account status is `closed`.
- `bank_name_mismatch`: bank account status is `name_mismatch`.
- `vendor_on_hold`: vendor status is `on_hold`.
- `expired_license`: registry `license_expiry` is before the review/as-of date.
- `missing_required_documents`: profile `missing_fields` is non-empty or required profile data is absent.
- `screening_not_run`: PEP or sanctions screening is `not_run`.
- `confirmed_pep`: PEP status is `confirmed_pep`.
- `sanctions_confirmed`: sanctions status is a confirmed match.
- `shell_company_suspected`: ownership says `shell_company_suspected` is true.
- Tax IDs are invalid when profile, registry, and vendor tax IDs disagree or the value is malformed for the task's expected `TIN...` pattern.
- Bank-last-four mismatches matter in account-change tasks: compare the requested last four in the local batch event to the current vendor bank last four and the compliance bank status.
- Risk score override flags usually use `risk_score >= 70` when the template defines that threshold.

Decision posture:

- Approve or release only when bank is verified, vendor is active, tax and license evidence are current, required documents are present, screening is clear, risk posture is acceptable, and account-change details match the current vendor record.
- Use `awaiting_information` or `hold` for remediable missing information, incomplete review, bank/account validation issues, or expired/missing documents when the template offers a non-escalation hold value.
- Use `escalate` for confirmed adverse screening, shell-company suspicion, vendor hold, high-risk override, unresolved bank closure/name mismatch when release would be unsafe, or any combination of hard stops that needs compliance owner action.
- For reportable UBO counts, count unique owner names with at least one listed `ownership_pct` at or above the reporting threshold, normally 25% unless the prompt states another threshold. Deduplicate repeated names.
- Sort per-business arrays and ID lists ascending by `business_id`; sort hard-stop flag lists alphabetically by enum value when the template says so.

## Prepaid Close Reconciliation

Use this flow for prepaid schedule versus GL checks.

Fetch current evidence:

- Scoped invoices only: `GET /api/prepaids/invoices?prepaid_invoice_id=...`
- GL balances: `GET /api/prepaids/gl-balances?account=...&period=YYYY-MM`

Calculation conventions:

- Limit the schedule to the invoice IDs and accounts in the scope payload. Preserve invoice result order when the template says "same order as scope."
- Use the invoice's `monthly_amortization` field for straight-line monthly amortization. Do not recompute a different monthly amount from original amount unless the record lacks the monthly field.
- Treat service months inclusively by month. If the close month overlaps the service period, March or current-period amortization is one monthly amortization amount; if not, it is zero.
- Cumulative amortization through the close period is monthly amortization times the count of service months through that period, capped by the service term and not beyond the original amount.
- Ending balance is `original_amount - cumulative_amortization_through_period`.
- Round currency outputs to two decimals. Be consistent about whether account totals sum rounded invoice outputs or unrounded intermediates; prefer final two-decimal invoice values when templates compare displayed totals.
- Account schedule ending balance is the sum of selected invoice ending balances for that account.
- Variance amount is `schedule_ending_balance - gl_ending_balance`.
- Use the scope's absolute variance threshold when provided. Set `variance_flag` when `abs(variance_amount)` exceeds that threshold.

Exception and status conventions:

- `default_missing_term_flag` is true for invoices with missing/default contract-date flags, absent service dates, or other default-term indicators.
- `exception_flag` is true for any invoice-level data quality issue that should be surfaced for close review, including missing terms, manual overrides, duplicate invoice numbers, rounded amounts when the template treats data-quality flags as exceptions, or missing schedule fields.
- `default_missing_term_invoice_ids` and `exception_invoice_ids` are sorted ascending by invoice ID unless a template says otherwise.
- `has_default_missing_term_flag` is true at account level when any selected invoice in that account has the invoice-level flag.
- Use `reconciled` only when the account has no material variance and no selected invoice exception requiring review. Use `variance_review` for a material variance without a stronger data-quality blocker. Use `requires_reconciliation` when missing GL data, default/missing terms, or other exception evidence means the account cannot be cleanly closed.

## JSON Output Checklist

Before finalizing:

- Return only one JSON object, with no narrative outside it.
- Include all required top-level keys and no extra keys when the template disallows them.
- Preserve any specified top-level order when practical.
- Use the exact enum strings from the template.
- Sort ID lists as requested: ascending by claim ID/business ID/invoice ID, or same order as the scope file when specified.
- Use cents only when the template asks for cents; otherwise use two-decimal USD numbers.
- Recount reviewed items from the requested scoped IDs, not from API totals.
- Parse the final JSON locally or mentally verify commas, booleans, strings, and numeric precision.
