# Output contract

The answer is exactly one JSON object matching `answer_template.json`. The
template is authoritative — when these notes and the template disagree, the
template wins.

## Shape

- Include every required key; omit keys not in the template
  (`additionalProperties: false`).
- Respect `minItems` / `maxItems` exactly (e.g. "exactly 5 focus clusters",
  "exactly 5 ranked carriers").
- Match id regex patterns stated in the template. Recognized hub id shapes
  include contact rows, transaction ids, charge ids, event ids, asset ids,
  and carrier ids — confirm the exact pattern from the current template
  rather than recalling it.

## Ordering

- ID lists: deduplicated, lexicographically ascending unless told otherwise.
- Ranked arrays: by `rank` ascending, with the `case_scope.json` tie-breaks
  applied (e.g. exception_count DESC then id ASC; mismatch_spend_usd DESC
  then id ASC).
- Rollups: lexicographically ascending by region / depot.
- Decision panels: ascending by their id, as the contract states.
- Within a duplicate group: snapshot ids lexicographically ascending.

## Numbers

- Counts are exact integers.
- Monetary and physical totals: round to the precision in the template
  (typically 2 dp).
- `quarantine_rate`: 4 dp, = quarantined ÷ canonical entities.
- Partition counts must sum to their total where the contract requires it
  (e.g. per-depot disposition counts summing to total_person_count).

## Final form

- One JSON object, no wrapper, no commentary, no Markdown.
- No trailing text after the closing brace.
- Re-validate against the template before emitting: required keys, enum
  membership, item counts, id patterns, ordering, and rounding.
