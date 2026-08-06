# Pre-submit checklist

Run every item against the task's own `answer_template.json` before returning.

## Shape
- [ ] Output is a **single JSON object**, valid JSON, **no prose / no code
      fences / no trailing commentary**.
- [ ] Exactly the template's `required_top_level_keys` — none missing, none
      extra.
- [ ] Every constant matches: `task_id` / `batch_id` / `roster_id` /
      `program_code` = the template's `required_value`/`constant`.
- [ ] Every list item has exactly its `item_required_keys`.

## Membership & ordering
- [ ] One item per required member — all `required_patient_ids` /
      every referral in the batch / every transfer / every returned candidate.
- [ ] Each list sorted per its `ordering` (ascending `*_id`, alphabetical by
      code, or the stated priority order). `priority_order`/ranked lists use
      dense integer ranks starting at 1.
- [ ] IDs verbatim from the portal (uppercase, original numbering).

## Values
- [ ] Every enum value is a literal from that field's `allowed_values`.
- [ ] "Unordered set" arrays (reason/issue/blocker/action/component codes,
      missing-artifact lists) contain **no duplicates**.
- [ ] `_or_null` fields use `null` (not `"none"`/`""`/`0`) when N/A; explicit
      `"none"`/`"not_applicable"` used only where the enum lists it.
- [ ] Dates are `YYYY-MM-DD`; free date fields hold the real value from the data
      or the chosen reference date.

## Internal consistency (recompute — don't guess)
- [ ] Every `total_*` equals the number of emitted items.
- [ ] Every `counts_by_*` / `*_counts` / `decision_counts` /
      `status_counts` object is tallied from the emitted item rows and sums
      correctly.
- [ ] Cross-field agreement: a `ready` / `ready_to_schedule` item has no
      blocking codes; a code that drives an item's status also appears in that
      item's code list and in the relevant `blocker_sets`/discrepancy list; a
      `none` owner/channel pairs with an accepted/clean item.
- [ ] Composite matrices (e.g. urgency×readiness) cover the emitted rows and sum
      to the total.
