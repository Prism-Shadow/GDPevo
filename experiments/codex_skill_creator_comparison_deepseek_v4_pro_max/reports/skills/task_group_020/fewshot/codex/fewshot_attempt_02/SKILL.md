---
name: ma-deal-workbench
description: Navigate the M&A deal workbench API to review draft agreements, compare terms against playbooks and policies, calculate quantified exposures, and produce structured JSON deliverables for seller-side issue registers, buyer-side closing packages, committee escalation memos, transition reviews, and deviation matrices. Use when Codex must act as deal counsel reviewing an asset purchase, stock purchase, or merger agreement by gathering deal records, terms, playbook rules, risk estimates, employee data, consents, regulatory facts, benchmarks, cap tables, material contracts, and diligence findings from a running workbench and assembling the output into prescribed JSON schemas.
---

# M&A Deal Workbench

## Overview

Use the workbench to gather deal data, compare draft terms against playbook or policy thresholds, compute quantified exposures, and produce structured JSON deliverables. All tasks share a common two-phase pattern: gather records from the REST API and SQL endpoint, then assemble outputs by comparing draft values against preferred and fallback positions.

## Two-Phase Workflow

### Phase 1 — Gather

Collect every source record the task prompt identifies. Start with parallel GET calls to the core endpoints then fill gaps.

Core records to gather for any task:

- **Deal record**: `GET /api/deals/{deal_id}` — headline purchase price, parties, deal type, signing date.
- **Draft terms**: `GET /api/deals/{deal_id}/terms` — current term_id, category, draft values (percentages, months, amounts, clause refs).
- **Playbook rules** (seller or buyer): `GET /api/playbooks/{playbook_id}/rules` — preferred and fallback thresholds per term category.
- **Committee policies**: `GET /api/policies`, `GET /api/policies/{policy_id}/thresholds` — hard caps and required triggers.
- **Risk estimates**: `GET /api/deals/{deal_id}/risk-estimates` — quantified low/high exposure per risk source.
- **Employees**: `GET /api/deals/{deal_id}/employees` — headcounts, PTO liabilities, service-credit eligibility, WARN risk.
- **Consents**: `GET /api/deals/{deal_id}/consents` — closing-condition, notice-only, or post-closing consents with contract names and amounts at risk.
- **Regulatory**: `GET /api/deals/{deal_id}/regulatory` — HSR required, hell-or-high-water, regulatory effort codes.
- **Benchmarks**: `GET /api/deals/{deal_id}/benchmarks` — market median, upper quartile, sample sizes for fee, survival, and cap metrics.
- **Notes**: `GET /api/deals/{deal_id}/notes` — negotiation history or open items.
- **Cap table** (SPA/stock deals): `GET /api/deals/{deal_id}/cap-table` — holder groups, security classes, fully-diluted percentages, as-converted shares.
- **Material contracts**: `GET /api/deals/{deal_id}/material-contracts` — contract IDs, names, annual revenue, condition type.
- **Diligence findings** (buyer-side): `GET /api/deals/{deal_id}/diligence-findings` — finding IDs, categories, quantified amounts.
- **Documents**: `GET /api/deals/{deal_id}/documents` — document IDs referenced in term gaps.

**Search**: When you need records by attribute, use `GET /api/search` with query parameters.

**SQL**: When a task requires cross-table joins, use `POST /api/query` with `{"token": "deal-workbench-readonly", "sql": "<single SELECT or WITH statement>"}`. Prefer API GET calls; reach for SQL only when a cross-entity join is needed.

### Phase 2 — Assemble

For every issue or deviation the task requires:

1. Match each draft term to its playbook rule or policy threshold.
2. Treat any term the playbook requires but the draft omits as `missing_required_term`.
3. Compare draft values (percentages, months, amounts) against preferred and fallback thresholds.
4. Compute deltas: `draft_value - fallback_value` for excesses, `fallback_value - draft_value` for shortfalls.
5. Pull quantified risk from risk-estimates records and benchmark positions from benchmarks records.
6. Use the headline purchase price from the deal record as the basis for all dollar calculations unless a record explicitly states a different basis.
7. Classify each issue with the enums the output template specifies (risk_rating, issue_status, recommended_action).
8. Sort the issue register: highest negotiation priority first. Use risk severity and dollar exposure as primary sort keys; when a template prescribes a priority_order, produce that.

## Data Conventions

When the template provides conventions, follow them exactly. When it is silent, use these defaults:

- **Currency**: integer USD (no cents, no commas).
- **Percentages**: the template will specify decimal precision (commonly two decimal places for percent points, one or four for holder percentages). Use the precision the template states.
- **Months**: integer months.
- **Dates**: ISO 8601 `YYYY-MM-DD`.
- **Source IDs**: stable workbench IDs (term_id, consent_id, contract_id, employee_id, finding_id, risk_estimate_id, document_id). Never invent IDs.

See [references/output_conventions.md](references/output_conventions.md) for detailed calculation rules.

## API Reference

The complete endpoint catalog is in [references/workbench_api.md](references/workbench_api.md). Load it when you need the full list of available routes, query parameters, or the exact SQL schema.

## Task-Type Guidance

### Seller Issue Register

Review the buyer draft against the seller playbook. For every term the playbook addresses: if the draft is absent, mark it `missing_required_term`. If the draft exceeds preferred or fallback limits, compute deltas and recommend `revise` or `add`. Include the priority_order array and summary_metrics object.

### Buyer Closing Package

Merge the economics, indemnity, escrow, NWC, consents, material contracts, employment covenants, restrictive covenants, D&O tail, and regulatory data into the template sections. Compute holder allocations from cap-table data. The `closing_readiness` block synthesizes blockers and tradeable issues.

### Committee Escalation Memo

Filter draft terms to only those that exceed policy thresholds. Exclude in-policy terms and non-committee distractor categories from the escalation list. Include benchmark support where the workbench provides it. The `aggregate_summary` tallies escalated counts, risk breakdown, and exposure components.

### Transition / Carveout Review

Focus on separation terms: IP/domain transition, TSA scope/duration/fees, employee continuity/field selection, Section 1060 allocation, transfer taxes, consent conditions, outside-date extension, and governing law. Every transition issue gets a matching redline entry.

### Deviation Matrix

Compare buyer positions on indemnity cap/basket, survival/knowledge qualifiers, materiality scrape, escrow/holdback, consents, HSR, and material contracts. Classify each as in_policy, draft_below_playbook, or missing_required_term. Produce closing_blockers and risk_totals blocks.

## Output Requirements

- Return only valid JSON. No prose outside the JSON object.
- Conform strictly to the schema in `input/payloads/answer_template.json` — same structure, same field names, same enum values.
- When the template provides a `possible_issue_ids` or `stable_issue_ids` list, use only those IDs.
- Sort arrays as the template instructs (by issue_id, priority, or redline_id).
- Include every required top-level field and every required issue-object field, even when the value is null.
