```markdown
# Skill: Finance & AP Operations API-Based Decision Tasks

## 1. Overview
Tasks in this group require reading an input payload (JSON or CSV), querying a shared read-only REST API, applying finance / control / risk rules, and producing a strictly formatted JSON answer.

## 2. API Reference
- **Base URL:** `http://localhost:8000` (documented in `environment_access.md`)
- **Pattern:** `GET /{collection}` returns all records; `GET /{collection}/{id}` returns a single record.
- **Collections commonly used:**
  - `/vendors` – `vendor_name`, `vendor_id`, etc.
  - `/businesses` – business entity records
  - `/invoices` – `status`, `amount`, `early_payment_discount_rate`, etc.
  - `/bank_accounts` – `status`, `verification_level`, `account_number` / `last4`, `vendor_id`
  - `/gl_accounts` – chart of accounts
  - `/compliance_flags` – `status` (`open` / `closed`), `vendor_id`
  - `/tax_records` – `status`, `vendor_id`
  - `/licenses` – `expiration_date`, `vendor_id`
  - `/screening_results` – `list_name`, `status` (`hit` / `clear`), `tax_id`, `vendor_id`
  - `/risk_scores` – numeric `score`, `vendor_id`
  - `/payments`, `/transactions`, `/journal_entries` – available when ledger data is needed

### Performance Tip
For batched lookups, fetch the full collection once (e.g., `GET /invoices`) and build an in-memory lookup dictionary keyed by ID (or by `vendor_id`, `business_id`, etc.). Avoid issuing individual GETs in a loop.

## 3. Input & Payload Handling
- The prompt names the payload file (e.g., `onboarding_batch.json`, `prepaid_close_scope.json`, `stale_ap_snapshot.csv`).
- Load it from `input/payloads/` inside the solver attempt directory.
- Use the provided `answer_template.json` **only** as the output schema guide.

## 4. Output Conventions
| Concern | Rule |
|---|---|
| **Format** | JSON object whose root keys match `answer_template.json`. |
| **Sorting** | Sort output arrays in **ascending lexicographic order** by the key specified in the prompt (`invoice_id`, `request_id`, `contract_id`, `ap_record_id`, `business_id`, etc.). If the sort key differs from the unique record ID, follow the prompt exactly. |
| **Rounding** | Round monetary amounts to exactly **2 decimal places** using standard half-up rounding when the prompt requires it. Do **not** round values used for threshold comparisons unless instructed. |
| **Nulls** | Use JSON `null` (not the string `"null"`) for optional fields when there is no value (e.g., `reason: null` on auto-approval). |
| **Omissions** | Exclude records entirely when the prompt says to omit them (e.g., zero-adjustment journal entries). |
| **Amount equality** | In journal-entry objects, ensure `debit_amount == credit_amount == abs(adjustment_amount)`. |

## 5. Decision & Control Rules
- **Rule precedence:** Apply rules **in the exact order given in the prompt**. The first matching condition determines the outcome; do not fall through to later rules.
- **Thresholds:** Use strict inequalities exactly as written (e.g., `> 50,000`, `<= 10,000`, `> 75`).
- **Vendor existence checks:** Compare the payload’s `vendor_name` against `/vendors` records. If no record has a matching `vendor_name`, the vendor does not exist. Match exactly as provided; if no exact match is found, a case-normalized comparison may be needed.
- **Sanctioned countries:** Use the country list supplied in the current prompt (commonly includes Iran, North Korea, Syria, Cuba, Russia). Do not assume a hard-coded global list.
- **Screening / OFAC:**
  - `list_name == "OFAC SDN"` and `status == "hit"` → **escalate** (or deny / manual review as specified).
  - Any other `list_name` with `status == "hit"` → **hold**.
- **Risk scores:** A score greater than the prompt’s threshold (commonly `> 75`) → **escalate**.
- **Compliance flags:** Any flag with `status == "open"` for the vendor → **hold**.
- **Tax records:** `status != "active"` → **hold**.
- **Licenses:** Compare `expiration_date` against the relevant review date. Expired or missing → **hold**. Treat a license that expires on the review date as expired unless the prompt states otherwise.
- **Bank accounts:** For a given vendor and `requested_bank_last4`, locate the account whose `account_number` ends with those four digits **and** whose `vendor_id` matches. It must satisfy `status == "active"` **and** `verification_level == "verified"` to pass; otherwise → **hold**.
- **Priority / urgency:** Does **not** override risk or compliance rules unless the prompt explicitly says otherwise.

## 6. Computation Rules (Prepaid Amortization / Journal Entries)
When a task requires closing or adjusting prepaid contracts:
1. `remaining_months = max(0, months_between(review_date, end_date))`
2. `monthly_amortization = total_prepaid_amount / original_term_months`
3. `required_prepaid_balance = remaining_months * monthly_amortization`
4. `adjustment_amount = required_prepaid_balance - current_prepaid_balance`

**Booking:**
- `adjustment_amount > 0` → Debit Prepaid Expense (use the GL account ID given in the prompt), Credit AP Liability.
- `adjustment_amount < 0` → Debit AP Liability, Credit Prepaid Expense.
- `adjustment_amount == 0` → Omit from output.

**Caution on `months_between`:** If the prompt does not define the exact algorithm, compute the integer number of **full calendar months** remaining. A robust approach is:
```
months = (end_year - review_year) * 12 + (end_month - review_month)
if review_day > end_day: months -= 1
remaining_months = max(0, months)
```

## 7. Common Pitfalls
1. **Lexicographic vs. numeric sort:** IDs such as `INV-2` and `INV-10` sort differently by string comparison. Always use standard string comparison unless numeric sorting is explicitly required.
2. **N+1 API calls:** Querying `/invoices/{id}` per record is slow and may time out. Fetch the collection once and index it.
3. **Wrong rule order:** In multi-rule tasks (especially risk review), evaluating a lower-priority condition first yields the wrong decision. Follow the numbered precedence in the prompt exactly.
4. **Case sensitivity:** Fields like `"active"`, `"open"`, or `"hit"` are case-sensitive. Match exactly.
5. **Bank account matching by last4 alone:** Always constrain the search to the correct `vendor_id` to avoid collisions.
6. **Returning the empty template:** Populate the arrays in `answer_template.json`; do not submit the empty skeleton.
7. **CSV payloads:** Some inputs are CSV files (e.g., `stale_ap_snapshot.csv`). Parse with a standard CSV reader and map header rows to dictionaries.
8. **Date boundary errors:** Parse dates into date objects before comparing. Avoid string comparison of ISO dates with variable zero-padding.
9. **Failure tokens:** When a prompt requires a specific reason token (e.g., `VENDOR_EXISTS`, `GL_MISSING`, `OFAC_HIT`), output the exact token string. Use `null` when there is no failure.
10. **Free-text summaries:** Some outputs require a `notes` field summarizing evidence. Build the summary from the actual API values inspected during rule evaluation.

## 8. Recommended Solver Workflow
1. Read the prompt and identify the payload filename, required API collections, and output schema.
2. Load the payload from `input/payloads/`.
3. Fetch each required API collection once and build lookup maps by the relevant key.
4. Iterate over payload records, applying control rules in the exact order specified.
5. Construct output objects, omitting any records the prompt says to skip.
6. Sort the final array in ascending lexicographic order by the key named in the prompt.
7. Apply rounding (half-up to 2 decimals) only where required.
8. Validate that debit/credit amounts balance, that nulls are real JSON `null`, and that the root object matches `answer_template.json`.
9. Write the final JSON answer.
```
