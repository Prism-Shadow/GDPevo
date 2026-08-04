---
name: erp-finance-review
description: Query a shared ERP/compliance API to reconcile claims, prepaids, vendor compliance, and AP close batches. Use when the task involves finance review, batch close decisions, vendor onboarding, or account-change release assessments against live API data.
---

# ERP Finance Close & Review Skill

Perform finance-operations review tasks against a shared ERP/compliance JSON API.
Use live API data—not local payloads—as the system of record. Local payloads
provide batch scope, candidate IDs, and review context only.

## API Reference

The runner supplies the API base URL. All endpoints accept GET with exact-match
query parameters and optional `limit`/`offset` integers.

| Domain | Endpoints |
|--------|-----------|
| Claims | `/claims`, `/api/claims`, `/api/claims/{claim_id}` |
| AP Bills | `/bills`, `/api/ap/bills` |
| AP Payments | `/payments`, `/api/ap/payments` |
| AP Aging | `/api/ap/aging` |
| Vendors | `/vendors`, `/api/vendors` |
| Compliance | `/compliance/objects`, `/api/compliance/objects`, `/api/compliance/ownership/{business_id}`, `/api/compliance/registry/{business_id}`, `/api/compliance/screening/{business_id}`, `/api/compliance/bank/{business_id}` |
| Prepaids | `/prepaids/invoices`, `/api/prepaids/invoices`, `/api/prepaids/gl-balances`, `/gl/balances` |
| Close Logs | `/close/logs`, `/api/close/logs` |

## Workflow

### Step 1 — Parse the Task

Read all three input components for the assigned task:

- `prompt.txt` — Task objective, candidate IDs, entity/period context, and
  special instructions.
- `payloads/*.json` or `payloads/*.csv` — Batch scope, candidate lists, domain-
  specific parameters, and review context (NOT the system of record).
- `payloads/answer_template.json` — Output schema with field descriptions,
  allowed enum values, ordering rules, and precision requirements.

Extract from the prompt:

- Which API domains are relevant (claims, bills, payments, compliance, prepaids,
  close-logs, vendors).
- Which candidate identifiers to evaluate (claim IDs, business IDs, invoice IDs).
- Any period, entity, or threshold parameters.
- Any special decision rules stated inline.

### Step 2 — Gather Live Data

Query the API for current records covering every candidate ID. Query patterns:

- **Claim review**: Fetch each claim by ID (`/api/claims/{id}`). For each claim,
  look up related AP bills (query `/api/ap/bills` filtering by claim_id if the
  API supports it, or enumerate). For each bill, look up payments
  (`/api/ap/payments` filtering by bill_id).
- **Compliance review**: Fetch `/api/compliance/ownership/{business_id}`,
  `/api/compliance/registry/{business_id}`,
  `/api/compliance/screening/{business_id}`, and
  `/api/compliance/bank/{business_id}` for each business. Cross-reference with
  `/api/vendors` for vendor details.
- **Prepaid schedule**: Fetch `/api/prepaids/invoices` filtered by account and
  period. Fetch `/api/prepaids/gl-balances` (or `/gl/balances`) for the
  specified accounts and period.
- **Close logs**: Fetch `/api/close/logs` when the task requires close-log
  evidence.

Always prefer detail endpoints (`{id}`) over collection endpoints when the ID
is known; use collection endpoints with query parameters for cross-referencing.

### Step 3 — Reconcile and Decide

Compare live API data against the batch scope. Core reconciliation rules:

**Claims ↔ AP Bills ↔ Payments**:
- A claim is **paid** when a matching AP bill exists (same amount, same claim
  ID) AND a cleared payment exists for that bill covering the full amount.
- A claim is **payable** when an approved AP bill exists for the correct amount
  but no matching cleared payment has been posted.
- A claim is **blocked** when there is no matching bill, the bill amount
  mismatches, the bill is void/voided, payment is partial/stale, or the claim
  itself is not in an approved state.

**Compliance Checks**:
- **Bank**: Check `bank_account_status` for `closed`, `name_mismatch`, or
  last-4 mismatch against the account-change ticket.
- **Screening**: Check for sanctions hits, PEP flags, or `screening_not_run`.
- **Registry**: Check license expiry against the review date. Flag expired
  licenses.
- **Ownership**: Count UBOs (ultimate beneficial owners) at or above the
  reporting threshold.
- **Risk**: A risk score ≥ 70 triggers a flag.

**Prepaid ↔ GL Reconciliation**:
- Compute schedule ending balance = original_amount − cumulative amortization
  through the close period.
- Compare against the GL ending balance for the account.
- Variance = schedule_ending_balance − gl_ending_balance.
- Flag variance when |variance| exceeds the threshold (default 100.00).
- Flag invoices missing term data (`default_missing_term_flag`).
- Set account status: `reconciled` (no variance and no flags), `variance_review`
  (variance within tolerance but flagged), `requires_reconciliation` (material
  variance or data-quality flags).

**Stale Snapshot Corrections**:
- Treat the local CSV/JSON snapshot as historical context only.
- For each candidate claim, compare the snapshot status against current API
  state and assign the appropriate correction code: `current_snapshot_ok`,
  `mark_in_flight_payment`, `replace_with_matched_paid_bill`,
  `exclude_amount_or_vendor_mismatch`, `ignore_void_bill`, or
  `block_unapproved_claim`.

### Step 4 — Format the Output

Produce a single JSON object matching the answer template exactly:

- **Top-level key order**: Match the template's declared order (e.g.,
  `required_top_level_keys` or `top_level_order`).
- **Sorting**: All ID lists are sorted ascending (lexicographic for claim IDs
  and business IDs; numeric for invoice IDs when prepended with account
  context).
- **Currency**: All money values in USD with exactly 2 decimal places.
  Use `0.00` / `0.0` as specified by the template.
- **Enums**: Use only values from the template's `allowed_values` lists.
  Never invent new values.
- **Required keys**: Every key listed in `required_top_level_keys` or
  `required_keys` must be present. Do not add extra top-level keys.
- **Empty collections**: Use `[]` for empty lists, never `null`.

### Decision Enum Reference

| Context | Enum Values | Meaning |
|---------|-------------|---------|
| Batch close status | `ready_to_close`, `open_payables`, `blocked` | Overall batch posture |
| Per-claim decision | `eligible`, `not_ready`, `blocked`, `paid` | Individual claim status |
| Vendor onboarding | `approve`, `awaiting_information`, `escalate` | Per-business release decision |
| Account change release | `release`, `hold`, `escalate` | Post-change payment release |
| AP batch status | `ready_to_send`, `needs_ap_refresh`, `blocked` | Stale-snapshot batch posture |
| Account close status | `reconciled`, `variance_review`, `requires_reconciliation` | GL reconciliation result |

## Anti-Patterns

- **Do not** trust local payload data as current. Always verify against the API.
- **Do not** invent enum values. Use only those in the answer template.
- **Do not** omit required keys or add undocumented top-level keys.
- **Do not** sort IDs in any order other than ascending.
- **Do not** report currency values with more or fewer than 2 decimal places.
- **Do not** skip querying relevant endpoints—an unqueried endpoint may hide a
  blocking condition.
- **Do not** output narrative text. Return JSON only.
