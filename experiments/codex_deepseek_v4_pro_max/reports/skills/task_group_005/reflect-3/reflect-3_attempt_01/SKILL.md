 # ERP Finance Close & Compliance Review Skill

 ## Overview
 This skill handles finance-operations review tasks that reconcile expense claims, AP bills,
 payments, prepaid amortization schedules, vendor compliance, and account-change risk against
 a shared ERP/compliance JSON API. Every task follows the same core loop: read the prompt and
 supplied payloads, query live API endpoints for current state, cross-reference records, classify
 entities according to the answer template, and return a single JSON result.

 ## When to use this skill
 - Reimbursement-to-AP close batch reviews
 - Vendor onboarding finance-risk release calls
 - Prepaid-expense close checks with GL reconciliation
 - Stale AP snapshot reconciliation against current ERP data
 - Payment-release risk reviews after account-change events
 - Any task that asks you to classify claim/business/invoice lists using a shared finance API

 ## Core workflow (apply to every task)

 ### 1. Absorb the inputs
 - Read the task `prompt.txt` carefully. It tells you which entity IDs to review, what the
   decision framework is, and where to find the answer template.
 - Read every payload file referenced in the prompt (batch JSON, snapshot CSV, scope file, etc.).
   Treat snapshot/payload files as **context** — the live API is always the system of record.
 - Read the `answer_template.json` to understand the exact output schema, allowed enum values,
   required keys, sort orders, numeric precision, and unit conventions (e.g. USD cents).
 - Note any hard constraints: sort orders, deduplication rules, currency precision, date formats.

 ### 2. Query the live API exhaustively
 The API base URL is `<TASK_ENV_BASE_URL>` supplied by the runner. Use it for every call.
 Common endpoints (append to base URL):

 | Endpoint | Purpose |
 |---|---|
 | `/api/claims` or `/api/claims/{claim_id}` | Expense claim details |
 | `/api/ap/bills` | AP bill records (filter by `claim_id`) |
 | `/api/ap/payments` | Payment records (filter by `bill_id`) |
 | `/api/vendors` | Vendor master data (filter by `vendor_id`) |
 | `/api/compliance/objects` | Consolidated compliance view per business |
 | `/api/compliance/ownership/{business_id}` | UBO ownership details |
 | `/api/compliance/registry/{business_id}` | Business registration & license |
 | `/api/compliance/screening/{business_id}` | PEP & sanctions screening |
 | `/api/compliance/bank/{business_id}` | Bank account verification status |
 | `/api/prepaids/invoices` | Prepaid invoice schedules |
 | `/api/prepaids/gl-balances` | GL ending balances by account/period |
 | `/api/close/logs` | Close review log entries |

 - Collection endpoints accept `?limit=` and `?offset=` for pagination.
 - Collection endpoints accept exact-match query parameters by field name (e.g. `?claim_id=CLM-…`
   or `?business_id=BUS-…` or `?vendor_id=VEN-…`).
 - Always pull enough pages to see every record relevant to the batch. Do not assume the first
   page covers everything.

 ### 3. Reconcile and classify
 - **Claims vs Bills vs Payments**: Match bills to claims by `claim_id`. Match payments to bills
   by `bill_id`. A claim is "paid" only when there is a bill whose amount matches the claim and
   a cleared payment whose amount matches the bill. Watch for multiple bills per claim (pick the
   one that matches the claim amount) and void bills (ignore).
 - **Amount mismatches**: When a bill amount differs from the claim amount, flag the claim as
   blocked/not-ready and record the correction.
 - **Vendor mismatches**: When a claim's `vendor_id` is null or differs from the bill's vendor,
   flag for remediation.
 - **Prepaid amortization**: Use straight-line monthly amortization as recorded. Count whole
   months from `service_start` through the close period. `monthly_amortization × months_elapsed`
   gives cumulative amortization. `original_amount - cumulative` is schedule ending balance.
   Compare schedule totals against GL ending balances for the same account and period.
 - **Data quality flags**: Treat `missing_contract_dates` as a default/missing-term flag. Do not
   treat `rounded_amount` alone as an exception. True exceptions come from un-reconcilable
   amounts or structural data problems, not cosmetic flags.
 - **Compliance risk**: Check bank account status (`closed`, `name_mismatch`), license expiry
   (before the review/as-of date), PEP status, sanctions screening, shell-company suspicion,
   missing required documents, vendor hold status, and risk score thresholds.
 - **Tax ID validation**: Compare the tax ID from the registry against the vendor record. Flag
   mismatches and obviously malformed IDs (containing non-standard characters like `X`).

 ### 4. Populate the answer template
 - Fill every required key in the exact order and shape defined by the template.
 - Sort all ID lists as specified (usually ascending alphanumeric).
 - Report currency amounts to the precision declared in the template (typically 2 decimal places).
 - Use the exact allowed enum values — do not invent new statuses.
 - For boolean flags, use JSON `true`/`false` (not strings).
 - When a template field is `list[string]` and no items match, use an empty list `[]` — never
   `null` or omit the key.
 - Double-check that every required business ID, claim ID, or invoice ID from the batch appears
   in the output.

 ### 5. Validate before returning
 - Verify all lists are sorted as required.
 - Verify arithmetic: rollup totals should equal the sum of individual line items.
 - Verify variance calculations: `schedule_ending_balance - gl_ending_balance`.
 - Verify that every entity in the input batch has a corresponding entry in the output.
 - Return only the JSON object — no narrative text, markdown fences, or extra commentary.

 ## Decision frameworks (by task type)

 ### Expense claim close review
 | Claim state | Classification |
 |---|---|
 | Paid: matching bill + cleared payment for claim amount | `paid_claim_ids` |
 | Approved, bill amount matches, no cleared payment yet | `payable_claim_ids` |
 | Approved but bill missing/void/mismatched, or claim not approved | `blocked_claim_ids` |
 | Blocked and needs owner cleanup or AP-link fix | `crm_required_claim_ids` |

 ### Vendor onboarding / compliance review
 - `approve`: No hard-stop flags, license valid, bank verified, screening clear.
 - `awaiting_information`: Minor issues that can be resolved with follow-up (e.g. only an
   expired license with no other red flags).
 - `escalate`: Multiple red flags, confirmed PEP, closed bank, sanctions issues, shell company
   suspicion, bank name mismatch combined with other problems.

 ### Account-change payment release
 - `release`: Clean compliance, verified bank, valid license, risk score under threshold.
 - `hold`: Moderate concerns (bank name mismatch, moderately elevated risk, sanctions not run)
   that need AP/compliance review before funds move.
 - `escalate`: Severe issues (closed bank, expired license + PEP hit, tax ID mismatch, vendor
   on hold) requiring immediate compliance intervention.

 ## Important conventions
 - **System of record**: The live API always takes precedence over local payload files.
 - **Void bills**: Treat as zero-value — they do not create an open AP balance.
 - **Partial receipt**: A claim with `receipt_status: "partial"` is a risk signal but does not
   by itself block the claim; combine with other signals.
 - **Payment in flight**: A payment with status `processing` or `scheduled` is not yet settled
   but does confirm the bill is in the payment pipeline.
 - **GL reconciliation**: A large negative variance (GL much higher than schedule) suggests
   invoices exist in the GL that are not in the selected scope — flag as `requires_reconciliation`.
   A positive variance (schedule higher) suggests the schedule may be overstated or the GL is
   understated — flag as `variance_review` or `requires_reconciliation` depending on magnitude.
 - **UBO reporting threshold**: Count unique beneficial-owner names where ownership percentage
   meets or exceeds the applicable regulatory threshold (typically 25%).
