This skill covers using an M&A deal workbench REST API to review and analyze acquisition agreements. The workbench hosts deal records, draft terms, playbooks, policy thresholds, risk estimates, employee and consent data, material contracts, regulatory facts, cap tables, diligence findings, documents, and negotiation notes. The skill applies to buyer-side, seller-side, and committee scenarios.

## Environment

The deal workbench runs at a base URL provided by the task, typically as `<TASK_ENV_BASE_URL>` or similar placeholder. All endpoints are relative to that base. The workbench may also expose a web UI at the root.

If read-only SQL access is available, the token is always `deal-workbench-readonly`.

## API Reference

### GET endpoints

| Route | Description |
|-------|-------------|
| `GET /` | Root, may return service status |
| `GET /workspace` | Workspace overview |
| `GET /deals/<deal_id>` | Single deal record |
| `GET /playbooks` | List of available playbooks |
| `GET /policies` | List of available policies |
| `GET /api/deals` | All deals |
| `GET /api/deals/<deal_id>` | Deal detail |
| `GET /api/deals/<deal_id>/terms` | Current draft terms |
| `GET /api/deals/<deal_id>/documents` | Deal documents |
| `GET /api/deals/<deal_id>/benchmarks` | Market benchmarks |
| `GET /api/deals/<deal_id>/risk-estimates` | Risk estimates |
| `GET /api/deals/<deal_id>/cap-table` | Capitalization table |
| `GET /api/deals/<deal_id>/consents` | Required and notice consents |
| `GET /api/deals/<deal_id>/employees` | Employee records |
| `GET /api/deals/<deal_id>/material-contracts` | Material contracts |
| `GET /api/deals/<deal_id>/regulatory` | Regulatory filings and status |
| `GET /api/deals/<deal_id>/diligence-findings` | Diligence findings |
| `GET /api/deals/<deal_id>/notes` | Negotiation notes |
| `GET /api/playbooks` | All playbooks |
| `GET /api/playbooks/<playbook_id>/rules` | Rules inside a playbook |
| `GET /api/policies` | All policies |
| `GET /api/policies/<policy_id>/thresholds` | Thresholds inside a policy |
| `GET /api/search` | Search across deal records |

### POST /api/query

Read-only SQL access with token `deal-workbench-readonly`.

Request body:
```json
{"token": "deal-workbench-readonly", "sql": "<SELECT or WITH query>"}
```

Tables typically include `deals`, `terms`, `consents`, `employees`, `material_contracts`, `regulatory`, `documents`, `benchmarks`, `risk_estimates`, `cap_table`, `diligence_findings`, `notes`, `playbooks`, `playbook_rules`, `policies`, `policy_thresholds`. Discover the exact schema by querying the API response fields and by running `SELECT * FROM <table> LIMIT 1`.

Always prefer direct API GET calls for record-by-record retrieval. Use SQL for cross-table joins, aggregation, or when a record's related data spans multiple endpoints.

## General Workflow

### Step 1 — Gather deal context

Fetch the deal record (`GET /api/deals/<deal_id>`) and any supporting documents (`GET /api/deals/<deal_id>/documents`). Identify:
- Project name, target name, counterparty name
- Client side (buyer or seller)
- Deal structure (asset purchase, stock purchase, merger)
- Headline purchase price / equity value
- Deal stage and signing date

### Step 2 — Collect draft terms, playbook rules, and policy thresholds

Fetch the current draft terms, the applicable playbook rules, and any committee-level policy thresholds:

- `GET /api/deals/<deal_id>/terms` — the current draft provisions
- `GET /api/playbooks/<playbook_id>/rules` — the client's preferred and fallback positions
- `GET /api/policies/<policy_id>/thresholds` — committee approval thresholds (when applicable)

Each term object typically contains a `term_id`, a `category`, a clause reference, and metric values (percent, dollars, months). Playbook rules describe preferred and fallback values. Policy thresholds define the maximum or minimum value allowed without committee escalation.

### Step 3 — Collect supporting deal data

Fetch all records that inform the analysis:

- **Risk estimates** (`/api/deals/<deal_id>/risk-estimates`) — modeled exposure low/high per category
- **Benchmarks** (`/api/deals/<deal_id>/benchmarks`) — market data (median, quartiles, sample sizes)
- **Consents** (`/api/deals/<deal_id>/consents`) — required closing consents and notice-only items
- **Employees** (`/api/deals/<deal_id>/employees`) — headcount, PTO liability, service-credit needs, WARN risk
- **Material contracts** (`/api/deals/<deal_id>/material-contracts`) — customer/supplier agreements requiring consent
- **Regulatory** (`/api/deals/<deal_id>/regulatory`) — HSR requirements, filing status, foreign clearances
- **Cap table** (`/api/deals/<deal_id>/cap-table`) — holder names, security classes, share counts, fully diluted percentages
- **Diligence findings** (`/api/deals/<deal_id>/diligence-findings`) — special indemnity items, NWC collar findings, privacy findings
- **Notes** (`/api/deals/<deal_id>/notes`) — negotiation history and positions

### Step 4 — Compare draft against playbook/policy and classify issues

For each relevant term or missing required term, determine its status:

| Status | Meaning |
|--------|---------|
| `in_policy` | Draft value is within the playbook/policy range or exactly matches |
| `out_of_policy` | Draft value exceeds or falls below the policy/playbook threshold |
| `missing_required_term` | The term does not appear in the draft but the playbook or deal data shows it is needed |
| `draft_exceeds_playbook` | Draft value is more aggressive than the playbook allows |
| `draft_below_playbook` | Draft value is weaker than the playbook's minimum position |

Do not flag terms that are:
- Already in policy (unless the task specifically requires in-policy terms to be listed)
- Stale or superseded by later drafts
- Not relevant to the specific deliverable requested
- Distractor terms from unrelated deal categories

### Step 5 — Compute dollar amounts and deltas

Use the deal's headline purchase price (equity value) as the basis for percentage-to-dollar conversion unless a source record explicitly states a different basis. For example, if the headline value is V and a term is at P%, the dollar amount is `round(V * P / 100)`.

Calculate:
- **Shortfall to fallback**: `fallback_amount - draft_amount` (or fallback percent vs draft percent, converted)
- **Shortfall to preferred**: `preferred_amount - draft_amount`
- **Delta to fallback months**: `draft_months - fallback_months` when draft exceeds
- **Quantified exposure**: from risk-estimate records, typically low and high bounds

### Step 6 — Assign risk ratings

| Rating | Criteria |
|--------|----------|
| `HIGH` | Directly threatens closing certainty, creates material uncapped exposure, or the draft is materially adverse to the client's core position |
| `MEDIUM` | Creates meaningful but manageable economic or legal risk; negotiation likely resolves |
| `LOW` | Administrative, notice-only, or low-dollar items with no structural impact |

### Step 7 — Assign recommended actions

| Action | When to use |
|--------|-------------|
| `delete` | Remove a buyer-favorable condition that the seller playbook prohibits |
| `revise` | Modify an existing draft term to align with playbook/policy |
| `add` | Insert a missing required term or closing condition |
| `accept` | The draft matches or exceeds the client's position |
| `escalate` | The term exceeds committee authority and requires approval |
| `approve` | Committee grants approval outright |
| `approve_with_conditions` | Committee approves subject to stated conditions |
| `reject` | Committee rejects the term; must be renegotiated |

### Step 8 — Prioritize issues

Order issues from highest to lowest negotiation priority. Priority drivers:
1. Closing certainty (financing conditions, regulatory conditions, consent conditions)
2. Direct dollar exposure (escrow amount, indemnity cap shortfall)
3. Structural leverage (break fees, fiduciary outs, MAE definitions)
4. Employee continuity and transition services
5. Administrative and tax items

### Step 9 — Build the JSON answer

Read the answer template at `input/payloads/answer_template.json`. The template defines:
- The exact shape and top-level keys required
- Allowed enum values for status, risk, action, and position fields
- The set of possible issue IDs (use exactly these; do not invent new ones)
- Which fields are required and their types

Populate every required field. For fields marked `null` in the template, provide a value (from data) or `null` (if genuinely not applicable). For boolean fields, use `true`/`false`; do not use string booleans.

**Do not include explanatory prose outside the JSON.** The output must be parseable as pure JSON.

## Units and Formatting

- **Currency**: integer USD (no decimals, no commas, no currency symbols). Round to nearest integer.
- **Percentages**: Percent points as decimal numbers. If the template says "two decimal places," format as `12.50`. If it says "one decimal place," format as `12.5`. If it says "four decimals," format as `0.1850`. If it says "whole percent points," format as `12`.
- **Months**: Integer months.
- **Dates**: `YYYY-MM-DD` format.
- **Source IDs**: Use stable IDs exactly as returned by the API (e.g., `TERM_PRJ_X_01`, `CNS_PRJ_X_01`, `EMP_PRJ_X_01`, `MAT_PRJ_X_01`, `FND_PRJ_X_01`, `RSK_PRJ_X_01`, `REG_PRJ_X`, `DOC_PRJ_X_01`). Never invent or modify source IDs.

## Task-Type Specific Guidance

### Seller APA Issue Register (like Train 1)

Compare the buyer's draft APA against the seller's playbook. Flag every deviation. For missing terms, check whether the deal context (e.g., HSR applicability, employee headcount, consent requirements) demands the term even though it is absent from the draft. If a term is absent and needed, set `source_term_ids` to `[]` and `issue_status` to `missing_required_term`.

Provide a `priority_order` array and a `summary_metrics` object with counts and aggregate dollar exposures.

### SPA Economics & Closing Package (like Train 2)

Compute holder-level consideration allocation from the cap table. Apply the purchase-price split (cash vs stock) proportionally by fully diluted ownership. Build the indemnity, escrow, NWC, covenant, and regulatory sections from the draft terms, playbook rules, and diligence findings. Identify all closing blockers (consents, contracts, regulatory) and classify the overall readiness.

### Committee Escalation Package (like Train 3)

Compare each draft term against the committee policy thresholds. Escalate only terms that are `out_of_policy`. Exclude in-policy terms and distractor terms not subject to committee review. For each escalated term, provide the policy comparison, quantified delta, benchmark support (if available), and required conditions for approval.

### Carveout Transition Review (like Train 4)

Focus on transition and separation terms: IP/domain transition, TSA scope/fees/duration, Section 1060 allocation, transfer-tax split, employee continuity and PTO, customer consent termination rights, outside-date extension for regulatory delay, and governing law/forum. Produce both `transition_issues` and `required_redlines` arrays, plus an `operational_risk` summary.

### SPA Deviation Matrix (like Train 5)

Build a `position_matrix` covering the standard SPA deviation dimensions: indemnity cap/basket, survival/knowledge qualifiers, materiality scrape, escrow/holdback/release, consent closing condition, HSR condition, and material contracts. For each dimension, classify the draft position, compare to playbook, and define the `final_position`. Produce `closing_blockers` and `risk_totals` aggregates.

## Error Handling and Edge Cases

- If an API endpoint returns an empty array or 404, treat the data as absent (which may itself be a finding, e.g., a missing required term).
- If a source record references an ID not found elsewhere, note the gap but do not invent data.
- If the headline purchase price is stated in the deal record but a specific term uses a different basis (e.g., upfront cash only), use the basis stated in that term's context.
- When the answer template specifies an enum and no value in the data fits, use the closest match and note (in your reasoning, not in the JSON output) any ambiguity.
- Do not assume that records from similarly named projects or deals apply to the current deal. Use only records scoped to the given deal ID.
