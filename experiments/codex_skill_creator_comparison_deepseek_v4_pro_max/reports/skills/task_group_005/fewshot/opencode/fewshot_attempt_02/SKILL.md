---
name: erp-finance-reconciliation
description: Reconcile ERP finance data across a shared API by fetching claims, AP bills, payments, compliance objects, vendors, prepaid invoices, GL balances, and close logs, then producing structured JSON decisions conforming to answer templates. Use this skill whenever the user mentions finance reconciliation, AP batch review, expense close, vendor onboarding, prepaid close checks, payment release after account changes, or any task that requires cross-referencing multiple ERP endpoints to produce a structured JSON answer. This includes close review, onboarding release, stale snapshot correction, vendor compliance checks, and GL reconciliation tasks.
---

# ERP Finance Reconciliation

Reconcile batches of claims, bills, payments, vendor compliance records, prepaid
invoices, and GL balances from a shared task-environment ERP API. Produce
strictly typed JSON output that conforms to an `answer_template.json` payload.

## Environment

The runner supplies the API base URL as `<TASK_ENV_BASE_URL>`. Do not use local
files as the system of record. The API supports these conventions on every
endpoint:

- Exact-match query parameters by field name (e.g. `?claim_id=CLM-2025-0090`,
  `?business_id=BUS-2025-0009`)
- Pagination with `limit` and `offset`
- `/api/...` and bare paths are equivalent (e.g. `/claims` and `/api/claims`)

## Step 1: Plan the answer space

Read the prompt, every payload file, and especially the answer template. Before
calling any API endpoint, confirm:

- Which record IDs are in scope (claim IDs, business IDs, invoice IDs)
- What the template requires at top level and nested inside
- Which list fields must be sorted ascending by ID
- Which amount fields expect USD with two decimal places
- Which enum values are allowed for each field
- Whether any fields only accept specific hardcoded values
- Whether any field depends on the prompt metadata (period, entity, as-of date)

The template is the ground truth for output shape. Missing a required key or
using a value outside the allowed enum set produces an invalid answer.

## Step 2: Fetch all source data

Call every endpoint needed to build the answer, then cross-reference records.

Read **[references/api_endpoints.md](references/api_endpoints.md)** for the
complete endpoint table, field schemas, and filtering patterns.

Key principles:

- Fetch paginated results in one sweep for each endpoint. Use `limit=200` (or
  larger if needed) and watch for `count` exceeding the returned page size.
- When the prompt gives a fixed set of claim IDs, business IDs, or invoice IDs,
  fetch the specific records by ID first, then pull the full reference tables
  (bills, payments, compliance objects, vendors) to match against them.
- Compliance data is available both as a bulk list
  (`/api/compliance/objects`) and per-business detail endpoints
  (`/api/compliance/ownership/{id}`, `/api/compliance/screening/{id}`,
  `/api/compliance/bank/{id}`, `/api/compliance/registry/{id}`). The bulk
  object already contains all four sub-views merged; prefer it unless a detail
  endpoint adds data not present in the bulk object.
- For prepaid close tasks, the GL balance endpoint returns balances keyed by
  `account` and `period`. Fetch only the period named in the prompt and the
  accounts in scope.

## Step 3: Reconcile and classify

For each record in the batch, gather the evidence chain across endpoints and
apply these rules.

### Claims to AP bills to Payments

A claim lifecycle is: submitted to (approved, rejected, needs_receipt, or
submitted) to AP bill created to payment scheduled/processing/cleared.

To classify a claim:

1. **Paid**: The claim has at least one matching AP bill where:
   - The bill `claim_id` equals the claim `claim_id`.
   - The bill `status` is `paid`.
   - There is a payment record for that bill with `status` `cleared` and a
     non-zero amount.
   A claim can have multiple bills. If one bill is paid+cleared for the full
   claim amount and another bill on the same claim is in a different state,
   the claim can still be treated as paid provided the paid+cleared path covers
   the claim amount. When a claim already shows `status: "paid"` in the claims
   endpoint, verify against bills+payments rather than trusting it blindly.

2. **Payable**: The claim status is `approved`, and there is at least one
   non-void AP bill linked to the claim where the bill is not yet fully
   paid+cleared. The bill-linked vendor must match the claim vendor (or the
   claim must have no vendor requirement). The open balance is the bill
   `amount` minus any cleared payment amounts.

3. **Blocked / CRM-required**: The claim needs owner intervention because:
   - Its `status` is not `approved` (e.g. `needs_receipt`, `rejected`,
     `submitted`).
   - It has no AP bill at all.
   - Its only linked bill is `void`.
   - Its linked bill amount differs substantially from the claim amount AND
     no matching paid/cleared alternative bill exists for the correct amount.
   - It has `receipt_status: "partial"` combined with policy flags like
     `over_limit`.
   - Its linked bill has a memo flag like `"Duplicate check required"` without
     a compensating resolution.

4. **Stale snapshot correction types**:
   - `current_snapshot_ok` -- the snapshot row matches current ERP data.
   - `mark_in_flight_payment` -- a bill is scheduled/approved with a pending
     payment; snapshot should note the in-flight status.
   - `replace_with_matched_paid_bill` -- a different bill than the snapshot
     bill is the correct paid match.
   - `exclude_amount_or_vendor_mismatch` -- bill amount or vendor does not
     match the claim.
   - `ignore_void_bill` -- the snapshot bill is now void.
   - `block_unapproved_claim` -- the claim is not approved in current ERP.

Close logs: When a close log references a period or account relevant to the
batch and its memo mentions export refresh, journal entries, or support
uploads that affect the batch, flag it. Use the `close_log_required` field
with `ids` sorted ascending.

### Vendor compliance to decisions

Read each business compliance object from `/api/compliance/objects`. The object
contains all relevant fields: `bank_account_status`, `license_expiry`,
`pep_status`, `sanctions_check_status`, `shell_company_suspected`,
`missing_fields`, `risk_score`, `tax_id`, `ubo_list`, `review_status`.

**Release decisions** (`release`, `hold`, `escalate`):

- **release**: Bank verified, license not expired by the review date, no PEP
  flags, no sanctions match, no shell company suspicion, no missing required
  documents (`license` and `beneficial_owner_id` in `missing_fields` are
  material), screening has been run (`not_run` is a control gap), and tax ID
  is valid (9-digit format, no embedded letters like `TIN12X899`).

- **hold**: Temporary blockers -- screening not run but otherwise clean, license
  recently expired with no other flags, bank name mismatch, risk score
  elevated but PEP/sanctions negative. These can likely resolve with follow-up.

- **escalate**: Hard stops -- confirmed PEP, sanctions confirmed match, bank
  closed, shell company suspected, expired license combined with other flags,
  missing required documents combined with screening not run or PEP/sanctions
  flags, or dense combinations of risk factors.

**Onboarding decisions** (`approve`, `awaiting_information`, `escalate`):
  Follow the same logic tuned for first-time onboarding rather than
  post-change release. `awaiting_information` maps to `hold`.

**Hard-stop flags**: Use the exact enum values from the template. Sort
  alphabetically. An empty list `[]` when none apply.

**UBO counts**: Count unique beneficial owner names whose `ownership_pct` meets
  the reporting threshold. Read the template to confirm whether the threshold
  applies at the individual entry level or aggregated by name. When the
  template is silent, count entries where `ownership_pct >= 25` individually.

**Follow-up IDs**: Any business whose decision is not `approve`. Sorted
  ascending.

**Overall release ready**: True only when every business in scope is `release`
  or `approve`.

### Prepaid invoices to GL balances

For each prepaid invoice in scope, the invoice record provides
`monthly_amortization`, `original_amount`, `service_start`, `service_end`.

1. **`monthly_amortization`**: Use the value from the invoice record directly.
   Do not prorate when months are partial -- the API provides the monthly
   figure already adjusted.

2. **`cumulative_amortization_through_period`**: Count the number of full
   months elapsed from `service_start` through the last day of the close
   period (inclusive). Multiply by `monthly_amortization`.

3. **`ending_balance`** = `original_amount` -
   `cumulative_amortization_through_period`. Clamp to 0.00 if negative.

4. **Per-account rollup**: Sum invoice-level `original_amount`,
   `march_amortization`, `cumulative_amortization`, and
   `schedule_ending_balance` across all invoices in that account. Then:

   - `schedule_ending_balance` = sum of invoice ending balances.
   - `variance_amount` = `schedule_ending_balance` - `gl_ending_balance`.
   - `variance_flag` = true when `|variance_amount| > variance_threshold_abs`
     (use 0 when no threshold is provided).
   - `account_status`: `reconciled` when no variance;
     `variance_review` when variance is small;
     `requires_reconciliation` otherwise.

5. **Exception flag**: Set true when:
   - `ending_balance` reaches exactly 0.00 at close (fully amortized on
     boundary).
   - `data_quality_flags` contains `missing_contract_dates` or
     `rounded_amount`.
   - `service_start` is in the same month as the close period (first
     amortization).

6. **Default/missing term flag**: True when `data_quality_flags` contains
   `missing_contract_dates` or the amortization schedule relies on a default
   service period.

### Account-change payment release

For post-account-change release decisions, cross-reference the compliance
object with the account-change event:

- `bank_mismatch_ids`: compliance `bank_account_status` is `name_mismatch`.
- `invalid_tax_ids`: `tax_id` contains non-digit characters (e.g. letters).
- `expired_license_ids`: `license_expiry` is before the `as_of_date`.
- `review_queue_ids`: any business with a risk flag or compliance issue.
- `risk_score_override_flags`: `risk_score >= 70`.

## Step 4: Assemble and validate output

1. Populate every required key from the answer template, in the order the
   template specifies.

2. Sort all ID lists ascending by their natural string sort. Claim IDs,
   business IDs, and invoice IDs sort lexicographically. Close log IDs sort
   numerically by the embedded number.

3. Round every currency field to exactly two decimal places. Use the exact
   values from the API; compute differences only when the template defines
   a formula.

4. Use exactly the allowed enum strings from the template. No aliases, no
   abbreviations.

5. Set boolean fields to JSON `true`/`false`, never strings.

6. When a field is a list of IDs and none apply, return `[]` not `null`.

7. Include every business ID key specified in the template even when the
   value is empty/zero.

## Edge cases

**Multiple bills for one claim**: Match each bill independently. If one bill
is paid+cleared and another is void or draft, ignore the void/draft for the
paid determination. Compute open balance from non-void bills only.

**Void bills**: A bill with status `void` contributes nothing to AP balances
or paid determinations. Flag it in stale snapshot corrections if a snapshot
still references it.

**Partial receipts**: A claim with `receipt_status: "partial"` is still
processable if all other conditions are met, but raises risk. Combine with
policy flags when deciding blocked vs. payable.

**Null vendor_id on claims**: Some claims lack a vendor. This does not block
payment -- the AP bill carries its own vendor. Only flag when the template
requires vendor matching.

**Duplicate amounts**: A `policy_flags` entry of `duplicate_amount` signals
another claim may share the same amount. Verify whether it is a distinct
claim or a systemic duplicate.

**Non-numeric tax IDs**: Tax IDs containing letters (like `TIN12X899`) are
invalid for compliance purposes.

**Screening not run**: `sanctions_check_status: "not_run"` and
`pep_status: "not_run"` mean the check has not happened. This is a control
gap -- treat as a hold factor unless combined with other red flags.

**Missing fields in compliance**: `missing_fields` can include `license`,
`website`, `bank_statement`, `beneficial_owner_id`. `license` and
`beneficial_owner_id` are material for onboarding. `website` alone is not
hard-stop material.

## API schema reference

For the complete endpoint table, field descriptions, and filtering details,
read **[references/api_endpoints.md](references/api_endpoints.md)**.

For detailed business rules with example decision flowcharts, read
**[references/business_rules.md](references/business_rules.md)**.
