# Analysis playbook

How to turn workbench rows into classified, quantified issue rows. Every rule here is
side-aware: the same draft number can be a win or a problem depending on whom you act for.

## 1. Establish the frame

- `client_side` from the deal record (confirm it matches the prompt's role).
- Governing standard: the deal's `playbook_id` (playbook rules) or `policy_id` (policy
  thresholds). Committee-escalation deliverables use policy thresholds; negotiation and
  redline deliverables use playbook rules.
- Value bases from the deal record: `headline_value`, `upfront_cash`, `stock_value`,
  `milestone_value`.

## 2. Assemble the in-scope term set

Start from `draft_terms` where `deal_id` matches and `staleness_flag = 'current'`. Then add
**absences**: categories the standard requires, or that the prompt's deliverable list names,
which have no current term. Both populate the issue register.

Drop from scope: stale rows; categories routed to a different approver when the deliverable is
approver-specific; terms belonging to another deal.

## 3. Classify status

Compare the draft's `numeric_value` (or the meaning of its `draft_value` prose for
`text`/`boolean` units) with the standard's `limit_value`/`threshold_value` and its
preferred/fallback prose.

| Situation | `issue_status` |
| --- | --- |
| Draft sits at or better than the preferred position for your client | `in_policy` |
| Draft breaches a policy threshold, or removes a required element | `out_of_policy` |
| Draft is beyond the playbook limit in the *worse* direction (too high a cap/escrow/fee/duration for your side) | `draft_exceeds_playbook` |
| Draft falls short of a required minimum (protection smaller/shorter than the playbook floor) | `draft_below_playbook` |
| No current term covers a required protection | `missing_required_term` |

Direction cheat-sheet:

- **Seller** wants a *lower* indemnity cap, *lower* escrow, *shorter* survival, *shorter* TSA,
  *no* financing condition (or a large reverse break fee if one stays), fewer conditions to
  closing, transfer-tax splitting, a mutually-agreed allocation, and affirmative separation
  protections (IP/domain transition, outside-date extension, employee continuity).
- **Buyer** wants a *higher* cap, *higher* escrow, *longer* survival, a *full* materiality
  scrape, *more* consents as closing conditions, service credit and PTO honored, D&O tail and
  seller expenses off its books, and regulatory efforts covenanted.
- A number that is "too big" for one side is "too small" for the other. Derive the direction
  from `client_side` plus the rule's `required_action` prose ("Escalate lower cap" vs
  "Escalate caps above fallback"), never from the raw magnitude.

## 4. Read the fallback's condition

Fallback and threshold prose is frequently conditional:

- "...may reach X% only for verified <risk>" → check `diligence_findings` for that risk.
- "...X months if escrow is Y% or higher" → check the escrow term (or its absence).
- "...closing condition for the top N revenue contracts" → rank `material_contracts` by
  `annual_revenue`.
- "...must include <trigger A> and <trigger B>" → the draft removing one is the deviation;
  record the removed trigger, not just a number.

An unmet condition means the fallback is unavailable and the preferred position governs. A met
condition means the fallback is live — say so in the recommendation and in any
`required_conditions` field rather than silently accepting the draft.

## 5. Rate risk

Start from the standard's `risk_default` for the category, then adjust on evidence in this
deal:

- Escalate toward `HIGH` when: the deviation blocks closing certainty (financing condition,
  missing regulatory covenant, unresolved consent on the top-revenue contract); a related
  `diligence_findings` row is `High` severity; a related `consents.risk_rating` is `High`; or
  the quantified gap is large relative to headline value.
- Keep `MEDIUM` for economic deviations with a bounded, quantified gap.
- `LOW` for administrative or clean-up items (forum/governing-law mechanics, notice-only
  consents).
- Absent protections are rated on the exposure they leave open, not on the fact of absence.

## 6. Choose the action

Map the standard's `required_action` prose plus the status onto the template's enum:

- Term present and unacceptable → `revise` (or `delete` for a provision that must come out,
  such as a financing condition); `escalate` when the standard says to escalate and the
  template offers it.
- Protection absent → `add`.
- Within policy → `accept`.
- Committee-style templates use `approve` / `approve_with_conditions` / `reject` instead:
  `approve_with_conditions` is the normal outcome for a quantified deviation that the
  fallback's condition can cure; `reject` for a breach with no available fallback.
- Redline objects pair with issues: `redline_action` is the narrower `delete`/`revise`/`add`
  set, and `must_have_terms` should state the required position concretely (numbers, months,
  triggers), not restate the problem.

## 7. Quantify

- **Percent → dollars**: `pct / 100 × base`, base chosen from the `basis` field (purchase /
  equity / enterprise value → headline value; upfront cash → the upfront cash field), integer,
  half-up.
- **Gap fields**: `delta_to_fallback` = draft minus fallback in the template's unit;
  `shortfall_to_*` = how much more is needed to reach that target, and shouldn't go negative
  when the draft already clears it (use `null` or `0` per the template's typing).
- **Fee requirements**: when a fallback demands a fee of at least X% of a stated basis,
  `required_fee_percent` = X, `required_fee_dollars` = X% of that basis, and the shortfall is
  that amount minus whatever the draft provides.
- **Exposure ranges**: from `risk_estimates.exposure_low/high`, selected by category. Aggregate
  only the components the template lists as included, and put the others in the excluded field.
- **Consents**: `amount_at_risk` summed over consents that are actually closing conditions
  (`required_for_closing = 'yes'`); notice-only consents go in the non-blocking list.
- **Material contracts**: `annual_revenue` summed over contracts requiring consent; that's the
  revenue conditioned on closing.
- **Employees**: `count` and `pto_liability` summed over the groups in scope — and when a
  template field names a specific group, use that group's row alone.
- **Cap table**: allocate consideration by `fully_diluted_pct` against the cash/stock/total
  components. Check that the allocated amounts sum back to the component totals; fix the
  largest holder's rounding residue if a rounding drift appears, and keep the percentages at
  the template's decimal count.

## 8. Prioritize

When a `priority_order` / `negotiation_priority` / `priority_rank` field exists, rank by
negotiation leverage, not by ID: closing-certainty blockers first (financing conditions,
regulatory covenants, must-have consents), then large quantified economics (cap, escrow,
break fee), then duration and mechanics (survival, TSA), then administrative items
(governing law, forum, tax allocation mechanics). Break ties with quantified exposure.

Keep the register's own sort order separate from the priority list — templates usually want
the register sorted by ID and the priority array sorted by importance.

## 9. Benchmarks

Where a template asks for benchmark support, pull the deal's `benchmarks` row whose `metric`
matches the issue's measure and report `sample_size`, `median_value`, `upper_quartile`, and a
`position` enum derived by comparing the draft value with those statistics. Use the enum's own
boundary language (at/below median, between median and upper quartile, at upper quartile,
above upper quartile) and `not_applicable` when no benchmark covers the metric.

## 10. Closing readiness

Blockers are the items that must be satisfied before closing: consents with
`required_for_closing = 'yes'`, material contracts requiring consent that the draft doesn't
condition on, and outstanding regulatory clearance where `hsr_required = 'yes'`. Everything
that is merely economic and can be traded is a tradeable issue, not a blocker. Overall status
is `NOT_READY` only when a blocker has no cure path in the record; a deal with open but
curable blockers is `READY_WITH_CONDITIONS`.
