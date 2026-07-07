# Skill: ERP Finance/Compliance Batch Review Workflow

## Overview
This skill covers reviewing and closing finance batches (AP reimbursements, vendor onboarding, prepaid amortization, payment release) using ERP API data. The key principle is to treat the live API as the system of record and any local payload files (snapshots, stale exports, batch definitions) as context only.

## General Workflow

### 1. Read All Local Inputs First
- Read `input/prompt.txt` to understand the review objective and candidate IDs.
- Read `input/payloads/answer_template.json` to understand the exact required schema, field types, ordering rules, and enum values.
- Read any additional local payloads (e.g., `onboarding_batch.json`, `prepaid_close_scope.json`) for candidate lists and thresholds.

### 2. Query the Live API Systematically
Use the shared API base URL. Common endpoints to explore:
- **Claims/AP:** `/claims`, `/ap/bills`, `/payments`, `/close-logs`
- **Vendor/Compliance:** `/vendors`, `/compliance/screening`, `/businesses`, `/ubo`
- **Prepaid/GL:** `/prepaids/invoices`, `/gl/balances`, `/api/prepaids/gl-balances`

For each candidate ID in the local payload, fetch its current state from the API. Do not rely on local snapshot values for final decisions.

### 3. Apply Domain Rules Precisely

#### AP Reimbursement / Close Review
- **Paid claims:** Must have a matching AP bill and a cleared payment for the exact claim amount.
- **Payable claims:** Approved batch claims with valid open AP reimbursement bills; include in AP open balance total.
- **Blocked claims:** Claims with case issues (unapproved, missing support, owner cleanup needed) or AP/payment evidence issues (void bill, mismatch). If any claim is blocked, `batch_status` = `blocked`.
- **CRM required:** Subset of blocked claims specifically needing expense-case owner cleanup or AP-link remediation.
- **Sort all claim ID lists ascending** by claim ID.
- **Currency amounts:** Use USD with two decimals.

#### Vendor Onboarding / Release Control
- Fetch vendor records, compliance screening results, UBO data, bank account status, and license/tax validity.
- **Decisions:** `approve` only if all checks pass; `awaiting_information` if documents or data are missing; `escalate` if hard-stop flags exist (sanctions, PEP, shell company suspicion, bank name mismatch, expired license, etc.).
- **Hard-stop flags:** Sort alphabetically. Use empty list when none apply.
- **UBO counts:** Count unique beneficial-owner names at or above the reporting threshold.
- `overall_release_ready` is `true` only if every listed business decision is `approve`.
- Sort business ID lists ascending.

#### Prepaid Close / Amortization
- Fetch prepaid invoice schedules and GL balances for the scoped accounts.
- Use straight-line monthly amortization as represented in invoice records.
- For each invoice, compute: March amortization, cumulative amortization through March, ending balance.
- Roll up to account level: sum original amounts, March amortization, cumulative amortization, schedule ending balance.
- Compare schedule ending balance to GL ending balance per account. Flag variance if absolute difference exceeds threshold (e.g., 100.00).
- Identify invoices with missing/default terms (`default_missing_term_flag`) and any other data-quality exceptions (`exception_flag`).
- Account status: `reconciled` if no variance and no missing terms; `variance_review` if variance flagged; `requires_reconciliation` if unable to reconcile.
- Maintain invoice ordering as specified in scope file.
- Report all currency amounts to two decimals.

#### AP Payment Release After Account Changes
- Fetch current vendor/compliance records for each business ID.
- Check: bank account status (name mismatch = `bank_mismatch_ids`), tax ID validity, license expiration relative to review date, risk scores.
- **Decisions:** `release` if clean; `hold` if expired license, invalid tax, or minor mismatch; `escalate` for sanctions, high risk score (>=70), or severe bank mismatch.
- `review_queue_ids`: Any business requiring compliance/AP review before release (holds + escalations).
- `risk_score_override_flags`: Business IDs with risk_score >= 70.
- Sort all business ID lists ascending.

### 4. Construct the Answer JSON
- Validate against the answer template schema: required keys, correct types, enum values, ordering.
- Do not include narrative text outside the JSON.
- Ensure all referenced IDs in the answer are exactly as provided in local payloads (no extra IDs, no missing IDs).

### 5. Final Sanity Checks
- Are all ID lists sorted as required?
- Are all enum values valid?
- Are currency amounts formatted to two decimals?
- Does the batch status / overall flag correctly reflect the worst-case item?
- Are there any additional properties not allowed by the template?
