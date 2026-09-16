---
name: procureops-analyst
description: >
  Fulfill procurement operations analyst tasks using a shared ProcureOps API.
  Use this skill whenever a user asks you to prepare a sourcing nomination
  packet, close out a receiving batch, resolve AP invoice holds, evaluate a
  contract change request, release receiving/AP exceptions, or perform any
  other operational-analyst workflow that names ProcureOps, procurement,
  sourcing, receiving, AP, vendor risk, or supply-chain operations.  Even when
  the user does not mention ProcureOps explicitly this skill should activate
  if the task involves procurement reconciliations, three-way matching, PO
  closeout, invoice-hold decisions, budget-impact analysis, or supplier-risk
  checks against a structured procurement data set.
---

# ProcureOps Analyst

Complete procurement-operations analyst tasks by reading the shared
ProcureOps API, applying local business memos, and returning a single
well-formed JSON answer that follows the provided template exactly.

## Quick-start

### 1. Read the task prompt

Every task supplies three things:

- A **plain-language business request** (the prompt itself).
- **Local payloads** under `input/payloads/` (at minimum an answer template
  JSON, often a business memo or packet file).
- A **ProcureOps API base URL** held in the environment variable
  `TASK_ENV_BASE_URL`.

### 2. Load the API reference

Read `references/api_endpoints.md` for the endpoint list, entity schemas,
and field notes.  That file is the canonical reference for every ProcureOps
endpoint available in a task environment.

### 3. Fetch the data you need

Use `curl` or an equivalent HTTP client to call the REST endpoints.  Every
endpoint returns a JSON envelope with `count` and `results`.  The results
list is your working dataset.  The API requires no authentication.

**Important patterns:**
- Fetch all records you might need in parallel (endpoints are independent).
- Filter and join records in memory — the API has no query parameters other
  than the endpoint path.
- When the task names specific IDs (PO, receipt, invoice, etc.), look them
  up in the relevant endpoint and trace all related records through the
  cross-reference fields (e.g. `po_id`, `supplier_id`, `program_id`,
  `contract_id`, `requisition_id`, `receipt_id`, `invoice_id`).

### 4. Trace the entity graph

The ProcureOps data model is a DAG, not a single hierarchy.  Trace
relationships through ID references — do not assume joins from a single
source entity.  The key links are:

```
program_id ──→ purchase_orders, contracts, budget_snapshots, requisitions
supplier_id ─→ purchase_orders, contracts, receipts, invoices, risk events
po_id ───────→ receipts, invoices
contract_id ─→ purchase_orders
requisition_id → purchase_orders, approvals
receipt_id ───→ invoices
invoice_id ───→ payments
```

Read `references/decision_rules.md` for the operational rules that
turn raw entity data into analyst decisions (nomination readiness,
hold/release, contract checks, budget checks, three-way match, etc.).

### 5. Fill the template

- Read the answer template from `input/payloads/` **in full** before
  writing any JSON.  The template defines every required key, allowed
  values, list orderings, and precision rules.
- Use the template as a schema — not a suggestion.  If the template says
  an enum value is `"release_amendment"` then use exactly that string.
- **Set ordering**: when the template says a list field should be sorted
  ascending or that the evaluator treats it as a set, sort it ascending
  in your output.
- **Currency**: every monetary field is USD rounded to two decimal places
  (cents).  Use `round(x, 2)` after each arithmetic step.
- **Nulls**: use JSON `null` (not the string `"null"`) for absent values.
- Return **only the JSON object** — no markdown fences, no prose.

### 6. Verify before returning

- Every top-level key in the template is present.
- Every nested required-key is present.
- Monetary values are rounded to two decimals.
- Lists that need sorting are sorted ascending.
- IDs are copied verbatim from API records (no reformatting).
- No task-specific final values from the train examples are injected.

---

## Domain vocabulary

| Term | Meaning in ProcureOps |
|------|----------------------|
| **Three-way match** | PO lines, receipt lines, and invoice lines all agree on quantity and unit price. |
| **Price type** | `fixed` means the contract unit price is authoritative; `variable` means invoice price may differ. |
| **Ceiling** | Maximum dollar amount allowed under a contract (sum of non-cancelled PO subtotals must stay under it). |
| **Committed amount** | Budget line showing dollars already encumbered by approved POs. |
| **Hold code** | Reason an invoice is blocked from payment (QTY_VARIANCE, NO_RECEIPT, PRICE_VARIANCE, SUPPLIER_REVIEW). |
| **Chargeback** | A local (non-API) register recording quantity or price disputes against an invoice. |
| **Supplier risk rating** | `low`, `medium`, `watch`, or `high` — always check for open risk events even when the rating is low. |
| **Approval action** | The latest event recorded against a requisition — `submitted` means not yet approved. |

---

## Bundled resources

| File | When to read it |
|------|----------------|
| `references/api_endpoints.md` | Every task — defines the API surface and entity schemas. |
| `references/decision_rules.md` | Every task — operational rules for nomination, hold/release, contract, budget, and risk decisions. |

Read both references at the start of every task.  They are short and
needed every time.
