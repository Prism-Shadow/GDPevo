<!--
  NOTE: This file is ~250 lines. Scan the endpoint list for the routes
  relevant to your task, then request the ones you need. The response shapes
  below are what the workbench typically returns; field values vary by deal.
-->

# Deal Workbench API Reference

## Base URL

```
<TASK_ENV_BASE_URL>
```

The prompt provides the concrete base URL. Substitute `<TASK_ENV_BASE_URL>` with
the value from the prompt. Never hardcode a base URL.

## Authentication

GET endpoints are public within the task environment. The read-only SQL
endpoint requires a token:
```
POST /api/query
Body: {"token": "deal-workbench-readonly", "sql": "<SELECT or WITH statement>"}
```

## Core Entities

| Prefix | Entity | Example |
|--------|--------|---------|
| PRJ_   | Deal / project | PRJ_ALPHA |
| TERM_  | Draft term | TERM_PRJ_ALPHA_01 |
| CNS_   | Consent requirement | CNS_PRJ_ALPHA_03 |
| MAT_   | Material contract | MAT_PRJ_ALPHA_01 |
| EMP_   | Employee record | EMP_PRJ_ALPHA_01 |
| RSK_   | Risk estimate | RSK_PRJ_ALPHA_01 |
| FND_   | Diligence finding | FND_PRJ_ALPHA_03 |
| DOC_   | Document record | DOC_PRJ_ALPHA_01 |
| REG_    | Regulatory record | (synthetic, not fetched via /api) |
| PB_    | Playbook | PB_SELLER_A, PB_BUYER_A |
| POL_   | Policy | POL_MA_2025_A |

## Endpoint Catalog

### Deal-Level Records

```
GET /api/deals/<deal_id>
```
Returns the deal header: deal ID, project name, target name, parties, deal
type (asset purchase, stock purchase, merger), headline purchase price,
currency, signing date, and status.

```
GET /api/deals/<deal_id>/terms
```
Returns an array of draft terms. Each term has:
- `term_id` (e.g., `TERM_PRJ_XXXXXX_NN`)
- Category and clause reference
- Draft values: percentages, dollar amounts, months, or boolean flags
- Scope and conditions

```
GET /api/deals/<deal_id>/benchmarks
```
Returns market benchmark data arrays. Each benchmark has:
- `metric` — what is measured
- `sample_size`, `median`, `upper_quartile` — statistics
- May be segmented by deal size or industry

```
GET /api/deals/<deal_id>/documents
```
Returns document metadata: document ID, type, title, status, and references.
Documents may indicate which clauses are present or absent.

```
GET /api/deals/<deal_id>/notes
```
Returns negotiation notes, deal-team commentary, and action items.

### Side-Specific Records

```
GET /api/deals/<deal_id>/consents
```
Returns consent requirements. Each consent has:
- `consent_id` (e.g., `CNS_PRJ_XXXXXX_NN`)
- `contract_name` and `counterparty`
- `condition_type`: `closing_condition`, `notice_only`, or `post_closing_covenant`
- `amount_at_risk` (USD) — null when not quantified
- `risk_rating`

```
GET /api/deals/<deal_id>/employees
```
Returns employee records. Each record has:
- `employee_id` (e.g., `EMP_PRJ_XXXXXX_NN`)
- Employee group, role, and department
- Service credit status, PTO accrual/liability
- WARN Act risk indicators
- Continuing or terminated classification
- Compensation details

```
GET /api/deals/<deal_id>/material-contracts
```
Returns material contracts. Each contract has:
- `contract_id` (e.g., `MAT_PRJ_XXXXXX_NN`)
- `contract_name` and counterparty
- `annual_revenue` (USD)
- Consent or assignment requirements
- `condition_type`

```
GET /api/deals/<deal_id>/risk-estimates
```
Returns quantified risk estimates. Each estimate has:
- `estimate_id` (e.g., `RSK_PRJ_XXXXXX_NN`)
- Risk type and category
- `low` and `high` dollar exposure bounds
- Basis and assumptions

```
GET /api/deals/<deal_id>/diligence-findings
```
Returns diligence findings. Each finding has:
- `finding_id` (e.g., `FND_PRJ_XXXXXX_NN`)
- Finding category and description
- Dollar impact (when quantified)
- Remediation status

```
GET /api/deals/<deal_id>/regulatory
```
Returns regulatory status: HSR required, threshold basis, approval type,
hell-or-high-water obligation, and closing condition status.

### Stock-Deal Records

```
GET /api/deals/<deal_id>/cap-table
```
Returns capitalization table data for stock purchase or merger deals. Each
holder group includes: holder name, security class (common stock, preferred
stock, options), fully-diluted ownership percentage, and as-converted share
count.

### Playbooks and Policies

```
GET /api/playbooks
GET /api/playbooks/<playbook_id>/rules
```
Playbook rules define the client's negotiation positions. Each rule has:
- Preferred position (ideal outcome)
- Fallback position (walk-away floor)
- Quantitative values: percentages, dollar amounts, months
- Structural requirements (e.g., deductible basket type, employee treatment)
- Conditional logic (e.g., "if financing risk remains, require reverse break
  fee")

```
GET /api/policies
GET /api/policies/<policy_id>/thresholds
```
Policy thresholds define hard limits for committee escalation. Each threshold
has a `threshold_value`, `unit`, and `basis`. Terms exceeding these thresholds
must be escalated to committee.

### Search

```
GET /api/search?q=<query>
```
Cross-entity search. Returns matching records across terms, consents,
contracts, employees, findings, and notes.

### Read-Only SQL

```
POST /api/query
Body: {"token": "deal-workbench-readonly", "sql": "<statement>"}
```

Allows cross-table joins and filtered queries. Use for:
- Verifying that no term addresses a specific subject (confirming a missing
  term is truly absent)
- Aggregating employee counts by group
- Cross-referencing consent IDs with material contract IDs
- Checking for hidden records not surfaced by direct endpoints

Only `SELECT` and `WITH` statements are allowed. Use single quotes for string
literals.

## Direct-Route Web UI Alternatives

The prompt may reference these GET routes without the `/api/` prefix. They
return HTML or the same underlying data:

```
GET /workspace
GET /deals/<deal_id>
GET /playbooks
GET /policies
```

Prefer the `/api/` routes for structured JSON responses.

## Response Patterns

### Money Values

API responses use integer USD for dollar amounts. Percentage values use the
percentage form (e.g., 14.0 means 14%, not 0.14). Months are integers.

### Null vs. Absent

When a record lacks a field, the API may either omit the key or return `null`.
Both mean "not applicable." When the draft is silent on a concept, treat the
relevant draft value as `null`.

### Arrays May Be Empty

An endpoint returning `[]` means no records of that type exist for the deal.
This is not an error — it is a finding that affects issue classification.

## Usage Notes

- Fetch the deal record and terms first — they establish the deal skeleton.
- Fetch playbooks or policies next — they define the normative baseline.
- Fetch supporting records (consents, employees, regulatory, etc.) in parallel.
- Use SQL only when cross-table verification is needed or direct endpoints
  do not surface a required detail.
- Never assume records from one deal apply to another. Each deal is isolated.
