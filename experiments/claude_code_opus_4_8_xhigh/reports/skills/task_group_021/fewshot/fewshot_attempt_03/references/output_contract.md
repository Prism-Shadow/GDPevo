# Output contract discipline

The task grades a single JSON object against `payloads/answer_template.json`. Treat that
template as law — it varies per task, so read it every time.

## Hard rules
1. **Output only the JSON object.** No prose, no Markdown fences, no trailing text. The
   prompts say "Return only one JSON object" / "Write JSON only".
2. **Match the schema exactly.** Most templates set `additionalProperties: false` and list
   `required` keys — include every required key and **no** extra keys, at every nesting level.
   Some templates are JSON-Schema (`$schema`, `properties`); others are a bespoke contract
   (`required_top_level_keys`, `field_contract`, `item_required_keys`). Honor whichever form
   is present.
3. **Enums:** every coded/status field must use a value from the template's `enum`
   (control codes, `status`, `action`/`routing`, fuel_type, service_class, region, etc.).
4. **Counts are exact integers.** No floats where an integer is required.
5. **Rounding:** apply the stated precision (money/volume/weight/distance usually 2 dp;
   `quarantine_rate` 4 dp; maintenance distance 2 dp / `multipleOf: 0.01`). Round once, at
   the reported value, after all summation. Keep phone as a **string** of digits even though
   it looks numeric.

## Ordering (very common failure point)
Follow the template's stated ordering for every array. Recurring rules:
- ID lists (`*_ids`) → **lexicographic ascending**, deduplicated / `uniqueItems`.
- `focus_*` arrays → ascending by the focus/cluster/person ID.
- Panels (`reference_decisions`, `event_decision_panel`, `source_retention`,
  `ledger_routing`, `duplicate_groups`) → ascending by their key (reference_id / event_id /
  charge_id / logical_event_id), and any inner `snapshot_ids` lexicographic ascending.
- Ranked arrays → by the named metric descending, ties broken by ID ascending, then `rank`
  filled 1..N ascending. Respect the `limit` from the scope.
- Grouped totals (`fuel_type_totals`, `service_class_totals`, `region_rollup`,
  `readiness_by_depot`) → ascending by the group key, **one row per group value**
  (fixed-length arrays such as `minItems == maxItems` must be complete).

## Fixed-length panels
When the template pins `minItems == maxItems` (e.g. exactly 5 focus clusters, 6 reference
decisions, N transaction decisions), emit exactly that many, one per scoped ID, in order —
even if a value is zero or a code had to be inferred.

## Self-check before returning
- Validate the object against the template (types, enums, required keys, `additionalProperties`).
- Confirm array lengths match `minItems`/`maxItems`/scope list sizes.
- Confirm every partition sums to its total and every ranked list is correctly sorted.
- Confirm no key was invented and every ID appears in the scope or public data.
