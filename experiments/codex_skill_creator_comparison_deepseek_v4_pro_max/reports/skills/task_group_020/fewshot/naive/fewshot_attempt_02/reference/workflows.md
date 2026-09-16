# Reusable Sub-Workflows

Each workflow maps to a common task pattern observed in the training set. Use these as methodology guides, not as sources of specific values.

## 1. Seller Issue Register (Playbook Comparison)

**When**: Producing a seller-side issue register that compares the buyer's draft against the seller's playbook.

**Data to fetch**:
- `/api/deals/<deal_id>` — headline value, parties
- `/api/deals/<deal_id>/terms` — draft terms
- `/api/playbooks/PB_SELLER_A/rules` (or the prompt's specified playbook) — seller positions
- `/api/deals/<deal_id>/risk-estimates` — quantified risk ranges
- `/api/deals/<deal_id>/employees` — employee count, PTO, service credit
- `/api/deals/<deal_id>/consents` — closing consent count
- `/api/deals/<deal_id>/regulatory` — HSR status

**Method**:
1. Match each draft term to its corresponding playbook rule by category.
2. For every playbook rule without a matching draft term, create a `missing_required_term` issue.
3. For matched terms, compare the draft value against playbook preferred and fallback values.
4. Classify the deviation: `draft_exceeds_playbook` (buyer overreach), `draft_below_playbook` (buyer has a term but value is too low for seller's position), or `in_policy`.
5. Calculate dollar deltas as (fallback - draft) × headline value for percent-based terms.
6. Assign risk ratings using risk estimates where available; HIGH for closing certainty items and large-dollar caps, MEDIUM for ancillary terms.
7. Order priority: financing/HSR items first, then large-dollar items, then missing structural terms, then revision items, then boilerplate.

**Output shape**: `issue_register` array, `priority_order` array, `summary_metrics` object with issue counts by risk, headline value, total exposure ranges, negotiation delta, consent count, employee count, PTO liability.

## 2. Buyer Closing and Economics Package (Stock Deal SPA)

**When**: Preparing a buyer-side closing and economics package for a stock purchase.

**Data to fetch**:
- `/api/deals/<deal_id>` — headline value, split into upfront/stock/milestone
- `/api/deals/<deal_id>/terms` — draft economics terms
- `/api/deals/<deal_id>/cap-table` — holder breakdown
- `/api/playbooks/PB_BUYER_A/rules` — buyer's playbook
- `/api/deals/<deal_id>/consents` — closing consents
- `/api/deals/<deal_id>/material-contracts` — material contract conditions
- `/api/deals/<deal_id>/employees` — employees, PTO, service credit
- `/api/deals/<deal_id>/regulatory` — HSR
- `/api/deals/<deal_id>/diligence-findings` — NWC, special indemnity
- `/api/deals/<deal_id>/risk-estimates` — risk ranges

**Method**:
1. Build economics section: headline value with upfront/stock/milestone splits from deal record.
2. Calculate per-holder allocation from cap table: `cash_amount = fully_diluted_pct × upfront_cash`, `stock_amount = fully_diluted_pct × stock_value`, `total_consideration = cash + stock`.
3. Build indemnity package: compare draft cap/survival against playbook preferred/fallback. Determine materiality scrape requirement (FULL_BREACH_AND_DAMAGES if buyer prefers it).
4. Build escrow section: use purchase price as basis, 10% at buyer fallback, release at general rep survival expiration.
5. Check for NWC adjustment from diligence findings.
6. Classify consents: closing_condition vs notice_only vs post_closing_covenant.
7. Classify material contracts by consent requirement and annual revenue.
8. Employee section: identify service-credit employees, sum PTO liabilities, flag WARN risk.
9. Restrictive covenants: require non-compete/non-solicit for founders and executives.
10. D&O tail: require 6-year tail at seller expense.
11. Regulatory: HSR yes/no, hell-or-high-water posture, closing condition required.
12. Closing readiness: classify as NOT_READY if any blockers exist; list blocker IDs and tradeable issue IDs.

**Output shape**: `economics`, `closing_conditions`, `covenants`, `regulatory`, `closing_readiness`.

## 3. M&A Committee Escalation (Policy Threshold Review)

**When**: Preparing an escalation package for committee review where terms exceed policy thresholds.

**Data to fetch**:
- `/api/deals/<deal_id>` — deal metadata, headline value
- `/api/deals/<deal_id>/terms` — draft terms
- `/api/policies/<policy_id>/thresholds` — policy thresholds (from prompt's policy_id)
- `/api/deals/<deal_id>/benchmarks` — market comparison data
- `/api/deals/<deal_id>/risk-estimates` — quantified exposure
- `/api/deals/<deal_id>/notes` — negotiation context

**Method**:
1. Build the memo header: deal parties, policy ID, signing/meeting dates, headline value.
2. For each draft term, check if it matches a policy threshold category.
3. A term is escalated when the draft metric exceeds the policy threshold. Exclude:
   - Terms within policy (list in `excluded_in_policy_terms`).
   - Terms subject to a different governance path (list in `excluded_in_policy_categories`).
   - Stale or non-committee distractor terms.
4. For each escalated term, capture:
   - `draft_metric`: the draft's value with unit and basis.
   - `policy_metric`: the policy threshold with approved carveouts or required triggers.
   - `delta`: the numeric difference, plus removed triggers or excess carveout counts.
   - `benchmark`: market position (at_or_below_median, between_median_and_upper_quartile, etc.) when market data exists; `not_applicable` when benchmarks do not cover the term.
   - `exposure`: quantified risk from risk estimates (low/high) for closing certainty or indemnity leakage; `not_quantified` for structural issues.
   - `recommendation`: approve, approve_with_conditions, or reject.
   - `required_conditions`: specific conditions for approval.
5. Aggregate summary: escalated count, excluded terms, risk counts, total quantified exposure, RTF excess, overall recommendation, committee action text, negotiation priority order.

**Output shape**: `memo`, `escalation_terms` array, `aggregate_summary`.

## 4. Carveout APA Transition Review (Separation Terms and Redlines)

**When**: Reviewing a carveout APA for transition and separation provisions.

**Data to fetch**:
- `/api/deals/<deal_id>` — deal metadata
- `/api/deals/<deal_id>/terms` — draft terms for TSA, employee, consent, outside-date
- `/api/deals/<deal_id>/documents` — disclosure schedules, ancillaries
- `/api/playbooks/<playbook_id>/rules` — seller playbook
- `/api/deals/<deal_id>/employees` — field/operations employee data
- `/api/deals/<deal_id>/consents` — customer consents
- `/api/deals/<deal_id>/material-contracts` — material contract revenues
- `/api/deals/<deal_id>/regulatory` — HSR status for outside date
- `/api/deals/<deal_id>/risk-estimates` — stranded costs, disruption estimates

**Method**:
1. Build `transition_issues`: one issue per carveout concern. Covers:
   - Customer consent termination rights (buyer's walk-away right vs seller's closing certainty).
   - Field employee continuity and PTO (buyer cherry-pick vs seller full-offer obligation).
   - Governing law/forum (missing term requiring Delaware with ancillary coverage).
   - IP/domain transition (missing trademark license, domain redirect provisions).
   - Outside date extension (missing seller regulatory extension when HSR applies).
   - Section 1060 allocation (missing mutual agreement method).
   - Transfer tax split (missing 50/50 allocation).
   - TSA scope/duration/fees (draft duration exceeds playbook, fee model mismatch).
2. Normalize each draft value into `draft_value_normalized` and the seller required position into `required_position_normalized`. Use descriptive keys within these objects that match the issue's subject matter.
3. Quantify impact in dollars: stranded cost gaps from TSA risk estimates, PTO from employee records, consent amounts at risk from consent records.
4. Build `required_redlines`: one redline per issue, linking `redline_id` to `related_issue_id`. Each redline specifies `must_have_terms` — the concrete text or provision changes needed.
5. Build `operational_risk`: overall rating, overall posture (accept_as_drafted, revise_before_signing, escalate_to_business_lead, reject), priority order of issues, quantified exposures summary, required closing consent IDs, material contract consent IDs, and protected business outcomes.

**Output shape**: `transition_issues`, `required_redlines`, `operational_risk`.

## 5. Buyer Deviation Matrix (Position Matrix with Blockers)

**When**: Producing a buyer-side SPA deviation matrix covering the core position issues.

**Data to fetch**:
- `/api/deals/<deal_id>` — headline value
- `/api/deals/<deal_id>/terms` — draft terms
- `/api/playbooks/PB_BUYER_A/rules` (or specified playbook)
- `/api/deals/<deal_id>/consents` — required consents
- `/api/deals/<deal_id>/material-contracts` — material contracts
- `/api/deals/<deal_id>/regulatory` — HSR status
- `/api/deals/<deal_id>/diligence-findings` — privacy, special indemnity
- `/api/deals/<deal_id>/risk-estimates` — modeled exposure

**Method**:
1. Build `position_matrix` with one entry per issue_id. The seven canonical issue IDs are:
   - `consent_closing_condition` — buyer needs all material consents as conditions.
   - `hsr_condition` — buyer needs express HSR clearance closing condition.
   - `material_contracts` — buyer needs specific material contract consents.
   - `indemnity_cap_and_basket` — buyer needs cap at least at fallback, plus basket.
   - `survival_and_knowledge` — buyer prefers 18-month survival with knowledge qualifiers.
   - `escrow_holdback_release` — buyer needs 10% escrow with agent and release terms.
   - `materiality_scrape` — buyer position on scrape (FULL_BREACH_AND_DAMAGES, BREACH_ONLY, or NONE).
2. For each issue, determine:
   - `status`: `draft_below_playbook` (draft less protective than playbook), `missing_required_term` (no draft term), `draft_exceeds_playbook` (draft goes further than buyer wants in seller's favor), `in_policy`.
   - `final_position`: a stable enum from the template describing the buyer's fallback position.
   - `priority_rank`: integer 1-N, with closing certainty terms first, then economics, then ancillary.
3. For `indemnity_cap_and_basket`: calculate cap shortfalls (fallback - draft) × headline, special indemnity and privacy amounts from diligence findings.
4. For `survival_and_knowledge`: compare draft months to preferred/fallback. Check whether knowledge qualifiers appear in draft terms (use `not_found_in_current_records` when absent).
5. For `escrow_holdback_release`: check if escrow agent and release terms are found in records (`not_found_in_current_records` when missing).
6. Build `closing_blockers`: one blocker per required consent, regulatory clearance, and material contract consent that must be satisfied before closing. Include amount_at_risk (from consent records) and annual_revenue (from material contract records).
7. Build `risk_totals`: aggregate counts, headline price, exposure ranges, cap shortfalls, consent revenue at risk, and highest exposure category.

**Output shape**: `position_matrix`, `closing_blockers`, `risk_totals`.
