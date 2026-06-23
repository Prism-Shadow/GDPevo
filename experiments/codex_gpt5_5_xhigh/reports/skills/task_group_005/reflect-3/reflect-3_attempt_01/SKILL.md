---
name: reflect-3_attempt_01
description: Solve task_group_005 ERP finance, AP, prepaid, and compliance release-control tasks using current API evidence and strict JSON schemas.
---

# Task Group 005 Reflect Skill

Use this workflow for ERP finance-control tasks that combine staged task payloads with the shared JSON API. Treat local payloads as scope, stale context, or schema instructions; treat the API as the system of record unless the prompt explicitly says otherwise.

## Core Workflow

1. Read the prompt, answer template, and any scoped payload first. Copy required IDs, dates, accounts, ordering rules, enum values, and precision rules from those files.
2. Query the shared API records needed for each scoped object. Prefer exact-match parameters for IDs and use the canonical `/api/...` endpoints when both aliases exist.
3. Reconcile current evidence, not stale exports or source review labels alone. A stale local row can explain what changed, but current claim, bill, payment, vendor, compliance, GL, and close-log records decide the answer.
4. Build the output directly against the answer template. Preserve required top-level keys, enum spellings, ordering rules, and two-decimal USD amounts.
5. Before finishing, re-check every list for the requested sort order and every numeric field for sign convention, especially variances defined as schedule minus GL.

## AP Claims And Reimbursements

For each claim, fetch the claim, AP bills by `claim_id`, payments by each `bill_id`, and close logs when the template asks for them.

Classify a claim as payable or eligible only when the current claim is approved, required support is adequate, vendor evidence is usable, and there is a non-void AP bill that matches the claim amount, vendor, currency, and reimbursement context. Paid claims require a matching paid AP bill and a cleared payment for the claim amount. Do not let an unrelated scheduled bill or stale bill override a matched paid bill.

Block or mark not ready when the current claim is unapproved, still needs receipt/support cleanup, lacks the vendor/AP link needed for release, has no matching bill, has only a void bill, or has amount/vendor/account evidence that does not match the claim. Keep owner cleanup issues separate from AP/payment evidence issues when the schema gives separate fields.

For balances, start from current matching AP bills. Subtract cleared payments. Ignore voided rows and stale rows that have been replaced by better current evidence. Treat processing or scheduled payments as in-flight evidence: flag them with the schema's in-flight enum when available, and decide whether the item can remain based on the prompt's batch purpose. A close-review batch may keep an in-flight open payable; a payment-send batch may need to avoid re-sending it.

Common stale snapshot correction mapping:

- `mark_in_flight_payment`: the stale row missed a current processing/scheduled payment.
- `replace_with_matched_paid_bill`: a stale bill is superseded by a matching paid bill and cleared payment.
- `exclude_amount_or_vendor_mismatch`: the AP row does not match the claim amount or vendor evidence.
- `ignore_void_bill`: the only current AP row is voided or the stale row is now void.
- `block_unapproved_claim`: the current claim is not approved for AP release.
- `current_snapshot_ok`: current API evidence still matches the staged snapshot and needs no correction.

Use `blocked` when any scoped claim is blocked by claim/support/AP defects. Use an open-payables or refresh status only when there are no true blockers and the remaining work is payment or export freshness.

## Vendor Compliance And Account-Change Reviews

For each business, fetch compliance profile, ownership, registry, screening, bank, risk, and the linked vendor record. Use the task's `as_of_date` or review date for date comparisons, not today's date.

Evidence rules:

- Bank name mismatch comes only from `bank_account_status: "name_mismatch"`. Closed bank status is also a release blocker, but keep it distinct from name mismatch.
- Expired licenses are licenses with `license_expiry` before the review/as-of date.
- Risk score override flags are inclusive: `risk_score >= 70`.
- Count reportable UBOs as unique owner names at or above the threshold implied by the task, normally 25%. Do not double count duplicate rows for the same name.
- Treat confirmed sanctions, confirmed PEP, shell-company suspicion, vendor-on-hold status, missing required documents, expired licenses, screening not run, bank closed, and bank name mismatch as release-control evidence when the schema exposes matching flags.
- For `invalid_tax_ids`, follow the field wording. Include malformed or official profile/registry tax evidence. Do not automatically include a business solely because the linked vendor master has a different tax value unless the prompt or schema says vendor mismatch belongs in that list.

Decision posture:

- `release` or `approve` only when bank, tax, license, screening, vendor status, and risk evidence are clean. A clean record whose source `review_status` is merely `in_review` can still release when the task asks for release-control decisions rather than a copy of the source label.
- `hold` or `awaiting_information` for remediable missing evidence, expired license, not-run screening, closed bank, or incomplete documentation when there is no severe escalation trigger.
- `escalate` for confirmed PEP, confirmed sanctions, shell-company suspicion, vendor on hold, malformed/invalid tax evidence, bank-name mismatch in an account-change payment release, or risk score override.
- Review queue lists should normally contain every non-release business and exclude clean release businesses.

## Prepaid Close Reconciliations

Use only the scoped invoice IDs and scoped accounts. Fetch prepaid invoices and GL balances for the close period and entity.

Use the invoice `monthly_amortization` value as represented in the record. Count whole calendar service months through the close period when the close period falls between `service_start` and `service_end`; mid-month starts still count as the service-start month unless the prompt gives a different convention. Do not recompute monthly amortization from original amount, and do not cap away small final-month residuals caused by rounded monthly amounts.

For each invoice:

- Current-period amortization is the record's monthly amortization when the period is in the service window; otherwise it is zero.
- Cumulative amortization through the period is monthly amortization times recognized months, rounded to two decimals.
- Ending balance is original amount minus cumulative amortization, rounded to two decimals.
- `default_missing_term_flag` is for missing/defaulted contract term evidence, such as `missing_contract_dates`.
- `exception_flag` is true for any invoice data-quality flag, including rounded amounts.

For account rollups, sum original amount, current-period amortization, cumulative amortization, and ending balance from the selected invoices only. Variance is `schedule_ending_balance - gl_ending_balance`. Set `variance_flag` from the absolute threshold in the payload. Use `requires_reconciliation` when a material variance exists; use `variance_review` for non-material variance or exception review; use `reconciled` only when the account is clean.

## Output Discipline

Return JSON only when requested. Sort business ID and claim ID lists ascending by ID unless the template says to preserve payload order. Preserve scoped invoice order for invoice result lists when requested. Use empty lists rather than omitted keys, and include zero balances as `0.00`-equivalent JSON numbers.
