# Output Discipline

The final answer is a single JSON object. These rules hold for every Cedar Ridge intake task,
regardless of which template is supplied.

## JSON only

- Return exactly **one JSON object**. No prose before or after. No markdown fences. No
  trailing commentary. If the prompt says "JSON only" or "no prose outside the JSON", treat that
  as strict.
- Top-level keys appear in the order the template lists them under `required_top_level_keys` /
  `top_level` / `field_definitions`.
- Use the exact key names from the template — no synonyms, no extra keys, no renamed keys.

## Controlled values only

- Every enum value you emit must appear in the template's `allowed_values` / `allowed` list for
  that field.
- `null` is allowed only where the template explicitly permits it (`enum_or_null`,
  `integer_or_null`, `enum_or_null` priority tiers).
- Integers are integers (no decimals, no strings) for counts and `first_checkin_days`.
- Dates are `YYYY-MM-DD` strings.
- Booleans are JSON `true` / `false`.

## ID fidelity

- Use IDs exactly as the portal returns them — same casing (uppercase prefixes like `P001`,
  `REF0001`, `TR0001`, `DUP-...`), same punctuation. Do not lowercase or "normalize" them.

## List ordering

Apply the template's `ordering` rule for each list exactly:

| Template wording | What to do |
|---|---|
| `ascending by patient_id` / `ascending referral_id` / `ascending transfer_id` / `ascending group_id` / `ascending insurance_id` | sort the list ascending by that id |
| `alphabetical by code` / `alphabetical by doc_type` / `alphabetical by artifact enum string` | sort alphabetically by that string |
| `urgency then readiness_status` | sort by urgency, then by readiness_status |
| `highest priority first, non-ready referrals only` | exclude `ready` referrals; order by `priority_tier` then urgency; assign `rank` from 1 |
| `treat as unordered set` / `order is not meaningful` / `unordered set` | emit the set; order is not meaningful — sorting for determinism is fine but do not imply meaning |

When a list and its items each have ordering rules (e.g. list ascending by `group_id`, with a
nested `referral_ids` ascending by `referral_id`), apply both.

## Summary counts

- Derive every summary count from the per-record list you built — do not count by eye, and do not
  recompute from the raw portal list (you may have excluded distractors).
- Include **every** bucket the template lists under `required_keys` / `count_keys` /
  `integer_keys`, even when the count is `0`. Missing a zero bucket is a common failure.
- For two-dimensional summaries (e.g. `counts_by_urgency_and_status`), emit one row per non-zero
  combination in the order the template specifies (e.g. urgency then readiness_status), and omit
  zero-count rows unless the template says otherwise.
- `total_*` counts equal the length of the corresponding per-record list — re-check this
  equality before returning.

## Pre-return checklist

Run through this before emitting the JSON:

- [ ] Scope is correct: every record in the per-record list belongs to the target
      `roster_id` / `batch_id` / `program_code`, and the list length matches the scope count.
- [ ] Every emitted enum value is in the template's allowed list for its field.
- [ ] Every required key (top-level, per-item, nested) is present.
- [ ] No extra keys, no renamed keys.
- [ ] Every list is ordered per its `ordering` rule; unordered-set arrays are treated as sets.
- [ ] IDs match the portal's casing exactly.
- [ ] All summary buckets the template requires are present, including zeros.
- [ ] Every `total_*` equals the length of its per-record list.
- [ ] Two-dimensional summary rows are ordered and zero-rows handled per the template.
- [ ] Output is a single JSON object with no prose or fences.
