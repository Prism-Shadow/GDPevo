---
name: finance-close-review
description: >
  Finance and AP close-review tasks using a shared ERP/compliance API. Use this
  skill whenever the user asks about closing a finance batch, reconciling
  claims or invoices against bills and payments, reviewing vendor or business
  onboarding against compliance evidence, performing prepaid amortization
  reconciliation, or releasing payments after account-change events. The skill
  covers cross-referencing multiple API endpoints, classification of items
  into decision buckets, and producing structured JSON answers that match an
  answer-template specification. Use it for any task that mentions claims,
  AP bills, payments, prepaid invoices, GL balances, vendor onboarding,
  compliance screening, or close/release review in a finance-operations
  context, even if the user does not say "close review" explicitly.
---

# Finance Close-Review

A reusable methodology for finance-operations close-review tasks backed by
a shared ERP/compliance API. The skill teaches a systematic cross-reference
pattern: pull current data from the API, map it to the answer template fields,
apply consistent decision rules from evidence, and produce a clean JSON result
matching the template constraints exactly.

## When to Use This Skill

This skill applies to any task where you are asked to:

- Classify claims, invoices, or business entities into decision buckets.
- Reconcile local batch payloads against current API records.
- Compute financial totals and balances from API data.
- Make release/block/approve decisions based on compliance or payment
  evidence.
- Produce a JSON answer that conforms to a provided answer template.

Common task types covered:

- Claim close-review (claims vs AP bills vs payments).
- Vendor onboarding release (business IDs vs compliance screening,
  ownership, registry, bank).
- Prepaid amortization reconciliation (invoices vs GL balances).
- Stale AP snapshot reconciliation (local snapshot vs current API).
- Post-account-change payment release (account-change tickets vs
  vendor/compliance data).

## Core Methodology

Follow these steps in order for every task:

### 1. Identify the input shape

Before hitting the API, read all the local inputs carefully:

- The `prompt.txt` or user instructions tell you what the task is about and
  what API base URL to use (given as `<TASK_ENV_BASE_URL>`).
- The `answer_template.json` defines the exact JSON shape you must return,
  including required keys, enum values, ordering rules, and numeric
  precision rules.
- Any local payload files (batch lists, snapshots, scope files) contain the
  candidate items you are reviewing. **These are context, not the system of
  record.** The API is always authoritative for current state.

Pay special attention to:
- **Ordering rules** -- most templates require ID lists sorted ascending
  by claim/business ID.
- **Precision rules** -- currency amounts must be USD with two decimals.
- **Enum values** -- use only the allowed values; do not invent your own.

### 2. Pull all relevant API data

Use the API base URL to fetch current records. Do this in parallel when
possible. Map each task type to the endpoints it needs:

| Task type | Key endpoints |
|-----------|--------------|
| Claim close-review | `/claims`, `/bills`, `/payments`, `/close/logs` |
| Vendor onboarding | `/compliance/objects`, `/compliance/ownership/{id}`, `/compliance/registry/{id}`, `/compliance/screening/{id}`, `/compliance/bank/{id}` |
| Prepaid reconciliation | `/prepaids/invoices`, `/gl/balances` |
| Stale AP reconciliation | Same as claim close-review |
| Account-change review | `/vendors`, `/compliance/objects`, `/compliance/ownership/{id}`, `/compliance/registry/{id}`, `/compliance/screening/{id}`, `/compliance/bank/{id}` |

Read [references/api-domains.md](references/api-domains.md) for the full
endpoint listing and the data model each endpoint returns.

The API returns JSON arrays or objects. **Do not guess field names** -- read
the actual response to learn the schema. Common patterns include:

- Claims have an `id`, `status`, `amount`, and sometimes linked `bill_id`.
- Bills have an `id`, `claim_id` (or reference), `status`, `amount`, and a
  linked `payment_id`.
- Payments have an `id`, `bill_id`, `status`, and `amount`.
- Compliance objects bundle screening, registry, ownership, and bank results
  per `business_id`.

### 3. Build the cross-reference table

This is the core of the methodology. Build an in-memory mapping from the
candidate items to their related API records. For claim tasks, the mapping
looks like:

```
claim_id -> claim record
         -> bill(s) linked to this claim
         -> payment(s) linked to those bills
```

For business/vendor tasks:

```
business_id -> compliance ownership records
           -> compliance registry records
           -> compliance screening results
           -> compliance bank status
           -> vendor record
```

Hold this mapping in your working memory. Do not cherry-pick fields; the
unexpected detail is often what drives a decision.

### 4. Apply decision rules from evidence

Classify each candidate item based on the evidence you gathered, not on
guesses or defaults. The decision logic varies by task type but always
derives from concrete observations:

**Claim close-review decisions:**

- **Paid**: The claim has a bill with status `paid` and there is a
  `cleared` payment for the claim amount.
- **Payable**: The claim is approved, has a valid open bill, and has
  no blocking issues.
- **Blocked**: The claim has a problem -- the claim itself is not
  approved, the bill is voided or mismatched, payment evidence is
  missing, or support documentation is incomplete.

**Vendor/business onboarding decisions:**

- **Approve**: All compliance checks pass (screening clear, bank
  active and matching, license valid, documents present, no PEP or
  sanctions flags).
- **Awaiting information**: A fixable gap exists (missing documents,
  screening not yet run).
- **Escalate**: A hard stop exists (confirmed PEP, sanctions match,
  bank closed, shell company suspected, vendor on hold).

**Prepaid invoice reconciliation:**

- **Exception**: Invoice has data quality issues (zero amortization,
  residual balance inconsistency, missing term when not expected).
- **Default/missing term**: The invoice amortization uses a default
  term rather than a contract-specified term.

Derive these decisions by inspecting the actual API data. Do not mirror
the answer templates for different tasks -- each task has its own
template with its own allowed enum values.

### 5. Compute financial totals

When the template requires financial totals, compute them only from the
items that belong in each category, using the API data as the source of
truth. Common computations:

- **AP open balance**: Sum of open bill amounts for payable claims.
- **Schedule totals**: Sum of original amounts, amortization, and ending
  balances across the scoped invoices for each account.
- **GL variance**: Schedule ending balance minus GL ending balance.
- **AP balance by claim**: The bill amount minus cleared payment amount
  for each claim.

Report all currency amounts with exactly two decimal places.

### 6. Assemble and validate the answer

Build the JSON object field by field, matching the answer template exactly:

1. Populate required top-level keys in the order the template specifies.
2. For each list field, sort by ID ascending.
3. For each numeric field, format to the specified precision.
4. For each enum field, use only the allowed values.
5. Include every key the template marks as required; do not add extra
   keys unless the template explicitly allows additional properties.

Before returning, **self-validate**:

- Check that every candidate item appears in exactly one bucket (unless
  the task design allows overlap).
- Check that all ID lists are sorted ascending.
- Check that financial totals are consistent with the per-item figures.
- Check that all enum values are from the template's allowed set.

## Common Pitfalls

**Trusting local payloads over the API.** Local files like stale CSVs or
batch JSON are context only. Always treat the API as the system of record.
If a local snapshot says a bill is `scheduled` but the API returns `paid`,
the API wins.

**Skipping the cross-reference step.** Don't make decisions by looking at
one endpoint in isolation. A claim might appear approved in the claims
endpoint but have a voided bill in the bills endpoint -- you only catch
this by cross-referencing.

**Inventing enum values.** If the template says allowed values are
`["approve", "awaiting_information", "escalate"]`, do not write `"approved"`
or `"pending"`. Match the template exactly.

**Computing totals from the wrong set of items.** For example,
`ap_open_balance_total` covers payable claims only, not all claims.

**Ignoring ordering rules.** Every template that lists IDs specifies an
ordering (almost always ascending by ID). Sort or the answer is wrong.

## Examples

The methodology is the same regardless of the specific finance domain.
Here is the pattern applied to different task types:

### Claim Close-Review Pattern

1. Read `answer_template.json` to learn the output fields.
2. Fetch `/claims`, `/bills`, `/payments` from the API.
3. Build mapping: claim_id -> bill -> payment.
4. Classify each claim into payable/blocked/paid based on the cross-reference.
5. Compute `ap_open_balance_total` from payable claims' open bill amounts.
6. Set `batch_status` based on the presence of blocked items.
7. Return JSON matching the template.

### Vendor Onboarding Pattern

1. Read `answer_template.json` and the batch payload.
2. For each business_id, fetch ownership, registry, screening, and bank
   from the compliance API endpoints.
3. Count reportable UBOs from ownership records.
4. Build hard-stop flags from screening/bank/registry evidence.
5. Decide approve/awaiting/escalate per business.
6. Return JSON matching the template with sorted lists.

### Prepaid Reconciliation Pattern

1. Read the scope file (invoice IDs) and `answer_template.json`.
2. Fetch `/prepaids/invoices` and `/gl/balances` from the API.
3. Filter invoices to the scoped IDs and the target accounts.
4. For each invoice, extract monthly amortization and compute cumulative
   and ending balance from the schedule data.
5. Roll up per-account totals and compare against GL ending balances.
6. Flag invoices with default/missing terms and data quality exceptions.
7. Set account status based on variance magnitude.
8. Return JSON matching the template.

### Stale Snapshot Reconciliation Pattern

1. Read the local snapshot and `answer_template.json`.
2. Fetch `/claims`, `/bills`, `/payments`, `/close/logs` from the API.
3. For each candidate claim, compare the snapshot to current API data.
4. Classify each claim as eligible or not-ready based on current state.
5. Assign a stale-snapshot correction for each claim.
6. Determine if close-log entries are required.
7. Return JSON matching the template.

### Account-Change Review Pattern

1. Read the account-change batch and `answer_template.json`.
2. For each business_id, fetch vendor info and compliance endpoints.
3. Compare requested bank last-4 against the API bank record.
4. Check tax status, license expiry, risk score, and screening results.
5. Decide release/hold/escalate per business.
6. Populate mismatch, invalid-tax, expired-license, review-queue, and
   risk-score-override lists.
7. Return JSON matching the template with all lists sorted ascending.

---

### Follow-Up

After reading this skill, if your task involves API endpoints not covered
here, read [references/api-domains.md](references/api-domains.md) for the
full endpoint catalog and data model guidance.
