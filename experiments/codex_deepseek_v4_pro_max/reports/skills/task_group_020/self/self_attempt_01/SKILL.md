 # M&A Deal Workbench Agent Skill

 ## When to use this skill

 Use when the task involves analyzing M&A deal data through a "deal workbench" REST API, preparing structured JSON outputs for seller- or buyer-side deal review. The prompt will reference a deal workbench at a configurable base URL, provide a deal ID and task-specific role, and require JSON output conforming to an answer template.

 ## Workflow overview

 1. **Input discovery** — locate and read `prompt.txt`, `answer_template.json`, and `environment_access.md`.
 2. **Environment setup** — extract the base URL, allowed endpoints, and SQL token from `environment_access.md`.
 3. **Data gathering** — call every API endpoint listed or implied by the prompt; use the SQL endpoint for cross-table checks.
 4. **Analysis** — compare draft terms against playbook rules, identify issues, calculate amounts.
 5. **Output** — produce a single valid JSON object conforming to the answer template.

 ## Step 1: Input discovery

 The working directory contains:

 - `environment_access.md` — base URL and allowed API endpoints.
 - `prompt.txt` — task description, role, deal ID, scope, and suggested API routes.
 - `input/payloads/answer_template.json` — output schema, allowed enums, unit conventions, and required fields.

 Read all three files before making any API calls. The `prompt.txt` identifies the deal ID and client role. The `answer_template.json` defines the exact output shape. The `environment_access.md` provides the infrastructure connection details.

 ## Step 2: Environment setup

 From `environment_access.md`, extract:

 - `GDPEVO_ENV_BASE_URL` — the base URL for all API calls (e.g., `http://task-env:9020`).
 - The list of allowed `GET` endpoints.
 - The `POST /api/query` endpoint details including the read-only token.

 Replace all occurrences of `<TASK_ENV_BASE_URL>` in the prompt with the extracted base URL before making calls.

 The SQL endpoint requires:
 ```
 POST {base_url}/api/query
 Content-Type: application/json
 Body: {"token": "deal-workbench-readonly", "sql": "<SELECT or WITH query>"}
 ```
 Use the SQL endpoint to join records, verify relationships, or extract aggregates that span multiple endpoints. Never use INSERT, UPDATE, DELETE, DDL, or any statement that modifies state.

 ## Step 3: Data gathering

 ### API discovery

 Start with the base endpoint to confirm the workbench is reachable:
 ```
 GET {base_url}/
 ```

 Fetch the deal record to confirm the deal ID and extract the headline purchase price:
 ```
 GET {base_url}/api/deals/{deal_id}
 ```

 Then fetch every endpoint listed in the prompt and any additional endpoints implied by the task scope. Common endpoints include:

 | Endpoint | Purpose |
 |---|---|
 | `/api/deals/{deal_id}` | Deal metadata, purchase price, parties |
 | `/api/deals/{deal_id}/terms` | Current draft terms for playbook comparison |
 | `/api/deals/{deal_id}/benchmarks` | Market benchmarks for negotiation support |
 | `/api/deals/{deal_id}/risk-estimates` | Quantified risk exposure estimates |
 | `/api/deals/{deal_id}/employees` | Employee data for continuity/transition analysis |
 | `/api/deals/{deal_id}/consents` | Third-party consents required for closing |
 | `/api/deals/{deal_id}/regulatory` | HSR, antitrust, and regulatory clearance |
 | `/api/deals/{deal_id}/cap-table` | Capitalization table for holder-level allocation |
 | `/api/deals/{deal_id}/material-contracts` | Material contracts requiring consent or notice |
 | `/api/deals/{deal_id}/diligence-findings` | Due diligence findings affecting terms |
 | `/api/deals/{deal_id}/notes` | Negotiation notes and team commentary |
 | `/api/deals/{deal_id}/documents` | Deal documents |
 | `/api/playbooks` | Available playbook IDs |
 | `/api/playbooks/{playbook_id}/rules` | Playbook rules for term comparison |
 | `/api/policies` | Available policy IDs |
 | `/api/policies/{policy_id}/thresholds` | Policy thresholds for committee escalation |
 | `/api/search` | Search across all records |

 ### Data collection principles

 - **Be exhaustive**: if the prompt mentions or implies an endpoint, fetch it. Missing data leads to incomplete analysis.
 - **Use stable IDs**: every record returned by the API has a stable identifier. Record these IDs exactly as returned.
 - **Cross-reference with SQL**: when relationships between records are unclear from individual endpoints, use the SQL endpoint to join and verify.
 - **Track sources**: for every value placed in the output, note which endpoint and record ID it came from.

 ## Step 4: Analysis methodology

 ### Playbook comparison

 1. Load the playbook rules for the appropriate playbook ID (e.g., `PB_SELLER_A`, `PB_BUYER_A`).
 2. Compare each draft term from `/api/deals/{deal_id}/terms` against the corresponding playbook rule.
 3. Classify each term using the `issue_status` enum:
    - `in_policy` — draft matches or is better than playbook.
    - `out_of_policy` — draft deviates from playbook in a way unfavorable to the client.
    - `draft_exceeds_playbook` — draft goes beyond playbook requirements.
    - `draft_below_playbook` — draft falls short of playbook thresholds.
    - `missing_required_term` — a playbook-required term has no corresponding draft term.

 ### Risk classification

 Assign `risk_rating` (`LOW`, `MEDIUM`, `HIGH`) based on:
 - The quantified exposure from risk estimates.
 - Whether the issue is a closing blocker.
 - The gap between draft and playbook position.
 - Market benchmarks for the term.

 ### Amount calculation rules

 - **Basis**: calculate all dollar amounts from the deal's headline purchase price, unless a specific record explicitly states a different basis.
 - **Currency**: integer USD. Round to the nearest integer dollar.
 - **Percentages**: decimal numbers representing percent points. Round to the precision specified in the answer template (typically two decimal places).
 - **Months**: integer months.
 - **Dates**: `YYYY-MM-DD` format when dates are required.

 ### Priority ordering

 When the template requires a `priority_order` array, rank issues from highest to lowest negotiation priority based on:
 1. Closing blockers (highest priority).
 2. High risk rating.
 3. Largest quantified exposure.
 4. Business-critical outcomes (closing certainty > indemnity exposure > employee transition > everything else).

 ## Step 5: Output construction

 ### Format rules

 - Return **only valid JSON**. No narrative, explanation, or prose outside the JSON object.
 - The JSON must conform exactly to the structure defined in `answer_template.json`.
 - Every string value in the output must be in English.
 - Use the exact enum values from the template's `allowed_enums`.
 - Use the stable issue/term/redline IDs from the template's `possible_issue_ids` or `stable_*_ids` lists.

 ### Required top-level fields

 Every output must include:
 - `deal_id` — the deal ID from the prompt.
 - `client_side` — `"seller"` or `"buyer"` based on the prompt's role description.

 ### Field population rules

 - **Null vs. omission**: if a field is not applicable or data is unavailable, set it to `null`. Do not omit optional fields that exist in the template.
 - **Empty arrays**: use `[]` for empty arrays, not null.
 - **source_term_ids**: use the stable `term_id` values from the terms endpoint. Use `[]` for missing required terms.
 - **source_record_ids**: use stable record IDs from consents, material contracts, employees, or other endpoints.

 ### Summary metrics

 When the template includes `summary_metrics` or aggregate fields:
 - Count issues, risks, and blockers from the register.
 - Sum quantified exposures from individual issues.
 - Extract employee counts and PTO liabilities from employee endpoint data.
 - Extract consent counts and amounts from consents endpoint data.

 ## Common enums reference

 ### risk_rating
 - `LOW` — minimal exposure, below policy thresholds.
 - `MEDIUM` — material exposure but manageable through negotiation.
 - `HIGH` — significant exposure, possible closing blocker, or far outside policy.

 ### recommended_action
 - `delete` — remove the term from the draft.
 - `revise` — modify the term to align with playbook.
 - `add` — insert a missing required term.
 - `accept` — accept the draft as-is.
 - `escalate` — escalate to committee or business lead.
 - `approve` — approve the term for committee review.
 - `approve_with_conditions` — approve only if conditions are met.
 - `reject` — reject the term outright.

 ### issue_status
 - `in_policy` — draft aligns with playbook.
 - `out_of_policy` — draft deviates unfavorably.
 - `missing_required_term` — required term absent from draft.
 - `draft_exceeds_playbook` — draft goes beyond playbook requirements.
 - `draft_below_playbook` — draft falls short of playbook thresholds.

 ### business_outcome
 - `closing_certainty` — affects whether the deal closes.
 - `escrow_economics` — affects escrow amount or release.
 - `indemnity_exposure` — affects indemnification liability.
 - `restrictive_covenants` — affects non-compete/non-solicit scope.
 - `employee_transition` — affects employee continuity.
 - `tax_allocation` — affects tax burden allocation.
 - `governing_law` — affects jurisdiction and forum.
 - `regulatory_efforts` — affects regulatory approval effort.

 ## Error handling and edge cases

 - **Unreachable endpoint**: if an endpoint returns an error, retry once. If it fails again, note the failure and continue with available data.
 - **Missing playbook**: if the playbook endpoint returns no rules for the given playbook ID, check `/api/playbooks` for available IDs and use the closest match.
 - **Missing template values**: if the answer template uses placeholder values (e.g., `null`, `0`, `"string"`), replace them with actual data from the workbench.
 - **Stale placeholder IDs**: if the template contains IDs like `TERM_PRJ_LYRA_00` or `stable_carveout_id`, treat these as format examples, not literal values. Use actual stable IDs from the API responses.
 - **Taxonomy conflicts**: if a template field uses pipe-delimited enums (e.g., `"FULL_BREACH_AND_DAMAGES | BREACH_ONLY | NONE"`), select exactly one value from the pipe-delimited list.

 ## Verification checklist

 Before finalizing the output, verify:

 1. The JSON parses successfully (no trailing commas, valid syntax).
 2. All required top-level fields are present.
 3. Every `issue_id` or `redline_id` is from the template's stable ID list.
 4. All enum values match the template's allowed values exactly.
 5. Dollar amounts are integers, percentages have correct precision, months are integers.
 6. No narrative text appears outside the JSON.
 7. All source term/record IDs reference actual records returned by the API.
 8. Priority ordering is consistent with risk and exposure analysis.
