# M&A Deal Workbench — Counsel Task Skill

## When to use

This skill applies whenever you are given a structured M&A transaction counsel task
with a deal workbench that exposes deal records, draft terms, playbooks, policies,
and diligence data through HTTP APIs. The task will ask you to prepare a structured
JSON answer — an issue register, closing package, committee escalation memo,
transition review, or deviation matrix — by gathering facts from the workbench and
comparing them against a playbook or policy.

## Core workflow

### 1. Orient from the prompt

Read the task prompt to extract these invariants:

- **Role and side**: Are you buyer-side or seller-side counsel? This determines which
  playbook or policy to apply and whether draft terms that are absent or one-sided
  are treated as pro-buyer or pro-seller issues.
- **Deal identifier**: The `deal_id` (e.g. `PRJ_XXXXX`) that anchors all API lookups.
- **Transaction type**: Asset purchase agreement, stock purchase agreement, public
  company merger, or carveout APA. The type drives which terms are expected and which
  template sections are in play.
- **Task category**: One of a small set of recurring shapes —

  | Category | What you produce |
  |---|---|
  | Issue register | Per-issue comparison of draft terms against a playbook, with risk ratings, recommended actions, quantified deltas, and a negotiation priority order. |
  | Closing / economics package | Holder-level consideration allocation, indemnity and escrow mechanics, NWC adjustment, required consents, employee and restrictive covenants, D&O tail, regulatory status, and closing-readiness classification. |
  | Committee escalation memo | Filter to *only* the current draft terms that exceed a policy threshold requiring committee approval; exclude in-policy, stale, and non-committee terms. Provide policy comparison, delta, benchmark context, exposure, recommendation, and aggregate summary. |
  | Carveout transition review | Focus on separation terms: IP/domain transition, TSA scope/duration/fees, purchase-price allocation, transfer taxes, employee continuity, outside date, governing law. |
  | Deviation matrix | Position-by-position matrix of buyer positions on indemnity, survival, materiality scrape, escrow, consents, HSR, and material contracts, with final-position enums, closing blockers, and risk totals. |

### 2. Read the answer template first

Every task provides an `answer_template.json` (or schema embedded in the prompt).
Read it **before** gathering data. It defines:

- The exact top-level keys your answer must contain.
- The allowed enum values for every categorical field (`risk_rating`,
  `issue_status`, `recommended_action`, `final_position`, etc.).
- The list of valid `issue_id` values — use only these.
- The precision rules: integer dollars, decimal percent-points to *n* places,
  integer months, holder percentages to four decimals, dates as `YYYY-MM-DD`.
- Which fields are nullable vs. required in every object.

**Never add keys that are not in the template.** If a field is not applicable,
use `null` (JSON null), not a placeholder string or zero — unless the template
explicitly calls for a zero.

### 3. Gather data from the workbench

Use the documented API routes. The base URL is provided as `<TASK_ENV_BASE_URL>`.
The minimum set of endpoints to hit for any task:

| Endpoint | What it provides | Always needed? |
|---|---|---|
| `GET /api/deals/<deal_id>` | Deal metadata, headline value, playbook/policy id, side, signing date | Yes |
| `GET /api/deals/<deal_id>/terms` | Current draft terms with numeric values, clause refs, staleness flags | Yes |
| `GET /api/playbooks/<playbook_id>/rules` | Preferred, fallback, and limit values per category | Yes (playbook tasks) |
| `GET /api/policies/<policy_id>/thresholds` | Committee-approval thresholds per category | Yes (policy tasks) |
| `GET /api/deals/<deal_id>/employees` | Employee groups, counts, PTO liability, service-credit flags, WARN risk | Yes |
| `GET /api/deals/<deal_id>/consents` | Third-party consents needed, amounts at risk, closing requirements | Yes |
| `GET /api/deals/<deal_id>/regulatory` | HSR required, hell-or-high-water, threshold basis | Yes |
| `GET /api/deals/<deal_id>/benchmarks` | Market median, upper quartile, sample size per category | Yes |
| `GET /api/deals/<deal_id>/risk-estimates` | Exposure ranges (low/high) per risk category | Yes |
| `GET /api/deals/<deal_id>/notes` | Deal-team guidance on posture, priorities, counterparty rationale | Yes |
| `GET /api/deals/<deal_id>/cap-table` | Holder names, security classes, share counts, fully-diluted percentages | When holders/structure matter |
| `GET /api/deals/<deal_id>/material-contracts` | Customer/supplier contracts, revenues, consent triggers | When contracts are in scope |
| `GET /api/deals/<deal_id>/diligence-findings` | Findings with amounts, severities, topics | When findings feed terms |
| `GET /api/deals/<deal_id>/documents` | Draft agreement versions, negotiation trackers, financial models | When documents are referenced |

**When the prompt mentions read-only SQL**, use `POST /api/query` with the
provided token for cross-table verification — but the REST endpoints above are
the primary data source and are always sufficient.

### 4. Compare draft against playbook or policy

This is the central analytical step. For each category present in the playbook
or policy, locate the corresponding draft term (match by `category` field).

**Determine `issue_status`:**

| Situation | issue_status |
|---|---|
| Draft numeric value ≤ playbook limit (seller) or ≥ playbook minimum (buyer) | `in_policy` |
| Draft exceeds a playbook ceiling or falls below a playbook floor | `draft_exceeds_playbook` / `draft_below_playbook` |
| No draft term exists but the playbook requires one | `missing_required_term` |
| Draft exists and matches playbook | `in_policy` |

**Seller vs. buyer orientation flips the direction of "exceeds":**

- **Seller-side**: wants *lower* caps, *shorter* survival, *less* escrow, *no*
  financing condition. Draft values *above* the playbook preferred are
  `draft_exceeds_playbook`.
- **Buyer-side**: wants *higher* caps, *longer* survival, *more* escrow,
  *full* materiality scrape. Draft values *below* the playbook preferred are
  `draft_below_playbook`.

**For policy tasks (committee escalation):**
- Only terms whose `restricted_flag` is `"yes"` and whose draft value exceeds
  the `threshold_value` are escalated. In-policy terms, stale terms, and terms
  approved at a lower level are excluded. The template's `excluded_in_policy_terms`
  and `excluded_in_policy_categories` fields should list what you considered but
  did NOT escalate — this proves you reviewed everything.

**Treat absent terms as issues when the data supports it:**
A missing term (`source_term_ids: []`) is an issue when the surrounding deal
data shows the term is needed. Examples: employees exist but no employee-continuity
term; required consents exist but no consent-closing-condition term; HSR is
required but no HSR covenant.

**Use stable identifiers from the workbench:**
- `source_term_ids` must contain the actual `term_id` values returned by the API
  (e.g. `"TERM_PRJ_XXXXX_NN"`). Use an empty array `[]` only for missing terms.
- Consent IDs, employee IDs, finding IDs, contract IDs, and note IDs must match
  the workbench exactly.

### 5. Calculate amounts

**Purchase price basis:** Use `headline_value` from the deal record as the
purchase-price basis for all percentage-to-dollar conversions unless the term
or playbook rule explicitly states a different basis (e.g. "enterprise value",
"upfront cash", "equity value").

**Dollar amounts:** `percentage × headline_value ÷ 100`, rounded to the nearest
integer dollar.

```
draft_amount_dollars = round(draft_percent / 100 * headline_value)
```

**Deltas:** The gap between the draft and the fallback position.

```
delta_to_fallback_dollars = draft_amount - fallback_amount
delta_to_fallback_months  = draft_months - fallback_months   (seller: draft exceeds → positive delta)
```

**Exposure aggregation:** Sum the `exposure_low` and `exposure_high` values from
`/risk-estimates` across the relevant categories. Use these for
`total_quantified_exposure_low_dollars` and `total_quantified_exposure_high_dollars`.

**Employee totals:** Sum `count` and `pto_liability` across all employee groups
in `/employees`. Count `required_for_closing: "yes"` consents for
`required_closing_consent_count`.

### 6. Assign risk, action, and priority

**Risk rating** defaults to the playbook's `risk_default` for that category.
Override based on deal-specific factors:
- `HIGH`: Required consents from top-revenue customers with termination leverage;
  terms where the draft is at the far extreme; regulatory conditions that can
  block closing; financing conditions without adequate break fees.
- `MEDIUM`: Terms where the draft exceeds playbook but a negotiated middle ground
  is likely; missing terms with quantifiable but manageable exposure.
- `LOW`: Standard terms with small deltas; governing law / forum preferences;
  items where counterparty leverage is weak.

**Recommended action** (use only values from the template's enum):
| Situation | Action |
|---|---|
| Remove an unwanted provision | `delete` |
| Modify an existing provision | `revise` |
| Insert a missing required term | `add` |
| Accept the draft as-is | `accept` |
| Escalate to business lead or committee | `escalate` |
| Committee: approve as presented | `approve` |
| Committee: approve with listed conditions | `approve_with_conditions` |
| Committee: do not approve | `reject` |

**Priority order:** Sort issues from highest negotiation priority (must-have
protections, closing blockers, largest dollar exposure) to lowest (nice-to-have
positions, small deltas). The deal notes often signal what the business team
considers must-have vs. tradeable.

### 7. Return JSON — and only JSON

The prompt will say "Return only valid JSON" or "Do not include narrative outside
the JSON." Follow this literally. Your entire response should parse as a single
JSON object conforming to the answer template.

Before returning, verify:
- [ ] Every `issue_id` is from the template's `possible_issue_ids` (or `stable_issue_ids`).
- [ ] Every enum field uses one of the template's `allowed_enums` values.
- [ ] Dollar amounts are integers; percentages are decimal numbers at the specified precision.
- [ ] `source_term_ids` match actual term IDs from the `/terms` endpoint.
- [ ] `priority_order` contains every `issue_id` from `issue_register` exactly once.
- [ ] `summary_metrics` counts are consistent with the `issue_register` contents.
- [ ] No extra keys, no missing required keys.

## Task-type quick reference

### Issue register (seller or buyer APA/SPA review)

1. Get deal → terms → playbook rules.
2. For every playbook rule, find the matching draft term by category.
3. For every draft term not in the playbook, decide if it's benign or an issue.
4. For every playbook rule with no matching draft term, decide if the deal context
   requires it (→ `missing_required_term`) or if it's not applicable (→ omit).
5. Populate the percent/month/amount fields that apply; leave others `null`.
6. Build `priority_order` from highest to lowest negotiation urgency.
7. Compute `summary_metrics` from the register.

### Closing / economics package (buyer SPA)

1. Get deal → terms → cap-table → consents → employees → material-contracts →
   regulatory → diligence-findings → playbook rules.
2. **Economics**: Distribute headline value across holders by fully-diluted
   percentage. Cash/stock split follows the deal's `upfront_cash` and `stock_value`.
3. **Indemnity**: Compare draft cap and survival against buyer playbook minimums.
4. **Escrow**: Determine basis, required percentage, release timeline, and trigger.
5. **NWC**: Check diligence findings for working-capital items; propose collar or
   fixed-price treatment.
6. **Consents**: Classify each consent as `closing_condition`, `notice_only`, or
   `post_closing_covenant` based on `required_for_closing` and contract type.
7. **Material contracts**: Same classification; attach `annual_revenue`.
8. **Employees**: Total continuing employee count, PTO liability, service-credit
   and WARN-risk employee IDs, required action.
9. **Restrictive covenants**: Whether non-compete/non-solicit is required; which
   holder groups must be covered.
10. **D&O tail**: Whether required, period, cost allocation.
11. **Regulatory**: HSR requirement, hell-or-high-water, closing-condition need.
12. **Closing readiness**: `READY` / `READY_WITH_CONDITIONS` / `NOT_READY`.
    Classification depends on blocker count and severity.

### Committee escalation (public company merger, policy-driven)

1. Get deal → terms → policy thresholds → benchmarks → risk estimates → notes.
2. **Filter strictly**: only terms flagged `restricted_flag: "yes"` in the policy
   AND whose draft values exceed the `threshold_value`.
3. **Exclude**: in-policy terms, stale terms, non-committee categories, and
   distractor terms (similar names, different deals).
4. For each escalated term, build the full comparison: `draft_metric`,
   `policy_metric`, `delta`, `benchmark`, `exposure`, `recommendation`,
   `required_conditions`.
5. **Benchmark position**: Compare the draft value to the benchmark median and
   upper quartile. Classify as `at_or_below_median`, `between_median_and_upper_quartile`,
   `at_upper_quartile`, or `above_upper_quartile`.
6. **Aggregate summary**: Include both the escalated count and explicit lists of
   what was excluded — the committee needs to know you reviewed everything.

### Carveout transition review (seller APA)

1. Get deal → terms → playbook rules → employees → consents → material-contracts →
   regulatory → benchmarks → risk estimates.
2. Focus on the eight standard transition issues: customer-consent termination risk,
   employee continuity/PTO, governing law/forum, IP/domain transition,
   outside-date extension, Section 1060 allocation, transfer-tax split, TSA scope/duration/fees.
3. For each issue, capture both the `transition_issues` entry (analysis) and the
   corresponding `required_redlines` entry (the specific contractual fix).
4. `draft_value_normalized` and `required_position_normalized` capture the
   comparison in a structured form; use the same units and shape for both.
5. `operational_risk` aggregates exposures: stranded cost gap, PTO liability,
   consent amount at risk, top-customer annual revenue at risk, transition
   disruption high estimate.
6. Map each exposure to a `business_outcomes_protected` value.

### Deviation matrix (buyer SPA)

1. Get deal → terms → playbook rules → consents → material-contracts → regulatory →
   diligence findings → benchmarks → risk estimates.
2. The seven standard positions: indemnity cap & basket, survival & knowledge,
   materiality scrape, escrow/holdback/release, consent closing condition, HSR
   condition, material contracts.
3. For each position, provide `draft_percent`/`draft_months`/`draft_amount_usd`,
   the corresponding `preferred_*` and `fallback_*` values, and the
   `shortfall_to_fallback_usd` / `shortfall_to_preferred_usd`.
4. `final_position` must be one of the template's position enum values.
5. **Closing blockers**: List every consent, regulatory clearance, or material
   contract that must be satisfied before closing. Each gets a `blocker_type`,
   `must_be_satisfied_before_closing: true`, and a risk rating.
6. **Risk totals**: Aggregate across all positions. `indemnity_cap_shortfall_to_fallback_usd`
   is the gap between the draft cap amount and the buyer's fallback cap amount.
   `total_modeled_exposure_low_usd` and `total_modeled_exposure_high_usd` sum the
   risk-estimate ranges for relevant categories.

## Common pitfalls

1. **Wrong basis for percentage calculations**: Always check the `basis` field on
   each term and playbook rule. Most are `"purchase price"`, but some are
   `"enterprise value"`, `"equity value"`, or `"upfront cash"`. Using the wrong
   basis produces wrong dollar amounts.

2. **Confusing percent values with decimal fractions**: The workbench uses
   percentage-point notation. A draft cap of 18% is `18.0`, not `0.18`.
   Percentages round to the decimal places specified in the template's `units`.

3. **Including stale or distractor terms**: Check `staleness_flag` on draft terms;
   stale terms should not be treated as current draft positions. Similarly,
   playbook rules and policy thresholds from unrelated deal types should not be
   applied.

4. **Omitting the "excluded" lists in committee memos**: The template has explicit
   fields for `excluded_in_policy_terms` and `excluded_in_policy_categories`.
   Populate these — they demonstrate completeness.

5. **Skipping missing terms**: When the playbook requires a provision and the draft
   is silent, this is a `missing_required_term` issue. Do not omit it just because
   there is no `source_term_id` to cite.

6. **Mismatched priority_order**: Every `issue_id` in `issue_register` must appear
   in `priority_order` exactly once, and vice versa. The lengths must match.

7. **Integer vs. float for dollars**: Dollar amounts must be integers. Round to
   the nearest dollar, not to thousands or millions.

8. **Inventing IDs**: Never fabricate term IDs, consent IDs, employee IDs, or
   other stable identifiers. Use only the values returned by the workbench APIs.
