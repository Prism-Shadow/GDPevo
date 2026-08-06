# Reconciliation, classification, and quantification

## Perspective controls the direction of every comparison

Read `client_side` from the deal record and confirm it against the persona in the prompt.
The same draft number is a win on one side and a gap on the other.

- **Seller-side** wants: lower escrow, lower indemnity cap, shorter survival, no financing
  condition, a reverse break fee that is *higher*, narrow restrictive covenants, employee
  continuity and PTO honored, mutually-agreed allocation, hell-or-high-water regulatory
  efforts, outside-date extension rights.
- **Buyer-side** wants: higher indemnity cap, longer survival, full materiality scrape,
  escrow with a real release trigger, consent closing conditions, HSR condition, founder
  non-competes, D&O tail at seller expense.

"Worse than standard" therefore means *below* the standard for the party seeking more and
*above* it for the party seeking less. Decide the direction before you compute a delta.

## Issue status decision table

Applied per issue, after filtering to `staleness_flag == "current"`:

| Situation | `issue_status` | `source_term_ids` | Typical action |
|---|---|---|---|
| No current term, and deal data shows the protection is needed | `missing_required_term` | `[]` | `add` |
| Term exists, meets or beats preferred | `in_policy` | term IDs | `accept` |
| Term exists, sits between preferred and fallback | `draft_below_playbook` (client wants more) or `draft_exceeds_playbook` (client wants less) | term IDs | `revise` |
| Term exists, past the fallback bound | `out_of_policy` | term IDs | `revise` / `escalate` / `reject` |
| Policy marks the category restricted or committee-approval | `out_of_policy` | term IDs | `escalate` / `approve_with_conditions` |

`draft_exceeds_playbook` vs `draft_below_playbook` describes the draft's position **relative
to the client's standard**, not raw numeric direction. State which you mean and stay
consistent across the whole answer.

Only emit `in_policy` rows when the template asks for full coverage. Escalation-style
templates ask you to *exclude* in-policy, stale, and non-committee terms and list them in a
separate `excluded_*` array instead — read the template's own instruction.

## Risk rating

Start from the standard's `risk_default` for the matched category, then adjust:

- **HIGH** — blocks closing (unobtained consent that is `required_for_closing`, missing HSR
  condition, financing condition on a seller deal), or quantified exposure that is large
  relative to headline value, or the policy flags the category restricted.
- **MEDIUM** — economic leakage inside a bounded range; a term between preferred and
  fallback; a missing protection with a modest or unquantified footprint.
- **LOW** — drafting or forum cleanups with no economic consequence.

Uppercase for output; sources use `High`/`Medium`/`Low`.

## Quantification

**Resolve the base from the rule's own `basis` string, every time.**

| `basis` text | Base |
|---|---|
| `purchase price`, `equity value`, `enterprise value` | deal `headline_value` |
| upfront / cash consideration | deal `upfront_cash` |
| identified findings | sum of the relevant `diligence_findings.amount` |
| `material contracts` | contract counts or `annual_revenue`, per the rule's unit |
| `general representations`, `continuing employees`, `post-closing operations`, `indemnity claims` | qualitative — no dollar base |

Then:

```
amount            = round(percent_points / 100 * base)
shortfall_to_X    = max(0, X_amount - draft_amount)       # client wants more
excess_over_X     = max(0, draft_amount - X_amount)       # client wants less
delta_to_fallback = fallback_amount - draft_amount        # signed; state the convention
delta_months      = required_months - draft_months
```

Round to integer dollars at the end, once. Never round an intermediate percentage.

When a template offers both `..._to_fallback` and `..._to_preferred`, compute both from the
same draft value — they differ only in the target.

Where a template asks for an amount that the workbench does not support, emit `null` or the
template's explicit "not quantified" enum (`not_quantified`, `amount_not_in_workbench`,
`not_found_in_current_records`, `open_item`). Those enums exist precisely so you do not
invent a number; using them is a correct answer, not a punt.

## Exposure aggregation

Use `risk_estimates` rows, keyed by `category`, and sum `exposure_low` / `exposure_high`
**only over the categories the template says to include**. Escalation templates require you
to list `included_exposure_components` and `excluded_exposure_components` explicitly — the
excluded ones are real rows you deliberately left out, so name them rather than dropping
them silently. Do not blend a risk-estimate range with a separately computed shortfall
unless the template defines a combined total.

## Benchmarks

Match by `metric`/`category`, then classify position with the template's own enum, e.g.
`at_or_below_median`, `between_median_and_upper_quartile`, `at_upper_quartile`,
`above_upper_quartile`, `not_applicable`. Compare against `median_value` and
`upper_quartile`; boundaries are inclusive at the named point. Carry `sample_size` through
when the template asks — it is the credibility of the comparison.

## Closing blockers vs tradeable issues

- **Blocker** — `consents.required_for_closing == "yes"`; a material contract whose
  `consent_required == "yes"` and whose revenue is material; a required regulatory clearance
  with no closing condition in the draft. These drive `NOT_READY` /
  `READY_WITH_CONDITIONS`.
- **Notice-only / non-blocking** — `consent_required == "notice only"`, or consents with
  `required_for_closing == "no"`. List them in the non-blocking array; do not count them in
  blocker totals or amounts at risk.
- **Tradeable** — economic terms inside the negotiable band. Deal notes often say outright
  which protections the business treats as must-have; that text should decide the split.

## Priority ordering

Highest first: closing-certainty blockers → largest quantified exposure → structural
protections without a dollar figure → drafting cleanups. The array must be a permutation of
exactly the issue IDs you emitted — no extras, no omissions, no duplicates.

## Aggregate consistency

Before emitting, verify each of these against your own rows:

- `issue_count` / `escalated_term_count` / `position_issue_count` == array length
- `high_risk_count` + `medium_risk_count` (+ low) == total, per your emitted ratings
- status counts (`out_of_policy_issue_count`, `missing_required_term_count`, …) == tallies
- `*_consent_amount_at_risk` == sum over the consents you listed as closing conditions
- `material_contract_revenue_*` == sum over the contracts you conditioned
- `total_employee_count` == sum of `employees.count`; `total_pto_liability` == sum of
  `pto_liability` — over the groups the template scopes (all vs continuing only)
- `headline_value` == the deal record's value, unmodified
- `business_outcome_count` == number of **distinct** business outcomes across your rows
- holder allocations sum to the total consideration, and `fully_diluted_pct` sums to 1.0
