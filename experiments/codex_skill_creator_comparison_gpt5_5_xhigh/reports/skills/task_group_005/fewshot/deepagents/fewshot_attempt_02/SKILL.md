---
name: finance-api-controls
description: "Solve finance-control tasks that combine local JSON/CSV payload scopes with a runner-provided ERP/compliance API. Use for reimbursement or AP close batches, stale AP export refresh checks, vendor onboarding or account-change payment release reviews, and prepaid schedule-to-GL reconciliations requiring strict JSON output."
---

# Finance API Controls

## Operating Rules

Use the local prompt and payloads for scope, dates, templates, candidate IDs, and stale context. Use the current ERP/compliance API as the system of record for claims, AP bills, payments, vendors, compliance, prepaid invoices, GL balances, and close logs.

Start by reading every local input file. Extract required output keys, ordering rules, precision, candidate IDs, review dates, periods, entities, accounts, and any variance thresholds. Return only JSON when the prompt or template requires it.

Use the runner-provided base URL. Call `/endpoints` first when endpoint spelling is uncertain. The API supports exact-match query parameters by field name plus `limit` and `offset`.

Use `scripts/api_collect.py` to gather scoped API records:

```bash
python scripts/api_collect.py "$TASK_ENV_BASE_URL" --claims CLAIM_ID ...
python scripts/api_collect.py "$TASK_ENV_BASE_URL" --businesses BUSINESS_ID ...
python scripts/api_collect.py "$TASK_ENV_BASE_URL" --prepaids INVOICE_ID ... --entity "ENTITY" --period YYYY-MM --accounts ACCOUNT ...
```

## Reimbursement And AP Close

For each candidate claim, fetch the claim, all AP bills with that `claim_id`, and payments for each bill. Treat local AP snapshots as context only.

Use current records to classify:

- A valid reimbursement bill has the exact claim ID, non-void/non-draft status, matching currency, matching claim amount, and matching vendor when the claim has a vendor. Ignore stale, void, draft, amount-mismatched, or vendor-mismatched bills.
- A claim is settled only when a valid paid bill has cleared payment evidence for the bill amount. Scheduled or processing payments are in flight; they do not settle the claim and do not reduce open balance unless the template explicitly says otherwise.
- A claim can remain payable/eligible when the current claim is approved, support is acceptable for the prompt, and a valid unpaid AP bill remains open or in flight.
- A claim is blocked/not ready when the claim is not approved, required support or receipt status is unresolved, no valid AP link exists, or the only current AP evidence is void/mismatched/stale.

When stale snapshot correction fields are requested, compare each stale row to the current API record:

- `block_unapproved_claim`: current claim is not approved for release.
- `ignore_void_bill`: stale or current linked bill is void and no valid replacement exists.
- `exclude_amount_or_vendor_mismatch`: linked bill does not match claim amount or vendor.
- `replace_with_matched_paid_bill`: a stale open row is superseded by a valid paid bill with cleared payment.
- `mark_in_flight_payment`: a valid bill has only scheduled or processing payment evidence.
- `current_snapshot_ok`: no correction is needed.

Compute AP open balances from valid current bills minus cleared payments only. For close-log fields, query close logs and include only log IDs that support the relevant AP close period or refresh event; do not include unrelated GL, Treasury, Prepaid, or Compliance logs.

Set batch status using the template's precedence. Common patterns are: blocked if any unresolved blocked item exists; otherwise open/refresh-needed if valid payables or stale corrections remain; otherwise ready.

## Vendor Onboarding

For each business ID, fetch the compliance object and, when needed, its ownership, registry, screening, bank, and vendor record.

Count reportable UBOs as unique owner names with `ownership_pct >= 25`. Deduplicate repeated names before counting.

Build hard-stop flags from current evidence:

- `bank_closed`: bank account status is closed.
- `bank_name_mismatch`: bank account status is name mismatch.
- `confirmed_pep`: screening has confirmed PEP.
- `expired_license`: license expiry is before the onboarding as-of date and the license is not merely missing from required documents.
- `missing_required_documents`: `missing_fields` is non-empty.
- `sanctions_confirmed`: sanctions status is confirmed or positive.
- `screening_not_run`: PEP or sanctions screening is not run.
- `shell_company_suspected`: ownership indicates shell-company suspicion.
- `vendor_on_hold`: vendor status is on hold.

Sort each flag list alphabetically. Derive decisions; do not copy source `review_status`. Approve only when no hard-stop flags apply. Use `awaiting_information` for remediable information gaps such as missing documents or screening not run without a more severe stop. Use `escalate` for sanctions, confirmed PEP, shell-company suspicion, bank closed/name mismatch, vendor hold, or expired license hard stops.

Follow-up business IDs are businesses not approved or businesses with any hard-stop flag. Overall release is true only when every business is approved.

## Account-Change Payment Release

For payment release after vendor account changes, combine each local ticket with current vendor and compliance evidence. Verify the ticket vendor ID, requested bank last four, compliance bank status, tax evidence, license expiry, screening, vendor status, missing fields, and risk score as of the review date.

Populate lists as follows:

- `bank_mismatch_ids`: compliance `bank_account_status` is `name_mismatch`.
- `invalid_tax_ids`: registry tax ID is missing, malformed for the task's pattern, or differs from the vendor tax ID.
- `expired_license_ids`: registry license expiry is before the review date.
- `risk_score_override_flags`: risk score is at or above the template threshold; use 70 when the prompt does not state another threshold.
- `review_queue_ids`: any business with bank not verified, bank last-four mismatch, invalid tax, expired license, missing required fields, screening not clear or not run, PEP concern, sanctions concern, shell suspicion, inactive/on-hold vendor, or risk override.

Decision posture:

- `release`: no review queue condition.
- `hold`: remediable AP/compliance issues such as bank mismatch/closed, missing documents, expired license, screening not run, bank last-four mismatch, or risk override without severe integrity evidence.
- `escalate`: invalid tax evidence, sanctions concern, confirmed or possible PEP, shell-company suspicion, vendor on hold/inactive for compliance reasons, or multiple severe control failures.

Sort ID lists ascending by business ID unless the template specifies a different order.

## Prepaid Close

Use the local scope for selected prepaid invoice IDs, entity, close period, accounts, and variance threshold. Fetch each selected invoice and the GL ending balance for each scoped account.

For invoice calculations:

- Preserve `selected_invoice_ids` and `invoice_results` order from the local scope.
- Use the record's `monthly_amortization` rather than recomputing a monthly amount from original amount.
- Count amortization months inclusively from the service-start month through the close period, capped at the service-end month. Use zero months when service starts after the close period.
- `march_amortization` or period amortization is the monthly amount only when the close period falls within the service term; otherwise it is zero.
- `cumulative_amortization_through_march` or through-period cumulative is monthly amount times counted months, rounded to two decimals and not below zero.
- `ending_balance` is original amount minus cumulative amortization, rounded to two decimals and not below zero unless the template requires preserving a rounding residual.
- `default_missing_term_flag` is true for flags indicating missing contract dates, default terms, or missing term evidence.
- `exception_flag` is true when any invoice data-quality flag is present.

For account rollups, sum only selected invoices for the scoped account. Compute `variance_amount` as schedule ending balance minus GL ending balance. Set `variance_flag` when absolute variance exceeds the scope/template threshold, or when the template defines any nonzero variance as a flag. Use `requires_reconciliation` for material variance or default/missing-term issues, `variance_review` for immaterial nonzero variance or data-quality review, and `reconciled` only when schedule, GL, and invoice flags are clean.

## Output Checks

Before final output, parse the JSON locally. Verify top-level keys, enum values, ordering, counts, and numeric precision against the template. Do not include narrative text outside the JSON when the task asks for JSON only.
