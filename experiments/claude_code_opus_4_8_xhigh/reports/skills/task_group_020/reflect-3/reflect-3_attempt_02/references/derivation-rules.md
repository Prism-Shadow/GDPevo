# Derivation rules

## Direction of harm depends on client side

Read `client_side` first; it flips every comparison.

| Term | Seller-protective | Buyer-protective |
|---|---|---|
| Indemnity cap | lower | higher |
| Survival period | shorter | longer |
| Escrow / holdback | smaller, shorter | larger, longer |
| Materiality scrape | none / breach-only | full breach and damages |
| Consent closing condition | narrow, scheduled consents only | broad, all material consents |
| Financing condition | absent, or paid for by a reverse fee | acceptable |
| Employee continuity | defined transfer, PTO assumed | selection rights |
| Regulatory efforts | capped efforts | hell-or-high-water |

A term is only an issue when it deviates **against** your client.

## Status classification

Compare the draft figure to the governing preferred and fallback positions:

| Situation | Status |
|---|---|
| Draft meets or beats preferred | `in_policy` |
| Draft sits between preferred and fallback, or exactly at a fallback whose condition is satisfied | `in_policy` |
| Draft is worse than fallback, in the direction that costs your client more | `draft_exceeds_playbook` (a cap/period/amount that is too large) or `draft_below_playbook` (a protection that is too small) |
| Draft breaches a hard policy ceiling, or strips a required element the rule text lists | `out_of_policy` |
| No draft term exists and the records show the protection is needed | `missing_required_term` |

`draft_exceeds_playbook` versus `draft_below_playbook` is about the **number's direction**,
not about who benefits: 18% where the ceiling is 12.5% exceeds; an 8% cap where the floor
is 10% is below.

## The missing-term test

Treat draft silence as an issue only when something in the records shows the term is
needed. Acceptable triggers, strongest first:

1. A governing rule category with no matching draft term.
2. A record family that establishes the need — consents flagged required for closing with
   no consent condition in the draft; a regulatory record requiring clearance with no
   regulatory covenant; employee rows whose requirement is unmet by any draft term.
3. A transaction-type implication the prompt names explicitly (an asset or carveout deal's
   purchase-price allocation and transfer-tax split; a carveout's separation and
   transition terms).

If the template supplies a closed list of stable issue IDs, that list already resolves
this question — emit every ID in it.

## Quantification

- Base: the term's own `basis`, else the deal headline value. Confirm by dividing any
  dollar figure quoted in the draft prose by its stated percent.
- Currency fields are integers. Round once, at the end, and never round an intermediate.
- Percent deltas are in percent points; month deltas are integer months.
- Shortfall = required amount − draft amount. Excess = draft amount − ceiling amount.
  Both are positive numbers; the field name tells you which direction is expected.
- Per-holder allocation: component × `fully_diluted_pct`, per component. Verify the column
  sums back to the deal totals.
- Aggregate exposure: sum `exposure_low` and `exposure_high` across only the estimate
  categories the template's inclusion list names. If the template also has an exclusion
  list, populate it with the categories you left out.

## Selection rules that recur

- **Closing blockers** = consents flagged required for closing, plus material contracts
  flagged consent-required, plus any regulatory clearance the records say is required.
  Notice-only contracts and consents not required for closing are non-blocking.
- **Amount at risk** aggregates over closing-required consents only.
- **Revenue conditioned** aggregates `annual_revenue` over consent-required contracts only.
- **Employee totals** sum across all groups; a group-scoped field uses that group's row.
- **Tradeable versus must-have**: a term whose governing rule offers a fallback is
  tradeable; a term that gates closing or that the rule states as mandatory is a must-have.

## Risk rating heuristics

Start from the rule's `risk_default`, then adjust:

- Raise to `HIGH` when the deviation is large, breaches a hard ceiling, sits above the
  benchmark upper quartile, or carries a quantified exposure.
- `MEDIUM` for deviations inside the benchmark range or with no quantified exposure.
- `LOW` for administrative gaps such as governing law, forum, or transfer-tax split.
- Where a record carries its own risk rating (consents do), use it rather than re-deriving.

## Ordering and priority

Sort arrays exactly as the template instructs. Where it asks for negotiation priority
rather than a sort key, order by client impact: quantified dollar exposure first, then
closing-certainty blockers, then covenant and employee terms, then administrative fixes.
Keep the priority array's membership identical to the row array's — same IDs, no more, no
fewer.

## Common ways these answers go wrong

- Using a legacy rule set whose ID differs from the deal record's by one character.
- Carrying a stale draft term into the register.
- Reading `limit_value` as the preferred position when it holds the fallback.
- Pulling a record from a similarly named project.
- Substituting `0` for a genuinely unknown quantity instead of `null`.
- Summary counts that do not match the rows actually emitted.
- Inventing record IDs for missing terms; a missing term has an empty source-ID array.
