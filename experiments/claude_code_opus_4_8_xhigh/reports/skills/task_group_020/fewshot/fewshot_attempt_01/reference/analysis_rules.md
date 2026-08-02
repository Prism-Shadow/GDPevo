# Analysis rules — classification, arithmetic, aggregation

These are the decision rules the workbench data supports. They hold across
seller-side registers, buyer-side matrices, closing packages and committee memos;
only the output shape changes.

## 1. Direction of deviation depends on `client_side`

A term is a problem when it sits on the wrong side of *your client's* playbook
position. The same numeric fact flips meaning between sides.

| Term | Buyer wants | Seller wants |
|---|---|---|
| Indemnity cap | higher | lower |
| Survival period | longer | shorter |
| Escrow % / release period | larger, longer | smaller, shorter |
| Materiality scrape | full (breach + damages) | none / breach-only |
| Consent closing condition | broader | narrower |
| Reverse break fee | smaller | larger |
| Restrictive covenants | broader | narrow, acquired-business only |

## 2. Status classification

Compare the current draft value against the playbook **preferred** and
**fallback** positions (or the policy threshold):

- **`in_policy`** — draft meets at least the fallback in the client's favour.
  A draft sitting exactly on the fallback is in policy; recommend `accept`.
- **`draft_below_playbook`** — the draft gives the client *less* than the
  playbook requires (buyer offered a cap under the fallback; a seller-required
  fee that is absent or set to zero).
- **`draft_exceeds_playbook`** — the draft demands *more* than the playbook
  allows (a buyer-side escrow or survival tail above the seller's ceiling; a
  buyer right to cherry-pick employees).
- **`missing_required_term`** — no current term covers the point and the deal
  data shows the protection is needed. Use an **empty** `source_term_ids` array
  and cite the draft-agreement document (or the record that proves the need) in
  `source_record_ids`.
- **`out_of_policy`** — for committee/policy tasks, any restricted term breaching
  its policy threshold.

Treat draft silence as an issue whenever the client's position requires an
affirmative provision. Missing terms are real findings, not omissions to skip.

Aggregate count fields such as `out_of_policy_issue_count` usually mean *every
issue that is not `in_policy`*, summed across all the deviation statuses — not
only rows whose literal status string is `out_of_policy`. Read the template's
sibling count fields (`draft_below_playbook_count`, `missing_required_term_count`)
to confirm which partition is intended.

## 3. Percentage → dollar arithmetic

- Basis is the deal's `headline_value` unless a source states otherwise. Policy
  rows citing `equity value`, and playbook rules citing `upfront cash` or
  `identified findings`, override the default. Check `basis` on every rule.
- `amount = round(basis × percent / 100)` → emit as an **integer**.
- Deltas are always the gap in the client's favour, as a **positive** integer:
  - client wants the number *lower*: `delta = draft − playbook_limit`
  - client wants the number *higher*: `shortfall = playbook_limit − draft`
- Compute the gap to preferred and to fallback separately when the template has
  both fields; they are different numbers.
- A required-but-absent economic term has a draft value of `0`, so its shortfall
  equals the full required amount.

## 4. Aggregation rules

- **Total modeled exposure** = sum of `exposure_low` / `exposure_high` across the
  deal's risk-estimate rows. Committee memos instead sum only the categories tied
  to escalated terms, and list the rest under excluded components — the template's
  `included_/excluded_exposure_components` fields tell you which.
- **Highest exposure category** = the category with the largest `exposure_high`,
  normalised to the template's casing.
- **Closing consent amount at risk** = Σ `amount_at_risk` where
  `required_for_closing = yes`.
- **Material contract revenue requiring consent** = Σ `annual_revenue` where
  `consent_required = yes` (never `notice only`).
- **Employee totals** — read the field name carefully. A deal-wide
  `total_employee_count` / `total_pto_liability` sums *all* groups; an
  issue-scoped `affected_employee_count` / `quantified_impact` covers only the
  group whose `draft_treatment` breaches the requirement.
- **Negotiation delta total** = sum of the per-issue deltas to fallback, counting
  only issues that have one.
- Never round a sourced figure to make it look tidy.

## 5. Risk rating

Start from the governing rule's `risk_default` / the record's own `risk_rating`,
then raise it when the deal data justifies it:

- **HIGH** — closing certainty is at stake (financing condition, missing
  reverse break fee, unobtained top-customer consent, regulatory clearance);
  the quantified gap is a large share of headline value; a high-severity
  diligence finding or top-revenue relationship is exposed.
- **MEDIUM** — real but bounded exposure: survival tails, tax allocation,
  governing law, baskets.
- **LOW** — small, well-covered items.

Normalise case: sources store `High`/`Medium`/`Low`; templates almost always
require `HIGH`/`MEDIUM`/`LOW`.

## 6. Priority ordering

`priority_order` / `priority_rank` is a negotiation judgement, not the sort order
of the register. Rank by: closing certainty and regulatory blockers first, then
the largest quantified economic gaps, then operational/employee continuity, then
clean-up items (tax allocation, governing law, forum). Keep the register itself
sorted as the template instructs — commonly `issue_id` ascending — and let the
priority array carry the judgement.

## 7. Closing blockers vs tradeable items

A blocker must be satisfied before closing:
- consents with `required_for_closing = yes`
- material contracts with `consent_required = yes` needing a closing condition
- outstanding regulatory clearance when `hsr_required = yes` (coin a stable
  synthetic id when the template asks for one and no record id exists)
- unresolved economic mechanics the template names as blockers

Tradeable / non-blocking: `required_for_closing = no` consents, `notice only`
contracts, and items whose amount is simply not recorded in the workbench —
templates provide an explicit status value for that case (e.g.
`amount_not_in_workbench`), which is the correct answer rather than a guess.

## 8. Output discipline

- Return **only** the JSON object. No prose, no markdown fence, no trailing commentary.
- Currency: bare integers — no decimals, no separators, no currency symbols, no strings.
- Percent points: numbers at the precision the prompt states (they differ between
  tasks, and a single task can set a different precision for one field, such as
  holder percentages). Months: integers.
- Enums: exact strings from the template. Never invent a value, never re-case one.
- IDs: copy `term_id` / `consent_id` / `contract_id` / `employee_id` /
  `estimate_id` / `finding_id` / `document_id` exactly as stored.
- Follow the template's own null convention. Where the template lists every field
  with `"... or null"`, emit **all** fields on every object, using `null` for the
  inapplicable ones. Where the template shows a sample object that is a union of
  variant-specific fields, include only the keys that apply to that row.
- Sort arrays exactly as the template instructs.
