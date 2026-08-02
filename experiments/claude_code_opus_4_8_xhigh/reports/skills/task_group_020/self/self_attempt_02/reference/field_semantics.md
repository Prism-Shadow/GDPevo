# Field semantics and traps

Column names in this workbench are misleading in specific, repeatable ways.
Check anything you are about to put a number into against this list.

## draft_terms

| Column | What it actually means |
|---|---|
| `staleness_flag` | `current` or `stale`. **Filter to `current`.** A category whose only row is stale means the draft is *silent*, i.e. a missing term — not a position |
| `numeric_value` | Exactly **one** quantity. Composite terms ("X% for N months") leave the second number in `draft_value` prose only |
| `unit` | `percent_points`, `months`, `dollars`, `contracts`, `boolean`, `text`, `additional_carveouts`, `restricted_change`. Tells you which template field the value belongs in |
| `basis` | The denominator. Overrides the prompt's default base whenever it names something else (`enterprise value`, `equity value`, `fully diluted shares`, …) |
| `draft_value` | Prose. Parse it for the second numeric, for silence/absence language, and for qualifiers |
| `counterparty_rationale` | The other side's argument. Useful for the rationale/justification fields; never a source of facts |
| `clause_ref` | Section reference for `clause_ref` fields. Copy verbatim |
| `last_updated` | Recency. **Not** a staleness signal — a stale row can be newer than a current one. Trust `staleness_flag` |

Expect at most one current row per `(deal_id, category)`. More means the query
leaked another deal.

## playbook_rules

| Column | What it actually means |
|---|---|
| `preferred_position` | Prose. **The preferred number exists only here** and must be parsed from the sentence |
| `fallback_position` | Prose. Often carries a **condition** ("… if escrow is at least X%", "… only for verified …"). The condition is part of the rule |
| `limit_value` | The **fallback** threshold, not the preferred one. Pairing `limit_value` with the preferred position is the most common numeric error |
| `limit_unit` / `basis` | Unit and denominator for `limit_value` |
| `risk_default` | Starting `risk_rating`. Escalate above it when the deal's own records show aggravating facts; the template's enum casing may differ from the column's |
| `required_action` | Phrased as escalation guidance; map it to the template's `recommended_action` vocabulary rather than copying it |

**Polarity depends on `client_side`.** For caps, escrow, survival and similar,
a seller playbook expresses a ceiling ("no more than N%") and a buyer playbook a
floor ("at least N%"). The same draft number therefore yields opposite
`issue_status` values depending on which side you act for. Read the preposition
in the prose; do not assume.

Thin playbooks with a single rule exist as decoys. If the deal's row names one,
that is still the applicable playbook — but categories it does not cover need a
different source of the required position.

## policy_thresholds

| Column | What it actually means |
|---|---|
| `restricted_flag` | `yes` → committee-restricted. **Only these categories escalate** |
| `approval_required` | Which body. Rows routed to a lower approver are distractors even when the draft is near the threshold |
| `threshold_value` / `threshold_unit` / `basis` | The ceiling and its denominator |
| `policy_standard` | Prose statement of the rule, including multi-part requirements (e.g. required triggers plus a match-right period). Parse all parts — a term can breach one part while satisfying another |
| `notes` | Sometimes names the governing board policy for a citation field; sometimes flags a near-threshold distractor |

Multiple policy versions coexist with **different thresholds**. Use the
`policy_id` on the target deal's row.

## cap_table

- `fully_diluted_pct` is a **fraction summing to 1.0**, not percent points.
  Multiply consideration by it directly. Convert to percent points only if the
  template says percent.
- `shares` ≠ `as_converted_shares` for preferred classes. Use whichever the
  template names.
- `holder` and `security_class` are the stable labels; quote them verbatim.
- `role_notes` flags which holders carry consent, support, or restrictive-covenant
  obligations — that is where founder/executive covenant groups come from.

## consents

- `required_for_closing` is `yes`/`no`. Closing-condition counts and
  amount-at-risk totals include **only `yes`**.
- `amount_at_risk` is per consent; sum across the qualifying rows.
- `risk_rating` arrives capitalized (`High`/`Medium`/`Low`); templates usually
  want `HIGH`/`MEDIUM`/`LOW`. Normalize casing to the template.

## material_contracts

- `consent_required` is **three-valued**: `yes`, `no`, `notice only`.
  `notice only` maps to a notice/non-blocking classification, never to a closing
  condition. Collapsing it into `yes` inflates every downstream revenue total.
- `annual_revenue` feeds "revenue conditioned/at risk" fields — sum only over
  contracts that actually carry a closing condition.
- `anti_assignment` and `change_of_control` explain *why* consent is required.

## employees

- Rows are **groups**, not people. `count` is the headcount in that group; total
  workforce is the sum.
- `pto_liability` is per group; sum for totals. Group-specific fields (e.g. a
  field-operations PTO figure) come from that group's row alone.
- `draft_treatment` prose carries the buyer-selection right ("may select",
  "cherry-pick") and PTO rejection — that is the evidence for continuity issues.
- `playbook_requirement` states the required position for this deal directly.
- `service_credit_required` / `warn_risk` are lowercase `yes`/`no` and
  `low`/`medium`/`high`; normalize to the template's enum casing and to booleans
  where the template asks for one.

## regulatory

One row per deal. `hsr_required`, `hell_or_high_water_required`
(`yes` / `no` / `limited covenant`), `threshold_basis`, `regulatory_approval`.
Templates frequently reuse these exact strings as enum values — copy verbatim,
and convert to booleans only where the template's type demands it.

## benchmarks

`median_value`, `mean_value`, `upper_quartile`, `sample_size`. Classify the
draft against median and upper quartile using the template's position enum.
Match the benchmark by `metric`/`category`, not by position in the list, and
confirm its `metric` shares the draft term's unit and basis before comparing.

## risk_estimates

Three categories per deal — closing certainty, indemnity leakage, transition
disruption (space-separated in the data; templates usually use underscores).
`exposure_low` / `exposure_high` are integer dollars.

Aggregate only the components your live issues depend on. Templates that expose
`included_` and `excluded_exposure_components` expect a category with no
corresponding escalated issue to be **excluded and named as excluded**.

## diligence_findings

`topic` + `severity` + `amount`. Sizes special indemnities, working-capital
collars, and privacy/security exposures. Cite `finding_id` wherever a template
asks for a source finding.

## deals

- `headline_value` is the default base for percentage math.
- `upfront_cash + stock_value + milestone_value` should reconcile to
  `headline_value`; a mismatch means you are on the wrong deal.
- Escrow and similar can be based on `upfront_cash` rather than headline when a
  template's `basis` enum offers it — follow the template.
- `client_side` drives comparison polarity throughout.
- `signing_date` / `meeting_date` are already `YYYY-MM-DD`; pass through
  unchanged.
- `project_name` is **not unique** across deals. Never join or filter on it.
