# Output contract — ordering, precision, emission

The answer is ONE JSON object that conforms EXACTLY to `answer_template.json`. The template is authoritative; these are the rules that recur across the family.

## Shape
- Single JSON object. No array wrapper, no top-level scalar.
- `additionalProperties: false` is common: emit ONLY keys the schema lists.
- Every key in `required` must be present; every `minItems`/`maxItems` must be satisfied (e.g., `minItems: 5, maxItems: 5` means exactly 5).
- Enums: emit only values in the listed `enum`. Patterns (e.g., `^FC-[0-9]{6}-[0-9]{6}$`) must match.

## Ordering (read the template's `description` / `x-ordering_rules`)
- ID lists (mismatch, quarantine, unrecognized, invalid, regression, dispatchable, contested, quarantine_row_ids): **deduplicated, lexicographically ascending**.
- Per-object arrays keyed by an ID: sorted by that ID **ascending** (transaction_id, charge_id, alias_id, reference_id, event_id, cluster_id, control_case_id, focus_person_id, depot_code, region, fuel_type, service_class).
- Rankings: by `rank` ascending (1..N), with the case_scope sort + tie-breaks deciding the order.
- `snapshot_ids` inside a duplicate group: unique, lexicographically ascending.

## Precision
- Counts are exact integers (no floats).
- Money and quantity fields: round to the decimals declared in the template (typically 2). Ratio fields like `quarantine_rate`: round to their declared decimals (e.g., 4) and satisfy any `multipleOf`.
- Round at emission only; keep full precision through the pipeline so per-category totals sum to the grand total.
- `total_*` = sum of the corresponding per-category totals. Compute consistently so the parts add up to the whole.

## IDs
- Use only stable IDs that exist in the public data or are supplied in `case_scope.json`.
- Do not invent IDs. Do not rename them.

## Emission
- Output the JSON object and nothing else: no commentary, no Markdown fences, no trailing text.
- Validate before emitting: `python3 skill/scripts/validate_answer.py <answer.json> <answer_template.json>`.
