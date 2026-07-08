# SKILL — Finance & Control Batch Reconciliation SOP

## 1. API Endpoints to Inspect
Always call the endpoints exactly as named in the task prompt. Common families across this group:

- **AP / Claims**
  - `GET /ap/claims/batch/{batch_id}`
  - `GET /ap/open-balance`
- **Onboarding / KYC / UBO**
  - `GET /onboarding/batch/{batch_id}`
  - `GET /screening/ubo/{business_id}`
  - `POST /onboarding/batch/{batch_id}/release-check`
- **Prepaid / Amortization**
  - `GET /finance/prepaid/close-scope?period={YYYY-MM}&entity={entity_name}`
  - `GET /finance/prepaid/amortization-schedule?invoice_id={invoice_id}`
- **Vendor Account Changes**
  - `GET /vendor/account-changes/batch/{batch_id}`
  - `GET /vendor/{business_id}/profile`
  - `GET /vendor/{business_id}/bank-details`
  - `GET /vendor/{business_id}/license`
  - `GET /vendor/{business_id}/tax-id`

Use the `environment_access.md` host/port in the workspace root for the base URL. Do not guess alternative endpoint names.

## 2. Answer Schema Compliance
Every task ships an `answer_template.json`. Produce JSON that **exactly** matches the template keys and value types (arrays, objects, booleans, numbers, strings). Never add extra top-level keys. Observed required top-level structures:

| Task Type | Key Patterns |
|-----------|--------------|
| AP Claims | `payable_claim_ids`, `blocked_claim_ids`, `paid_claim_ids`, `ap_open_balance_total`, `crm_required_claim_ids`, `batch_status`, `reviewed_claim_count` |
| AP Stale Snapshot | `eligible_claim_ids`, `not_ready_claim_ids`, `ap_balance_by_claim`, `stale_snapshot_corrections`, `close_log_required`, `batch_status` |
| Onboarding | `per_business`, `reportable_ubo_counts`, `hard_stop_flags`, `follow_up_business_ids`, `overall_release_ready` |
| Prepaid Close | `period`, `entity`, `selected_invoice_ids`, `account_rollup`, `invoice_results`, `default_missing_term_invoice_ids`, `exception_invoice_ids` |
| Vendor Changes | `task_id`, `batch_id`, `as_of_date`, `target_business_ids`, `decisions`, `bank_mismatch_ids`, `invalid_tax_ids`, `expired_license_ids`, `review_queue_ids`, `risk_score_override_flags` |

## 3. Sorting & Ordering Rules
- **All ID lists and object keys must be sorted lexicographically (alphabetical)** unless the prompt explicitly specifies a processing order.
  - Example arrays: `blocked_claim_ids`, `eligible_claim_ids`, `target_business_ids`, `follow_up_business_ids`, `selected_invoice_ids`, `default_missing_term_invoice_ids`, `exception_invoice_ids`.
  - Example objects: keys inside `reportable_ubo_counts`, `hard_stop_flags`, `ap_balance_by_claim`, `stale_snapshot_corrections`, `decisions`.
- For `per_business` arrays, sort entries by `business_id` ascending.

## 4. Rounding & Monetary Conventions
- **Round all currency fields to 2 decimal places** (e.g., `1842.36`, `0.00`, `-290855.05`).
- Represent zero as `0.0` or `0.00` consistently with the template example.
- Do not truncate intermediate values unless specified; present final outputs with 2-decimal precision.

## 5. Finance & Control Decision Rules (Transferable Patterns)

### AP / Claims Batches
- A claim is **payable** if its open AP balance is `> 0` and it is **not** blocked by CRM.
- A claim is **paid** if its status is already `paid` (goes into `paid_claim_ids`).
- A claim is **blocked** if on CRM hold (`crm_required_claim_ids` == `blocked_claim_ids`).
- `batch_status`:
  - `"blocked"` if any claim is blocked.
  - Otherwise `"ready"` or status derived from prompt rules.
- `reviewed_claim_count` = total unique claims examined.

### AP Stale Snapshot Reconciliation
- Cross-reference the stale CSV / snapshot against live `GET /ap/claims/batch/{batch_id}` and `GET /ap/open-balance`.
- `eligible_claim_ids`: claims that are live-matched, approved, and have a legitimate balance.
- `not_ready_claim_ids`: claims that are void, unapproved, mismatched, or have zero balance.
- `stale_snapshot_corrections`: map every claim ID in scope to a canonical reason string (e.g., `block_unapproved_claim`, `ignore_void_bill`, `exclude_amount_or_vendor_mismatch`, `replace_with_matched_paid_bill`, `mark_in_flight_payment`).
- `close_log_required`: object with boolean `required` and `ids` array of close log IDs (sorted) when corrections exist.
- `batch_status`: typically `"needs_ap_refresh"` when stale mismatches are found.

### Onboarding / UBO Release
- For each business in the batch, fetch UBO screening and profile data.
- `reportable_ubo_counts`: count of UBOs that meet the reportable threshold per jurisdiction.
- `hard_stop_flags`: list all applicable stop flags per business (e.g., `confirmed_pep`, `expired_license`, `vendor_on_hold`, `bank_name_mismatch`, `shell_company_suspected`, `bank_closed`, `screening_not_run`, `missing_required_documents`). Sort the list lexicographically.
- Decision logic:
  - Any hard stop → `"escalate"` or `"awaiting_information"` depending on missing-doc vs. confirmed-risk rules in prompt.
  - Clean + UBO thresholds met → `"approve"`.
- `follow_up_business_ids`: all businesses whose decision is **not** `"approve"`.
- `overall_release_ready`: `true` only if **all** businesses are approved and no hard stops exist.

### Prepaid Amortization Close
- `selected_invoice_ids`: only invoices included in the `close-scope` response for the given `period` and `entity`.
- Per-invoice schedule (`GET /finance/prepaid/amortization-schedule`):
  - Extract `march_amortization` (or period-specific amortization), `cumulative_amortization_through_march`, and `ending_balance`.
  - `default_missing_term_flag`: `true` when the schedule uses a fallback term because the original term is missing.
  - `exception_flag`: `true` for invoices that trigger control exceptions (e.g., ending balance mismatch, missing term, duplicate, or out-of-sequence amortization).
- `account_rollup`:
  - Sum `selected_invoice_count`, `original_amount_total`, `march_amortization_total`, `cumulative_amortization_through_march`.
  - `schedule_ending_balance` = sum of invoice ending balances for that account.
  - `gl_ending_balance` comes from the close-scope GL snapshot.
  - `variance_amount` = `schedule_ending_balance - gl_ending_balance`.
  - `variance_flag`: `true` if `variance_amount != 0`.
  - `has_default_missing_term_flag`: `true` if any invoice in the account has the flag.
  - `account_status`: `"requires_reconciliation"` when `variance_flag` is `true` or missing-term flags exist; otherwise `"ok"` per prompt rules.

### Vendor Account Change Batch
- For each `business_id` in the batch payload, compare:
  - `bank-details` vs. change request → `bank_mismatch_ids`.
  - `tax-id` validity → `invalid_tax_ids`.
  - `license` expiration vs. `as_of_date` → `expired_license_ids`.
  - Risk-score overrides → `risk_score_override_flags`.
- Decisions:
  - `"release"` only when zero mismatches, valid tax, valid license, and no risk override.
  - `"hold"` for bank mismatches or risk overrides without disqualifying tax/license issues.
  - `"escalate"` for invalid tax IDs, expired licenses, or combined severe flags.
- `review_queue_ids`: union of all businesses that are **not** `"release"`.

## 6. Pitfalls
1. **Do not omit zero-balance entries** in `ap_balance_by_claim`; include every claim in scope with its exact live balance.
2. **Do not invent endpoint names** — copy them verbatim from the prompt and `environment_access.md`.
3. **Ensure lexicographic sort on every list and every object key** before emitting JSON; unsorted output fails validation even if values are correct.
4. **Prepaid ending balance** may legitimately be `0.01` due to rounding; treat it as non-zero and do not round to zero.
5. **Hard-stop flags** must be sorted internally per business; missing this causes array-mismatch failures.
6. **Batch status strings** are lowercase snake_case (e.g., `blocked`, `needs_ap_refresh`, `ready`). Match exactly.
7. **Do not include test-specific answer values** in the skill — this SOP is for future solvers; keep rules generic.

## 7. Execution Checklist
1. Read `prompt.txt` and identify the exact API calls.
2. Read `answer_template.json` to lock the required output schema.
3. Call endpoints in the order dictated by dependencies (e.g., fetch batch list first, then per-item details).
4. Apply control rules, sort all IDs/keys, round money to 2 decimals.
5. Validate that no extra keys were added and all required keys are present.
6. Write final JSON to `answer.json`.
