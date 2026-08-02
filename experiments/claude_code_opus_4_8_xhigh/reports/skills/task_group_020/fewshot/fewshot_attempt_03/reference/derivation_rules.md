# Derivation rules

Rules confirmed by reproducing worked examples end to end. Symbols: `H` =
`deals.headline_value`, `C` = `upfront_cash`, `S` = `stock_value`.

## 1. Money base

Percent-denominated terms convert on `H`:

    amount = round(percent_points * H / 100)

Every stated basis — "purchase price", "equity value", "enterprise value" — maps
to `H`. The workbench publishes no separate equity or enterprise figure, so a
differing `basis` string is descriptive, not a different base. Only depart from
`H` when a record supplies an explicit alternative number (a finding amount, a
prose dollar figure inside `draft_value`).

Consideration splits are the exception: holder cash comes from `C`, holder stock
from `S`.

    holder_cash  = round(fully_diluted_pct * C)
    holder_stock = round(fully_diluted_pct * S)
    holder_total = holder_cash + holder_stock

`fully_diluted_pct` is already a fraction — do not divide by 100. The column sums
to 1.0 across holders; the allocations sum to `C + S`.

## 2. Reading a playbook rule

Each rule carries two prose positions plus a numeric limit:

- `preferred_position` — the client's opening ask
- `fallback_position` — the worst acceptable landing spot
- `limit_value` — matches *one* of the two, and **which one varies by rule**

Parse the numbers out of both prose strings and use `limit_value` only to confirm.
A rule may state its preferred number in prose while `limit_value` carries the
fallback, or the reverse. Assuming `limit_value` is always the fallback produces
wrong preferred/fallback pairs.

Prose also carries conditions that belong in the answer: a fallback available only
"if escrow is 10.0% or higher", a cap reachable "only for verified customer
concentration risk", a duration allowed "if monthly fees cover stranded cost".
When the template has a `final_position` or `required_position_code` enum, pick
the value that names that condition.

## 3. Direction of deviation

`issue_status` depends on which side you act for, because "too high" is bad for
one side and good for the other.

| Situation | `issue_status` | `recommended_action` |
| --- | --- | --- |
| Draft is worse than playbook for a **seller** (bigger escrow/cap, longer survival/TSA) | `draft_exceeds_playbook` | `revise`, or `delete` for a whole objectionable clause |
| Draft is worse than playbook for a **buyer** (smaller cap, shorter survival, narrower consent condition) | `draft_below_playbook` | `revise` |
| Required provision absent from all current terms | `missing_required_term` | `add` |
| Draft sits within the preferred–fallback band | `in_policy` | `accept` |

`missing_required_term` takes an **empty** `source_term_ids` array. Cite the gap's
evidence in whatever record-ID field the template offers (the draft-agreement
document, the regulatory row, the employee group) rather than inventing a term ID.

Decide "missing" against **current** terms only. A required provision whose only
appearance is a `stale` row is still missing.

## 4. Deltas and shortfalls

Report magnitudes as positive integers.

    seller overage      = draft_amount - fallback_amount
    buyer  shortfall    = fallback_amount - draft_amount
    month delta         = |draft_months - fallback_months|

When a template asks for shortfalls to both positions, compute each against its
own target (`preferred_amount - draft_amount` and `fallback_amount - draft_amount`).

A term that is absent entirely has a draft value of zero, not null, when the
template models it numerically: its shortfall equals the full required amount.

A total negotiation delta is the sum of the per-issue deltas that are actually
quantified — overages, shortfalls, and required-fee amounts. Issues with no dollar
figure contribute nothing.

## 5. Consents, contracts, regulatory

- **Required closing consents** = `consents` rows with `required_for_closing = yes`.
  Their `amount_at_risk` sum is the closing-consent exposure; their count is the
  required-consent count. Rows with `no` are notice/non-blocking items — list them
  as tradeable or non-blocking, never as blockers.
- **Material contracts** needing a closing condition = `consent_required = yes`.
  `notice only` is **not** a blocker; it belongs in the non-blocking list. Sum
  `annual_revenue` over the `yes` rows for conditioned revenue; the single largest
  `annual_revenue` answers "top customer revenue at risk".
- **HSR**: `regulatory.hsr_required = yes` means a clearance condition is required.
  If no current draft term imposes one, that is a `missing_required_term` and a
  closing blocker. `hell_or_high_water_required` is usually `no` — carry it through
  as stated rather than assuming the aggressive covenant.
- Normalize `High`/`Medium`/`Low` to the template's uppercase enum.
- Where a template wants a blocker ID for something with no natural record ID
  (regulatory clearance, an indemnity package, a working-capital mechanic), use a
  synthetic stable ID and keep it consistent across every field that references it.

## 6. Employees

Rows are groups. Totals are sums over groups: `total_count = Σ count`,
`total_pto_liability = Σ pto_liability`.

- `service_credit_required = yes` → include that group's `employee_id`.
- `warn_risk` in {`medium`, `high`} → WARN-risk group. `low` is excluded.
- A `draft_treatment` that lets the buyer **select** or cherry-pick continuing
  employees is a deviation whenever the playbook requires a defined transfer
  process; pair it with accrued-PTO allocation and service credit in the fix.

Scope the numbers to the issue. If the deviation is about one group's treatment,
report that group's `count` and `pto_liability`. If it is about the whole
continuing-employee population, report the totals. Let the draft term or
`draft_treatment` that creates the issue tell you which.

## 7. Risk estimates and exposure

`risk_estimates` rows are the only sanctioned exposure numbers — never model your
own. Category names map to snake_case enums (`closing certainty` →
`closing_certainty`, `indemnity leakage` → `indemnity_leakage`, `transition
disruption` → `transition_disruption`).

Two aggregation modes, chosen by the template:

- **Unqualified total** ("total modeled exposure"): sum `exposure_low` and
  `exposure_high` across *all* categories for the deal.
- **Component-scoped total** (template has `included_exposure_components` /
  `excluded_exposure_components`): sum only categories tied to an issue you
  actually raised, and list the untied ones as excluded.

"Highest exposure category" compares `exposure_high`. A single issue's quantified
impact is the matching category's `exposure_high` when the template wants one
number for a timing or certainty risk.

Exposure figures are not always round — carry them through digit for digit.

## 8. Benchmarks

Compare the draft metric to the benchmark row whose `metric` matches:

| Draft vs benchmark | `position` |
| --- | --- |
| ≤ `median_value` | `at_or_below_median` |
| between median and upper quartile | `between_median_and_upper_quartile` |
| = `upper_quartile` | `at_upper_quartile` |
| > `upper_quartile` | `above_upper_quartile` |

Use `sample_size`, `median_value`, `upper_quartile` verbatim. Where no benchmark
covers the metric (fiduciary outs, MAE carve-outs), emit the template's
`not_applicable` position with zeroed statistics rather than borrowing an
unrelated row.

## 9. Committee escalation filter (policy tasks)

Escalate a draft term only when **all** hold:

1. `staleness_flag = current`
2. its category matches a `policy_thresholds` row for the deal's policy
3. that row has `restricted_flag = yes` and `approval_required = M&A Committee`
4. the draft actually breaches the standard

Everything else is a distractor and belongs in the excluded lists — most often a
term whose category routes to a different approver (`General Counsel`), a term
inside its threshold, or a `stale` row. When the template asks for excluded terms
*and* excluded categories, report the term IDs in one and the category names in
the other.

Non-numeric thresholds still breach: a policy requiring two fiduciary-out triggers
is breached when the draft removes one, and a carve-out allowance of N is breached
by N+1 items in the draft (`excess_count = draft_count - threshold`). Read the
`policy_standard` prose to enumerate what the policy requires and diff it against
the `draft_value` prose.

## 10. Risk ratings and recommendations (calibration)

Start from the playbook rule's `risk_default`, then adjust:

- **HIGH** — anything that blocks closing (required consents, regulatory
  clearance, financing conditions, material-contract conditions), and any
  deviation whose quantified delta is a material fraction of `H`.
- **MEDIUM** — drafting gaps with no dollar quantification: governing law and
  forum, tax allocation mechanics, a missing basket, a moderate month delta.
- Downgrade one notch when the draft already sits at the fallback rather than the
  preferred position — the residual risk is the gap to preferred, not the whole
  position.

Recommendations follow the same shape: `delete` a clause that should not exist,
`revise` a present-but-wrong number, `add` a missing provision, `accept` an
in-policy term. For committee memos, `reject` a term the policy forbids outright,
`approve_with_conditions` where a cap or revision makes it acceptable, and hang
the specific fixes off `required_conditions`.

Priority order runs closing-certainty and blocker issues first, then large-dollar
economics, then operational/employee terms, then unquantified drafting cleanups.

## 11. Formats

- Currency: integer dollars, no decimals, no separators, no currency symbol.
- Percent points: decimal numbers at the precision the prompt names (two places
  unless told otherwise); `fully_diluted_pct`-style holder fractions keep their
  four-decimal fractional form.
- Months and counts: integers.
- Dates: `YYYY-MM-DD`, copied from `signing_date` / `meeting_date`.
- Use `null` for genuinely inapplicable numerics — never `0` as a stand-in, and
  never the string `"null"`. `0` means a measured zero (a draft that provides no
  fee is `0`, not `null`).
- Empty arrays stay `[]`.
- Emit every field the template lists for an object, including the ones that are
  `null` for that row.
