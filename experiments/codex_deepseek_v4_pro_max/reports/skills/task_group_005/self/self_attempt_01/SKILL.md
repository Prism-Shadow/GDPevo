## When to Use

Use this skill when working with the task_group_005 ERP/Finance shared API to complete finance operations tasks including: claims-to-AP reconciliation, vendor onboarding compliance review, prepaid schedule close, account-change payment release review, and similar finance-risk or close-checklist workflows. The skill codifies the reusable data-retrieval patterns, decision frameworks, and output conventions observed across the task_group_005 training suite.

## Environment & API

### Base URL

The shared API base URL is always provided by the runner as `<TASK_ENV_BASE_URL>`. Substitute this placeholder before issuing any HTTP request. There is no authentication.

### Endpoints

All endpoints accept `limit` and `offset` integer query parameters for pagination. Collection endpoints accept exact-match query parameters by field name.

| Data Domain | Collection Endpoint | Detail Endpoint |
|---|---|---|
| Claims | `/claims` or `/api/claims` | `/api/claims/{claim_id}` |
| AP Bills | `/bills` or `/api/ap/bills` | — |
| AP Payments | `/payments` or `/api/ap/payments` | — |
| AP Aging | `/api/ap/aging` | — |
| Vendors | `/vendors` or `/api/vendors` | — |
| Compliance Objects | `/compliance/objects` or `/api/compliance/objects` | — |
| Compliance Ownership (UBO) | — | `/api/compliance/ownership/{business_id}` |
| Compliance Registry | — | `/api/compliance/registry/{business_id}` |
| Compliance Screening | — | `/api/compliance/screening/{business_id}` |
| Compliance Bank | — | `/api/compliance/bank/{business_id}` |
| Prepaid Invoices | `/prepaids/invoices` or `/api/prepaids/invoices` | — |
| GL Balances | `/gl/balances` or `/api/prepaids/gl-balances` | — |
| Close Logs | `/close/logs` or `/api/close/logs` | — |

No POST endpoints are available. All data retrieval is read-only via GET.

### Query Mechanics

- Collection endpoints: append `?field_name=value` for exact-match filters. Use `&limit=N&offset=M` for pagination.
- Detail endpoints: replace `{claim_id}` or `{business_id}` with the identifier string directly in the path.
- When fetching many items, iterate with offset until the returned list is shorter than the limit or empty.

## Input & Output Conventions

### Task Scope

The task prompt always identifies the candidate scope: a list of claim IDs, business IDs, invoice IDs, or similar identifiers. A local payload file (JSON or CSV) may supplement the scope with batch metadata, stale snapshots, or review context — but the API is always the system of record. Treat local payloads as context, not authoritative state.

### Answer Shape

Every task supplies an `answer_template.json` in its `input/payloads/` directory. The final response must be a single JSON object that conforms exactly to that template: every required key present, every value matching the declared type, precision, ordering, and allowed values. Do not include narrative text outside the JSON.

### Currency

All monetary amounts are in USD. Precision is specified per field in the template — either whole cents (integer) or two-decimal dollars (number with precision 2). Follow the template's unit and precision exactly.

### Sorting

- Claim ID lists: ascending alphanumeric by claim ID.
- Business ID lists: ascending alphanumeric by business ID.
- Invoice ID lists: either the same order as the scope payload or ascending by invoice ID, whichever the template specifies.
- Flag/enum lists: alphabetical by enum value.
- Close log ID lists: ascending by close log ID.

## Decision Frameworks

### Claims-to-AP Reconciliation

Use this framework when classifying claims for a reimbursement or AP batch.

1. **Fetch current state.** For each candidate claim ID, retrieve the claim detail from `/api/claims/{claim_id}`. Also fetch the full AP bill and payment collections, filtering by the candidate claim IDs as needed.

2. **Match claims to bills.** Link each claim to its AP bill(s) by matching claim ID references in the bill payload. If a claim has no matching bill, it is not payable.

3. **Match bills to payments.** For each matched bill, check whether a payment exists that clears the bill amount. A payment is "cleared" when its status indicates settlement and its amount covers the bill.

4. **Classify into three buckets:**
   - **Paid:** claim has a matched bill AND a cleared payment covering the bill amount.
   - **Payable:** claim has a matched bill, no cleared payment, and the claim/bill state supports AP release (e.g., claim approved, bill not void).
   - **Blocked:** claim has no matched bill, or the claim state is not approved, or the bill is void, or the claim requires owner/CRM cleanup before AP can proceed.

5. **Distinguish CRM vs AP issues.** When a claim is blocked, determine whether the root cause is in the claim/expense case itself (CRM-required: missing approval, owner action needed, incomplete supporting documents) or in the AP link (bill missing, bill void, payment evidence gap). Populate separate output fields for CRM-required vs. general blocked claims when the template asks for this split.

6. **Compute open AP balance.** Sum bill amounts for payable claims, net of any partial payments. Report as specified (USD cents or two-decimal dollars).

7. **Set batch status:**
   - `blocked` if any claim is blocked.
   - `open_payables` if no blocked claims but unpaid payable claims remain.
   - `ready_to_close` / `ready_to_send` if all claims are paid and no blocked claims exist.

### Vendor Onboarding Compliance Review

Use this framework when reviewing business/vendor entities for onboarding or access decisions.

1. **Fetch compliance data per business.** For each business ID, retrieve:
   - Registry: `/api/compliance/registry/{business_id}`
   - Ownership (UBO): `/api/compliance/ownership/{business_id}`
   - Screening: `/api/compliance/screening/{business_id}`
   - Bank: `/api/compliance/bank/{business_id}`
   - Vendor: `/api/vendors` (filtered by vendor ID if available from registry/ownership data)

2. **Count reportable UBOs.** From the ownership endpoint response, count unique beneficial-owner names whose ownership percentage is at or above the applicable reporting threshold (typically 25%). Report as a whole number.

3. **Build hard-stop flags.** Check each data source for blocking conditions. Common flags include:
   - `sanctions_confirmed` — screening result shows confirmed sanctions match
   - `confirmed_pep` — screening result shows politically exposed person match
   - `bank_name_mismatch` — bank account name does not match registered business name
   - `bank_closed` — bank account status is closed
   - `expired_license` — business license expiry is before the review/as-of date
   - `missing_required_documents` — registry shows missing required filings or documents
   - `screening_not_run` — screening endpoint returns no result or pending status
   - `shell_company_suspected` — registry or ownership data indicates shell risk
   - `vendor_on_hold` — vendor record shows hold status

4. **Determine per-business decision:**
   - `approve` — no hard-stop flags, all compliance checks pass, documentation complete
   - `awaiting_information` — missing non-critical data or screening not yet run, but no hard-stop flags
   - `escalate` — one or more hard-stop flags present, or critical compliance failure

5. **Identify follow-up business IDs.** Any business not in `approve` state that needs additional review or information before release.

6. **Set overall release readiness.** `true` only if every business is `approve`.

### Prepaid Schedule Close

Use this framework when reconciling prepaid amortization schedules against GL balances for a period close.

1. **Fetch source data.** Retrieve prepaid invoices from `/prepaids/invoices` (or `/api/prepaids/invoices`), filtering to the scoped invoice IDs. Retrieve GL ending balances from `/gl/balances` (or `/api/prepaids/gl-balances`) for the specified accounts and period.

2. **Group invoices by account.** Each invoice belongs to exactly one GL account. Sum the period amortization and cumulative amortization for all selected invoices within each account.

3. **Compare to GL.** For each account, compute the variance between the sum of invoice-level ending balances and the GL ending balance. Flag any account where the absolute variance exceeds the configured threshold.

4. **Flag data-quality issues per invoice:**
   - `default_missing_term_flag` — invoice has no amortization term defined, or uses a default/placeholder term
   - `exception_flag` — invoice has schedule inconsistencies (e.g., negative amortization, cumulative exceeding total, missing periods)

5. **Determine account status.** Based on variance and exception counts:
   - `reconciled` — variance within threshold, no exceptions
   - `reconciled_with_exceptions` — variance within threshold, but one or more invoices have flags
   - `variance` — variance exceeds threshold

6. **Use straight-line monthly amortization** as represented in the invoice records. Report all amounts to two decimal places.

### Account-Change Payment Release Review

Use this framework when vendor payment releases must be reviewed after account-change events.

1. **Fetch vendor and compliance data.** For each target business ID, retrieve the vendor record, compliance registry, ownership, screening, and bank endpoints from the shared API.

2. **Check bank status.** Compare the bank account name on file with the registered business name. Flag any mismatch or closed-bank status. Also check the bank account last-four digits against the change ticket if one is provided.

3. **Check tax/registry validity.** Verify the tax ID is valid and not expired. Flag any business with an invalid tax ID.

4. **Check license expiry.** Compare the business license expiry date against the review/as-of date. Flag any expired licenses.

5. **Check screening results.** Review sanctions, PEP, and adverse-media screening data. Flag any confirmed hits.

6. **Assess risk score.** If the compliance data includes a risk score, flag any business at or above 70.

7. **Determine per-business decision:**
   - `release` — all checks pass, no flags
   - `hold` — one or more flags present but severity is below escalation threshold
   - `escalate` — critical flags (sanctions, closed bank, fraud indicators) present

8. **Populate flag lists.** For each flag category (bank mismatch, invalid tax, expired license, review queue, risk score override), list the business IDs in ascending order.

## General Operating Rules

1. **API is authoritative.** Always query live API data. Never rely solely on local payloads for current state. Local files provide scope and context only.

2. **Handle missing records gracefully.** If an API endpoint returns 404 or empty for an expected identifier, treat it as a data gap that may affect the decision — do not crash or skip silently.

3. **Sort all ID lists.** Every list of identifiers in the output must be sorted as specified by the answer template (almost always ascending).

4. **Match the template exactly.** Use every required key. Do not add extra keys. Use the exact allowed enum values. Match the specified precision, type, and ordering.

5. **No narrative outside JSON.** The response must be pure JSON. Do not wrap in markdown fences unless the task prompt explicitly instructs otherwise.

6. **Currency is USD.** All monetary values use USD. Follow the template's unit and precision specification per field.

7. **Iterative pagination.** When fetching collections, paginate through all results using offset/limit until fewer results than the limit are returned.

8. **Review date awareness.** When an as-of date or review date is specified, use it as the comparison date for expiry checks, effective-date checks, and period selection.
