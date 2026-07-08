# Reflect-3 Finance Reconciliation Skill

Use this skill for task_group_005 finance-operations tasks that require a JSON answer from the shared ERP/compliance API plus a local scoped payload.

## Core Workflow

1. Treat local payloads as scope and context, not the source of truth. Pull current records from the runner-provided ERP API for every scoped ID.
2. Read the answer template first and mirror its keys, enum values, ordering rules, and numeric precision exactly.
3. Query only the object families needed by the prompt:
   - Claims/AP: current claims, AP bills, AP payments, vendors, close logs when requested.
   - Compliance/vendor: profile, ownership, registry, screening, bank, risk, vendor master.
   - Prepaids: scoped prepaid invoices and period/entity GL balances.
4. Reconcile from current evidence, then format. Do not copy review/status fields blindly when objective evidence contradicts them.
5. Sort ID lists ascending unless the template says to preserve input order. Report money as two-decimal USD numbers unless the template says otherwise.

## Reimbursement And AP Batch Rules

- A claim is releasable/payable only when the current claim is approved or otherwise settled, support is sufficient for the requested posture, and a current AP bill matches the claim ID, amount, currency, and vendor where available.
- A claim is paid/settled only with a current paid AP bill and a cleared payment for the matched amount. A claim status alone is not enough.
- Valid open AP balance is the matched non-void AP bill amount minus cleared payments. Scheduled or processing payments are in flight and do not reduce the cleared open balance.
- Ignore stale AP rows when a current matched bill/payment exists. Void bills do not create open AP balance. Amount or vendor mismatches should be excluded and routed for cleanup.
- Paid and cleared reimbursements may be eligible in stale-export refresh tasks; when a schema separates paid claims from payable claims, keep that distinction.
- Use the schema's correction enum consistently:
  - in-flight payment for matched bills with non-cleared payment activity,
  - matched paid bill for stale rows replaced by current paid/cleared evidence,
  - mismatch exclusion for amount/vendor mismatches,
  - void-bill ignore for voided AP rows,
  - unapproved-claim block for claims whose current case status is not releasable.
- Batch posture is blocked when any scoped item has a current claim, support, bill, or vendor/AP-link blocker. Use the intermediate refresh/open-payable status only when the remaining issues are stale export refresh or valid open/in-flight AP work without hard blockers.
- If close logs are requested, include current unresolved logs tied to the relevant account, area, or stale-export issue; do not include closed logs just because their wording resembles the task.

## Compliance And Vendor Release Rules

- Pull compliance profile, ownership, registry, screening, bank, risk, and vendor master for each business.
- Count reportable UBOs as unique owner names with ownership at or above 25%. Deduplicate repeated names before counting.
- Hard stop flags come from objective fields:
  - `bank_closed` from closed bank status.
  - `bank_name_mismatch` from name-mismatch bank status.
  - `confirmed_pep` from confirmed PEP screening.
  - `sanctions_confirmed` from confirmed sanctions matches.
  - `screening_not_run` when required PEP or sanctions screening was not run.
  - `expired_license` when registry license expiry is before the as-of date.
  - `missing_required_documents` when required profile fields are missing.
  - `shell_company_suspected` from ownership evidence.
  - `vendor_on_hold` from vendor master hold status.
- Possible PEP/sanctions statuses are review signals, not confirmed-stop flags unless the template explicitly treats them as stops.
- Tax IDs are invalid when they are malformed, placeholder-like, or inconsistent with the linked vendor master for a payment-release decision.
- Risk scores at or above a stated override threshold, commonly 70, should be surfaced even if the source review status says approved.
- Release only when bank, tax, license, screening, vendor status, and risk evidence all pass. Escalate confirmed severe issues, multiple hard stops, vendor holds, closed banks, or bank mismatches combined with high risk/invalid tax. Hold isolated remediable gaps that need AP/compliance review before release.
- A clean record with an in-progress review status can still be released when the task asks for release control based on current objective evidence and no blocker remains.

## Prepaid Close Rules

- Use only the invoice IDs and accounts in the local scope payload.
- Use each invoice's stored `monthly_amortization`; do not recompute a perfect monthly amount from original amount and dates.
- For the close period, count a full amortization month when the service period overlaps that calendar month. Cumulative amortization is stored monthly amortization times the number of active months through the close period, limited to months in the service term.
- Do not force small residuals to zero when they arise from the stored monthly schedule. Ending balance is original amount minus cumulative amortization, rounded to two decimals.
- Roll up only selected invoices by account. Variance is schedule ending balance minus the GL ending balance for the same entity, account, and period.
- Apply the absolute variance threshold from the payload. Use `variance_review` for material GL variance without blocking schedule defects, `requires_reconciliation` when default/missing-term or other blocking data-quality issues exist, and `reconciled` only when both schedule and GL evidence clear.
- `default_missing_term` applies to missing/defaulted contract-term data. Invoice exception flags should follow source data-quality flags, including rounded-amount flags when the template asks for invoice-level data-quality exceptions.

## Output Self-Check

Before returning JSON, verify:

- Every scoped ID appears in required per-ID objects.
- Lists follow the requested ordering.
- Currency values are rounded to two decimals after summing.
- Enum strings exactly match the template.
- No narrative text appears outside the JSON answer.
