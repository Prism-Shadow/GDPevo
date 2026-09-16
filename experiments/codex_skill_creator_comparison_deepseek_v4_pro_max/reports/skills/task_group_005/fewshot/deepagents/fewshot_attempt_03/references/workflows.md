# Finance Close Review Workflows
 
 This document captures the reusable patterns for the five task types supported by this skill. Each workflow describes the data fetches, decision logic, and answer formatting rules. Follow these workflows exactly — the evaluator checks conformance to the expected output shape.
 
 ## Workflow A: Reimbursement-to-AP Close Batch
 
 ### Input
 - A list of claim IDs to review.
 - An answer template defining the output schema.
 
 ### Data Fetching
 
 1. Fetch all claims in the batch: `GET /api/claims?claim_id=...` for each ID, or bulk-fetch all claims and filter locally.
 2. Fetch AP bills linked to each claim: `GET /api/ap/bills?claim_id=...` for each claim ID.
 3. Fetch all AP payments: `GET /api/ap/payments?limit=200`, or filter by relevant bill IDs.
 4. Optionally fetch AP aging for each bill to confirm open balances: `GET /api/ap/aging?bill_id=...`.
 
 ### Classification Rules
 
 For each claim in the batch:
 
 **Paid claim** — The claim has a matching paid AP bill with a matching cleared payment for the claim amount. Look up the claim's AP bill(s); if a bill's `status` is `paid` and a payment with `status` = `cleared` exists for that bill with the same amount, the claim is paid. Place in `paid_claim_ids`.
 
 **Payable claim** — The claim's status is `approved` (or `paid` with a remaining bill), it has a valid AP bill (status `approved` or `scheduled`, not `void`/`draft`), and no hard block exists. Place in `payable_claim_ids`.
 
 **Blocked claim** — Any of:
 - Claim status is not `approved` (e.g., `needs_receipt`, `submitted`, `rejected`).
 - Claim has a void AP bill.
 - Claim's AP bill amount does not match the claim amount (mismatch).
 - Claim has no valid AP bill at all.
 - Claim has bill + payment issues that prevent AP release.
 
 Place in `blocked_claim_ids`.
 
 **CRM-required claims** — A subset of blocked claims where the issue is expense-case owner cleanup or AP-link remediation (e.g., missing receipts, submitted claims, void bills). Place in `crm_required_claim_ids`.
 
 ### Aggregation
 
 - `ap_open_balance_total`: Sum of `balance` (from aging) or `amount - paid_amount` for all payable claims' active AP bills. Two decimal places, USD.
 - `batch_status`:
   - `blocked` — any claim is blocked.
   - `open_payables` — no blocked claims and at least one payable claim with a positive open balance.
   - `ready_to_close` — no blocked claims and no positive open balances (all paid).
 - `reviewed_claim_count`: Total number of claim IDs in the batch.
 
 ### Sort Order
 All claim ID lists ascending by claim ID.
 
 ---
 
 ## Workflow B: Vendor Onboarding Finance-Risk Release
 
 ### Input
 - A batch payload with `business_ids` and `as_of_date`.
 - An answer template.
 
 ### Data Fetching
 
 For each `business_id` in the batch:
 
 1. Fetch aggregate compliance: `GET /api/compliance/objects?business_id=...`
 2. Fetch ownership detail: `GET /api/compliance/ownership/{business_id}`
 3. Fetch registry: `GET /api/compliance/registry/{business_id}`
 4. Fetch screening: `GET /api/compliance/screening/{business_id}`
 5. Fetch bank: `GET /api/compliance/bank/{business_id}`
 6. Fetch vendor: `GET /api/vendors?vendor_id=...` (find vendor_id from compliance object)
 
 ### Hard-Stop Flag Detection
 
 Check each business and collect flags from this list:
 - `sanctions_confirmed` — `sanctions_check_status` is `confirmed`
 - `confirmed_pep` — `pep_status` is `confirmed_pep`
 - `bank_closed` — `bank_account_status` is `closed`
 - `bank_name_mismatch` — `bank_account_status` is `name_mismatch`
 - `expired_license` — `license_expiry` date is before `as_of_date`
 - `screening_not_run` — `sanctions_check_status` is `not_run`
 - `missing_required_documents` — `missing_fields` is non-empty
 - `shell_company_suspected` — `shell_company_suspected` is true
 - `vendor_on_hold` — vendor `status` is `on_hold` or `inactive`
 
 Sort flags alphabetically per business. Use empty list when none apply.
 
 ### Decision Logic
 
 - `approve` — Zero hard-stop flags.
 - `awaiting_information` — Only flags that can be resolved by providing information: `screening_not_run`, `missing_required_documents`. No escalation-required flags.
 - `escalate` — Any of: `confirmed_pep`, `sanctions_confirmed`, `bank_closed`, `bank_name_mismatch`, `expired_license`, `shell_company_suspected`, `vendor_on_hold`.
 
 ### UBO Counting
 
 Collect all `ubo_list` entries from both aggregate compliance and ownership detail. Count unique names where `ownership_pct >= 25`. A name appearing multiple times at different ownership percentages counts once.
 
 ### Follow-Up and Overall
 
 - `follow_up_business_ids`: All business IDs not marked `approve`. Ascending.
 - `overall_release_ready`: `true` only if every business is `approve`.
 
 ---
 
 ## Workflow C: Prepaid Close Check
 
 ### Input
 - A close scope payload with `entity`, `close_period`, `accounts`, `selected_prepaid_invoice_ids`, and `variance_threshold_abs`.
 - An answer template.
 
 ### Data Fetching
 
 1. Fetch all prepaid invoices in scope: `GET /api/prepaids/invoices?prepaid_invoice_id=...` for each ID.
 2. Fetch GL balances: `GET /api/prepaids/gl-balances?account=...&period=...&entity=...` for each account.
 
 ### Invoice-Level Calculations
 
 For each prepaid invoice, with target month from `close_period`:
 
 - `march_amortization` = `monthly_amortization` (the monthly amount as-is from the invoice record; if service starts mid-month, the invoice record's `monthly_amortization` already reflects the correct period amount).
 - `cumulative_amortization_through_march` = Full months from `service_start` through the end of the target month times `monthly_amortization`. Count: number of complete calendar months where the service is active through the end of the target month.
 - `ending_balance` = `original_amount - cumulative_amortization_through_march`. Clamp to zero when negative.
 
 **Default/missing term flag:** `true` if `data_quality_flags` contains `missing_contract_dates`.
 
 **Exception flag:** `true` when any of:
 - `data_quality_flags` is non-empty (any flag at all).
 - `ending_balance` is effectively zero or negative.
 
 ### Account-Level Rollup
 
 For each account, aggregate across its invoices:
 - `selected_invoice_count`: Count of invoices in this account.
 - `original_amount_total`: Sum of `original_amount`.
 - `march_amortization_total`: Sum of `march_amortization`.
 - `cumulative_amortization_through_march`: Sum.
 - `schedule_ending_balance`: Sum of `ending_balance`.
 - `gl_ending_balance`: From GL balances for that account and period.
 
 Then:
 - `variance_amount` = `schedule_ending_balance - gl_ending_balance`.
 - `variance_flag`: `true` if `abs(variance_amount) >= variance_threshold_abs`.
 - `has_default_missing_term_flag`: `true` if any invoice in that account has the flag.
 - `account_status`:
   - `reconciled` — `variance_flag` is false.
   - `variance_review` — `variance_flag` is true but variance is within a reasonable band.
   - `requires_reconciliation` — `variance_flag` is true with a material variance.
 
 ### Invoice Ordering
 All invoice-level output lists follow the same order as the input `selected_prepaid_invoice_ids` list. Exception and default-term ID lists are ascending by invoice ID.
 
 ---
 
 ## Workflow D: Stale AP Snapshot Reconciliation
 
 ### Input
 - A list of candidate claim IDs.
 - A stale AP snapshot CSV (context only, not system of record).
 - An answer template.
 
 ### Data Fetching
 
 1. Fetch current claim records for all candidate IDs.
 2. Fetch current AP bills linked to those claims.
 3. Fetch current payments for relevant bill IDs.
 4. Fetch close logs: `GET /api/close/logs?area=Expense` or `area=AP`, filtered by recent periods.
 
 ### Per-Claim Reconciliation
 
 For each candidate claim ID:
 
 1. **Get current claim state** — status, amount, vendor.
 2. **Get current AP bill state** — find the active bill (not void). Compare bill amount to claim amount. Check bill status.
 3. **Get current payment state** — find payments against the active bill. Check for cleared payments.
 4. **Compare to stale snapshot** — determine the correction type.
 
 ### Correction Types
 
 - `current_snapshot_ok` — Current data matches the snapshot (same bill, correct status).
 - `mark_in_flight_payment` — Bill is scheduled/approved with a payment in processing status; snapshot showed no payment.
 - `replace_with_matched_paid_bill` — Snapshot referenced a stale bill ID; the claim now has a different paid bill with a cleared payment.
 - `exclude_amount_or_vendor_mismatch` — Bill amount does not match claim amount, or vendor differs.
 - `ignore_void_bill` — The bill in the snapshot is now void.
 - `block_unapproved_claim` — Claim status is not `approved` (e.g., `needs_receipt`, `submitted`).
 
 ### Eligibility
 
 - `eligible_claim_ids`: Claims where the current state supports staying in the batch — active approved/scheduled bill, no mismatches, claim is approved.
 - `not_ready_claim_ids`: Claims with void bills, unapproved claim status, amount mismatches, or already fully paid.
 
 ### AP Balance
 
 For each candidate claim, `ap_balance_by_claim` is the current open AP balance (from aging or bill minus cleared payments). Set to 0.00 when no active payable bill exists.
 
 ### Close Log Check
 
 If any snapshot row needs correction or a void/paid bill supersedes the stale record, check whether a close log entry exists. Set `close_log_required.required` to `true` and include the relevant log IDs.
 
 ### Batch Status
 
 - `ready_to_send` — All claims eligible, no stale corrections needed.
 - `needs_ap_refresh` — At least one correction needed but no hard blocks.
 - `blocked` — At least one claim is blocked by unapproved status or other hard stop.
 
 ---
 
 ## Workflow E: Account-Change Payment Release
 
 ### Input
 - A batch payload with `target_business_ids`, `account_change_events`, `review_date` (`as_of_date`).
 - An answer template.
 
 ### Data Fetching
 
 For each business ID:
 
 1. Fetch aggregate compliance: `GET /api/compliance/objects?business_id=...`
 2. Fetch ownership: `GET /api/compliance/ownership/{business_id}`
 3. Fetch registry: `GET /api/compliance/registry/{business_id}`
 4. Fetch screening: `GET /api/compliance/screening/{business_id}`
 5. Fetch bank: `GET /api/compliance/bank/{business_id}`
 6. Fetch vendor: `GET /api/vendors?vendor_id=...`
 
 ### Decision Logic
 
 Review each business against its account-change context:
 
 - `release` — All compliance checks are clear (bank verified, license current, tax ID valid, sanctions clear, no PEP, no shell company flag, vendor active, screening run and clear). Risk score is acceptable and no override is needed.
 - `hold` — Some flags require attention but none are escalation-grade. Examples: bank not yet verified, screening not run, missing documents, license not yet expired but approaching. Risk score elevated but under threshold.
 - `escalate` — Hard stops: confirmed PEP, sanctions confirmed, bank closed, bank name mismatch, expired license, shell company suspected, vendor on hold, invalid tax ID.
 
 ### List Flags
 
 - `bank_mismatch_ids` — Business IDs where `bank_account_status` is `name_mismatch`.
 - `invalid_tax_ids` — Business IDs where `tax_id` field is flagged or invalid (e.g., placeholder TINs like TIN999999, or missing).
 - `expired_license_ids` — Business IDs where `license_expiry` < `as_of_date`.
 - `review_queue_ids` — Business IDs not marked `release`.
 - `risk_score_override_flags` — Business IDs where `risk_score >= 70`.
 
 ### Sort Order
 All lists ascending by business ID.
