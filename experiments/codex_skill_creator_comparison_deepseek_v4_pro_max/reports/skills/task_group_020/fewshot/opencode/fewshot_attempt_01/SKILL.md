---
name: deal-workbench-review
description: How to review M&A deal documents using the deal workbench API. Use when the task involves reviewing purchase agreements, producing issue registers, preparing closing packages, compiling committee escalation memos, conducting transition reviews, or building deviation matrices against a deal workbench. Applies to buyer-side or seller-side APA/SPA reviews, playbook comparisons, policy threshold checks, and any structured M&A deal analysis where the task provides an answer_template.json payload and references a running deal workbench at a TASK_ENV_BASE_URL.
---

# Deal Workbench Review

This skill teaches a systematic method for completing M&A deal review tasks against the deal workbench API. The core pattern is: read the template first, gather all deal data from the workbench, compare draft terms against playbook rules or policy thresholds, compute dollar amounts from the headline purchase price, and produce JSON that conforms exactly to the provided answer template.

## Key Principle

The task always provides an `answer_template.json` payload. This is your contract for output shape. Read it first and treat every field, enum, and constraint in it as non-negotiable. The workbench API provides the facts; the template defines what shape those facts must take.

## Connecting to the Workbench

The task always provides the base URL as `<TASK_ENV_BASE_URL>` (or similar placeholder). Substitute it everywhere. The read-only SQL endpoint, when available, is `POST <BASE>/api/query` with body `{"token": "deal-workbench-readonly", "sql": "<single SELECT or WITH statement>"}`.

The primary API surface for a deal `DEAL_ID` consists of these endpoints:

| Endpoint | Purpose |
|----------|---------|
| `GET <BASE>/workspace` | Workspace overview |
| `GET <BASE>/api/deals/<DEAL_ID>` | Deal record (headline price, parties, structure) |
| `GET <BASE>/api/deals/<DEAL_ID>/terms` | Current draft terms |
| `GET <BASE>/api/deals/<DEAL_ID>/risk-estimates` | Risk estimates for the deal |
| `GET <BASE>/api/deals/<DEAL_ID>/employees` | Employee data |
| `GET <BASE>/api/deals/<DEAL_ID>/consents` | Required third-party consents |
| `GET <BASE>/api/deals/<DEAL_ID>/regulatory` | Regulatory filings and status |
| `GET <BASE>/api/deals/<DEAL_ID>/benchmarks` | Market benchmarks for terms |
| `GET <BASE>/api/deals/<DEAL_ID>/documents` | Deal documents |
| `GET <BASE>/api/deals/<DEAL_ID>/notes` | Negotiation notes |
| `GET <BASE>/api/deals/<DEAL_ID>/cap-table` | Capitalization table (stock deals) |
| `GET <BASE>/api/deals/<DEAL_ID>/material-contracts` | Material contracts |
| `GET <BASE>/api/deals/<DEAL_ID>/diligence-findings` | Diligence findings |
| `GET <BASE>/api/playbooks` | Available playbooks |
| `GET <BASE>/api/playbooks/<PLAYBOOK_ID>/rules` | Playbook rules for a side |
| `GET <BASE>/api/policies` | Available policies |
| `GET <BASE>/api/policies/<POLICY_ID>/thresholds` | Policy thresholds |
| `GET <BASE>/api/search` | Search across the workbench |

The older non-`/api` prefixed routes (`/deals/<id>`, `/playbooks`, `/policies`) return the same data and can be used interchangeably with the `/api` variants. Use whichever the task prompt references.

## Systematic Workflow

Follow these steps in order. Complete each step before moving to the next.

### Step 1: Read the Answer Template

Read `input/payloads/answer_template.json` in full. Map every field:

- **Top-level required fields** and their types
- **Allowed enum values** for every constrained field (risk_rating, issue_status, recommended_action, etc.)
- **Stable identifier lists** (possible_issue_ids, stable_redline_ids, etc.) — these define the universe of expected outputs
- **Numeric constraints** (integer dollars, percent points to N decimal places, integer months)
- **Array element shapes** — the exact fields each object must have

The template is your schema. Every null in the template marks a place you must fill from workbench data.

### Step 2: Gather the Deal Record

Fetch `GET <BASE>/api/deals/<DEAL_ID>`. Extract:

- The deal ID (confirm it matches the task)
- The headline purchase price (this is your calculation basis for all dollar amounts unless a source explicitly states a different basis)
- The parties (target, buyer, seller names)
- The deal structure (stock purchase, asset purchase, merger)
- The client side implied by the task context (buyer-side or seller-side counsel)

### Step 3: Gather the Terms

Fetch `GET <BASE>/api/deals/<DEAL_ID>/terms`. These are the current draft terms the counterparty has proposed. Map each term to its stable ID. Pay attention to:

- Indemnity caps, baskets, and survival periods
- Escrow amount, duration, and release triggers
- Financing conditions and reverse break fees
- Restrictive covenants (non-compete, non-solicit)
- Employee provisions (service credit, PTO, retention)
- Tax allocation and transfer tax splits
- Governing law and forum
- Consent conditions and material contract treatment
- Closing conditions and outside dates
- Materiality scrapes, knowledge qualifiers, and sandbagging

### Step 4: Gather the Rules or Policies

Depending on the task type:

- **Playbook comparison tasks**: Fetch `GET <BASE>/api/playbooks/<PLAYBOOK_ID>/rules`. The playbook defines preferred and fallback positions for each term category. Compare each draft term against the playbook's preferred, fallback, and prohibited positions.
- **Policy threshold tasks**: Fetch `GET <BASE>/api/policies/<POLICY_ID>/thresholds`. The policy defines approval thresholds that draft terms must not exceed without committee escalation.

### Step 5: Gather Supporting Records

Fetch all endpoints the task references. Common supporting data:

- **Employees** (`/api/deals/<ID>/employees`): headcount, PTO liabilities, service credit needs, WARN risks
- **Consents** (`/api/deals/<ID>/consents`): which third-party consents are required, which are notice-only
- **Regulatory** (`/api/deals/<ID>/regulatory`): HSR filing status, thresholds, effort standards
- **Benchmarks** (`/api/deals/<ID>/benchmarks`): market data for term comparison
- **Risk estimates** (`/api/deals/<ID>/risk-estimates`): quantified risk estimates
- **Material contracts** (`/api/deals/<ID>/material-contracts`): contracts requiring consent or notice
- **Cap table** (`/api/deals/<ID>/cap-table`): for stock deals, holder breakdowns
- **Diligence findings** (`/api/deals/<ID>/diligence-findings`): issues from due diligence
- **Documents** (`/api/deals/<ID>/documents`): relevant deal documents
- **Notes** (`/api/deals/<ID>/notes`): negotiation context

Use the read-only SQL endpoint for cross-table checks when needed — send POST to `/api/query` with `{"token": "deal-workbench-readonly", "sql": "..."}`.

### Step 6: Perform the Analysis

This step depends on the task type. Common analyses:

**Playbook comparison (buyer or seller APA/SPA review):**
1. For each draft term, look up the corresponding playbook rule
2. Classify the issue status:
   - `draft_exceeds_playbook`: draft is more favorable to counterparty than playbook's fallback (e.g., higher cap, longer survival)
   - `draft_below_playbook`: draft is less protective than playbook requires (e.g., lower escrow, missing fee)
   - `missing_required_term`: a term the playbook requires is absent from the draft
   - `in_policy` / `out_of_policy`: for policy threshold tasks
3. Determine risk rating (HIGH/MEDIUM/LOW) based on dollar exposure and closing impact
4. Determine recommended action (revise/add/delete/accept)
5. Calculate dollar deltas: `draft_amount - fallback_amount` or `fallback_amount - draft_amount`

**Committee escalation (policy threshold):**
1. For each draft term, compare against the policy threshold
2. Exclude terms that are in-policy or stale
3. For out-of-policy terms, compute the delta between draft and threshold
4. Provide benchmark context and quantified exposure

**Closing package / transition review:**
1. Identify missing provisions the client side requires
2. Classify each gap and provide the required position
3. Produce redlines showing what must change

### Step 7: Compute Dollar Amounts

All dollar amounts derive from the deal's headline purchase price unless a specific source (term, finding, risk estimate) explicitly states a different basis.

- `amount = headline_price × (percent / 100)`, rounded to integer dollars
- Percent values are expressed as decimal numbers in percent points (e.g., 12.5, not 0.125)
- Month values are integers
- Holder allocation: `cash_amount = upfront_cash × holder_pct`, `stock_amount = stock_value × holder_pct`

### Step 8: Produce the Final JSON

Follow the answer template exactly:

- Every field in the template must appear in the output, even if null
- Use stable IDs from the workbench (term IDs, consent IDs, contract IDs, employee IDs, finding IDs)
- Sort arrays as the template instructs (typically by issue_id, priority, or redline_id)
- Use only the allowed enum values
- Do not invent IDs or values not present in the template or workbench
- Do not include explanatory prose outside the JSON

## Issue Classification Guide

Use these issue status values consistently:

| Status | Meaning |
|--------|---------|
| `draft_exceeds_playbook` | Draft term gives counterparty more than the playbook's fallback allows |
| `draft_below_playbook` | Draft term gives the client less protection than the playbook requires |
| `missing_required_term` | A term the playbook or policy requires is absent from the draft |
| `out_of_policy` | Draft term exceeds a policy threshold requiring committee approval |
| `in_policy` | Draft term is within acceptable bounds — include only when template requires it |

## Risk and Action Classification

**Risk ratings:**
- `HIGH`: Direct dollar exposure above materiality thresholds, closing certainty at risk, or regulatory clearance required
- `MEDIUM`: Moderate exposure, secondary protections missing, or procedural gaps
- `LOW`: Minor gaps or notice-only items

**Recommended actions:**
- `revise`: Modify an existing draft term toward the playbook position
- `add`: Insert a missing required term
- `delete`: Remove a draft term the playbook prohibits
- `accept`: Term is within acceptable bounds
- `reject`: Term is fundamentally unacceptable
- `approve` / `approve_with_conditions`: Committee escalation context only
- `escalate`: Needs higher-level business decision

## Data Formatting Conventions

- Currency: integer dollars (no cents, no commas in JSON numbers)
- Percentages: decimal numbers in percent points to the precision specified by the template (typically two decimal places or one decimal place)
- Months: integers
- Dates: `YYYY-MM-DD` strings
- Holder percentages: to four decimal places (e.g., 0.1850) when specified
- Empty arrays use `[]`, not `null`
- Missing source term IDs use `[]` (empty array), not `null`
- Booleans are `true`/`false`, never strings

## Validation Checklist

Before delivering the final JSON, verify:

1. The `deal_id` matches the task
2. Every required top-level field from the template is present
3. All enum values come from the template's allowed set
4. All dollar amounts are integers computed from the correct basis
5. All stable IDs (term IDs, consent IDs, contract IDs, employee IDs) match workbench records exactly
6. Array lengths match the template's expectations (no missing or extra items)
7. The `priority_order` array references only issue_ids that appear in the issue register
8. Summary metrics are internally consistent (counts match array lengths, totals sum correctly)
9. No narrative text appears outside the JSON structure
10. All nulls are intentional — every null field in the output corresponds to a field that genuinely has no applicable data

## Using the SQL Endpoint

When cross-table verification helps, use `POST <BASE>/api/query` with token `deal-workbench-readonly`. Keep queries to single SELECT or WITH statements. Use this sparingly — the dedicated API endpoints should cover most needs. SQL is most useful for verifying counts, cross-referencing IDs across endpoints, or aggregating values that span multiple records.
