---
name: finance-close-operations
description: ERP finance close, AP release, vendor compliance, and prepaid reconciliation tasks against a shared finance API. Use when the task involves batch claim/bill/payment reconciliation, vendor onboarding or account-change compliance review, prepaid amortization schedule-to-GL close, stale AP snapshot correction, or any multi-endpoint finance close decision that produces a structured JSON result conforming to a provided answer template. Triggered by tasks referencing claims, AP bills, payments, close logs, vendors, compliance endpoints (ownership, registry, screening, bank), prepaid invoices, GL balances, or batch review contexts like reimbursement close, vendor access release, payment release risk review, or prepaid close.
---

# Finance Close Operations

## Overview

This skill covers batch reconciliation and close/release review tasks against a shared ERP finance and compliance API. Every task follows the same core pattern: read the batch scope from local payloads, gather current records from the shared API, cross-reference and classify items, and return a JSON result that conforms to the provided answer template.

## Core Workflow

Every task in this domain follows four phases. Execute them in order.

### Phase 1: Read the batch scope

Identify the item IDs the task targets. The batch scope is always explicit in one of these forms:

- A list of claim IDs, business IDs, or invoice IDs in the prompt itself
- A local payload file listing targets plus review context
- A CSV snapshot whose row IDs form the candidate list

Also read the answer template from the payloads directory. Know every required key, allowed enum values, ordering rules, and precision constraints before writing any result.

### Phase 2: Gather live API records

Use the shared API base URL the runner provides. All GET endpoints are listed in [references/api_endpoints.md](references/api_endpoints.md). Key rules:

- Fetch data for every target ID. Use individual-ID endpoints when available. Fall back to collection endpoints when needed.
- Treat the API as the system of record. Local payloads (CSV snapshots, batch JSON) are stale context, not authoritative.
- Currency amounts are in USD. Preserve two-decimal precision for all calculations. Convert whole-USD values to two decimals when assembling output.
- Collect all API responses before making any classification decisions.

### Phase 3: Cross-reference and classify

Apply the decision rules from [references/decision_framework.md](references/decision_framework.md). The framework covers:

- **Claim/AP reconciliation**: Match claims to bills and payments, classify as paid/payable/blocked, determine remedial requirements, compute open AP balances, and flag stale snapshot corrections.
- **Vendor compliance review**: Classify business IDs as approve/awaiting_information/escalate, compute UBO counts, and populate hard-stop flags from compliance evidence.
- **Prepaid close**: Reconcile invoice amortization schedules against GL balances, compute account-level rollups, flag variances, and identify data-quality exceptions.
- **Payment release risk review**: Cross-reference vendor account changes against compliance evidence to produce release/hold/escalate decisions and flag bank mismatches, invalid tax IDs, expired licenses, and high-risk scores.

Always load the relevant section of the framework before classifying. Do not guess decision rules from train answers alone.

### Phase 4: Assemble and validate the result

Build the JSON output strictly against the answer template:

- Fill every required key. Never omit a key present in the template.
- Use only allowed enum values. Never invent a new category.
- Sort ID lists ascending (lexicographic for claim IDs, business IDs, invoice IDs).
- Report amounts in USD with exactly two decimal places. Zero balances are `0.00`.
- Verify completeness: the reviewed count must match the batch size, every target ID must appear in every per-ID section, and no target ID may appear in conflicting categories.

## Key Behaviors

### API selection

The API exposes endpoints under both bare paths (e.g., `/claims`) and `/api/`-prefixed paths (e.g., `/api/claims`). Both are identical. Use whichever form the task or environment documentation suggests, and prefer the `/api/` prefix when neither is specified.

### Amount precision

All currency amounts are in USD. Store and compute with full precision, then format to exactly two decimal places in output. A zero balance is `0.00`, never `0` or `0.0`. Never round intermediate values.

### ID ordering

All ID lists in output are sorted ascending by their natural string order (lexicographic). This applies to claim IDs, business IDs, invoice IDs, and close log IDs. Process order does not matter, but output order always does.

### Variance thresholds

When a task specifies a variance threshold, compare the absolute value of the variance against it. Flag only when `abs(variance) > threshold`, not `>=`.

### Batch status derivation

Batch status is always derived from per-item decisions, not stated explicitly in the API:

- `blocked` / `needs_ap_refresh` / `escalate`: At least one item has a blocking issue
- `open_payables`: Some items are payable and none are blocked
- `ready_to_close` / `ready_to_send`: All items are settled or payable with no blockers
- `overall_release_ready: false`: At least one business is not `approve`

### Default/missing term detection

For prepaid invoices, a default or missing term exists when the invoice record shows a term of 1 month, 0 months, or no term field, or when the amortization schedule is inconsistent with a standard straight-line schedule. Flag these in `default_missing_term_invoice_ids`.

### Exception detection

An invoice is an exception when its ending balance is non-zero but under $1.00, its cumulative amortization exceeds its original amount, its schedule shows incomplete or inconsistent amortization, or the invoice data has structural anomalies. Flag these in `exception_invoice_ids`.

## References

- [API Endpoints](references/api_endpoints.md) — Full catalog of API endpoints, response shapes, and field meanings
- [Decision Framework](references/decision_framework.md) — Reusable decision logic and classification taxonomies for all task types
