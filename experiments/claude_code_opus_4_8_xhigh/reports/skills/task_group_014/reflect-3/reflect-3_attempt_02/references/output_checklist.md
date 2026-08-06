# Output checklist (reference)

Run this before returning the answer. You are the only reviewer — verify by re-reading the
template and re-deriving from the records, not by intuition.

## Structure
- [ ] Output is a single JSON object, parseable, with **no** prose, comments, or markdown
      fences around it.
- [ ] Every `required_top_level_fields` / `required_top_level_keys` key is present.
- [ ] If `additional_fields_allowed` is false (or "extras not evaluated"), emit no unlisted
      top-level keys.
- [ ] Nested objects (`authorization`, `assistance`, each line, `basis_audit`) include all
      their required sub-keys.

## Values
- [ ] Every enum value is spelled exactly as one of the template's choices (case, spaces,
      punctuation). This includes `source_precedence`, dispositions, routes, statuses,
      letters, actions, segments, program names.
- [ ] Codes, ids, medication names, and modifiers match the records; apply the required
      case (e.g. lowercase medication names).
- [ ] `null` (not `""` or `0`) for an absent modifier; `null` for a non-applicable date or
      deadline.

## Lists
- [ ] Contents are exactly the correct set — every required element present, no spurious or
      near-miss element (a wrong element and a missing element each cost separately).
- [ ] Sorted per the field's ordering rule (ascending id, alphabetical, choice order,
      claim-line order, or memo order) and de-duplicated.
- [ ] `evidence`/`controlling` lists hold relied-on records; `excluded`/`exception`/
      `missing` lists hold the stale/gap/excluded records — no overlap that contradicts the
      decision.

## Numbers & dates
- [ ] Each numeric field is rounded to the field's stated precision (cents for currency,
      the stated decimals for ratios).
- [ ] Line-level amounts sum to the totals; recovery/gap use the correct sign convention
      (positive = underpayment recovery / revenue shortfall).
- [ ] Every derived number was recomputed from source values, not carried over from a
      requested/billed figure.
- [ ] Dates are `YYYY-MM-DD`; any date arithmetic is anchored on the correct source date
      (e.g. the determination/event date, not the reporting date) and uses the window the
      task states.

## basis_audit
- [ ] `source_precedence` matches the lever that governed the decision.
- [ ] `controlling_record_ids` and `exception_record_ids` use real environment ids and land
      on the right side (drivers vs. gaps/exclusions).
- [ ] `precedence_record_order` lists controlling records before exceptions, highest
      priority first.
