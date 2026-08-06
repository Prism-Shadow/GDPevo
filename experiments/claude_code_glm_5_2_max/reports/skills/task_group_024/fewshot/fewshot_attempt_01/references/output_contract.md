# Output contract — schema conformance, precision, ordering

The `answer_template.json` is the contract. These are the conventions that recur across templates;
follow the template literally wherever it is more specific.

## Conformance
- Include every field in `required`; omit every field not allowed (`additionalProperties: false`).
- Echo `const` values verbatim (e.g. `scope_id`, `quarter`, `product_area` constants).
- Use only values from each `enum`; use `null` only where the schema explicitly allows it (e.g. a
  nullable `primary_category`/`secondary_category`).
- Respect `type` (integer counts vs number percentages; arrays vs objects) and bounds (`minimum`,
  `minItems`, `maxItems`, `pattern`).
- Output **one JSON object**, no prose, no markdown fences, no trailing commas.

## Precision
- Percentages / completion (`actual_pct`, `target_pct`, `gap_pct`, `completion_pct`,
  `category_percentages`): **1 decimal place**.
- Rates / scores (`breach_rate`, `sla_breach_rate`, `readiness_score`): **exactly 3 decimals**.
- Counts: integers.
- Round half up at the stated precision (e.g. 5/8 = 62.5%; 7/9 = 0.7777… → 0.778).
- `gap_pct` / `gap` = `actual − target` (sign matters; negatives are deficits/under-invested).

## Ordering (defaults — override per the schema's `description`)
- ID lists: ascending / lexicographic.
- `included_work_item_ids`: `closed_at` ascending, then id ascending.
- Teams: alphabetical (some schemas fix a specific order — follow the schema).
- Mix/gap tables: fixed order NewFeature, TechDebt, Reliability, Security.
- `under_invested_categories`: most-negative gap first.
- `duplicate_clusters`: by `primary_id` ascending; each `duplicate_ids` ascending.
- `milestone_completion`: by `milestone_id` ascending.
- `gating_work_item_ids`: ascending, unique.
- `critical_dependency_chains`: lexicographic by full path.
- `escalation_queue_ids`: priority/urgency order (NOT lexicographic).
- Exclusion ID lists: by the schema's stated order (closed_at then id, or ascending).

## Validation checklist (manual, if the script is unavailable)
- [ ] All `required` fields present; no extra properties.
- [ ] All `const` fields equal the template's constant.
- [ ] All values within their `enum`.
- [ ] Counts are integers and non-negative where required; percentages are numbers.
- [ ] `category_counts` sum == `total_included` == `len(included_work_item_ids)` (mix tasks).
- [ ] Mix/gap table has exactly 4 rows in the fixed category order; `gap == actual − target`.
- [ ] `under_invested_categories` are exactly the negative-gap categories, most-negative first.
- [ ] `overdue_primary_ids ⊆ included_primary_ids`; severity/aging counts sum correctly.
- [ ] `breach_rate`/`readiness_score` have exactly 3 decimals and equal the stated ratio.
- [ ] Duplicate IDs are excluded from every primary count/total; clusters sorted by `primary_id`.
- [ ] Every ID list ordered per the schema.
- [ ] Valid JSON; no prose outside the object.

## Validate with the script
```bash
python3 skill/scripts/validate_answer.py path/to/answer.json path/to/answer_template.json
```
It is dependency-free: it checks `required`, `type`, `const`, `enum`, `additionalProperties`,
`minItems`/`maxItems`, and `pattern`, and exits non-zero with a violation list on failure. If
`jsonschema` is installed in the environment, prefer it for full draft-2020-12 coverage.
