---
name: erp-finance-review
description: "ERP finance close and review operations using a shared REST API. Use when working with finance review tasks that involve cross-referencing claims, AP bills, payments, vendors, compliance records, prepaid schedules, GL balances, or close logs to produce structured release, close, or reconciliation decisions. Triggers include: (1) Reimbursement or AP claim close review, (2) Vendor onboarding or account-change release review, (3) Prepaid expense close reconciliation against GL balances, (4) Stale AP snapshot reconciliation against current system records, (5) Any task requiring multi-endpoint finance API cross-referencing to classify items into decision categories and produce JSON output matching a supplied answer template."
---

# ERP Finance Review

## Core Workflow

When executing a finance review task, follow this sequence:

1. **Gather context**: Read the task prompt to identify candidate IDs, any local payloads (snapshots, CSVs, JSON batches), the review date/period, and the target answer template. Do not assume values from local payloads are current.
2. **Discover API surface**: Hit `GET /api/endpoints` to confirm available endpoints. Use the runner-provided `<TASK_ENV_BASE_URL>` as the base URL.
3. **Pull current records**: Query each relevant endpoint for data covering the candidate IDs. When both short-path (`/claims`) and `/api/*` (`/api/claims`) variants exist, prefer the `/api/*` path for consistency. Use query parameters or iterate IDs as needed.
4. **Cross-reference evidence**: Join records across endpoints by their shared keys. Claims join to bills and payments on `claim_id`. Business entities join across vendor and compliance endpoints on `business_id`. Prepaid invoices join to GL balances on account code. Always treat the API response as the system of record.
5. **Apply decision framework**: Classify each item using the task-appropriate framework (close review, release review, or reconciliation). Document the evidence chain that supports each decision.
6. **Produce output**: Return JSON only, matching the supplied answer template exactly. Apply the output conventions from [output_conventions.md](references/output_conventions.md).

## API Patterns

The API uses dual-path routing with consistent schemas across both path variants. Full endpoint documentation is in [api_endpoints.md](references/api_endpoints.md).

Key relationships:

- **Claims cycle**: `claims` → `bills` → `payments` joined on `claim_id`. A claim may have zero, one, or multiple bills; each bill may have zero or more payments.
- **Vendor/compliance cycle**: `vendors` joined to `compliance/ownership`, `compliance/registry`, `compliance/screening`, and `compliance/bank` on `business_id`.
- **Prepaid cycle**: `prepaids/invoices` reconciled against `gl/balances` on account code, with per-invoice schedule details.
- **Close logs**: `close/logs` provide audit trail entries keyed by claim or batch identifiers.

When cross-referencing, prefer exact key matches and treat missing records as evidence (e.g., a claim with no matching bill is blocked).

## Decision Frameworks

Three frameworks cover the review types seen in finance close operations. Full criteria are in [decision_patterns.md](references/decision_patterns.md).

**Close Review**: Used for claims batches. Classify each claim as paid (matching paid bill with cleared payment), payable (approved claim with valid unpaid AP bill), or blocked (claim missing an approved bill, bill with void status, payment evidence mismatched, or CRM-level issue).

**Release Review**: Used for vendor onboarding and account-change batches. Classify each business entity as approve (all compliance checks pass with no flags), awaiting_information (minor gaps resolvable without escalation), or escalate (hard-stop flags present: sanctions, PEP match, expired license, closed bank, missing required documents, screening not run).

**Reconciliation**: Used for prepaid close reviews. Compute per-invoice amortization, ending balance, and flag exceptions. Roll up to account-level totals, compute GL variance, and determine account status (reconciled, variance_review, requires_reconciliation) based on the variance threshold and whether default/missing terms or exceptions are present.

## Snapshot vs. System of Record

Some tasks include a local payload (CSV or JSON) representing a stale snapshot. When present:

- Use the snapshot only to identify which IDs to evaluate and to understand what was previously believed.
- All final decisions must be based on current API responses.
- Report corrections per-item when the snapshot diverges from current state. Common corrections include: a claim that appeared approved in the snapshot but now shows a void bill; a payment that was in-flight in the snapshot but has now cleared; a bill amount that changed between snapshot capture and the current API.

## Output Rules

Apply the conventions in [output_conventions.md](references/output_conventions.md). The critical rules:

- Return JSON only, no narrative text outside the JSON structure.
- ID lists are always sorted ascending (lexicographic order).
- Currency amounts in USD with exactly 2 decimal places.
- Enum values must match the template's allowed values character for character.
- Empty lists use `[]`, empty objects use `{}`.
- Top-level key order must match the template's required order when one is specified.
