Based on my thorough analysis of all five training tasks, I now present the complete **SKILL.md**:

---

```markdown
# SKILL.md — Accounts Payable & Vendor Control Review SOP

## 1. Scope
This skill covers vendor onboarding eligibility reviews, payment-release risk assessments after account-change events, prepaid expense close-scope analysis, and stale AP snapshot reconciliation. All tasks require querying shared API endpoints and producing structured JSON decisions.

---

## 2. API Endpoint Patterns

### 2.1 Vendor & Compliance Endpoints
Always inspect these endpoints for vendor-related reviews (onboarding, payment release, account changes):

| Resource | Endpoint Pattern |
|----------|------------------|
| Vendor profile | `GET /vendors/{vendor_id}` |
| Compliance record | `GET /vendors/{vendor_id}/compliance` |
| Bank details | `GET /vendors/{vendor_id}/bank` |
| Tax record | `GET /vendors/{vendor_id}/tax` |
| License record | `GET /vendors/{vendor_id}/license` |
| Screening record | `GET /vendors/{vendor_id}/screening` |
| Risk assessment | `GET /vendors/{vendor_id}/risk` |

**Caution:** The exact vendor_id for a business_id may need to be discovered via a vendor lookup or derived from the input payload. If the prompt provides both `business_id` and `vendor_id`, use the stated `vendor_id` directly.

### 2.2 AP (Accounts Payable) Endpoints
For stale-snapshot or claims-related tasks:

| Resource | Endpoint Pattern |
|----------|------------------|
| AP claim | `GET /ap/claims/{claim_id}` |
| AP bill | `GET /ap/bills/{bill_id}` |

### 2.3 Prepaid Endpoints
For prepaid expense close-scope tasks:

| Resource | Endpoint Pattern |
|----------|------------------|
| Prepaid items list | `GET /prepaid/items` (with query params as needed) |
| Prepaid item ledger | `GET /prepaid/items/{item_id}/ledger` |

---

## 3. Input Payload Conventions

### 3.1 Batch Review Inputs
Batches typically contain:
- `batch_id`: Identifier for the review batch.
- `as_of_date` or `review_date`: The cutoff date for evaluating data.
- `business_ids` or `target_business_ids`: List of entities to review.
- `requested_result`: Describes the expected output (e.g., release-control decisions and summary fields).

### 3.2 Account-Change Event Inputs
Account-change batches contain an `account_change_events` array with fields:
- `ticket_id`, `business_id`, `vendor_id`, `change_type`
- `requested_release_amount_usd`, `requestor`, `priority`
- `requested_bank_last4`: The last-4 digits of the newly requested bank account.

---

## 4. Decision Framework

### 4.1 Decision Values
Standard three-way decision taxonomy:
- **`release`** — All controls satisfied; payment/onboarding can proceed.
- **`hold`** — Missing or non-compliant evidence; block until resolved.
- **`escalate`** — High-risk condition or insufficient data; route to senior review.

### 4.2 Control Rules for Vendor Reviews
Evaluate the following dimensions. A failure in any critical dimension typically yields **hold** or **escalate**:

| Dimension | Release Criteria (typical) |
|-----------|---------------------------|
| **Compliance** | Status = `active`, no expired certifications, required docs on file. |
| **Bank** | Account validated, `bank_last4` matches requested, no `closed` or `frozen` status, revalidation current if required. |
| **Tax** | Tax ID valid, W-9/W-8 on file, no IRS flags, withholding status clear. |
| **License** | Business license active, not expired as of `review_date`, jurisdiction matches. |
| **Screening** | Sanctions / PEP / adverse media checks clear; no open alerts. |
| **Risk** | Risk rating within acceptable threshold; no open fraud or credit risk flags. |

**Priority override:** Urgent-priority tickets may still be denied if bank or compliance is critically deficient. Do not auto-release solely because of `priority: urgent`.

### 4.3 Change-Type Specific Rules
- `new_account_after_remittance_failure`: Verify new bank account is validated and distinct from the failed one.
- `reactivation_after_closed_bank_notice`: Confirm closure reason resolved and new bank evidence current.
- `account_revalidation`: Ensure revalidation date is on or after the review date.
- `account_change`: Treat as standard new-account validation.

---

## 5. Output Conventions

### 5.1 Answer Template Structure
Always mirror the provided `answer_template.json`. Common top-level fields:
- `review_date`
- `memo_id`
- `decision` or `decisions` array
- Summary statistics (counts of release / hold / escalate)
- Total amounts affected

### 5.2 Sorting Rules
- **ID lists**: Return in **ascending alphanumeric order** (e.g., `business_id`, `ticket_id`, `claim_id`).
- This is explicitly required in some prompts and should be treated as a universal default.

### 5.3 Rounding & Currency
- Express all USD amounts with **two decimal places** (e.g., `15476.30`).
- Use standard rounding (half-up) when deriving totals.
- Verify that sum totals match the arithmetic total of listed items; do not rely on input payload summaries if they are stale.

### 5.4 Reasoning Fields
- Provide concise, factual `reasoning` strings.
- Reference specific evidence from API responses (e.g., "Bank account VEN-0043 last4 3067 validated 2025-05-28; compliance active").
- Do not include speculative language; cite the control that failed if decision is `hold` or `escalate`.

---

## 6. Stale Snapshot Reconciliation Workflow

When provided with a CSV snapshot (e.g., `stale_ap_snapshot.csv`):

1. **Parse the snapshot** — note `snapshot_generated_at`, `claim_id`, `bill_id`, and frozen statuses/amounts.
2. **Query current API state** for each `claim_id` and `bill_id`.
3. **Identify stale items** by comparing snapshot status vs. current status:
   - Snapshot says `scheduled`/`approved` but API says `paid`/`cleared` → stale; mark for removal/update.
   - Snapshot says `none` for payment but API shows a payment → stale.
   - Amount mismatches between snapshot and current state → stale.
4. **Produce a clean list** of items that are genuinely still pending as of the review date.
5. **Sort** output lists in ascending order.

---

## 7. Prepaid Close-Scope Workflow

For prepaid expense tasks:

1. Retrieve the prepaid items list and item-level ledgers.
2. Apply the close-scope policy criteria (e.g., fully amortized, zero remaining balance, or specific date thresholds).
3. For each qualifying item, capture:
   - `item_id`
   - `remaining_balance` (if any)
   - `close_reason`
4. Sum totals and sort lists in ascending `item_id` order.

---

## 8. Summary Statistics

Batch-review outputs often require aggregate fields:

| Summary Field | Calculation |
|---------------|-------------|
| `total_release_count` | Count of decisions == `release` |
| `total_hold_count` | Count of decisions == `hold` |
| `total_escalate_count` | Count of decisions == `escalate` |
| `total_release_amount_usd` | Sum of `requested_release_amount_usd` for `release` decisions |
| `total_hold_amount_usd` | Sum of `requested_release_amount_usd` for `hold` decisions |
| `total_escalate_amount_usd` | Sum of `requested_release_amount_usd` for `escalate` decisions |

Ensure these arithmetic totals are computed independently and match the individual line items.

---

## 9. Pitfalls & Cautions

1. **Do not trust stale snapshots** — Always query current API state; never answer solely from CSV or cached JSON.
2. **Vendor ID vs. Business ID** — The API uses `vendor_id`; the batch may reference `business_id`. Map carefully.
3. **Date comparisons** — Use ISO-8601 string comparison or proper date parsing. "Expired as of 2025-06-01" means expiration date < 2025-06-01.
4. **Bank last-4 matching** — For account-change reviews, explicitly confirm the current API bank last-4 matches the `requested_bank_last4`.
5. **Missing API fields** — If an endpoint returns `null` or omits a required field, treat as missing evidence → default to `hold` or `escalate`.
6. **Do not brute-force endpoints** — Use only the endpoint patterns listed in the prompt and this SOP.
7. **Self-contained reasoning** — Future test solvers should not reference files outside their own solver attempt directory.

---

## 10. Quick Reference Checklist

Before submitting any batch review:
- [ ] All target IDs queried from API
- [ ] Decisions are one of: `release`, `hold`, `escalate`
- [ ] ID lists sorted ascending
- [ ] Currency amounts rounded to 2 decimals
- [ ] Summary counts and totals computed and cross-checked
- [ ] Reasoning cites specific API evidence
- [ ] Answer template schema matches the provided template exactly
```
