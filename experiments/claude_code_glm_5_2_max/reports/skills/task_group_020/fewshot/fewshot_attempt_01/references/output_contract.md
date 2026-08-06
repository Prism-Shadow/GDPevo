# Output Contract

## Conform to THIS task's template
- The authoritative schema is `input/payloads/answer_template.json` for the current task. Read it before writing output.
- Honor its required top-level fields, nested object fields, allowed enums, stable ID lists, and any ordering/instructions block.
- Templates differ across tasks (different fields, enums, stable IDs, ordering rules). Do not import a prior task's schema, enums, or IDs.

## Units and precision vary per task — read them from the prompt + template
Common conventions (confirm per task):
- **Currency:** integer USD (whole dollars) unless the template says otherwise.
- **Percent points:** precision is task-specific — one decimal, two decimals, or whole points. Use exactly what the prompt states.
- **Holder fully-diluted percentages** may require four decimals.
- **Months:** integers.
- **Dates:** `YYYY-MM-DD`.

Never mix precisions from different tasks.

## Stable IDs
- Use stable source IDs exactly as they appear in the workbench (term ids, consent ids, material-contract ids, employee ids, finding ids, risk-estimate ids, document ids).
- `source_term_ids` is an empty array `[]` for a missing required term (no draft term to cite).
- Never invent IDs and never reuse an ID from a different deal.

## Quantification base
- Derive dollar amounts from the deal's headline purchase price unless a source explicitly states a different basis. See `analysis_method.md` §5.

## JSON only
- Return only valid JSON conforming to the template. No prose, commentary, or markdown fences around the JSON unless the harness requires them.
- Every enum value must be one the template allows; every required field present.

## No hardcoded / cross-deal values
- Do not copy deal-specific values (deal ids, dollar amounts, percents, term ids, position codes) from any example into output. Every value must come from the current task's workbench or be computed from it.
