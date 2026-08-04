 # M&A Deal Workbench Skill

 ## Overview

 This skill covers systematic analysis of M&A transaction documents using a RESTful deal workbench API. You will gather deal records, draft terms, playbook rules, policy thresholds, risk estimates, and supporting diligence data, then produce structured JSON answers conforming to provided answer templates.

 ## API Interaction

 ### Base URL

 The workbench runs at an environment-specific base URL provided as `<TASK_ENV_BASE_URL>` in the prompt.

 ### Core Endpoints

 - `GET /api/deals/<deal_id>` — deal record with headline value, client side, playbook/policy, and transaction type.
 - `GET /api/deals/<deal_id>/terms` — current draft terms with term IDs, categories, numeric values, units, clause references, and staleness flags.
 - `GET /api/playbooks/<playbook_id>/rules` — playbook rules with preferred positions, fallback positions, risk defaults, limit values, and units.
 - `GET /api/policies/<policy_id>/thresholds` — policy thresholds with restricted flags and approval requirements.
 - `GET /api/deals/<deal_id>/risk-estimates` — risk exposure ranges (low/high) by category with estimate IDs.
 - `GET /api/deals/<deal_id>/consents` — third-party consents with amount-at-risk, required-for-closing flags, and risk ratings.
 - `GET /api/deals/<deal_id>/employees` — employee groups with counts, PTO liability, service-credit requirements, and WARN risk.
 - `GET /api/deals/<deal_id>/material-contracts` — material contracts with annual revenue and consent requirements.
 - `GET /api/deals/<deal_id>/regulatory` — HSR and regulatory clearance status.
 - `GET /api/deals/<deal_id>/benchmarks` — market benchmarks with median, upper-quartile, and sample sizes.
 - `GET /api/deals/<deal_id>/diligence-findings` — diligence findings with severity and quantified amounts.
 - `GET /api/deals/<deal_id>/cap-table` — capitalization table with holder names, share counts, percentages, and security classes.
 - `GET /api/deals/<deal_id>/notes` — deal team notes with topics and authors.
 - `GET /api/deals/<deal_id>/documents` — document metadata with types and versions.

 ### Read-Only SQL

 - `POST /api/query` with `Content-Type: application/json`
 - Body: `{"token": "deal-workbench-readonly", "sql": "<SELECT or WITH query>"}`
 - Use for cross-table checks when a single entity endpoint is insufficient.
 - Use single-quote escaping compatible with the shell (e.g., `'"'"'` in bash) or template the JSON body in a language with proper string handling.

 ## Answer Template Conformance

 Every task provides an `input/payloads/answer_template.json`. Study it before gathering data:

 1. **Identify the required output shape.** Templates define top-level fields, array item schemas, and enum values.
 2. **Note unit conventions.** Currency is integer dollars. Percentages are decimal numbers (e.g., `12.50` for 12.5%). Months are integers. Some tasks specify extra precision (e.g., "four decimals" for holder percentages).
 3. **Use allowed enum values exactly as given.** Do not invent new enum strings. If a field expects one of `["LOW", "MEDIUM", "HIGH"]`, use only those.
 4. **Include all required fields in every object.** Even when irrelevant, provide `null`, `0`, `[]`, `false`, or `{}` as appropriate rather than omitting the key.
 5. **Sort arrays as directed** (by `issue_id` ascending, by `priority_rank`, or by `redline_id` ascending).

 ## Cross-Referencing Draft Terms Against Playbook / Policy

 ### Core Method

 1. Load all current draft terms from `GET /api/deals/<deal_id>/terms`. Ignore terms marked `"staleness_flag": "stale"` unless the prompt explicitly says otherwise.
 2. Load the applicable playbook rules (`GET /api/playbooks/<playbook_id>/rules`) or policy thresholds (`GET /api/policies/<policy_id>/thresholds`).
 3. Match each draft term to its playbook rule by `category`.
 4. For every match, determine the issue status:
    - `draft_exceeds_playbook` — draft exceeds the maximum allowed by the playbook (e.g., cap is higher, escrow is larger, survival is longer, fee is bigger).
    - `draft_below_playbook` — draft falls short of the minimum required (e.g., cap is lower, fee is smaller, survival is shorter, fewer consents covered).
    - `in_policy` — draft falls within playbook bounds.
    - `out_of_policy` — draft violates a policy threshold (committee-level review).
 5. For playbook categories with no matching draft term, mark as `missing_required_term` when the surrounding deal data shows the term is needed.

 ### Determining Risk Ratings

 - Use the playbook's `risk_default` for matched categories.
 - For missing terms, assess based on surrounding data: HIGH for consent/financing conditions with large dollar exposure, MEDIUM for standard protections, LOW for administrative provisions.
 - When a draft term exceeds both the preferred and fallback playbook positions by a wide margin, escalate risk to HIGH.

 ### Recommended Actions

 - `delete` when the draft includes a provision the playbook says should not exist (e.g., a financing condition the seller rejects entirely).
 - `revise` when a draft value deviates from the playbook and the position is negotiable.
 - `add` when a required term is missing from the draft.
 - `accept` when the draft is at or within the playbook fallback.
 - `approve` / `approve_with_conditions` / `reject` for committee-level escalations.

 ## Financial Computations

 ### Purchase Price Basis

 - Use the deal's `headline_value` as the purchase price unless a specific term or rule states a different basis (e.g., `enterprise value` or `equity value`).
 - For stock purchases, `headline_value = upfront_cash + stock_value + milestone_value`.
 - Cross-check: compute `headline_value` from components. If they don't match the stated value, use the stated `headline_value` and note the discrepancy.

 ### Dollar Amount from Percentages

 - `amount = round(percentage / 100 * basis_value)` → integer dollars.
 - When the template requires `percent_points` (not percent), `12.0` means 12.0%, not 0.12.

 ### Delta and Shortfall

 - `delta_to_fallback_dollars = draft_amount - fallback_amount` (positive means the draft exceeds fallback).
 - `shortfall_to_fallback_usd = fallback_amount - draft_amount` (positive means the draft is below fallback).
 - Use the convention specified in the template field name.

 ### Holder Allocation (Stock Purchase)

 - Use percentages from the cap table. Verify they sum to 1.000 (or 1.0000).
 - `cash_amount = fully_diluted_pct * upfront_cash` (integer).
 - `stock_amount = fully_diluted_pct * stock_value` (integer).
 - `total_consideration = cash_amount + stock_amount` (integer).
 - Verify that sums of all holders' cash, stock, and total match the deal values.

 ### Quantified Exposures

 - Sum `exposure_low` across included risk estimate categories. Exclude categories the template marks as excluded.
 - Sum `exposure_high` similarly.
 - Do not double-count the same risk estimate across multiple issues in the aggregate summary.

 ## Data Gathering Order

 1. **Deal record** — identifies client side, playbook/policy, and transaction structure.
 2. **Draft terms** — the baseline for comparison.
 3. **Playbook rules or policy thresholds** — the standard to compare against.
 4. **Supporting records** — consents, employees, material contracts, regulatory, risk estimates, benchmarks, cap table, diligence findings, notes.
 5. **SQL** (optional) — for cross-table verification only when a direct endpoint is insufficient.

 ## Task-Type Patterns

 ### Seller Issue Register (APA)

 - Compare buyer's draft APA against the seller playbook.
 - Present issues sorted by `issue_id` or workflow priority.
 - Provide a `priority_order` array ranking issues from highest to lowest negotiation importance.
 - Include `summary_metrics` aggregating issue counts, risk counts, quantified exposures, employee counts, and PTO liability.
 - Treat absent seller-protective terms as `missing_required_term` issues.

 ### Buyer Closing & Economics Package (SPA)

 - Compute holder-level consideration from the cap table.
 - Compare seller's draft against the buyer playbook for indemnity, survival, materiality scrape, escrow, and consent conditions.
 - Categorize closing conditions as required consents, material contract conditions, and non-blocking notices.
 - Address employee service credit, PTO, WARN risk, restrictive covenants, and D&O tail.
 - Classify overall closing readiness with blocker IDs and tradeable issue IDs.

 ### Committee Escalation Package

 - Identify only terms that are out of policy or restricted for committee approval.
 - Exclude stale terms, in-policy terms, and non-committee (e.g., General Counsel) approval items.
 - For each escalated term, provide draft metric, policy metric, delta, benchmark position, exposure, and recommendation with conditions.
 - Aggregate exposure by including the relevant risk categories and excluding non-quantified or excluded categories.

 ### Carveout Transition Review

 - Focus on transition and separation terms: TSA scope/duration/fees, customer consent termination rights, employee continuity/PTO, IP/domain transition, outside date provisions, tax allocation (Section 1060), transfer tax split, and governing law/forum.
 - Treat missing transition provisions as issues.
 - Provide both `transition_issues` and corresponding `required_redlines` with `must_have_terms`.
 - Quantify stranded cost gaps, PTO liability, consent amounts at risk, and transition disruption exposure.

 ### SPA Deviation Matrix

 - Cover the full set of issue IDs defined in the template.
 - Assign `final_position` from the template's allowed enum values.
 - Classify each issue with a `status`, `risk_rating`, and `priority_rank`.
 - List `closing_blockers` separately for consents, regulatory clearances, and material contract consents.
 - Compute `risk_totals` from the position matrix and blocker data.

 ## Common Pitfalls

 - **Using the wrong basis for dollar calculations.** Always check the term's `basis` field and the playbook rule's `basis` field. Some use `purchase price`, others `enterprise value` or `equity value`.
 - **Including stale terms.** Skip terms flagged as `"stale"` unless the prompt specifically asks for them.
 - **Double-counting risk estimates in aggregates.** If two issues share the same risk estimate, include the estimate only once in the aggregate sum.
 - **Missing required template fields.** Every field shown in the answer template must appear in the output, even with null/false/empty values.
 - **Inventing enum values.** Use only the exact strings from the template's `allowed_enums` or inline enum comments.
 - **Computing percentages as fractions.** A `draft_percent` of `8.0` means 8.0 percent points, not 0.08.
 - **Omitting the task_id wrapper.** The judge expects `{"task_id": "...", "answer": <candidate>}` even when the answer template itself contains `task_id`.

 ## Output Discipline

 - Return only valid JSON.
 - Do not include explanatory prose outside the JSON structure.
 - Use stable IDs from the API responses (term IDs, consent IDs, employee IDs, etc.) — do not fabricate identifiers.
 - If the deal record shows a value that differs from the sum of its components, use the deal record's stated value.
