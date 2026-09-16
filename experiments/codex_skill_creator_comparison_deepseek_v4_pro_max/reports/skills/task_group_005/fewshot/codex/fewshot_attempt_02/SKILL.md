---
name: erp-finance-review
description: Cross-reference ERP finance API records to produce structured close, release, and reconciliation decisions. Use when the task requires reviewing expense claims against AP bills and payments, evaluating vendor business IDs against compliance screening/bank/registry/ownership records, reconciling prepaid invoice amortization schedules against GL balances, correcting stale AP snapshots against current API state, or producing a structured JSON decision payload from a shared finance REST API environment where the base URL is supplied as TASK_ENV_BASE_URL.
---

# ERP Finance Review

## Overview

Cross-reference records from a shared ERP/finance REST API to make structured operational decisions. The API exposes claims, AP bills, payments, vendors, compliance checks, prepaid invoices, GL balances, and close logs through parallel endpoint paths.

## General Conventions

Every task in this domain shares these conventions:

- **API base URL**: supplied by the runner as TASK_ENV_BASE_URL. Always resolve this substitution before issuing requests.
- **Parallel endpoint paths**: most resources are reachable at both `/` and `/api/` variants (e.g., `/claims` and `/api/claims`). Both return the same data. Use whichever the task prompt or payload references.
- **Currency**: all monetary values in USD with two-decimal precision. Report in dollars (e.g., `1500.00`), not cents, unless the answer template explicitly says otherwise.
- **ID lists**: always sort ascending by string ID unless the template specifies a different order.
- **Answer templates**: every task provides a JSON schema. Read it first, then populate every required key. Return only the JSON object (no narrative text outside it) unless the prompt explicitly asks otherwise.
- **Local payloads**: treat local payload files as context or scope, not as the system of record. The API is authoritative.
- **Stale data**: when a task provides a stale snapshot (CSV, JSON batch), compare it against current API records and flag every discrepancy.

**Endpoint catalog**: see [references/endpoints.md](references/endpoints.md) for the full list.

## Workflow Selection

Identify which workflow the task belongs to by scanning the prompt and answer template:

1. **Claims-AP Close Review** — prompt mentions expense claims, reimbursement batch, AP bills, payments, close status, or stale AP snapshot. See [references/close_patterns.md](references/close_patterns.md).

2. **Vendor Compliance Review** — prompt mentions vendor onboarding, payment release after account changes, business IDs, compliance screening, UBO counts, hard-stop flags. See [references/compliance_patterns.md](references/compliance_patterns.md).

3. **Prepaid-GL Reconciliation** — prompt mentions prepaid invoices, amortization, GL balances, variance, close period, or accounts 1250/1251. See [references/prepaid_patterns.md](references/prepaid_patterns.md).

Some tasks combine workflows (e.g., stale-snapshot correction layered on top of a claims-AP review). When that happens, apply the base workflow first, then layer on the correction logic from the appropriate pattern file.

## Step-by-Step Procedure

### 1. Orient from the prompt and template

Read the prompt, every local payload file, and the answer template. Confirm:

- Which workflow (or combination) applies.
- The exact JSON keys required and their allowed values.
- The list of claim IDs, business IDs, or invoice IDs scoping the review.

### 2. Fetch current API records

Pull all relevant endpoints in parallel. Do not rely on local payloads as the system of record. For a claims-AP review pull `/claims`, `/bills` (or `/api/ap/bills`), `/payments` (or `/api/ap/payments`), and optionally `/close/logs`. For a compliance review pull `/vendors` (or `/api/vendors`), plus compliance endpoints for each business ID. For a prepaid review pull `/prepaids/invoices` (or `/api/prepaids/invoices`) and `/gl/balances` (or `/api/prepaids/gl-balances`).

### 3. Cross-reference

Follow the decision rules in the appropriate pattern reference. Key cross-reference operations:

- **Claims → Bills**: match on claim_id found in bill records.
- **Bills → Payments**: match on bill_id found in payment records, or claim_id when available.
- **Businesses → Compliance**: fetch ownership, screening, registry, and bank endpoints per business_id.
- **Invoices → GL**: group invoices by account code, compute straight-line amortization, compare schedule totals to GL balances.

### 4. Populate the answer JSON

Fill every required key. Use the allowed enum values exactly as stated. Compute derived fields (totals, variances, flags) from API data. Sort all ID lists as specified.

### 5. Output

Return the JSON object. Do not wrap in markdown fences unless the prompt explicitly asks for a code block.

## Resources

### references/

- [endpoints.md](references/endpoints.md) — Complete API endpoint catalog with field descriptions.
- [close_patterns.md](references/close_patterns.md) — Claims-AP close review patterns and decision rules.
- [compliance_patterns.md](references/compliance_patterns.md) — Vendor compliance review patterns and decision rules.
- [prepaid_patterns.md](references/prepaid_patterns.md) — Prepaid-GL reconciliation patterns.

### scripts/

- [scripts/amortization.py](scripts/amortization.py) — Deterministic straight-line monthly amortization computation. Execute without loading into context, or read for patching.
