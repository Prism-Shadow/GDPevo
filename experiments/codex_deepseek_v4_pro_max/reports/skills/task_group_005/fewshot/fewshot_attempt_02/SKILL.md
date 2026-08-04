 # ERP Finance Operations Review Skill

## Overview

This skill enables an agent to perform batch finance operations reviews against a live ERP/compliance API. The agent reads a task prompt, payload files, and an answer template from the `input/` directory, queries a shared JSON API to retrieve current records, cross-references batch items against live data, applies domain-specific business rules, and returns a single JSON result matching the provided answer template.

## Supported Review Types

The skill handles these finance operations review patterns:

- **Reimbursement / AP close review** — classify expense claims as payable, blocked, or paid based on current claim, bill, and payment records.
- **Vendor onboarding / risk review** — decide whether businesses can be released for vendor access based on compliance, UBO, screening, bank, and document checks.
- **Prepaid / amortization close review** — reconcile prepaid invoice schedules against GL balances, compute amortization, and flag account-level variances and invoice-level data-quality exceptions.
- **Stale AP snapshot reconciliation** — reconcile an aged AP snapshot against live claim, bill, and payment data to determine which claims are still eligible for a batch.
- **Account-change payment release review** — review businesses after account-change events for payment release posture using compliance, bank, tax, license, screening, and risk evidence.

## General Workflow

### Step 1 — Load inputs

Read every file under the `input/` directory provided by the task runner:

- `input/prompt.txt` — Natural-language instructions describing the review task, the batch scope, and any special rules.
- `input/payloads/answer_template.json` — The JSON schema that defines the required output shape, including top-level key order, allowed enum values, sort order, and field descriptions.
- Any additional payload files in `input/payloads/` (e.g., JSON batch definitions, CSV snapshots). These define the scoped items to review and may supply supplementary context such as thresholds, review dates, or event tickets.

### Step 2 — Retrieve live data from the API

The runner supplies the API base URL as `<TASK_ENV_BASE_URL>`. All API endpoints are read-only GET requests with no authentication required. Use the endpoints documented in `api_reference.md` (included with this skill) to fetch current records.

**Collection endpoints** support optional `limit` and `offset` query parameters (integers) and exact-match query parameters by field name. When fetching a large collection, paginate with `limit` and `offset` to ensure complete coverage.

**Detail endpoints** accept an identifier in the path (e.g., `{claim_id}`, `{business_id}`).

Fetch all data relevant to the scoped batch items before making decisions. Prefer retrieving collection-level data and filtering client-side unless a detail endpoint maps 1:1 to a batch item.

### Step 3 — Cross-reference and apply business rules

For each batch item (claim, business, invoice, etc.), compare the live API data against the batch scope, the snapshot (if provided), and the review criteria described in the prompt. Apply these general rules:

**Claim / AP reviews:**
- A claim is **paid/closed** when a matching AP bill exists with a cleared payment for the full claim amount.
- A claim is **payable** when it is approved, has a valid open AP bill with no blocking issues, and no payment has cleared.
- A claim is **blocked** when the expense case needs owner cleanup (missing approval, missing support, CRM remediation) or the AP link is broken (voided bill, amount mismatch, vendor mismatch, missing bill).
- Compute open AP balances as bill amounts minus cleared payments, excluding voided bills and stale rows.

**Vendor / compliance reviews:**
- A business can be **approved** when all compliance checks pass (valid license, bank match, screening clear, required documents present, no sanctions/PEP hits, vendor not on hold).
- A business needs **escalation** when hard-stop flags are present (sanctions, confirmed PEP, shell company suspected, bank closed, vendor on hold).
- A business is **awaiting_information** when missing documents, screening not run, or other non-critical gaps exist.
- Count unique beneficial owners at or above the reporting threshold from the ownership/compliance endpoint.

**Prepaid / amortization reviews:**
- For each prepaid invoice, compute: monthly amortization = original_amount / term_months (use a default term if missing and flag it), cumulative amortization through the close period, and ending balance = original_amount − cumulative.
- Roll up per-account totals and compare schedule ending balances against GL ending balances. Flag accounts with absolute variance exceeding the supplied threshold.
- Flag individual invoices with data-quality exceptions (missing/defaulted term, negative/zero ending balance, mid-schedule edge cases).

**Stale snapshot reconciliation:**
- Compare each claim's snapshot row against current API data. A claim is **not ready** when: the current claim status is not approved, the snapshot bill is voided, the current bill amount or vendor does not match, or the payment has already cleared for a different amount.
- A claim is **eligible** when the current state confirms it can remain in the batch.
- Snapshot corrections map each claim to a specific correction label reflecting the discrepancy found.
- Check for required close logs when stale-snapshot corrections indicate blocking issues.

**Account-change release reviews:**
- Cross-reference each business against its current compliance, bank, tax, and license records.
- Flag businesses whose bank account status is `name_mismatch`, whose tax ID is invalid, or whose license is expired relative to the as-of date.
- Mark businesses with risk scores at or above 70 for override review.
- Decision logic: **release** when no flags are present and all checks pass; **hold** when non-critical issues exist that can be resolved without escalation; **escalate** when hard-stop or compliance-red-flag issues are present.

### Step 4 — Build the JSON response

Construct a single JSON object that exactly matches the structure, key order, and value constraints defined in `answer_template.json`:

- **Top-level key order**: Follow the `top_level_order` or `required_top_level_keys` array when present in the template.
- **Enum values**: Only use values listed in each field's `allowed_values`.
- **Sorting**: Sort all ID lists in ascending order (lexicographic for strings like `CLM-...`, `BUS-...`, `PPD-...`). Sort per-business/per-item arrays by the item identifier ascending.
- **Numeric precision**: Use exactly 2 decimal places for USD currency amounts. Use whole integers for counts.
- **Booleans**: Use JSON `true`/`false`, not strings.
- **Empty collections**: Use `[]` for empty lists, `{}` for empty objects — never `null` for list/object fields.
- **Dates**: Use `YYYY-MM-DD` string format.

### Step 5 — Validate and output

Before finalizing:
- Verify every required key from the template is present.
- Confirm all enum values are valid per the template.
- Check that all ID lists are sorted ascending.
- Ensure the batch-status or overall-release-ready field is consistent with the per-item decisions.
- Output only the JSON object — no narrative text, no markdown fences, no commentary.

## API Reference

See `api_reference.md` for the full list of available endpoints. The API is unauthenticated, read-only, and supports GET requests with optional query parameters for filtering and pagination.

## Conventions

- All monetary values in USD with 2-decimal precision.
- All ID lists sorted ascending unless the template specifies otherwise.
- Per-business and per-item arrays sorted ascending by the item's primary identifier.
- Hard-stop / flag lists sorted alphabetically within each item.
- When a field expects an empty list, use `[]`, not `null` or omission.
- Do not fabricate data — every value must be derivable from either the API response, the supplied payloads, or deterministic computation on those sources.

## Error Handling

- If an API endpoint returns an error or empty result for a batch item, treat that item as needing review/escalation (not silently omitted).
- If a payload file is malformed, report the issue rather than guessing.
- If the answer template specifies a required value for a field (e.g., `task_id`, `batch_id`), copy it exactly from the template or the matching payload field.
