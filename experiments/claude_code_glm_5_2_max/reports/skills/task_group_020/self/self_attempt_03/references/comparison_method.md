# Comparison & Quantification Method

How to turn draft terms + a governing standard into classified, quantified issues. The standard is either a **playbook** (negotiation positions: preferred + fallback) or a **policy** (committee thresholds: restricted_flag + approval_required). The comparison differs only in which boundary you test against.

## Matching

Match each **current** draft term (`staleness_flag="current"`) to the standard rule/threshold by **`category`**. Examples of recurring categories: `financing_condition`, `reverse_break_fee` / `reverse_termination_fee`, `indemnity_cap`, `indemnity_basket`, `survival_period` / `rw_survival`, `escrow`, `non_compete_non_solicit`, `employee_continuity`, `transition_services`, `tax_allocation`, `governing_law_forum`, `consent_condition`, `materiality_scrape`, `hsr_covenant`, `fiduciary_out`, `mae_carveouts`, `termination_fee`, `voting_agreements`.

If the deal uses a playbook, compare against that playbook's rules only (scope by `playbook_id`). If it uses a policy, compare against that policy's thresholds only (scope by `policy_id`). Never mix standards.

## Issue-status classification

The `issue_status` enum (common values): `in_policy`, `out_of_policy`, `missing_required_term`, `draft_exceeds_playbook`, `draft_below_playbook`. Apply the rule that fits the standard:

### Playbook reviews (issue register / transition review / deviation matrix / closing package)

Direction depends on whose side you are on and whether "bigger" hurts or helps. Think in terms of the side's exposure: a **seller** wants lower caps/escrow/fees and shorter survival; a **buyer** wants higher caps/escrow and longer survival. "Exceeds" always means the draft is **harsher than the side's fallback allows**; "below" means weaker than the side's preferred.

| Draft vs playbook | `issue_status` |
|---|---|
| Draft at or inside preferred | `in_policy` |
| Draft between preferred and fallback (conceded but acceptable) | `in_policy` or `draft_below_playbook` per template |
| Draft beyond fallback (harsher than the side will accept) | `draft_exceeds_playbook` |
| No current draft term, but the side's position requires one | `missing_required_term` (`source_term_ids: []`) |

- For a **seller** reviewing a buyer draft: a buyer-proposed cap/escrow/fee/survival **above the seller's fallback `limit_value`** → `draft_exceeds_playbook`.
- For a **buyer** reviewing a seller draft: a seller-proposed cap **below the buyer's fallback minimum** or survival **shorter than fallback** → `draft_below_playbook` (or `draft_exceeds_playbook` if the template frames buyer protection as the boundary).
- Always re-check the template's own enum definitions; some templates name the same condition differently.

### Policy / committee reviews (escalation memo)

Escalate **only** `restricted_flag="yes"` thresholds whose draft breaches `threshold_value`. Classification:

| Draft vs policy threshold (restricted) | Escalate? | `issue_status` |
|---|---|---|
| Draft breaches threshold | yes | `out_of_policy` |
| Draft at/inside threshold | **no — exclude** | (in_policy; not in output) |
| `restricted_flag="no"` term | **no — exclude** | non-committee distractor |
| `approval_required` below committee | **no — exclude** | distractor |
| Stale row | **no — exclude** | distractor |

Excluded terms belong only in the aggregate's `excluded_in_policy_*` lists if the template asks for them — never in the escalation list.

### Missing-term issues

When the side's position requires an affirmative provision and the draft is silent (no current term for that category), emit `missing_required_term` with `source_term_ids: []`. Justify from surrounding data: e.g., a carveout with customer consents at risk needs a customer-consent closing condition; a TSA with stranded costs needs a fee/cost mechanic; an APA needs a §1060 allocation and a transfer-tax split. Common in transition reviews (IP/domain, outside-date extension, §1060, transfer tax) and seller issue registers.

## Quantification

### Value base (read the `basis` field — do not assume)

| `basis` value | Base field on the deal record |
|---|---|
| `purchase price` | `headline_value` |
| `equity value` | `headline_value` |
| `enterprise value` | `headline_value` (unless a distinct EV is recorded) |
| `upfront cash` | `upfront_cash` |
| `identified findings` / a specific finding or consent | that record's `amount` / `amount_at_risk` |
| `fully diluted shares` | sum of `cap_table.as_converted_shares` |

`amount_dollars = percent_points × base`, rounded to **integer USD** (round half up). If a `draft_value` prose string states an explicit dollar amount on a different basis, use the stated amount verbatim.

### Deltas

- `delta_to_fallback_dollars` = draft_amount − fallback_amount (signed per template; usually the excess exposure).
- `delta_to_fallback_months` = draft_months − fallback_months.
- `shortfall_to_fallback_usd` / `shortfall_to_preferred_usd` = preferred/fallback amount − draft amount, when the draft is below the side's minimum (buyer-protection framing).

Sign convention: follow the template's field name. When unclear, compute the magnitude that represents the side's unmet protection and let the field name carry the direction.

### Risk estimates → exposure totals

`risk_estimates` rows give `exposure_low` / `exposure_high` by category. For `total_quantified_exposure_low_dollars` / `_high_dollars`:
- **Include** only the categories the task names (commonly `closing certainty` + `indemnity leakage`).
- **Exclude** the rest (commonly `transition disruption` unless the task is a transition review).
- Sum the included `exposure_low` for the low total and `exposure_high` for the high total.
- Record what was included/excluded in the template's `included_exposure_components` / `excluded_exposure_components` if present.

## Benchmark positioning

From `/api/deals/<id>/benchmarks`, match the benchmark `category`/`metric` to the issue. Set `position`:

| Draft vs benchmark | `position` |
|---|---|
| `numeric_value` ≤ `median_value` | `at_or_below_median` |
| between `median_value` and `upper_quartile` | `between_median_and_upper_quartile` |
| ≈ `upper_quartile` | `at_upper_quartile` |
| > `upper_quartile` | `above_upper_quartile` |
| no matching benchmark | `not_applicable` |

Carry `sample_size`, `median`, `upper_quartile` into the output where the template asks.

## Risk rating & recommended action

- `risk_rating`: start from the rule's `risk_default` (Medium/High etc.), then adjust by dollar exposure and severity — a draft far beyond fallback with large quantified exposure is HIGH; a minor within-fallback gap is LOW.
- `recommended_action`: choose from the template enum (`delete`, `revise`, `add`, `accept`, `escalate`, `approve`, `approve_with_conditions`, `reject`) guided by the rule's `required_action` prose. Missing terms → `add`; beyond-fallback drafts → `revise` or `escalate`; in-policy drafts → `accept`/`approve`.

## Aggregation

Compute only the metrics the template's summary block lists. Recurring ones:
- `issue_count`, `high_risk_count`, `medium_risk_count`, `out_of_policy_issue_count`, `missing_required_term_count`, `draft_below_playbook_count`.
- `headline_value_dollars`, `total_quantified_exposure_low/high_dollars`, `total_negotiation_delta_dollars`.
- `required_closing_consent_count` (count of `consents.required_for_closing="yes"`) and `required_consent_amount_at_risk` (sum of their `amount_at_risk`).
- `material_contract_revenue_requiring_consent` (sum of `annual_revenue` for `consent_required="yes"` contracts).
- `total_employee_count` (sum of `employees.count`), `total_pto_liability_dollars` (sum of `pto_liability`).
- `closing_blocker_count` and per-blocker `amount_at_risk`/`annual_revenue`.
- `highest_modeled_exposure_category` — the risk-estimate category with the largest `exposure_high` among included components.

Re-read the template's metric field list for each task — names and required breakdowns differ across the five deliverable shapes.
