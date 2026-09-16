---
name: ma-deal-workbench
description: "M&A deal workbench REST API for transactional practice tasks. Use when the task references a configurable base URL for deal endpoints, requires gathering structured M&A data (deals, terms, playbooks, policies, employees, consents, material contracts, regulatory records, diligence findings, risk estimates, benchmarks, notes, cap tables, documents), comparing draft terms against playbook or policy thresholds, and producing structured JSON output conforming to a provided answer template. Covers seller-side APA reviews, buyer-side SPA closing packages, committee escalation memos, carveout transition reviews, and deviation matrices. Use when the prompt mentions an M&A deal workbench, deal IDs like PRJ_*, playbooks like PB_SELLER_A or PB_BUYER_A, or read-only SQL tokens."
license: MIT
compatibility: designed for deepagents-code
---

# M&A Deal Workbench

## Quick Start

The workbench runs at a configurable base URL provided in the prompt. All API responses are JSON. Use the read-only SQL endpoint for cross-table queries when available.

```
TASK_ENV_BASE_URL = <value from prompt>
```

Read the prompt-supplied answer template first to understand the exact output shape required. Then gather all records referenced in the prompt, and map data fields to template slots.

## Workflow

### 1. Read the Answer Template

Load `input/payloads/answer_template.json` (or whichever path the prompt specifies) before making API calls. The template defines the schema, allowed enums, stable IDs, units, and required fields. Never invent new enum values or field names.

### 2. Gather Deal Records

Call the endpoints listed in the prompt. The workbench exposes these standard routes:

| Category | Endpoint |
|---|---|
| Deal meta | `GET /api/deals/<deal_id>` |
| Draft terms | `GET /api/deals/<deal_id>/terms` |
| Playbook rules | `GET /api/playbooks/<playbook_id>/rules` |
| Policy thresholds | `GET /api/policies/<policy_id>/thresholds` |
| Risk estimates | `GET /api/deals/<deal_id>/risk-estimates` |
| Employees | `GET /api/deals/<deal_id>/employees` |
| Consents | `GET /api/deals/<deal_id>/consents` |
| Regulatory | `GET /api/deals/<deal_id>/regulatory` |
| Benchmark data | `GET /api/deals/<deal_id>/benchmarks` |
| Notes | `GET /api/deals/<deal_id>/notes` |
| Cap table | `GET /api/deals/<deal_id>/cap-table` |
| Material contracts | `GET /api/deals/<deal_id>/material-contracts` |
| Diligence findings | `GET /api/deals/<deal_id>/diligence-findings` |
| Documents | `GET /api/deals/<deal_id>/documents` |

See [references/api_reference.md](references/api_reference.md) for the full endpoint catalog, query patterns, and stable-ID conventions.

For cross-table checks, use:

```
POST /api/query
Body: {"token": "deal-workbench-readonly", "sql": "<SELECT or WITH statement>"}
```

### 3. Compare Draft Against Playbook or Policy

Every task centers on comparing current draft terms against a governing rule set -- either a playbook (seller or buyer) or a policy with numeric thresholds.

**Playbook comparison**: Each playbook rule typically provides a preferred position and a fallback position. Classify each term as:
- `in_policy` -- draft meets or exceeds playbook requirements
- `out_of_policy` -- draft contradicts the playbook
- `missing_required_term` -- term is absent from draft but playbook requires it
- `draft_exceeds_playbook` -- draft goes beyond what the playbook allows
- `draft_below_playbook` -- draft falls short of playbook minimums

**Policy comparison**: Policies define numeric thresholds (fee caps, survival months, basket amounts). A term is escalated for committee review when it exceeds a threshold or adds restricted carveouts.

See [references/domain_guide.md](references/domain_guide.md) for playbook interpretation rules, common M&A concepts, and calculation conventions.

### 4. Assign Risk Ratings

Use `LOW`, `MEDIUM`, or `HIGH` exactly as defined in the template. General guidance:
- **HIGH**: Terms affecting closing certainty, indemnity caps well below/above playbook, missing escrow, HSR conditions absent when required, material consent blockers
- **MEDIUM**: Survival periods, basket mechanics, tax allocation, governing law/forum
- **LOW**: Administrative notices, non-blocking consents, minor drafting gaps

### 5. Quantify Dollar Amounts

Calculate all amounts from the headline purchase price found in the deal record unless a record explicitly states a different basis. Rules:

- Currency values: integer USD (round to nearest dollar)
- Percentage values: decimal numbers at the precision the template specifies (one or two decimal places in percent points)
- Time values: integer months or days as the template requires
- Holder allocations: multiply fully-diluted percentages by total consideration components

### 6. Apply Stable Identifiers

Use stable IDs from the workbench records exactly as they appear. Do not invent IDs. Common prefixes:
- `TERM_<deal>_##` for draft terms
- `CNS_<deal>_##` for consents
- `MAT_<deal>_##` for material contracts
- `EMP_<deal>_##` for employees
- `FND_<deal>_##` for diligence findings
- `RSK_<deal>_##` for risk estimates
- `REG_<deal>` for regulatory records
- `DOC_<deal>_##` for documents

### 7. Build Priority Order

Order issues from highest negotiation priority to lowest. Closing-certainty issues (financing conditions, reverse break fees, HSR, consent conditions) rank highest. Economics (escrow, indemnity caps) come next. Administrative and governance items rank lowest.

### 8. Return Only JSON

The final answer must be valid JSON conforming to the template. No narrative, explanation, or markdown outside the JSON object. Escape strings properly and avoid trailing commas.

## Resources

- [references/api_reference.md](references/api_reference.md): Complete workbench API endpoint catalog with response shapes, field meanings, and SQL query patterns.
- [references/domain_guide.md](references/domain_guide.md): M&A domain concepts, playbook interpretation methodology, calculation rules, and common output conventions.
