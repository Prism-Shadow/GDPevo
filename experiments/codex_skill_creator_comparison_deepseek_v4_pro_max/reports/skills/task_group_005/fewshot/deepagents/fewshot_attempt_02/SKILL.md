---
name: finance-close-review
description: Finance close and compliance review operations against a shared ERP API. Use when the task involves batch reconciliation of expense claims, AP bills, vendor onboarding, prepaid amortization, account-change payment release, or compliance screening. Trigger on prompts about AP close review, reimbursement batch settlement, vendor finance-risk review, prepaid schedule reconciliation against GL balances, stale AP snapshot reconciliation, payment release after account changes, or any finance operations task that references a shared task environment API with endpoints under /api/claims, /api/ap/, /api/compliance/, /api/prepaids/, /api/vendors, or /api/close/.
---

# Finance Close Review

## Overview

This skill covers batch-oriented finance close and compliance review workflows
against a shared read-only ERP/compliance API. Every task follows the same
pattern: candidate IDs, an answer template, cross-endpoint reconciliation, and
a populated JSON result.

## General Workflow

For any task in this domain:

1. Read the prompt to identify the candidate IDs and the answer template.
2. Read the answer template to understand the output schema and allowed values.
3. Query the API for each candidate ID across all relevant endpoints. Use
   `curl -s` with the runner-provided `<TASK_ENV_BASE_URL>`. Page through
   results when needed with `?limit=100&offset=N`.
4. Apply the business rules for the task type (see reference files below).
5. Populate the template. Write the final JSON with `apply_patch` — do not use
   `echo` or `cat` to write structured JSON.

**Universal rules:**
- Sort ID lists ascending lexicographically.
- Report all currency amounts in USD with 2 decimal places.
- Use the API as system of record; local payloads are context, not truth.

## Reference Files

### API Catalog

[references/api_catalog.md](references/api_catalog.md) — Every endpoint, field
table, query parameter, hard-stop flag derivation, UBO counting rules,
amortization formulas, and reconciliation logic. Load this for any task to
understand the available data and schemas.

### Reconciliation Patterns

[references/reconciliation_patterns.md](references/reconciliation_patterns.md) —
Step-by-step classification logic for each task type:

- **Pattern A** — Claims-to-AP Reconciliation: classify claims as paid, payable,
  or blocked; compute AP open balance; handle stale snapshot corrections.
- **Pattern B** — Vendor Onboarding / Compliance Release: derive hard-stop
  flags, assign approve/awaiting_information/escalate decisions, count
  reportable UBOs.
- **Pattern C** — Prepaid Amortization Close: compute straight-line amortization
  per invoice, reconcile schedule totals against GL balances, flag exceptions.
- **Pattern D** — Account-Change Payment Release: cross-reference vendor and
  compliance data, assign release/hold/escalate decisions, populate risk and
  mismatch lists.

Load the relevant pattern when the task type is clear. Load both references
when the task spans multiple patterns or the type is ambiguous.
