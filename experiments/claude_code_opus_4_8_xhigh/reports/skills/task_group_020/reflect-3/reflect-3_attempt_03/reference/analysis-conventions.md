# Classification and quantification conventions

Apply these consistently across every row. Consistency matters more than any single call: a
summary block that disagrees with its own rows is wrong twice.

## 1. Which side are you on

`client_side` sets the direction of "worse". A number that is out of policy for a seller is often
in policy for a buyer.

| Term | Seller wants | Buyer wants |
|---|---|---|
| indemnity cap | lower | higher |
| survival period | shorter | longer |
| escrow / holdback | smaller, released sooner | larger, released later |
| materiality scrape | none | full (breach **and** damages) |
| consent closing conditions | few, narrowly scheduled | all material consents |
| financing condition | none, or a large reverse fee | flexibility |
| employee selection rights | none; buyer assumes accrued PTO | selection flexibility |
| transition services | short, at full cost recovery | long, at cost |

So a draft cap *above* the seller's limit and a draft cap *below* the buyer's limit are both
deviations. State the deviation relative to **your client's** position.

## 2. `issue_status`

- `in_policy` — the current draft already sits at or better than your side's position. Belongs in
  an exclusion list when the task asks only for deviations.
- `draft_exceeds_playbook` — a numeric term is past your limit in the direction that hurts you
  (typically a seller facing too high a cap/escrow, or too long a survival).
- `draft_below_playbook` — a numeric term falls short of your position in the direction that
  hurts you (typically a buyer facing too low a cap or too short a survival).
- `missing_required_term` — the protective term appears in no current draft term. Source-ID
  arrays are `[]`, draft-side numbers are `null`.
- `out_of_policy` — a non-numeric or structural deviation: a removed trigger, a carve-out list,
  a right the counterparty should not have, a scope exclusion. Also the right label for a
  committee-policy breach where `restricted_flag` is set.

Prefer the specific numeric label over the generic `out_of_policy` whenever a limit value exists
and both sides of the comparison are numbers.

## 3. `risk_rating`

Default to the applicable rule's `risk_default` (playbook) — it is the author's own rating and
beats an independent judgment call. Otherwise:

- inherit the `risk_rating` on the underlying consent row, or the `severity` on the finding;
- inherit `warn_risk` for employee issues;
- a term that defeats closing (walk rights, financing outs, termination triggers, removal of a
  required fiduciary trigger) is `HIGH`;
- pure drafting hygiene with no quantified exposure (governing law, forum, transfer-tax split) is
  `LOW`;
- otherwise `MEDIUM`.

## 4. `recommended_action`

Map from the deviation, and prefer the verb the source itself uses — playbook rules carry a
`required_action` sentence ("Escalate caps above fallback", "Escalate waiver of material
consents") and policy thresholds carry `approval_required`.

- missing protective term → `add`
- numeric term past a limit → `revise`
- a right/condition the counterparty should not have at all → `delete`
- term already at or better than the fallback → `accept`
- deviation the source's own `required_action` says to escalate, or any policy row whose
  `restricted_flag` is set → `escalate`
- committee memos use the approval family instead: `approve`, `approve_with_conditions`,
  `reject`. A schema built around `required_conditions` lists expects
  `approve_with_conditions` as the normal outcome for a curable breach; reserve `reject` for a
  deviation no condition can cure.

## 5. Priority order

Highest first, unless the template says to sort by ID:

1. terms that determine whether the deal closes at all (conditions, walk rights, consents,
   financing/regulatory outs);
2. terms with the largest quantified dollar delta;
3. remaining economic terms (escrow, survival, baskets);
4. operational/transition terms (employees, transition services, IP separation);
5. hygiene terms (tax allocation, transfer taxes, governing law and forum) last.

When the template also wants a "tradeable" list, the must-haves are the closing-certainty items;
the tradeables are the negotiable economics.

## 6. Quantification patterns

- `amount = round(percent / 100 × base)`, base per the term's `basis` (default: headline value).
- `delta_to_fallback = |draft_amount − fallback_amount|`; same for months. Compute shortfalls to
  the fallback and to the preferred position separately when both slots exist.
- A required fee expressed as a floor ("at least N% of X") produces both the required amount and,
  when the draft provides nothing, a shortfall equal to that amount.
- **Benchmark position** compares the draft metric against the benchmark whose `metric` string
  matches that metric — and against the *same* sub-metric the benchmark names (a benchmark for
  "general representation survival months" is compared against the general-survival figure, not
  the fundamental one). Exactly at the upper quartile is `at_upper_quartile`, not above it.
- **Deviation counts** (extra carve-outs, removed triggers) are counts of what the draft added or
  removed relative to the approved list, not the size of the resulting list.
- Holder allocations: split each consideration component by `fully_diluted_pct`, then confirm the
  components sum back to the deal's totals before writing them out.

## 7. Free-form object fields

Where a template shows `{}` (a "normalized" draft/required position, a redline's must-have
terms), mirror the vocabulary the template already establishes: reuse its enum *names* as keys
(`fee_model`, `tax_allocation_method`, `governing_law`, `forum`) and its enum *values* verbatim.
Express the same fact as a machine-comparable key/value pair, not a sentence.

## 8. Standing traps

- A stale term that looks perfectly on point.
- A second deal whose project name differs by one word.
- A consent that is *not* required for closing sitting next to two that are.
- A material contract marked "notice only" — it is not a consent blocker.
- A percentage quoted against enterprise or equity value when the dollar figure in the same
  sentence back-solves to the headline value.
- A rule whose fallback is conditional ("N months **if** escrow is at least X%") — the condition
  is itself a required position elsewhere in your answer.
