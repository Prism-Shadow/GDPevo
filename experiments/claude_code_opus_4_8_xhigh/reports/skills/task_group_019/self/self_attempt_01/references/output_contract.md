# Output contract

The `answer_template.json` for the task is the single source of truth for the
output. Before writing any answer, extract from it:

- **Top-level keys** — emit exactly these, no more, no fewer.
- **Per-item schema** — the keys and types for each list element.
- **Enum `allowed_values`** for every coded field — you may emit only these
  strings. Vocabularies differ between tasks even in the same family; never carry
  a code over from another task.
- **Required list length** (e.g. exactly 8 applications, queue of 10) and the
  **exact target set** named in the prompt.
- **Ordering rules** — e.g. "ascending by application_id", "sort ascending by
  code and remove duplicates", "order by ascending rank", "operational
  sequence." Some fields say "any order is accepted" — dedupe anyway.
- **Empty-value handling** — use an empty array `[]` when no code/id applies
  (do not omit the key, do not use null).
- **Date format** — `YYYY-MM-DD` wherever dates appear.

## Hard rules

1. **JSON only.** No prose, markdown, code fences, comments, citations, or keys
   outside the template. The response body is the JSON object itself.
2. **Exactly the required entities**, in the required order and count.
3. **Only allowed enum values.** If your reasoning produces a fact with no code
   in this template, it simply does not appear in the output.
4. **Sort and dedupe** every list per the template's ordering.
5. **Internal consistency.** Summary/aggregate fields must be derivable from the
   item-level decisions:
   - counts equal the tallies of determinations and sum to the item count;
   - "high risk", "policy impacted", "board review", "close/uncertain match"
     lists exactly equal the items meeting those conditions;
   - excluded-ID and flagged-ID lists match what the per-item logic produced.

## Pre-submit checklist

- [ ] Correct family, correct target set, correct list length.
- [ ] Every emitted code is in the template's `allowed_values`.
- [ ] Every list sorted + deduped as specified; empty arrays where nothing applies.
- [ ] Summary numbers and lists reconcile with the items.
- [ ] Thresholds/boundaries were read from `details_json`, not hardcoded.
- [ ] Output is a single JSON object and nothing else.
