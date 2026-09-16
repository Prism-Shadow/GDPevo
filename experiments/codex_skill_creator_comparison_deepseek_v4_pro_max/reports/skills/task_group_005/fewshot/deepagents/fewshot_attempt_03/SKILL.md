---
name: finance-close-review
description: Finance close and AP review operations against a shared ERP JSON API. Use when tasks involve reviewing expense claims against AP bills and payments, releasing vendor onboarding batches with compliance checks, reconciling prepaid invoice schedules against GL balances, reconciling stale AP snapshots against current ERP state, or reviewing account-change payment releases with compliance and risk screening. Triggered by prompts mentioning claim-AP close, reimbursement batch, vendor onboarding, prepaid close, stale AP reconciliation, or account-change payment review.
compatibility: designed for deepagents-code
---
 
# Finance Close Review
 
 ## Overview
 
 This skill covers finance close review workflows that pull data from a shared ERP JSON API and produce structured close decisions. The API exposes claims, AP bills, payments, aging, vendors, compliance objects, prepaid invoices, GL balances, and close logs.
 
 ## Quick Start
 
 The runner provides the API base URL as `<TASK_ENV_BASE_URL>`. All endpoints are relative to that base. Data is JSON with pagination via `limit` and `offset` and filtering via exact-match query parameters.
 
 Always fetch current API data — never trust local payloads as the system of record. Local files (CSV snapshots, batch payloads) provide context and scope only.
 
 ## Resources
 
 - [api_schemas.md](references/api_schemas.md) — Complete field-level reference for every endpoint. Read this first when you need schema details for any endpoint.
 - [workflows.md](references/workflows.md) — Step-by-step workflows for all five task types. Read this when you need the decision logic for a specific task type.
 
 ## Task-Type Selection
 
 Match the prompt to the correct workflow:
 
 | Prompt signals | Workflow |
 |---|---|
 | Claim IDs + AP bills/payments + "close status" or "reimbursement batch" | A: Reimbursement-to-AP Close Batch |
 | Vendor onboarding + business IDs + compliance + "release" or "finance-risk" | B: Vendor Onboarding Finance-Risk Release |
 | Prepaid invoices + GL balances + accounts + "close check" or "amortization" | C: Prepaid Close Check |
 | Stale AP snapshot + candidate claims + "reconciliation" + CSV context | D: Stale AP Snapshot Reconciliation |
 | Account-change events + business IDs + payment release + compliance screening | E: Account-Change Payment Release |
 
 When a prompt spans multiple signals, pick the workflow that matches the primary output schema.
 
 ## Cross-Cutting Rules
 
 These apply across all workflows:
 
 **Claim-AP linkage.** Claims link to AP bills via `claim_id` on the bill record. A claim may have zero, one, or multiple bills. Filter `/api/ap/bills?claim_id=...` to find them. Ignore void bills when determining active AP state.
 
 **Payment settlement.** A payment is settled only when `status` is `cleared`. Payments in `scheduled` or `processing` status have not yet settled. Use `/api/ap/aging` for reliable open-balance data (the `balance` field already nets cleared payments).
 
 **Compliance data sources.** Use `/api/compliance/objects` as the primary aggregate source. Supplement with detail endpoints (`ownership`, `registry`, `screening`, `bank`) when the aggregate result is incomplete or needs cross-verification.
 
 **Amount precision.** All currency amounts use USD with two decimal places. Use floating-point arithmetic and round to two decimals at the final aggregation step.
 
 **Sort order.** All ID lists in output are sorted ascending by ID unless the template specifies input order (like prepaid invoice results).
 
 **API filtering.** Use exact-match query parameters: `?claim_id=CLM-2025-0001`, `?business_id=BUS-2025-0009`, `?account=1250&period=2025-03`. For bulk fetches, use high `limit` values (e.g., `?limit=200`) and filter locally.
