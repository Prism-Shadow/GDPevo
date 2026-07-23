---
name: ma-deal-workbench-json
description: Produce structured JSON M&A deal-workbench outputs for APA, SPA, carveout, closing-readiness, deviation-matrix, seller or buyer issue-register, and M&A Committee escalation tasks. Use when a prompt provides a deal ID, a workbench API/base URL, playbook or policy records, and an answer_template.json that must be filled from deal evidence without narrative prose.
---

# M&A Deal Workbench JSON

## Core Workflow

1. Read the user prompt and the referenced `answer_template.json` before querying data. Treat the template as the output contract: required keys, enum strings, stable issue IDs, rounding rules, sort order, and placeholder meanings come from the template.
2. Extract the exact `deal_id`, client side, transaction type, requested work product, and any named playbook or policy. Use the exact `deal_id` for every record lookup; ignore similarly named projects.
3. Read `environment_access.md` if present. Use only the base URL, token, and endpoints allowed there. Do not use outside network sources.
4. Fetch `/api/deals/<deal_id>` first, then follow its links or fetch the relevant standard endpoints:
   - `/terms`
   - `/documents`
   - `/benchmarks`
   - `/risk-estimates`
   - `/cap-table`
   - `/consents`
   - `/employees`
   - `/material-contracts`
   - `/regulatory`
   - `/diligence-findings`
   - `/notes`
5. Fetch `/api/playbooks/<playbook_id>/rules` for playbook-driven buyer or seller reviews. Fetch `/api/policies/<policy_id>/thresholds` for committee or policy-threshold reviews.
6. Use `POST /api/query` with the read-only token only as a cross-check for joins, counts, or totals that are awkward from individual endpoints. Keep SQL scoped by the exact `deal_id`.
7. Build the JSON only after reconciling draft terms, playbook or policy authority, and supporting records. Return valid JSON only, with no prose outside the object.

## Evidence Rules

- Use only records for the requested `deal_id`.
- Prefer records with `staleness_flag: "current"` for current draft analysis. Exclude stale draft terms unless the template asks for excluded or stale items.
- Use stable source IDs from the workbench: `term_id`, `consent_id`, `contract_id`, `employee_id`, `finding_id`, `estimate_id`, `benchmark_id`, `document_id`, and `note_id`.
- For existing draft issues, put the relevant current `term_id` values in `source_term_ids`.
- For missing required provisions, use an empty `source_term_ids` array and classify the row as `missing_required_term`.
- Treat draft silence as an issue when the prompt, template, playbook, or policy requires an affirmative term, closing condition, redline, escrow, regulatory condition, tax allocation, employee protection, or transition provision.
- Do not invent evidence. If the template asks for a field not available in the workbench, use the template's null, false, empty-array, or "not found" enum pattern.

## Comparing Terms

### Playbook Reviews

Use playbook `category`, `basis`, `preferred_position`, `fallback_position`, `limit_unit`, `limit_value`, `required_action`, and `risk_default`.

- Buyer-side review: buyer-favorable protections below fallback or preferred levels are usually `draft_below_playbook` or `out_of_policy`; missing buyer-required protections are `missing_required_term`.
- Seller-side review: buyer draft terms above seller caps, longer than seller limits, broader than seller accepts, or below seller economics are usually `draft_exceeds_playbook`, `draft_below_playbook`, or `out_of_policy` according to the field.
- Use `in_policy` only when the current draft satisfies the relevant playbook position.
- Use `recommended_action` directionally:
  - `delete` for an adverse term that should be removed.
  - `revise` for an existing term that should be narrowed, raised, lowered, shortened, or otherwise changed.
  - `add` for a missing required term.
  - `accept` for in-policy terms.
  - `escalate`, `approve`, `approve_with_conditions`, or `reject` when the template is an approval or committee package.

### Committee or Policy Reviews

Use policy `approval_required`, `restricted_flag`, `category`, `threshold_unit`, `threshold_value`, `basis`, and `policy_standard`.

- Include only current draft terms that require the requested committee route and breach a restricted policy standard.
- Exclude stale terms, in-policy terms, and non-committee distractors. Populate excluded-term fields when the template requires them.
- Compute threshold amounts from the policy basis and the deal record. Do not assume a basis: use the policy row's `basis` field.
- Classify committee rows as `out_of_policy` unless the template provides a more specific restricted-status enum.
- Recommendation should reflect severity and available conditions: use `approve_with_conditions` for fixable restricted deviations, and `reject` when the deviation cannot be accepted under the policy and evidence.

## Common Issue Mapping

Map by template stable IDs first, then by normalized draft/playbook/policy category.

- Closing certainty: financing conditions, reverse break fees, consent closing conditions, HSR clearance, regulatory covenants, outside dates, and material-contract consents.
- Escrow and indemnity economics: escrow or holdback, indemnity cap, basket, special indemnities, materiality scrape, survival periods, and knowledge qualifiers.
- Employee transition: service credit, continuing employee process, buyer selection rights, PTO allocation, WARN risk, retention, and restrictive covenants.
- Carveout transition: transition-services duration/scope/fees, stranded-cost reimbursement, IP transition, trademark/domain redirects, customer consent termination rights, outside-date extensions, Section 1060 allocation, transfer-tax allocation, governing law, and forum.
- Committee matters: reverse termination fees, fiduciary-out restrictions, representation survival, MAE carve-outs, voting agreements, and any other category marked restricted for committee approval.

## Calculation Rules

- Use `deal.headline_value` as the default purchase-price or equity-value basis unless the prompt, template, term, playbook, policy, or source record states a different basis such as upfront cash, stock value, milestone value, identified findings, or annual revenue.
- Dollar amount from percent points: `round(basis_amount * percent_points / 100)`, then output an integer dollar value.
- Percent points are numbers, not strings. Round to the precision required by the prompt or template.
- Months are integers. Convert numeric month values like `15.0` to `15`.
- Holder allocations use cap-table `fully_diluted_pct` as provided. If values are fractional shares of total ownership, allocate cash and stock by multiplying consideration pools by that fraction and round output dollars to integers. Preserve holder percentages to the requested precision.
- Consent exposure totals normally sum `amount_at_risk` for consents with `required_for_closing: "yes"` unless the template asks for notices or post-closing covenants separately.
- Material-contract revenue totals normally sum `annual_revenue` for contracts with `consent_required: "yes"` or otherwise required as closing blockers. Put notice-only contracts in non-blocking lists when requested.
- Employee counts and PTO totals normally sum the relevant continuing groups from `/employees`; use `service_credit_required`, `warn_risk`, `draft_treatment`, and `playbook_requirement` to decide which IDs require action.
- Risk-estimate totals should use matching `category` values from `/risk-estimates` and avoid double-counting the same exposure under multiple names. If the template asks for low/high aggregate modeled exposure, sum the requested components explicitly and list included/excluded components when fields exist.
- Diligence findings support escrows, special indemnities, NWC collars, privacy/cyber issues, customer concentration, and quantified identified-findings bases.
- Benchmarks support market-position fields. Match by metric/category, carry `sample_size`, `median`, and `upper_quartile`, and classify the draft as at/below median, between median and upper quartile, at upper quartile, above upper quartile, or not applicable.

## Drafting the JSON

- Start from the template shape, but replace every placeholder with evidence-derived values, `null`, `false`, `[]`, or a valid enum.
- Use exact enum strings from the template. Do not emit explanatory labels outside the allowed values.
- Keep stable issue IDs and redline IDs from the template. Do not create new issue IDs unless the template explicitly allows synthetic IDs.
- Sort arrays exactly as instructed by the template. If no sort order is specified, use a counsel workflow order: highest closing or regulatory blockers first, then quantified economic exposure, then operational or drafting cleanup.
- Priority arrays should contain only issue IDs already present in the related issue matrix/register.
- Closing readiness should distinguish blockers from tradeable issues. Required closing consents, HSR clearance, and required material-contract consents are blockers; economics and drafting deltas are usually tradeable unless the prompt says otherwise.
- Validate the final object with a JSON parser before responding. The final answer must be JSON only.
