---
name: ma-deal-workbench
description: Navigate the M&A deal workbench REST API and read-only SQL to review deal records, compare draft terms against playbooks and policies, and produce structured JSON outputs for APA/SPA negotiation, committee escalation, transition review, and deviation-matrix tasks. Use when the task involves deal_id-scoped records, playbook rules, policy thresholds, benchmarks, risk estimates, consents, material contracts, regulatory status, cap tables, employees, diligence findings, or negotiation notes accessed through the workbench API.
---

# M&A Deal Workbench

## Overview

This skill covers the M&A deal workbench — a REST API plus read-only SQL layer that serves deal records, draft terms, playbook rules, policy thresholds, benchmarks, risk estimates, and related diligence data. Every task in this domain follows the same core pattern: gather records for a specific deal, compare positions against playbook/policy rules, flag deviations, and produce a structured JSON answer.

## Connection Model

The workbench runs at a base URL provided in the task prompt via `TASK_ENV_BASE_URL`. Two access channels exist:

**REST API** — `GET` endpoints return JSON arrays or objects scoped to `deal_id` or `playbook_id`/`policy_id`.

**Read-only SQL** — `POST /api/query` with body `{"token": "deal-workbench-readonly", "sql": "<single SELECT or WITH statement>"}`. Use SQL for cross-table checks or when no REST endpoint covers the needed join.

Currency amounts in output are always integer USD. Percent values follow the task template's declared precision (typically two decimal places for percent points). Month values are integers unless the template says otherwise. Dates use `YYYY-MM-DD`.

## Core Workflow

### Step 1: Gather the Deal Record and Context

Start by pulling the deal record, draft terms, and the applicable playbook or policy. The three foundational calls for any deal task:

```
GET <BASE>/api/deals/<deal_id>
GET <BASE>/api/deals/<deal_id>/terms
GET <BASE>/api/playbooks/<playbook_id>/rules   OR   GET <BASE>/api/policies/<policy_id>/thresholds
```

If the task mentions a client side (seller or buyer), note it: it determines which playbook/policy to load and how to interpret term deviations.

### Step 2: Pull Supporting Records

Read the task prompt to determine which additional endpoints are needed. The full endpoint catalog is in [api_endpoints.md](references/api_endpoints.md). Common combinations:

- **Issue register / position matrix** → risk-estimates, employees, consents, regulatory, benchmarks, notes
- **Closing economics package** → cap-table, consents, employees, material-contracts, regulatory, diligence-findings
- **Committee escalation** → policies (thresholds), benchmarks, risk-estimates, notes
- **Transition review** → documents, employees, consents, material-contracts, regulatory, risk-estimates
- **Deviation matrix** → consents, material-contracts, regulatory, employees, risk-estimates

Always pull notes and documents when the task references negotiation history or ancillary agreements.

### Step 3: Compare Against Playbook / Policy

For each draft term that maps to a playbook rule or policy threshold:

1. **Identify the relevant rule/threshold** from the playbook or policy response.
2. **Compare the draft value** (percentage, amount, months, boolean flag) against the preferred and fallback values.
3. **Assign issue status**: `draft_exceeds_playbook` when the draft is worse for the client than the fallback, `draft_below_playbook` when the draft is weaker, `missing_required_term` when the playbook requires a provision that the draft omits, `in_policy` when compliant, `out_of_policy` when the draft violates a hard policy threshold.
4. **Treat draft silence as an issue** when the playbook/policy requires an affirmative provision and the surrounding deal data shows the term is needed.

### Step 4: Calculate Quantified Amounts

When a term carries a financial dimension:

- Derive dollar amounts from the deal's headline purchase price unless a source explicitly states a different basis.
- Compute `delta_to_fallback` as the difference between the draft amount and the fallback amount (always non-negative; the direction is already captured by `issue_status`).
- For missing terms where the draft has no value, the shortfall equals the full fallback amount.

### Step 5: Build the Output JSON

Read the `answer_template.json` from the task payloads directory. Every field in the template must be populated — use `null` for inapplicable scalar fields, `[]` for inapplicable arrays, and `{}` for inapplicable objects.

Order arrays as directed by the template (by `issue_id`, `priority`, or `redline_id`). When the template says "stable" IDs, use the exact IDs from the workbench records; do not invent synthetic IDs.

If the task says "return only JSON" or "do not include narrative outside the JSON", emit raw JSON with no markdown fences, preamble, or commentary.

## Task-Type Patterns

The workbench supports several distinct output shapes. The task prompt and answer template together tell you which one applies:

### Issue Register (seller-side APA review)

- Compare buyer draft terms against the seller playbook.
- Flag absent seller-protective terms as issues when deal data shows need.
- Output: an `issue_register` array, a `priority_order` array, and `summary_metrics`.
- Priority ordering: put closing-certainty items first (financing condition, reverse break fee), then escrow/indemnity economics, then employee/transition items, then restrictive covenants, then tax/general provisions.

### Closing & Economics Package (buyer-side SPA review)

- Pull the cap table and allocate consideration across holder groups.
- Compute indemnity, escrow, survival, and NWC mechanics.
- Classify consents, material-contract conditions, and regulatory status.
- Output: `economics`, `closing_conditions`, `covenants`, `regulatory`, and `closing_readiness` blocks.
- Escrow basis is `purchase_price` when the deal is a stock purchase; release is tied to general-rep survival expiration.
- Buyer-side: draft caps and survival periods that are too low for the buyer are `draft_below_playbook`; the buyer wants higher caps and longer survival.

### Committee Escalation Memo

- Compare only the terms that are out of policy against committee thresholds.
- Exclude stale, in-policy, or non-committee distractor terms.
- Provide benchmark comparisons and quantified exposure for each escalated term.
- Output: `memo`, `escalation_terms`, and `aggregate_summary`.
- The `delta` block captures numeric excess, missing triggers, or added carveout counts.
- Exposure is split into `low` (direct delta amount) and `high` (multiples or worst-case) estimates sourced from risk-estimate records.
- `benchmark.position` maps to where the draft value sits relative to the benchmark sample's median and upper quartile.

### Transition Review (carveout APA)

- Focus on transition, separation, IP, TSA, tax allocation, employee continuity, and governing law.
- Pair each issue with a corresponding redline entry.
- Output: `transition_issues`, `required_redlines`, and `operational_risk`.
- The `draft_value_normalized` and `required_position_normalized` objects capture the factual comparison in a non-enumerated shape; use the template's field names.
- `operational_risk.priority_order` ranks issues from highest negotiation priority down.

### Deviation Matrix (buyer-side SPA)

- Build a position matrix covering indemnity, survival, materiality scrape, escrow, consents, HSR, and material contracts.
- Classify closing blockers by type: `required_consent`, `regulatory_clearance`, `material_contract_consent`.
- Output: `position_matrix`, `closing_blockers`, and `risk_totals`.
- For the indemnity cap issue, include special-indemnity and privacy-finding amounts from diligence-findings when available.
- The `final_position` field captures the concrete buyer ask in the template's own enum.

## Enum Values

All output enums come from the answer template. The template's `allowed_enums` (or inline enum annotations) are authoritative. Do not invent values.

Common enums across tasks include:

- `risk_rating`: `LOW`, `MEDIUM`, `HIGH`
- `recommended_action`: `delete`, `revise`, `add`, `accept`, `escalate`, `approve`, `approve_with_conditions`, `reject`
- `issue_status`: `in_policy`, `out_of_policy`, `missing_required_term`, `draft_exceeds_playbook`, `draft_below_playbook`
- `business_outcome`: `closing_certainty`, `escrow_economics`, `indemnity_exposure`, `restrictive_covenants`, `employee_transition`, `tax_allocation`, `governing_law`, `regulatory_efforts`

When the template provides `possible_issue_ids` or `stable_issue_ids`, restrict `issue_id` values to that list.

## SQL Usage

Use `POST /api/query` with token `deal-workbench-readonly` when:

- You need to join records across endpoints (e.g., matching consent IDs to material contracts).
- The task asks for a cross-table check.
- You need aggregation that the REST endpoints don't provide.

Submit only single `SELECT` or `WITH` statements. The query returns a JSON array of result rows.

## Reference Files

- [api_endpoints.md](references/api_endpoints.md) — Full catalog of REST endpoints with path, query behavior, and response shape guidance. Load when the task prompt does not enumerate the needed endpoints or when you need to discover available data for a deal.
