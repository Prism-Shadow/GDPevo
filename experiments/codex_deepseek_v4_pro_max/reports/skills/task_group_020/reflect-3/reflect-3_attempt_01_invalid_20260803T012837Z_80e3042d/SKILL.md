 # M&A Deal Workbench Skill

 ## Overview
 This skill guides an agent through analyzing M&A transaction records using a deal workbench REST API and read-only SQL endpoint. The workbench models draft agreements, playbooks, policies, diligence records, and risk data for multiple concurrent deals. The agent must gather data from correct endpoints, compare draft positions against playbook rules or policy thresholds, quantify exposures in integer dollars, and produce structured JSON answers conforming to task-specific answer templates.

 ## Environment
 - The base URL is provided via `<TASK_ENV_BASE_URL>` in the task prompt.
 - All API responses are JSON.
 - A read-only SQL endpoint accepts `POST /api/query` with token `deal-workbench-readonly` and a `sql` field containing only SELECT or WITH statements.

 ## Core API Endpoints

 ### Deal Records
 - `GET /api/deals` — list all deals.
 - `GET /api/deals/<deal_id>` — single deal with headline_value, upfront_cash, stock_value, milestone_value, client_side, playbook_id, policy_id, status, and sub-resource links.

 ### Draft Terms
 - `GET /api/deals/<deal_id>/terms` — current draft terms. Each term has: term_id, category, draft_value, numeric_value, unit, basis, source_document, clause_ref, counterparty_rationale, last_updated, staleness_flag.
 - Treat `staleness_flag: "stale"` rows as superseded; exclude them from issue registers and escalation packages unless the task explicitly instructs otherwise.

 ### Playbooks
 - `GET /api/playbooks` — list available playbooks.
 - `GET /api/playbooks/<playbook_id>/rules` — rules with preferred_position, fallback_position, limit_value, limit_unit, basis, required_action, risk_default.
 - Compare each draft term against the corresponding playbook rule by category. A term is `draft_exceeds_playbook` when its numeric value exceeds the rule's limit_value (for caps or maximums). It is `draft_below_playbook` when its numeric value falls below the rule's limit_value (for minimums). It is `out_of_policy` when a boolean or structural provision contradicts the preferred position.

 ### Policies (Committee Thresholds)
 - `GET /api/policies` — list policies.
 - `GET /api/policies/<policy_id>/thresholds` — thresholds with policy_standard, threshold_value, threshold_unit, restricted_flag, approval_required.
 - A term is out of policy when it exceeds a restricted threshold or violates a structural requirement. Exclude stale terms and terms where `restricted_flag` is `"no"` from committee escalation packages.

 ### Sub-Resources (per deal)
 - `GET /api/deals/<deal_id>/employees` — employee groups with count, pto_liability, service_credit_required, warn_risk.
 - `GET /api/deals/<deal_id>/consents` — required and non-required third-party consents with amount_at_risk, risk_rating.
 - `GET /api/deals/<deal_id>/material-contracts` — contracts with annual_revenue, consent_required, anti_assignment, change_of_control flags.
 - `GET /api/deals/<deal_id>/regulatory` — HSR requirement, hell_or_high_water, threshold_basis.
 - `GET /api/deals/<deal_id>/risk-estimates` — exposure_low, exposure_high per risk category.
 - `GET /api/deals/<deal_id>/benchmarks` — market benchmarks for termination economics, indemnity, survival.
 - `GET /api/deals/<deal_id>/diligence-findings` — issues with severity, amount, topic.
 - `GET /api/deals/<deal_id>/cap-table` — holder-level ownership with fully_diluted_pct, as_converted_shares.
 - `GET /api/deals/<deal_id>/notes` — deal team notes with topic, content, author.
 - `GET /api/deals/<deal_id>/documents` — document metadata.

 ## Calculation Conventions

 ### Purchase Price and Basis
 - Default "purchase price" to the deal's `headline_value` in integer dollars unless a draft term or playbook rule explicitly states a different basis (e.g., "enterprise value", "equity value", "upfront_cash").
 - When a term's `basis` field says "purchase price", use headline_value.
 - When a term's `basis` field says "enterprise value" or "equity value", use headline_value unless the deal structure suggests a different equity value (e.g., for public-company mergers where equity value equals headline value as shown by reverse-calculation from a stated fee amount).

 ### Dollar Amounts
 - All currency fields must be integer dollars (no decimals, no commas).
 - Multiply the percentage (as a decimal, e.g., 0.08 for 8%) by the appropriate basis amount, then truncate or round to integer.

 ### Percentages and Months
 - Percentage values (percent_points) to two decimal places unless the answer template specifies otherwise.
 - Month values as integers.
 - Holder percentages to four decimal places when specified by template.

 ## Issue Identification Workflow

 1. **Load the deal record** from `/api/deals/<deal_id>` to determine client_side, playbook_id, policy_id, headline_value, and transaction_type.
 2. **Load draft terms** from `/api/deals/<deal_id>/terms`. Ignore stale rows.
 3. **Load the applicable playbook** from `/api/playbooks/<playbook_id>/rules` (if playbook_id is set).
 4. **Load the applicable policy** from `/api/policies/<policy_id>/thresholds` (if policy_id is set).
 5. **For each current draft term**, compare against the playbook rule with the matching category:
    - If the playbook rule does not exist, mark the term as `out_of_policy` when it contradicts standard seller/buyer protective positions.
    - If the term's numeric value exceeds a cap or maximum limit, status is `draft_exceeds_playbook`.
    - If the term's numeric value falls below a minimum or floor, status is `draft_below_playbook`.
    - If the term's provision contradicts the preferred_position (boolean/structural), status is `out_of_policy`.
    - If the term matches the fallback_position exactly, status is `in_policy`.
 6. **Identify missing required terms**: when a playbook rule or policy threshold exists for a category but no current draft term is present, and the surrounding deal data (employees, consents, regulatory, material contracts) shows the term is needed, mark it as `missing_required_term`.
 7. **Cross-reference supporting data**: use employees for employee continuity issues, consents for consent conditions, regulatory for HSR covenants, material contracts for contract consent requirements, risk estimates for quantified exposures, benchmarks for market context, and diligence findings for special indemnity or working capital issues.
 8. **Compute quantified impacts**: stranded cost gaps from draft-vs-required fee models, PTO liability from employee records, consent amounts at risk from consent records, revenue at risk from material contracts, and exposure ranges from risk estimates.

 ## Risk Rating Guidelines
 - **HIGH**: draft position materially exceeds playbook fallback, or missing required term creates significant closing or indemnity exposure. Playbook rules with `risk_default: "High"` indicate HIGH risk.
 - **MEDIUM**: draft position exceeds playbook preferred but is within fallback range, or missing term has moderate operational impact.
 - **LOW**: in-policy terms, or missing terms with minimal financial exposure.

 ## Answer Construction
 - Always return valid JSON conforming exactly to the provided `answer_template.json`.
 - Include every field listed in the template, using `null` for inapplicable values.
 - Use only the allowed enum values specified in the template.
 - Sort issue arrays as directed (by issue_id ascending unless priority_order is requested).
 - Exclude narrative prose outside the JSON structure.
 - Use stable identifiers (term_id, consent_id, contract_id, employee_id, finding_id, estimate_id) from the workbench as source references.

 ## Common Pitfalls
 - Do not use upfront_cash as purchase price unless a term or rule explicitly designates that basis; default to headline_value.
 - Do not include stale terms in issue registers or escalation packages.
 - Do not include in-policy terms in escalation packages unless the task explicitly requires it.
 - Do not skip the playbook comparison: every current draft term must be checked against the applicable playbook rule.
 - Do not submit exploratory or minimal judge requests; use each round to submit a complete candidate and improve using the returned score.
 - Check the `restricted_flag` on policy thresholds: only terms with `restricted_flag: "yes"` require committee escalation.
