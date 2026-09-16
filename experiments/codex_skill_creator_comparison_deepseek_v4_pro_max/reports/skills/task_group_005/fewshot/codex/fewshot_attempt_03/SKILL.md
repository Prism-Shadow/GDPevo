---
name: erp-finance-review
description: Finance close and AP operations review against a shared ERP/compliance API. Covers reimbursement-to-AP close review (claims, bills, payments), vendor onboarding compliance (UBO, PEP, sanctions, bank, license), prepaid schedule-to-GL reconciliation, stale AP batch refresh with snapshot corrections, and account-change payment release risk review. Use when Codex is asked to review claim batches, vendor onboarding, prepaid close periods, stale AP snapshots, or account-change payment releases against the ERP API. The runner supplies the API base URL as <TASK_ENV_BASE_URL>.
---

# ERP Finance Review

## Overview

Review finance close, AP, compliance, and prepaid data from a shared ERP JSON API. The runner provides the API base URL via `<TASK_ENV_BASE_URL>`. Use it for every endpoint call.

## API Endpoints

| Endpoint | Query Filters | Purpose |
|---|---|---|
| `/api/claims` | `claim_id` (repeatable) | Expense/reimbursement claims |
| `/api/ap/bills` | `claim_id`, `bill_id` | AP bills linked to claims |
| `/api/ap/payments` | `bill_id`, `vendor_id` | Payment transactions against bills |
| `/api/ap/aging` | `vendor_id` | AP aging by vendor |
| `/api/vendors` | `vendor_id` | Vendor master data |
| `/api/compliance/objects` | `business_id` (repeatable) | Merged compliance view per business |
| `/api/compliance/ownership/{business_id}` | path param | UBO ownership detail |
| `/api/compliance/registry/{business_id}` | path param | Registration, license, tax ID |
| `/api/compliance/screening/{business_id}` | path param | PEP and sanctions status |
| `/api/compliance/bank/{business_id}` | path param | Bank account verification status |
| `/api/prepaids/invoices` | `prepaid_invoice_id` (repeatable), `account` | Prepaid invoice amortization schedules |
| `/api/prepaids/gl-balances` | `account`, `period` (YYYY-MM) | GL ending balances by account/period |
| `/api/close/logs` | `claim_id`, `period`, `area` | Close-period log entries |

All list endpoints accept `limit` and `offset` for pagination. Filter parameters use exact match; repeat a parameter for multiple values.

Full field schemas are in [references/api-guide.md](references/api-guide.md). Load it when field-level detail is needed.

## General rules

- Amounts are USD with two decimals.
- Sort ID lists ascending by default. When the task provides a specific input order for a list, preserve that order; otherwise sort ascending.
- Always fetch current API data as the system of record. Do not rely on local payload snapshots as truth.
- When a bill's `claim_id` does not match a claim, or a bill amount does not match its claim amount, treat the mismatch as a blocking condition.
- Bills with status `void` are ignored for AP balance calculations.

## Workflow recipes

Detailed step-by-step instructions for each workflow are in [references/workflows.md](references/workflows.md). Load that file when starting a task:

- **Claims Reimbursement Close** — Classify a claim batch into paid, payable, and blocked using claims, bills, and payments.
- **Vendor Onboarding Compliance** — Assess release readiness using compliance ownership, registry, screening, and bank endpoints.
- **Prepaid Close Reconciliation** — Reconcile prepaid amortization schedules against GL balances for scoped accounts.
- **Stale AP Batch Refresh** — Compare a stale AP snapshot CSV against current API data with stale-row correction codes.
- **Account-Change Payment Release** — Review vendor account-change tickets against compliance and vendor data for release posture.

## Output

Return JSON only unless the prompt explicitly asks for narrative. Match the provided answer template exactly on key names, types, ordering, and enum values.
