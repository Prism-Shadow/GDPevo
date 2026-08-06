# Classification, Quantification, and Output Discipline

## Issue / term status (allowed values)

- `in_policy` — draft term is within playbook/policy bounds. Usually excluded
  from escalation registers.
- `out_of_policy` — draft term violates a playbook rule or policy threshold.
- `missing_required_term` — the draft is silent on a term the side's position
  requires to be affirmative; treat the silence as an issue.
- `draft_exceeds_playbook` — the draft metric has crossed the playbook bound in
  the direction that disfavors your client (e.g., survival longer than the seller
  playbook's max).
- `draft_below_playbook` — the draft metric is short of the playbook bound in the
  direction that disfavors your client (e.g., indemnity cap below the buyer
  playbook's min).

"Exceeds" vs "below" is about crossing the playbook bound **against your client**,
not raw magnitude. The same draft can be `draft_exceeds_playbook` for one side and
`draft_below_playbook` for the other — classify from the side the prompt assigns
you. See `side_posture.md`.

## Risk rating

`LOW` / `MEDIUM` / `HIGH`. Drive from dollar exposure, whether the item is a
closing blocker, regulatory criticality, and benchmark position (e.g., above the
upper quartile in the disfavored direction pushes toward HIGH).

## Recommended action

`delete` / `revise` / `add` / `accept` / `escalate` / `approve` /
`approve_with_conditions` / `reject`. Use only the subset the template allows:
committee/escalation tasks typically restrict to `approve` /
`approve_with_conditions` / `reject`; `redline_action` is `delete`/`revise`/`add`.

## Classification procedure (per draft term)

1. Locate the term in `/terms` by `term_id` / clause ref. If it is absent and the
   side's position requires an affirmative provision → `missing_required_term`
   (use `[]` for `source_term_ids`).
2. Fetch the matching playbook rule (preferred + fallback) or policy threshold.
3. Compare the draft metric to preferred and fallback:
   - At or within preferred → `in_policy`.
   - Between preferred and fallback, or beyond, in the disfavored direction →
     `out_of_policy` and, where the template distinguishes, `draft_exceeds_playbook`
     or `draft_below_playbook`.
   - Beyond fallback → `out_of_policy`, typically higher risk.
4. For a committee/escalation deliverable: include **only** out-of-policy or
   restricted terms. Exclude `in_policy`, stale, and non-committee distractor
   terms; record excluded in-policy terms/categories in the aggregate summary if
   the template has those slots.
5. Attach benchmark position and risk-estimate exposure where the template has
   slots for them.

## Quantification

- **Base.** Compute dollar amounts from the headline purchase price unless a
  source explicitly states a different basis — e.g., the memo `value_basis`
  (equity value), upfront cash, identified findings, or annual revenue. Use the
  basis the source names.
- **Per-item amounts.** `amount = base × percent`. Deltas/shortfalls:
  `draft − fallback` and `draft − preferred` (sign and field per template).
- **Aggregates.** Sum PTO liability across employees; sum consent amounts at
  risk; sum material-contract revenue requiring consent; aggregate exposure low
  and high **separately**, pulling each component's low/high from
  `/risk-estimates` by `source_estimate_id`. Do not double-count components the
  template says to exclude (e.g., transition disruption may be excluded from the
  committee aggregate).
- **Rounding.** Integer dollars; round once at the end of each computation, not
  mid-step, to avoid drift. Percent to the precision the template states. Months
  integer. Dates `YYYY-MM-DD`.

## Units and precision

Defaults — **the template overrides these**:

- Currency: integer USD.
- Percent points: two decimals.
- Months: integer.
- Dates: `YYYY-MM-DD`.

Read the template's `units` / `instructions`. Known per-task variants seen: one
decimal percent, whole percent points, holder fully-diluted percentages to four
decimals. When the template conflicts with a default here, follow the template.

## Ordering

- Issue register: by `issue_id` ascending or by counsel workflow — use whichever
  the template's ordering field specifies.
- `priority_order` / `negotiation_priority`: highest negotiation priority →
  lowest. Drive priority by exposure size, closing-blocker status, and
  regulatory criticality.
- `required_redlines`: by `redline_id` ascending.
- `priority_rank`: numeric, in the convention the template states.

## Output discipline

- Output exactly one JSON object conforming to the template.
- Include every required top-level field and every required field on each object.
- Use only allowed enum values and only the stable IDs the template enumerates.
- `null` for no-value fields; `[]` for empty lists; never omit required fields.
- Add keys outside the template only where it explicitly permits free-form
  objects (e.g., `must_have_terms`, `draft_value_normalized`,
  `required_position_normalized`, `covenant_limits`).
- No prose, no markdown fences, no commentary — raw JSON only.
