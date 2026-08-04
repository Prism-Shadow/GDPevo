 # M&A Deal Workbench Skill

 ## Overview
 This skill provides reusable instructions for completing structured M&A (mergers and acquisitions) deal analysis tasks using a RESTful deal workbench API. The workbench exposes deal records, draft terms, playbook rules, policy thresholds, and related diligence data through a consistent API surface.

 ## API Conventions

 ### Base URL
 The base URL is provided as `<TASK_ENV_BASE_URL>`. Replace this placeholder with the actual URL before making requests.

 ### Core GET Endpoints
 For any deal with id `<deal_id>`:
 - Deal overview: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>`
 - Draft terms: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/terms`
 - Playbook rules: `GET <TASK_ENV_BASE_URL>/api/playbooks/<playbook_id>/rules`
 - Policy thresholds: `GET <TASK_ENV_BASE_URL>/api/policies/<policy_id>/thresholds`

 ### Supporting GET Endpoints
 - Consents: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/consents`
 - Employees: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/employees`
 - Material contracts: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/material-contracts`
 - Regulatory: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/regulatory`
 - Risk estimates: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/risk-estimates`
 - Benchmarks: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/benchmarks`
 - Deal notes: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/notes`
 - Cap table: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/cap-table`
 - Diligence findings: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/diligence-findings`
 - Documents: `GET <TASK_ENV_BASE_URL>/api/deals/<deal_id>/documents`

 ### Read-Only SQL
 Use `POST <TASK_ENV_BASE_URL>/api/query` with JSON body:
 ```json
 {"token": "deal-workbench-readonly", "sql": "<SELECT or WITH query>"}
 ```
 This is useful for cross-table verification and discovering data not exposed through the primary endpoints.

 ## Data Gathering Protocol

 1. Start by fetching the deal overview to get deal-level metadata: headline value, client side, playbook ID, policy ID, transaction type, signing date, meeting date, and strategic context.
 2. Fetch draft terms to see what the counterparty has proposed.
 3. Fetch the applicable playbook rules (for seller-side or buyer-side guidance) or policy thresholds (for committee escalation tasks).
 4. Fetch all supporting records: consents, employees, material contracts, regulatory data, risk estimates, benchmarks, notes, and diligence findings.
 5. Use SQL queries only for cross-table checks or to discover data not exposed through direct endpoints.

 ## Analysis Framework

 ### Issue Classification
 Compare each draft term against the playbook rule or policy threshold:
 - `in_policy`: Draft matches or is within the playbook/policy range.
 - `out_of_policy`: Draft explicitly contradicts the playbook/policy requirement.
 - `missing_required_term`: A term that the playbook/policy requires but which is absent from the draft.
 - `draft_exceeds_playbook`: Draft value exceeds the playbook maximum (e.g., escrow too high, survival too long).
 - `draft_below_playbook`: Draft value falls below the playbook minimum (e.g., indemnity cap too low).

 ### Risk Rating
 - `HIGH`: Closing certainty risk, regulatory conditions, missing critical protections.
 - `MEDIUM`: Economics at risk, employee transition gaps, material contract exposure.
 - `LOW`: Administrative or clarifying provisions like governing law, tax allocation.

 ### Recommended Actions
 - `add`: For missing required terms.
 - `revise`: For terms that are out of policy or exceed/fall below playbook limits.
 - `accept`: For terms that are in policy.
 - `reject`: For terms that fundamentally violate committee policy.
 - `escalate`: For terms needing business or committee attention.
 - `approve` / `approve_with_conditions`: For committee-approvable deviations.
 - `delete`: For provisions that should be removed entirely.

 ### Priority Ordering
 Sort issues from highest to lowest negotiation priority. Higher priority goes to:
 1. Closing certainty items (financing conditions, HSR, consent conditions)
 2. Material economics (indemnity caps, escrow amounts)
 3. Employee and transition issues
 4. Governance and administrative provisions

 ## Calculation Rules

 ### Dollar Amounts
 - Use the deal's `headline_value` as the purchase price basis unless the draft or policy explicitly states a different basis (e.g., `upfront_cash`, `enterprise value`, `equity value`).
 - All currency values must be **integer dollars** (no cents).
 - Compute percentages as: `round(percentage / 100 * basis_amount)` then floor to integer.

 ### Percentages
 - Express percentages as decimal numbers (e.g., 12.5 for 12.5%, not 0.125).
 - Round to the precision specified in the answer template (typically two decimal places for percent points, four decimals for ownership percentages).

 ### Months
 - Express survival periods, escrow releases, and transition service durations as **integer months**.

 ### Dates
 - Use `YYYY-MM-DD` format.

 ## Holder Allocation (Stock Purchase / Merger)
 When allocating deal consideration across holders:
 - Use `as_converted_shares` / total shares for precise allocation, not the approximate `fully_diluted_pct`.
 - Cash component: `floor(holder_shares * upfront_cash / total_as_converted_shares)`
 - Stock component: `floor(holder_shares * stock_value / total_as_converted_shares)`
 - Adjust the last holder's cash and stock so the totals exactly equal `upfront_cash` and `stock_value`.

 ## Exposure Aggregation
 - When multiple issues share the same risk estimate, do not double-count.
 - Sum unique risk estimate exposures: low = sum of all unique low exposures, high = sum of all unique high exposures.
 - Include only the exposure categories specified in the template.

 ## Answer Format
 - Return **only valid JSON** matching the provided answer template.
 - Use stable, exact source IDs from the workbench for all references (term_ids, consent_ids, contract_ids, employee_ids, finding_ids, estimate_ids).
 - Do not fabricate synthetic IDs unless the template explicitly requires them for items with no workbench source (e.g., a regulatory blocker when no regulatory record ID exists; in that case, use a consistent naming convention like `HSR_<deal_id>`).
 - Every enum value must exactly match one of the allowed values in the template.
 - Do not include explanatory prose, markdown, or commentary outside the JSON.

 ## Common Pitfalls
 1. **Wrong purchase price basis**: Some terms use `enterprise value` or `equity value` instead of `headline_value`. Check the `basis` field on each term and playbook rule.
 2. **Double-counting risk exposure**: When multiple issues map to the same risk estimate, sum exposures once.
 3. **Including stale or in-policy terms in escalation lists**: Filter out terms with `staleness_flag: "stale"` and terms that are within policy thresholds.
 4. **Missing required terms**: Even when no draft term exists, the playbook or policy may imply a required term. Flag these as `missing_required_term`.
 5. **Enum case sensitivity**: All enum values are case-sensitive. Use exact strings from the template.
 6. **Synthetic IDs**: When a blocker has no workbench ID (e.g., missing HSR condition), create a synthetic ID consistently but prefer real workbench IDs.

 ## Task-Type Patterns

 ### Seller Issue Register (e.g., train_001)
 - Compare buyer draft against seller playbook rules.
 - For each playbook rule, check if a corresponding draft term exists and whether it meets the preferred or fallback position.
 - Include all issues from the template's `possible_issue_ids` list that are relevant to the deal.

 ### Buyer Closing Package (e.g., train_002)
 - Compare seller draft against buyer playbook rules.
 - Include holder-level consideration allocation when a cap table is available.
 - Address indemnity, escrow, survival, working capital, consents, regulatory, employment, restrictive covenants, and D&O tail.

 ### Committee Escalation (e.g., train_003)
 - Compare draft terms against policy thresholds.
 - Only include terms that are **out of policy** and require committee approval.
 - Explicitly list excluded in-policy and stale terms.
 - Provide benchmark comparisons for each escalated term.

 ### Transition/Carveout Review (e.g., train_004)
 - Focus on transition services, employee continuity, IP/domain transition, tax allocation, governing law, and closing mechanics.
 - Map draft terms to stable issue IDs from the template.
 - Provide both issue analysis and corresponding redline instructions.

 ### Deviation Matrix (e.g., train_005)
 - Build a position matrix comparing draft against buyer playbook across key SPA terms.
 - Classify each position with a final negotiating stance.
 - Identify closing blockers with type, risk, and amount-at-risk classification.

 ## Quick Reference: Key Fields
 - `headline_value`: Total deal value (purchase price for APA, equity value for mergers).
 - `upfront_cash`: Cash portion of consideration.
 - `stock_value`: Stock portion of consideration.
 - `milestone_value`: Contingent consideration.
 - `playbook_id`: Reference for playbook rules endpoint.
 - `policy_id`: Reference for policy thresholds endpoint.
 - `staleness_flag`: `"current"` or `"stale"`; exclude stale terms from analysis.
