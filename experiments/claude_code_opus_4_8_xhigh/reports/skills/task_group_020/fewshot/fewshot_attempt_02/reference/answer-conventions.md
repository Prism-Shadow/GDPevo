# Answer conventions

House rules for converting workbench records into the graded JSON. Each was
checked to reproduce the reference answers across seller-side, buyer-side,
committee-escalation, carveout-transition, and deviation-matrix variants.

---

## 1. Which records count

**Draft terms: `staleness_flag == "current"` only.** Stale rows are deliberate
decoys — they carry plausible categories and near-threshold numbers. Exclude
them from the analysis. When a template asks for excluded/stale terms, list
those IDs (and their categories) in that field, and only there.

**Deal scope.** Filter every table on the prompt's `deal_id`. The workbench
holds dozens of deals, several with confusingly similar project names. Never
carry a value from a similarly named project.

**Playbook / policy scope.** Use the ID named in the prompt; otherwise the
deal header's `playbook_id` / `policy_id`.

---

## 2. Value bases

Compute dollars from **`headline_value`** unless a source explicitly names a
different base. `basis` on the term, playbook rule, or policy threshold is that
explicit statement — read it before multiplying.

- "purchase price", "equity value", "enterprise value" → `headline_value`.
  These are all the deal's headline figure; there is no separate enterprise or
  equity value field. A playbook fallback phrased against "enterprise value"
  still computes off `headline_value`.
- Only split into `upfront_cash` / `stock_value` / `milestone_value` when the
  template asks for the split, or for per-holder consideration (§5).

`percent × headline_value` lands on exact integers throughout this dataset. If
you get a fraction, re-check the base before rounding.

---

## 3. Comparing draft against playbook or policy

**Playbook (negotiating positions).** Pull three numbers per category: the
draft value, the *preferred* position, and the *fallback* position. Preferred
and fallback are stated in the prose of `preferred_position` and
`fallback_position`; `limit_value` typically mirrors only one of them, so
parse the prose.

Direction depends on which side you act for — the same number is a problem in
opposite directions:

- **Seller**: caps, escrow, and survival that run *above* the playbook are
  adverse (`draft_exceeds_playbook`); a missing fee protection is
  `draft_below_playbook`.
- **Buyer**: caps, escrow, and survival that run *below* the playbook are
  adverse (`draft_below_playbook`).

`in_policy` is reserved for a term that genuinely meets the position — including
one that lands exactly on the fallback. Accepting a fallback is compliant, not a
deviation.

**Policy (approval thresholds).** A term escalates only when **all** of:

1. it is a **current** draft term,
2. its category has a policy threshold with `restricted_flag == "yes"` **or**
   the drafted position breaches `threshold_value`, and
3. `approval_required` names the approving body the prompt is packaging for.

A restricted category with no current draft term does **not** escalate — there
is nothing drafted to approve. A near-threshold term routed to a lower approval
authority is a decoy; exclude it and, when the template has a field for it, name
it as excluded.

---

## 4. Missing terms

Silence is an issue when the client's position requires an affirmative
provision and the surrounding data shows it is needed. Treat as
`missing_required_term` with:

- `source_term_ids`: **empty array** (no term exists to cite),
- `source_record_ids`: the record that proves the need — the current draft
  agreement document for pure silence, or the consent / employee / regulatory /
  finding row that creates the requirement,
- `recommended_action`: `add`.

Typical affirmative provisions worth checking for silence: indemnity basket,
escrow, restrictive covenants, employee continuity and PTO allocation,
transition services, Section 1060 allocation, transfer-tax split, governing law
and forum, outside-date extension, HSR closing condition, IP and domain
transition.

Do not invent an issue for a term the data gives no need for.

---

## 5. Standard computations

**Deltas.** `delta_to_fallback = |draft_amount − fallback_amount|`, same for
months. Report the gap to the position you are actually demanding; a
`shortfall` field means the same gap expressed from the deficient side. Where a
template carries both a fallback and a preferred shortfall, compute both.

**Aggregate negotiation delta.** Sum the per-issue deltas that are non-null.
Issues with no dollar delta contribute nothing.

**Consents.** `required_for_closing == "yes"` → a closing blocker; sum their
`amount_at_risk` for the "amount at risk" total and count them for the
"required consent count". `required_for_closing == "no"` → notice-only /
non-blocking; list separately, never in the blocker total.

**Material contracts.** `consent_required == "yes"` → conditioned; sum their
`annual_revenue`. `"notice only"` and `"no"` are excluded from that total and
belong in the non-blocking list. "Top customer revenue at risk" is the single
largest `annual_revenue` among the consent-required customer contracts.

**Employees.** Totals are sums over **all** employee group rows: headcount from
`count`, PTO from `pto_liability`. Service-credit IDs are rows with
`service_credit_required == "yes"`. WARN-risk IDs are rows with `warn_risk` of
`medium` or `high`. A group whose `draft_treatment` lets the buyer select or
cherry-pick employees, or reject accrued PTO, is the issue to raise.

**Risk estimates.** Modeled exposure low/high totals are the sums of
`exposure_low` / `exposure_high` across **all** categories for the deal, unless
the template or prompt names which components to include or exclude — then
follow that list exactly and report the named exclusions. The "highest exposure
category" is the category with the largest `exposure_high`, written in the
template's casing (usually snake_case).

**Cap-table allocation.** Per holder, using `fully_diluted_pct` and
`as_converted_shares`:

```
cash_amount  = fully_diluted_pct × upfront_cash
stock_amount = fully_diluted_pct × stock_value
total_consideration = cash_amount + stock_amount
```

Percentages sum to ~1.0 and the allocations sum to the cash and stock totals —
check both.

**Findings.** A working-capital collar amount, a privacy exposure, or a special
indemnity sized off diligence is the `amount` on the matching
`diligence_findings` row — cite its `finding_id`. A special indemnity stated
inside a draft term's prose comes from that prose instead.

**Benchmarks.** Position the drafted metric against the matching benchmark row:
at or below `median_value` → `at_or_below_median`; between median and
`upper_quartile` → `between_median_and_upper_quartile`; equal to the upper
quartile → `at_upper_quartile`; above it → `above_upper_quartile`. Compare the
metric the benchmark actually measures (e.g. *general* representation survival,
not the longest survival in the term). With no matching benchmark, use
`not_applicable` and zero out the sample/median fields.

---

## 6. Risk rating

Start from the playbook rule's `risk_default` (Title case → uppercase), then
adjust on the evidence:

- **HIGH** — blocks or conditions closing (required consents, regulatory
  clearance, financing/termination-fee gaps); a large quantified deviation
  relative to headline value; loss of a core protection the client cannot
  reinstate later.
- **MEDIUM** — real but bounded: documentation and allocation gaps (governing
  law, tax allocation, basket), duration deviations with modest exposure, terms
  already sitting at fallback.
- **LOW** — administrative, or already compliant with a low-value record.

A term you are accepting as `in_policy` should not be rated HIGH; a fallback you
are conceding is normally MEDIUM.

---

## 7. Priority order

`priority_order` is negotiation sequence, not sort order. Rank by: deal-breaking
closing certainty first, then the largest quantified economic exposure, then
operational continuity, then documentation cleanups. Include **every** issue ID
exactly once. Where a separate array must be sorted (`issue_register`,
`transition_issues`, `required_redlines`), sort it ascending by its stable ID
unless the template says otherwise, and keep `priority_order` as the separate
judgment-ordered list. Templates that carry a `priority_rank` field instead
usually want the array itself in rank order — follow the template's own
`ordering` instructions when present.

---

## 8. Counters and summary metrics

Read each counter name literally, then confirm against the arrays you emitted:

- `issue_count` / `position_issue_count` — every row in the register.
- `high_risk_count` / `medium_risk_count` — rows at that rating.
- `business_outcome_count` — **distinct** values used, not the row count.
- Status counters named for a specific enum (`missing_required_term_count`,
  `draft_below_playbook_count`) count exactly that enum value.
- An umbrella counter such as `out_of_policy_issue_count` counts every
  non-compliant row — all statuses except `in_policy` — even when
  `out_of_policy` is also a literal enum value. The name describes the concept,
  not the token.
- `closing_blocker_count` — length of the blocker array.

---

## 9. Normalization

- **Currency**: integer dollars. No decimals, no strings, no separators.
- **Percent**: decimal number in percent points (e.g. `12.5`, not `0.125`), at
  the precision the prompt states. Holder percentages are the fractional
  `fully_diluted_pct` as stored, to the stated decimals.
- **Months / counts**: integers.
- **Dates**: `YYYY-MM-DD`, copied from the deal record.
- **Enums**: exactly as the template spells them. Source data uses Title case
  (`High`, `Medium`) while templates usually want `HIGH`/`MEDIUM` — uppercase
  when converting. Free-text codes are snake_case.
- **Booleans**: real JSON `true`/`false`. Source `"yes"`/`"no"` strings convert
  to booleans only where the template's type is boolean; some templates keep
  `"yes"`/`"no"` as enum values — match the template.
- **Not applicable**: `null` for a scalar, `[]` for a list. Only use a
  `not_found_in_current_records`-style enum where the template offers it, and
  reserve it for something genuinely absent from the records — use
  `not_applicable` when the field simply does not pertain to that row.
- **Unknown amounts**: if a template offers an `amount_not_in_workbench`-style
  status, use it rather than guessing a number.
