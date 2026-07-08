# Task Group 005 – Reusable Skill (SOP)

## 1. Environment & Base URL
- **Always use the remote base URL from `environment_access.md` (`GDPEVO_ENV_BASE_URL`).**
- **Override any `localhost` or `127.0.0.1` references in the prompt** with the remote URL.
- Do not start local environments or read `env/` source directories.

## 2. Confirmed API Endpoints
| Endpoint | Purpose | Typical Query Params |
|----------|---------|----------------------|
| `GET /vendors` | Vendor master data | `vendor_id` |
| `GET /claims` | Expense claim headers | `claim_id` |
| `GET /bills` | AP bill records | `claim_id`, `bill_id` |
| `GET /payments` | Payment records | `bill_id`, `payment_id` |
| `GET /prepaids/invoices` | Prepaid invoice schedules | `prepaid_invoice_id` |
| `GET /gl/balances` | Period-end GL balances | `account`, `period` (YYYY-MM) |

- **Pagination:** Responses wrap lists in `"data"`. Use `limit`/`offset` if counts exceed 100.
- **Path-parameter style:** `/vendors/{id}` returns `not_found`. Use query parameters instead (`?vendor_id=...`).

## 3. Task-Type Workflows

### A. AP Close / Reimbursement Batch Review (train_001, train_004)
**Data to pull per claim:**
1. `GET /claims?claim_id={id}` → `status`, `amount`, `vendor_id`, `receipt_status`, `policy_flags`.
2. `GET /bills?claim_id={id}` → all bills linked to the claim.
3. `GET /payments?bill_id={bill_id}` → payment state for each bill.

**Classification rules:**
- **Paid:** Claim status is `paid` **and** there is a `paid` bill with a `cleared` payment matching the claim amount.
- **Payable / Eligible:** Claim status is `approved`, has a valid open AP bill (`scheduled` or `approved`), and no `cleared` payment yet. In-flight payments (`processing`, `scheduled`) keep the claim in the payable queue.
- **Blocked / Not-ready:** Any of the following:
  - Claim status is **not** `approved` (e.g., `needs_receipt`, `submitted`, `rejected`).
  - No bill exists for the claim.
  - Bill is `void`.
  - Bill amount ≠ claim amount (vendor or amount mismatch).
  - Missing required AP-link evidence.

**Stale-snapshot reconciliation (train_004):**
- Treat the local CSV snapshot as **context only**; the API is the system of record.
- Map each claim to one `stale_snapshot_corrections` value:
  - `current_snapshot_ok` – API matches the stale row.
  - `mark_in_flight_payment` – snapshot shows no payment, but API shows a `processing`/`scheduled` payment.
  - `replace_with_matched_paid_bill` – snapshot references the wrong bill/amount, but API shows a paid bill that matches the claim.
  - `exclude_amount_or_vendor_mismatch` – bill amount or vendor does not align with the claim.
  - `ignore_void_bill` – the bill is `void` in the API.
  - `block_unapproved_claim` – claim status is not `approved`.

**AP balance computation (train_004):**
- Sum bill amounts that are **not** `paid`/`void` and have **no** `cleared` payment.
- Ignore voided or stale rows.

**Close logs:**
- If the API exposes `/close-logs` or similar, query it by claim/bill. If the endpoint is absent, set `close_log_required.required = false` and `ids = []` unless the prompt explicitly supplies close-log data.

### B. Vendor Onboarding / Release Control (train_002, train_005)
**Data to pull:**
- `GET /vendors?vendor_id={id}` for basic fields: `status`, `bank_account_last4`, `tax_id`, `legal_name`, `updated_at`.
- **Caution:** Dedicated compliance/onboarding endpoints (e.g., `/compliance`, `/screening`, `/licenses`, `/risk`) are **not confirmed** on the remote API.
  - If present, query them for `bank_account_status`, `tax_valid`, `license_expiry`, `risk_score`, `screening_status`, and UBO data.
  - If absent, infer release decisions from the payload context and flag missing evidence as `awaiting_information` / `hold`.

**Decision values:**
- train_002: `approve`, `awaiting_information`, `escalate`.
- train_005: `release`, `hold`, `escalate`.

**Hard-stop flags (train_002):**
- `bank_closed`, `bank_name_mismatch`, `confirmed_pep`, `expired_license`, `missing_required_documents`, `sanctions_confirmed`, `screening_not_run`, `shell_company_suspected`, `vendor_on_hold`.
- Sort flags **alphabetically** per business.

**Train-005 specific lists:**
- `bank_mismatch_ids` – `bank_account_status == name_mismatch`.
- `invalid_tax_ids` – tax ID validation fails.
- `expired_license_ids` – `license_expiry < as_of_date`.
- `review_queue_ids` – any compliance/AP review required.
- `risk_score_override_flags` – `risk_score >= 70`.
- **All ID lists ascending by `business_id`.**

**Overall release readiness:**
- `overall_release_ready` (train_002) is `true` **only if every** listed business gets `approve`.

### C. Prepaid Close Reconciliation (train_003)
**Data to pull:**
1. `GET /prepaids/invoices?prepaid_invoice_id={id}` for each scoped invoice.
2. `GET /gl/balances?account={acct}&period={YYYY-MM}` for each account.

**Amortization math:**
- Use the `monthly_amortization` value straight from the invoice record (straight-line).
- Count months elapsed from `service_start` **through** the close period month (inclusive).
  - Example: close period `2025-03`.
  - Invoice starting `2025-01-01` → 3 months (Jan, Feb, Mar).
  - Invoice starting `2025-03-01` or `2025-03-15` → 1 month for March.
  - Invoice ending `2025-03-31` → count all months in its term.
- `cumulative_amortization_through_march = monthly_amortization × months_elapsed`.
- `ending_balance = original_amount − cumulative_amortization_through_march`.
- Round all currency fields to **two decimals**.

**Variance check:**
- `variance_amount = schedule_ending_balance − gl_ending_balance`.
- `variance_flag = abs(variance_amount) > variance_threshold_abs` (from payload, e.g., `100.0`).

**Flags & exceptions:**
- `default_missing_term_flag` at invoice level: `true` when `data_quality_flags` contains `missing_contract_dates` (or similar term-missing flag).
- `exception_flag` at invoice level: `true` when `data_quality_flags` is **non-empty** (includes `rounded_amount`, `missing_contract_dates`, etc.).
- `default_missing_term_invoice_ids`: scoped invoices with missing-term flags, sorted ascending.
- `exception_invoice_ids`: scoped invoices with **any** data-quality flag, sorted ascending.

**Account status mapping:**
- `reconciled` – no variance and no flags.
- `variance_review` – `variance_flag == true`.
- `requires_reconciliation` – missing-term/exception flags present or other schedule issues.

## 4. Output Conventions
- **Format:** Return **only** a JSON object matching the `answer_template.json` schema.
- **Currency:** Always report USD amounts with **two decimal places** (e.g., `1234.50`).
  - *Note:* Prompts may say "USD cents"; interpret this as cent-precision dollars (two decimals), not integer cents.
- **Sorting:**
  - All `claim_id` lists: ascending lexicographically.
  - All `business_id` lists: ascending lexicographically.
  - All `invoice_id` lists: ascending lexicographically.
  - `selected_invoice_ids`: preserve the order given in the payload unless the template explicitly requires ascending.
- **Key ordering:** When the template specifies `top_level_order` (e.g., train_002), emit keys in that exact order.
- **No extra properties:** Do not add keys not defined in the template (train_005 explicitly forbids additional properties).

## 5. Common Pitfalls
- **Using localhost:** Always override with the remote base URL from `environment_access.md`.
- **Path vs. query params:** `/vendors/{id}` fails; use `/vendors?vendor_id={id}`.
- **Multiple bills per claim:** Some claims have >1 bill. Evaluate **all** bills and payments before classifying the claim.
- **Claim status vs. bill status:** A claim may be `paid` in the claim table but still have an unrelated stale bill open. Cross-check amounts and payment clearance.
- **Stale snapshots:** Treat local CSV snapshots as **context only**; the API is the system of record.
- **Missing compliance endpoints:** If onboarding/compliance data is not exposed, fall back to `/vendors` basic fields and default to conservative decisions (`awaiting_information` / `hold`).
- **Prorated months:** For prepaid close, use the **given** `monthly_amortization`; do not recalculate prorated daily amounts unless the invoice explicitly indicates daily recognition.
- **Zero balances:** Keep `.00` for zero amounts (two-decimal precision).
