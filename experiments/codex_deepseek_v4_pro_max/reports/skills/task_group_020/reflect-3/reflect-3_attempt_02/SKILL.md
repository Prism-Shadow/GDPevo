 # M&A Deal Workbench — Counsel Review Skill

 ## Overview

 This skill covers structured review of M&A transaction drafts using a deal workbench API. The agent acts as buyer-side or seller-side counsel, comparing current draft terms against playbooks or committee policies, and producing a JSON answer that conforms to a supplied answer template.

 ## When to Use

 - The task provides a `<TASK_ENV_BASE_URL>` pointing to an M&A deal workbench.
 - The prompt references deal IDs (e.g., `PRJ_JUNIPER`), playbook IDs (e.g., `PB_SELLER_A`, `PB_BUYER_A`), or policy IDs (e.g., `POL_MA_2025_A`).
 - An `answer_template.json` is supplied with the task input.

 ## Step 1 — Gather All Deal Records

 Fetch every available endpoint for the target deal. Do not skip any that exist.

 **Core endpoints** (replace `{deal}` with the deal ID):

 | Endpoint | Returns |
 |---|---|
 | `GET /api/deals/{deal}` | Deal metadata (headline value, client side, playbook, etc.) |
 | `GET /api/deals/{deal}/terms` | Current draft terms with numeric values and units |
 | `GET /api/deals/{deal}/consents` | Third-party consents with risk ratings and amounts |
 | `GET /api/deals/{deal}/employees` | Employee groups, counts, PTO liability, service credit |
 | `GET /api/deals/{deal}/regulatory` | HSR status, hell-or-high-water, approval type |
 | `GET /api/deals/{deal}/benchmarks` | Market benchmarks by category |
 | `GET /api/deals/{deal}/risk-estimates` | Low/high exposure ranges by category |
 | `GET /api/deals/{deal}/notes` | Deal-team notes, counterparty rationale |
 | `GET /api/deals/{deal}/documents` | Draft agreements and financial analyses |
 | `GET /api/deals/{deal}/diligence-findings` | Findings with severity and dollar amounts |
 | `GET /api/deals/{deal}/material-contracts` | Contracts with annual revenue and consent requirements |
 | `GET /api/deals/{deal}/cap-table` | Holder breakdown (for stock/merger deals) |

 **Playbook or policy** (fetch every rule, not just the first page):

 - `GET /api/playbooks/{playbook_id}/rules`
 - `GET /api/policies/{policy_id}/thresholds`

 **SQL cross-checks** (if available):

 ```
 POST /api/query
 {"token": "deal-workbench-readonly", "sql": "SELECT * FROM table WHERE deal_id = '{deal}'"}
 ```

 Available tables: `deals`, `draft_terms`, `playbook_rules`, `policy_thresholds`, `benchmarks`, `risk_estimates`, `cap_table`, `consents`, `employees`, `material_contracts`, `regulatory`, `diligence_findings`, `deal_notes`, `documents`.

 Use SQL to confirm row counts and spot-check values, especially when an API response appears truncated.

 ## Step 2 — Understand the Template

 Before building the answer, parse the `answer_template.json` thoroughly:

 1. **Top-level keys**: Identify every required top-level field (e.g., `deal_id`, `client_side`, `issue_register`, `position_matrix`, `economics`, `closing_readiness`).
 2. **Allowed enums**: Note every constrained value (risk ratings, issue statuses, recommended actions, final positions). Never invent a value outside these lists.
 3. **Nested object shapes**: For arrays of objects (e.g., issues, redlines, holders), note every required key and its type.
 4. **Numeric precision rules**: Currency must be integer dollars. Percent points are typically to two decimal places but check the template's `units` block. Months are integers. Dates are `YYYY-MM-DD`.

 If the template provides `stable_issue_ids` or `stable_redline_ids`, use exactly those identifiers — do not invent new ones.

 ## Step 3 — Map Draft Terms to Playbook/Policy Rules

 For each draft term, find the matching playbook rule or policy threshold by `category`. A rule match exists when:
 - The playbook/policy `category` matches the term's `category`; or
 - The playbook/policy covers a category the term belongs to (e.g., an `indemnity_cap` rule matches a term in `indemnity_cap`).

 **Issue status assignment:**

 | Condition | Status |
 |---|---|
 | Draft value is within playbook preferred or fallback range | `in_policy` |
 | Draft value exceeds a playbook ceiling (from the client's perspective) | `draft_exceeds_playbook` |
 | Draft value is below a playbook floor (from the client's perspective) | `draft_below_playbook` |
 | Draft includes a provision the playbook says should not exist | `out_of_policy` |
 | Required term is absent from draft and deal data shows it is needed | `missing_required_term` |

 **Seller-side perspective (PB_SELLER_A):** Seller wants lower caps, shorter survival, smaller escrow, no financing conditions. "Exceeds playbook" means the draft value is higher than the playbook limit.

 **Buyer-side perspective (PB_BUYER_A):** Buyer wants higher caps, longer survival, full materiality scrape, all material consents. "Below playbook" means the draft value is lower than the playbook minimum.

 **Policy thresholds (POL_MA_2025_A, etc.):** Terms flagged `restricted: yes` with `approval_required: "M&A Committee"` are escalations. Stale terms (`staleness_flag: "stale"`) and in-policy terms must be excluded. Only current, restricted, out-of-policy terms go into escalation packages.

 ## Step 4 — Identify Missing Required Terms

 A term is `missing_required_term` only when BOTH conditions hold:
 1. The draft does not contain a term for that category.
 2. Surrounding deal data shows the term is affirmatively needed.

 Examples of data triggers:
 - Consents marked `required_for_closing: "yes"` → a consent closing condition is needed.
 - `hsr_required: "yes"` → an HSR regulatory covenant is needed.
 - Employees with `service_credit_required: "yes"` → employee continuity provisions are needed.
 - A playbook rule exists for the category → the client expects the term.
 - The deal is an asset purchase/carveout → Section 1060 allocation and transfer-tax split are needed.
 - The deal involves IP/assets → IP transition and domain redirect protections are needed.
 - The draft agreement has no governing-law or forum clause → these are always required.

 Do not flag a term as missing solely because it is common practice. There must be a data-backed reason.

 ## Step 5 — Calculate Dollar Amounts and Deltas

 **Base value for calculations:** Use the deal's `headline_value` (total purchase price) unless a term or rule explicitly states a different basis (e.g., "enterprise value," "equity value," "upfront cash"). The basis is recorded in each term's and rule's `basis` field.

 **Dollar from percent:** `int(headline_value * percent / 100.0)` for percent-point values like "14.0%."

 **Delta calculations:**
 - `delta_to_fallback_dollars = draft_amount - fallback_amount` (absolute difference, positive when draft exceeds fallback from client's perspective)
 - `shortfall_dollars`: the amount by which a required fee or provision falls short
 - For missing terms where no draft value exists, use the fallback or preferred value as the shortfall

 **Holder allocation for stock deals:** Each holder's consideration = `headline_value * fully_diluted_pct`. Cash portion = `upfront_cash * fully_diluted_pct`. Stock portion = `stock_value * fully_diluted_pct`. Use `as_converted_shares` from the cap table for allocation.

 ## Step 6 — Build and Validate the Answer

 1. Start with the exact top-level structure from `answer_template.json`.
 2. Populate every required field — use `null` (not omission) for inapplicable scalar fields, `[]` for empty arrays, `{}` for empty objects.
 3. Ensure every enum field uses a value from the template's allowed list.
 4. Use stable source IDs from the workbench: term IDs (`TERM_PRJ_...`), consent IDs (`CNS_PRJ_...`), employee IDs (`EMP_PRJ_...`), contract IDs (`MAT_PRJ_...`), finding IDs (`FND_PRJ_...`), risk estimate IDs (`RSK_PRJ_...`), benchmark IDs (`BM_PRJ_...`), note IDs (`NOTE_PRJ_...`), document IDs (`DOC_PRJ_...`).
 5. Sort arrays as the template instructs (by `issue_id`, by `priority_rank`, or by counsel workflow).
 6. Double-check that every dollar amount is an integer and every percent has the correct number of decimal places.
 7. Confirm that `summary_metrics` / `risk_totals` counts match the issue register content.

 ## Common Patterns by Task Type

 **Issue Register (seller APA review):** Top-level keys are `deal_id`, `client_side`, `issue_register` (array), `priority_order` (array of IDs), `summary_metrics`. Each issue has `issue_id`, `source_term_ids`, `business_outcome`, `issue_status`, `risk_rating`, `recommended_action`, `required_position_code`, and conditional numeric fields.

 **Closing Package (buyer SPA):** Top-level keys are `task_id`, `deal_id`, `economics` (with `holder_allocation`, `indemnity_package`, `escrow`, `nwc_adjustment`), `closing_conditions` (required consents, material contract conditions, non-blocking notices), `covenants` (employment, restrictive, D&O tail), `regulatory`, `closing_readiness`.

 **Committee Escalation (policy review):** Top-level keys are `task_id`, `deal_id`, `memo`, `escalation_terms` (array), `aggregate_summary`. Only include current, restricted, out-of-policy terms. Exclude stale and in-policy terms. Each escalation term compares `draft_metric` against `policy_metric` with a `delta`.

 **Transition Review (carveout APA):** Top-level keys follow the template's `required_output_shape` with stable `issue_ids` and matching stable `redline_ids`. Each issue maps to exactly one redline. The `operational_risk` block includes quantified exposures and closing consent lists.

 **Deviation Matrix (buyer markup):** Top-level keys are `deal_id`, `prepared_for`, `currency`, `position_matrix` (array), `closing_blockers` (array), `risk_totals`. Each matrix entry maps to one of the template's predefined issue IDs with a specific `final_position` enum.

 ## Quick-Reference: Playbook Rules

 ### PB_SELLER_A (seller-side)

 | Category | Preferred | Fallback | Limit |
 |---|---|---|---|
 | financing_condition | No buyer financing condition | RBF ≥ 6% of enterprise value | 6% pts |
 | indemnity_cap | ≤ 10% of purchase price | ≤ 12.5% for verified concentration risk | 10% pts |
 | survival_period | 12 months | 15 months for customer contracts | 15 months |
 | escrow | ≤ 8% of purchase price | ≤ 10% with 12-month release | 10% pts |
 | transition_services | ≤ 6 months | ≤ 9 months if fees cover stranded cost | 9 months |

 ### PB_BUYER_A (buyer-side)

 | Category | Preferred | Fallback | Limit |
 |---|---|---|---|
 | indemnity_cap | ≥ 12% of purchase price | ≥ 10% with special indemnity for findings | 10% pts |
 | survival_period | ≥ 18 months | ≥ 15 months if escrow ≥ 10% | 15 months |
 | materiality_scrape | Full (breach + damages) | Breach-only | — |
 | consent_closing_condition | All material consents required | Top 10 revenue contracts | 10 contracts |
 | employee_service_credit | Credit prior service + honor PTO | Service credit for benefits only | — |
