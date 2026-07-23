---
name: deal-workbench-ma-json
description: Prepare strict JSON legal-analysis outputs from an M&A deal workbench. Use when a task asks counsel to review buyer-side or seller-side draft M&A terms, compare them against a playbook or M&A committee policy, quantify economics, closing, consent, employee, regulatory, indemnity, escrow, transition, or committee risks, and return only JSON conforming to a provided answer template.
---

# Deal Workbench M&A JSON

## Workflow

1. Read the user prompt and the provided answer template before querying data. Extract the deal ID, client side, transaction type, requested work product, required units, enum values, stable issue/redline IDs, ordering rules, and whether the comparison source is a playbook or committee policy.
2. Use only the base URL, token, and endpoints authorized by the task environment. Start with `GET /api/deals/<deal_id>`, then follow the requested records through the deal links or documented routes.
3. Fetch all record families that could affect requested fields: `/terms`, `/benchmarks`, `/risk-estimates`, `/consents`, `/employees`, `/material-contracts`, `/regulatory`, `/diligence-findings`, `/cap-table`, `/documents`, and `/notes`. Fetch `/api/playbooks/<playbook_id>/rules` for playbook comparisons and `/api/policies/<policy_id>/thresholds` for committee/policy comparisons.
4. If cross-table checks are useful and the task permits SQL, call `POST /api/query` with the provided read-only token and a JSON body like `{"token":"...","sql":"select ... "}`. Use SQL for filtering, joins, counts, sums, and schema checks; do not use it to bypass endpoint restrictions.
5. Work only on the exact `deal_id`. Do not borrow facts from similarly named projects, related examples, or other deals.
6. Build the JSON directly from the answer template. Preserve field names, nesting, types, enums, and requested ordering exactly. Return no prose outside the JSON.

## Source Handling

- Treat `deals` as the authoritative source for client names, counterparty, target, signing/meeting dates, currency, headline value, upfront cash, stock value, milestone value, playbook ID, policy ID, status, and transaction type.
- Treat `draft_terms` with `staleness_flag: current` as the current draft. Exclude stale terms unless the template asks to identify excluded or stale rows.
- Use stable source IDs from the workbench: `term_id`, `consent_id`, `contract_id`, `finding_id`, `estimate_id`, `document_id`, and `employee_id`. Use empty arrays for genuinely missing draft terms. Create synthetic IDs only when the template explicitly permits them.
- Treat `numeric_value`, `unit`, and `basis` as normalized metrics; read `draft_value`, `counterparty_rationale`, and `clause_ref` for text-only positions and legal characterization.
- Use notes, documents, benchmarks, findings, and risk estimates as support. Do not let narrative records override explicit numeric draft terms, playbook rules, policy thresholds, or the deal economics.

## Comparison Rules

- For playbook work, compare current draft terms against the deal's applicable playbook rules from the client side stated in the deal and prompt.
- For buyer-side playbooks, draft terms below buyer minimums, missing buyer protections, narrowed remedies, inadequate escrows, waived consents, missing HSR conditions, and employee disclaimers are issues.
- For seller-side playbooks, draft terms that impose excessive caps, escrows, survival periods, buyer optionality, financing conditions, broad consent conditions, underpriced transition services, employee cherry-picking, or below-cost support are issues.
- Use `limit_value` and `limit_unit` as normalized fallback or threshold values, but parse `preferred_position`, `fallback_position`, `required_action`, and `notes` for additional preferred values, release periods, conditions, and action logic.
- For committee or policy work, include only current draft terms that are out of policy or restricted for the requested approval body. Exclude stale, in-policy, and non-committee distractor terms, but list them in exclusion fields when the template asks.
- Treat a missing affirmative provision as `missing_required_term` when the prompt, template stable IDs, playbook rule, policy threshold, or surrounding deal data show the client position requires it.
- Choose status consistently:
  - `in_policy`: draft satisfies the client position.
  - `draft_below_playbook`: buyer-side draft is below the buyer playbook minimum or fallback.
  - `draft_exceeds_playbook`: seller-side draft exceeds the seller playbook cap, duration, scope, or fallback.
  - `out_of_policy`: draft violates a policy threshold or restricted policy standard.
  - `missing_required_term`: required protection is absent from current draft terms.
- Choose actions consistently: `add` for missing protections, `revise` for terms needing changes, `delete` for adverse provisions to remove, `escalate` for unresolved deviations requiring approval, and `approve_with_conditions` only when the template asks for an approval recommendation and concrete conditions are supplied.

## Issue Identification

- Indemnity: Compare cap, basket, survival, scrape, escrow/holdback, special indemnities, and knowledge qualifiers against playbook or policy. Use diligence findings to support special indemnities, holdbacks, or escrow release conditions.
- Closing certainty: Use financing conditions, reverse fees, required consents, material-contract consents, HSR/regulatory records, outside dates, and closing-condition terms.
- Consents and contracts: Closing blockers usually include consents with `required_for_closing: yes` and material contracts with `consent_required: yes`. Treat notice-only items as non-blocking unless the template says otherwise. Sum `amount_at_risk` for required consents and `annual_revenue` for material contracts requiring consent.
- Employees: Sum employee `count` and `pto_liability` when requested. Include employee IDs where service credit is required, PTO is not honored, WARN risk is relevant, or field selection/cherry-picking affects continuity.
- Regulatory: Use `hsr_required`, `threshold_basis`, `regulatory_approval`, and `hell_or_high_water_required`. If HSR is required and the draft lacks a clearance condition where the client position requires it, classify a missing regulatory condition.
- Cap table and economics: Allocate consideration by holder using `fully_diluted_pct`, `as_converted_shares`, `holder`, and `security_class`. Treat `fully_diluted_pct` as a fraction unless the template explicitly asks for percent points.
- Committee terms: For reverse termination fees, fiduciary outs, representation survival, MAE carve-outs, voting agreements, and similar policy terms, compare current draft metrics to `policy_thresholds`, identify restricted changes, attach benchmark support when available, and quantify only requested exposure components.
- Carveout transition: Evaluate transition services duration, fee model, stranded cost reimbursement, IP/trademark/domain transition, redirects, customer consent termination rights, employee continuity, Section 1060 allocation, transfer-tax allocation, outside-date protection, governing law, and forum. Use missing-term issues and redlines when the seller position requires affirmative provisions.

## Calculations

- Use the deal's `headline_value` as the default purchase-price or equity-value base unless a source explicitly states a different basis such as upfront cash, stock value, milestone value, identified findings, annual revenue, or a specific dollar amount.
- Convert percent points to dollars as `base * percent_points / 100`, then round to integer dollars. Preserve requested percentage precision: percent points are usually one or two decimals; holder percentages usually use four decimals.
- Compute buyer shortfalls as `max(required_or_fallback - draft, 0)` for percentages, months, dollars, or contract counts. Compute seller excesses as `max(draft - allowed_or_fallback, 0)`.
- Compute policy excess as the draft metric minus the policy threshold on the policy basis. For restricted nonnumeric changes, report restricted flags, removed triggers, added carve-outs, or excess counts rather than invented dollars.
- For cap-table allocations, multiply each consideration component by each holder's fully diluted fraction and round integer dollar fields. Ensure holder totals reconcile reasonably to deal totals after rounding.
- For exposure totals, sum only the risk estimate categories requested by the template. Avoid double-counting the same `risk_estimates` category across multiple issues; include low/high estimates in aggregate once per included category.
- For counts, count records or output rows after filtering to the exact requested class, such as current issues, high-risk issues, required closing consents, continuing employees, or closing blockers.

## Output Validation

- Produce valid JSON only. No Markdown, comments, citations, or explanatory prose outside the JSON object.
- Replace every template placeholder with a resolved value, `null`, empty array, or empty object as appropriate. Do not leave instructional strings such as `"stable source ID"` in the output.
- Match enum spellings, boolean style, date format, numeric precision, and nullability exactly. Use JSON booleans for boolean fields unless the template enum requires strings such as `"yes"` or `"no"`.
- Respect template-specific ordering. If no ordering is specified, sort stable issue/redline IDs ascending and order priority lists from highest negotiation or closing risk to lowest.
- Re-parse the final JSON before responding. Check that all required top-level fields are present, all source IDs exist in collected records unless explicitly synthetic, all amount fields are integer dollars, and all percentages/months match the requested precision.
