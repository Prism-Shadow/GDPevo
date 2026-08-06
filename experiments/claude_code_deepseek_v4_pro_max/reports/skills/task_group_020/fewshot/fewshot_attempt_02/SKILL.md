# M&A Deal Workbench — Structured Deal Review Skill

## Overview

This skill enables you to act as deal counsel reviewing an M&A transaction using a running **M&A Deal Workbench** REST API. You gather deal records, draft terms, playbook/policy rules, benchmarks, risk estimates, and related diligence data, then produce a structured JSON answer conforming to a task-specific answer template.

## Activation

Invoke this skill when the task involves:
- A deal ID (e.g. `PRJ_*`)
- An M&A deal workbench base URL (provided as `<TASK_ENV_BASE_URL>`)
- An answer template JSON (provided as `input/payloads/answer_template.json`)
- A playbook ID or policy ID for comparison
- Any of these review types: issue register, closing package, escalation memo, transition review, or deviation matrix

## Core Workflow

### Phase 1 — Read the Task Materials

1. **Read the prompt** (`input/prompt.txt`) to understand the deal role (buyer/seller counsel), deal ID, playbook/policy IDs to compare against, and any deal-specific instructions.
2. **Read the answer template** (`input/payloads/answer_template.json`) to understand the exact output schema, allowed enums, stable IDs, and required fields.

### Phase 2 — Gather Deal Data from the Workbench

Use the workbench base URL (`<TASK_ENV_BASE_URL>`) to fetch all relevant records. The API surface includes:

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/deals/<deal_id>` | Deal record (headline value, parties, structure) |
| GET | `/api/deals/<deal_id>/terms` | Current draft terms with term IDs, clause references, values |
| GET | `/api/deals/<deal_id>/benchmarks` | Market benchmark data (sample sizes, medians, quartiles) |
| GET | `/api/deals/<deal_id>/risk-estimates` | Quantified risk estimates with estimate IDs |
| GET | `/api/deals/<deal_id>/consents` | Required third-party consents with counterparties and amounts |
| GET | `/api/deals/<deal_id>/employees` | Employee records with IDs, groups, PTO, service credit |
| GET | `/api/deals/<deal_id>/cap-table` | Capitalization table (holder names, share classes, percentages) |
| GET | `/api/deals/<deal_id>/material-contracts` | Material contracts with IDs, counterparties, revenue |
| GET | `/api/deals/<deal_id>/regulatory` | HSR status and other regulatory facts |
| GET | `/api/deals/<deal_id>/diligence-findings` | Diligence findings with finding IDs |
| GET | `/api/deals/<deal_id>/documents` | Deal documents (governing law, forum, missing provisions) |
| GET | `/api/deals/<deal_id>/notes` | Negotiation notes |
| GET | `/api/playbooks/<playbook_id>/rules` | Playbook rules (preferred, fallback positions per term) |
| GET | `/api/policies/<policy_id>/thresholds` | Committee policy thresholds |

**Read-only SQL** (if available): Use `POST /api/query` with header `Authorization: Bearer deal-workbench-readonly` for cross-table verification. Body: `{"sql": "<query>"}`.

Start by fetching the deal record, terms, and the applicable playbook/policy rules. Then fetch supporting records (risk estimates, employees, consents, regulatory, benchmarks, notes, documents) as directed by the answer template's schema.

### Phase 3 — Compare Draft Terms Against Playbook/Policy

For each relevant term or issue area:

1. **Find the draft term** in `/api/deals/<deal_id>/terms` — note its term ID, clause reference, and numeric values (percentages, dollar amounts, months).
2. **Find the playbook/policy position** in the rules or thresholds endpoint — note the preferred value and fallback value.
3. **Calculate deltas** — draft minus fallback, draft minus preferred, etc.
4. **Classify status** using the answer template's allowed enums:
   - `in_policy` — draft meets or exceeds the playbook position
   - `out_of_policy` — draft violates a policy threshold
   - `missing_required_term` — no draft term exists for a required provision
   - `draft_exceeds_playbook` — draft imposes more burden on your client than the playbook allows
   - `draft_below_playbook` — draft gives your client less protection than the playbook requires
5. **Assign risk ratings** (`LOW`, `MEDIUM`, `HIGH`) based on quantified exposure and closing impact.
6. **Determine recommended actions** (`delete`, `revise`, `add`, `accept`, `escalate`, `approve`, `approve_with_conditions`, `reject`).

### Phase 4 — Compute Dollar Amounts and Metrics

**Always calculate from the deal's headline purchase price** unless a source record explicitly states a different basis.

**Unit conventions** (from the answer template's `units` block):
- Currency amounts: **integer USD** (round to nearest dollar)
- Percentages: **decimal number to the template's specified precision** (typically 1 or 2 decimal places)
- Months: **integer months**
- Holder percentages: to four decimal places when specified

**Calculation patterns:**
- `draft_amount_dollars = headline_value × draft_percent / 100`
- `delta_to_fallback_dollars = draft_amount_dollars - fallback_amount_dollars` (positive when draft is worse for your client)
- `shortfall_dollars = fallback_amount_dollars - draft_amount_dollars` (positive when draft is below playbook)
- `total_quantified_exposure = sum of relevant risk estimate low/high values`
- `negotiation_delta = sum of all deltas between draft and fallback positions`

### Phase 5 — Build the Output

1. **Sort** issue arrays as directed by the template (typically by `issue_id` ascending or by negotiation priority).
2. **Use only stable IDs** from the workbench — term IDs, consent IDs, employee IDs, contract IDs, finding IDs, risk estimate IDs.
3. **Use only allowed enum values** from the template.
4. **Include every required field** from the template, even when the value is `null`.
5. **Return only valid JSON** — no explanatory prose, no markdown fences, no trailing text.
6. **Do not fabricate values** — if a value is not found in the workbench, use `null`, `0`, or `"not_found_in_current_records"` as the template dictates.

### Common Issue Categories

These issue categories recur across deal review types. Map them to the template's `possible_issue_ids` or `issue_id` enums:

| Issue ID | Typical Concern | Playbook Comparison |
|----------|----------------|---------------------|
| Financing condition | Buyer financing contingency | Seller: delete; Buyer: condition on commitment letters |
| Reverse break fee | Fee if buyer fails to close | Compare draft % vs playbook minimum % |
| Escrow / holdback | Post-close security | Compare draft % and release months vs playbook |
| Indemnity cap | Maximum seller/buyer exposure | Compare draft % of purchase price vs playbook cap |
| Indemnity basket | Minimum claim threshold | Check for deductible vs tipping basket |
| Survival period | How long reps survive closing | Compare draft months vs playbook months |
| Non-compete / non-solicit | Restrictive covenants | Check scope, duration, covered parties |
| Employee continuity | Treatment of transferred employees | Service credit, PTO, cherry-pick rights |
| Transition services | Post-close support | Duration, fee model (at-cost vs cost-plus) |
| Tax allocation | Section 1060 / transfer taxes | Mutual agreement vs unilateral |
| Governing law / forum | Dispute resolution venue | Delaware vs other |
| Consent condition | Third-party consent as closing condition | Required vs notice-only |
| Materiality scrape | Indemnity damage calculation | Full breach-and-damages vs breach-only |
| HSR covenant | Antitrust clearance effort | Hell-or-high-water vs reasonable best efforts |

### Cross-Task Patterns

**When the task is an issue register / deviation matrix** (trains 001, 005):
- Compare each draft term against playbook preferred and fallback positions
- Compute deltas, shortfalls, and quantified exposures
- Produce a priority-ordered list
- Include summary metrics (counts, totals, exposures)

**When the task is a closing/economics package** (train 002):
- Extract economics from deal record + cap table
- Allocate consideration across holders proportionally
- Evaluate indemnity, escrow, NWC mechanics
- Assess closing readiness: blockers vs tradeable issues
- Check regulatory status (HSR, hell-or-high-water)

**When the task is a committee escalation memo** (train 003):
- Filter to ONLY out-of-policy or restricted terms
- Exclude in-policy, stale, and non-committee terms
- Provide policy comparison, benchmark support, delta, exposure for each
- Aggregate risk counts, exposure totals, and committee routing

**When the task is a transition/carveout review** (train 004):
- Focus on separation terms: IP transition, TSA, employees, tax allocation, governing law
- Produce paired issue + redline entries with must-have terms
- Compute operational risk: stranded costs, PTO liability, consent amounts at risk

### Error Avoidance

- **Never assume** a provision is present or absent — verify by fetching the terms endpoint.
- **Never mix deal records** — each deal ID has its own data; PRJ_JUNIPER records do not apply to PRJ_ORION.
- **Empty arrays are meaningful** — use `[]` when the template expects an array but no values exist, vs `null` when the field is not applicable.
- **Verify calculations** — recompute dollar amounts from percentages against the headline purchase price; cross-check with risk estimates.
- **Watch for distractor terms** — stale, in-policy, or non-committee terms that should be excluded per the task instructions.
