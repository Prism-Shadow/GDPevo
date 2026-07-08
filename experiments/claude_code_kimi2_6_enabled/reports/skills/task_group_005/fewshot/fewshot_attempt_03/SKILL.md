Let me now write the `SKILL.md` file directly. Since the file-writing tool is not available, I will output the complete `SKILL.md` content as my final response.

---

```markdown
# SKILL.md — Task Group 005 Reusable SOP

## 1. Environment & API Base URL
- **Always use** `GDPEVO_ENV_BASE_URL=http://34.46.77.124:8005`.
- Do **not** use `localhost`, `127.0.0.1`, or any local env directory unless the remote URL itself points there. If a prompt mentions a local URL, override it with the remote endpoint above.

## 2. Core API Endpoints to Inspect
The task group interacts with five inter-related domains. Prefer these endpoint patterns (exact paths may vary slightly by prompt; trust the prompt's stated path over guessing):

| Domain | Endpoint Pattern | Used In |
|--------|------------------|---------|
| **Claims** | `GET /finance/claims/{claim_id}` | AP batch review, stale snapshot |
| **AP Bills** | `GET /finance/ap/bills?claim_id={claim_id}` | AP batch review, stale snapshot |
| **AP Close Logs** | `GET /finance/ap/close-logs?claim_id={claim_id}` | Stale snapshot reconciliation |
| **Business KYC** | `GET /control/kyc/business/{business_id}` | Onboarding, account-change review |
| **UBO** | `GET /control/kyc/ubo?business_id={business_id}` | Onboarding |
| **Screening** | `GET /control/kyc/screening?business_id={business_id}` | Onboarding |
| **Compliance Screening** | `GET /control/compliance/screening?business_id={business_id}` | Account-change review |
| **Accounts** | `GET /finance/accounts/{account_id}` | Account-change review |
| **Prepaid Invoices** | `GET /finance/prepaid/invoices?entity={entity}&period={period}` | Prepaid close |
| **Prepaid Amortization** | `GET /finance/prepaid/amortization/{invoice_id}` | Prepaid close |

**Pitfall:** Do not brute-force scan endpoints. Read the prompt for the exact endpoint names it references; use only those.

---

## 3. Output Conventions (Universal)

### 3.1 JSON Format
- Return **only** a single JSON object. Do not wrap it in markdown code blocks in the final answer file unless the runner explicitly requires it.
- Match the provided `answer_template.json` schema exactly; missing or extra top-level keys will fail validation.

### 3.2 Sorting Rules
- **All ID lists must be sorted ascending** (lexicographic/string sort) unless the prompt explicitly states otherwise.
  - `claim_id` lists: `CLM-2025-0015`, `CLM-2025-0037`, `CLM-2025-0038`, `CLM-2025-0080`, `CLM-2025-0090`, `CLM-2025-FIN-042`, `CLM-2025-OPS-017`
  - `business_id` lists: `BUS-2025-0006`, `BUS-2025-0009`, `BUS-2025-0018`, `BUS-2025-0041`, `BUS-2025-0056`

### 3.3 Currency & Rounding
- **Use USD with two decimal places** (e.g., `1842.36`, `0.00`) unless the prompt explicitly says "cents."
- When the prompt says "USD cents," convert dollars to cents and return an integer.
- Round to **exactly two decimals** for dollar amounts; do not truncate.

---

## 4. Task-Type Decision Rules

### 4.1 AP Claims Batch Review (Train 001 / Train 004)
**Goal:** Classify claims into `payable`, `blocked`, `paid`, and compute balances.

**Endpoint calls needed:**
- `GET /finance/claims/{claim_id}` — for approval status and claim metadata.
- `GET /finance/ap/bills?claim_id={claim_id}` — for current bill status, amount, and payment state.

**Classification logic:**
| Bucket | Rule |
|--------|------|
| `paid_claim_ids` | Claim status is "paid" **or** the matched AP bill shows `paid`/`cleared` with zero remaining balance. |
| `blocked_claim_ids` | Claim is unapproved, on hold, has hard-stop flags, or requires owner/CRM cleanup. |
| `payable_claim_ids` | Claim is approved, **not** blocked, **not** paid, and has a positive open AP balance. |
| `not_ready_claim_ids` | (Stale-snapshot variant) Claims that are blocked, void, mismatched, or unapproved. |

**Balance & totals:**
- `ap_open_balance_total` = sum of current open AP balances for **payable** claims only.
- `ap_balance_by_claim` = current open balance for **every** claim in scope (payable = positive, paid/blocked/void = `0.0`).
- `reviewed_claim_count` = total number of claim IDs processed in the batch.

**Batch status:**
- `"blocked"` if `blocked_claim_ids` is non-empty.
- `"needs_ap_refresh"` if stale-snapshot corrections are required.
- Otherwise, infer from prompt context (e.g., `"ready"` or `"released"`).

**Stale snapshot corrections** (Train 004):
Map each claim ID to exactly one correction reason string. Observed values:
- `"block_unapproved_claim"` — claim approval status is not approved.
- `"ignore_void_bill"` — the matched bill is void.
- `"exclude_amount_or_vendor_mismatch"` — snapshot amount or vendor does not match current API data.
- `"replace_with_matched_paid_bill"` — claim is already paid (replace stale scheduled entry).
- `"mark_in_flight_payment"` — payment is scheduled/in-flight but not yet cleared.

**Close logs:**
- Query `GET /finance/ap/close-logs?claim_id={claim_id}`.
- `close_log_required.required` = `true` if any close-log records exist for claims in scope.
- `close_log_required.ids` = the `close_log_id` values, sorted ascending.

---

### 4.2 Vendor Onboarding Batch Review (Train 002)
**Goal:** Per-business KYC/screening triage.

**Endpoint calls needed:**
- `GET /control/kyc/business/{business_id}` — license, tax, bank, document status.
- `GET /control/kyc/ubo?business_id={business_id}` — beneficial owners and reportable flags.
- `GET /control/kyc/screening?business_id={business_id}` — PEP, sanctions, adverse media.

**Decision matrix:**
| Decision | Condition |
|----------|-----------|
| `"escalate"` | Any **hard_stop_flags** are present (e.g., `confirmed_pep`, `shell_company_suspected`, `bank_closed`, `expired_license`, `vendor_on_hold`, `bank_name_mismatch`). |
| `"awaiting_information"` | **No** hard_stop_flags, **but** missing required documents or screening not run. |
| `"approve"` | No hard_stop_flags and no missing items (clean). |

**Output fields:**
- `per_business`: array of `{business_id, decision}` for every target business, sorted by `business_id`.
- `reportable_ubo_counts`: object keyed by `business_id`; value = count of UBOs where `reportable_flag == true`.
- `hard_stop_flags`: object keyed by `business_id`; value = array of flag strings (sorted alphabetically). Empty array `[]` if none.
- `follow_up_business_ids`: sorted list of all `business_id`s where `decision != "approve"`.
- `overall_release_ready`: `true` only if **every** decision is `"approve"`. Otherwise `false`.

**Common hard-stop flag strings observed:**
`confirmed_pep`, `expired_license`, `vendor_on_hold`, `bank_name_mismatch`, `shell_company_suspected`, `bank_closed`, `screening_not_run`, `missing_required_documents`.

---

### 4.3 Prepaid Close Scope (Train 003)
**Goal:** Reconcile prepaid amortization schedules against GL for a given entity and period.

**Endpoint calls needed:**
- `GET /finance/prepaid/invoices?entity={entity}&period={period}` — list of invoices in scope.
- `GET /finance/prepaid/amortization/{invoice_id}` — schedule details per invoice.

**Scope & selection:**
- `period` format: `YYYY-MM` (e.g., `"2025-03"`).
- `entity`: exact entity name from the scope/prompt (e.g., `"Aurisic US"`).
- `selected_invoice_ids`: every invoice returned by the API for the entity+period, sorted ascending.

**Invoice-level result (`invoice_results`):**
One object per selected invoice:
- `prepaid_invoice_id`
- `account` (account number string, e.g., `"1250"`)
- `march_amortization` (the amortization amount for the target month)
- `cumulative_amortization_through_march` (sum of amortization from start through target month)
- `ending_balance` (original amount minus cumulative amortization)
- `default_missing_term_flag` (`true` if the invoice lacks a defined term/default term)
- `exception_flag` (`true` if the invoice triggers any exception rule — e.g., missing term, schedule anomaly, or GL mismatch)

**Pitfall:** Do not assume `exception_flag` is only `default_missing_term_flag`. Inspect the amortization response for additional anomaly indicators.

**Account rollup (`account_rollup`):**
Keyed by account number. Compute per account:
- `selected_invoice_count`
- `original_amount_total` (sum of invoice original amounts)
- `march_amortization_total` (sum of month amortization)
- `cumulative_amortization_through_march` (sum of cumulative amortization)
- `schedule_ending_balance` = `original_amount_total` − `cumulative_amortization_through_march`
- `gl_ending_balance` (from API/scope)
- `variance_amount` = `schedule_ending_balance` − `gl_ending_balance` (can be negative)
- `variance_flag` = `true` if `variance_amount != 0.00`
- `has_default_missing_term_flag` = `true` if **any** invoice in the account has `default_missing_term_flag == true`
- `account_status`:
  - `"requires_reconciliation"` if `variance_flag == true` OR `has_default_missing_term_flag == true`
  - Otherwise `"ok"` (or prompt-specific clean status)

**Special lists:**
- `default_missing_term_invoice_ids`: sorted list of all invoices where `default_missing_term_flag == true`.
- `exception_invoice_ids`: sorted list of all invoices where `exception_flag == true`.

---

### 4.4 Account-Change Payment Release Review (Train 005)
**Goal:** Determine release posture after vendor bank/account changes.

**Endpoint calls needed:**
- `GET /finance/accounts/{account_id}` or vendor/account endpoint — bank match status.
- `GET /control/compliance/screening?business_id={business_id}` — tax validity, license expiry, risk score.
- `GET /control/kyc/business/{business_id}` — supporting evidence.

**Decision matrix:**
| Decision | Condition |
|----------|-----------|
| `"escalate"` | `invalid_tax_id` is present (compliance hard stop). |
| `"hold"` | `bank_mismatch` OR `risk_score_override_flag` OR (`expired_license` without `invalid_tax_id`). |
| `"release"` | None of the above issues. |

**Output fields:**
- `task_id`, `batch_id`, `as_of_date`: copy from prompt/template.
- `target_business_ids`: sorted ascending.
- `decisions`: object keyed by `business_id`.
- `bank_mismatch_ids`: sorted list of businesses with bank account name/number mismatch.
- `invalid_tax_ids`: sorted list of businesses with invalid tax ID.
- `expired_license_ids`: sorted list of businesses with expired license.
- `review_queue_ids`: sorted list of all businesses where `decision != "release"`.
- `risk_score_override_flags`: sorted list of businesses flagged for risk-score override.

**Priority tie-break:** If a business qualifies for both `"escalate"` and `"hold"`, `"escalate"` wins because `invalid_tax_id` is a compliance hard stop.

---

## 5. Cross-Cutting Pitfalls

1. **Sorting:** Always double-check that every list of IDs is sorted ascending before emitting JSON. This is the most common silent failure.
2. **Currency precision:** Financial totals must be numbers (not strings) with exactly two decimal places when denominated in dollars. `0.00` is required, not `0` or `0.0`.
3. **Empty collections:** Return empty arrays `[]` or empty objects `{}` rather than omitting keys. The templates expect the keys to exist.
4. **Do not access local env files:** The prompts may mention local files or `127.0.0.1`, but `environment_access.md` always overrides with the remote API. Use only the remote API.
5. **Do not include narrative:** Output must be **only** the JSON object. No markdown fences, no explanatory text.
6. **Claim vs. Bill vs. Payment distinction:** In AP tasks, claims are reimbursement requests; bills are AP liabilities; payments are settlement events. Preserve the distinction in output fields.
7. **Variance sign:** In prepaid reconciliation, `variance_amount` can be negative. Do not take the absolute value unless the prompt explicitly says so.
```

---
