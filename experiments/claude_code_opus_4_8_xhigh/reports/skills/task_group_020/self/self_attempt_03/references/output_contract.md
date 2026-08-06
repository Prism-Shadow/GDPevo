# Conforming to answer_template.json

The template is written in several dialects. Identify which one you are holding before you
build the answer.

1. **Skeleton** — a literal example object with `null`s and one placeholder row per array
   (`"holder": "stable holder name from cap table"`). Mirror the shape exactly; replace
   every placeholder; repeat array rows as many times as the data requires.
2. **Spec sheet** — meta-blocks (`required_top_level_fields`, `issue_object_fields`,
   `required_output_shape`, `allowed_enums`, `units`, `instructions`, `ordering`) that
   *describe* the answer. The answer contains the described keys **only** — never the
   meta-blocks themselves. Do not emit `allowed_enums` or `required_output_shape` keys.
3. **Hybrid** — a skeleton plus an `instructions`/`allowed_enums` header. Obey both.

## Placeholders are never values

| Template text | Meaning |
|---|---|
| `"LOW \| MEDIUM \| HIGH"` | pick exactly one member |
| `"one of: a, b, c"` | pick exactly one member |
| `"string"`, `"integer or null"`, `"number or null"` | type spec |
| `"stable consent ID"`, `"stable holder name from cap table"` | put a real ID from the workbench |
| `"TERM_PRJ_<NAME>_00"`, `"stable_carveout_id"` | example ID format — substitute real IDs |
| `0` / `null` in a skeleton | placeholder, not a default |

Emitting a union string verbatim is the single most common fatal error. A literal like
`"currency": "USD"` or `"prepared_for": "M&A Committee"` **is** a real value — copy those.

## ID discipline

When a template supplies a closed list (`possible_issue_ids`, `stable_issue_ids`,
`stable_redline_ids`, an inline `one of:` list), use those spellings exactly and use nothing
else. Not every listed ID must appear — include the ones the deal supports — but never
invent an ID outside the list. Where the template asks for source IDs, use the workbench's
own identifiers (`TERM_*`, `CNS_*`, `MAT_*`, `EMP_*`, `FND_*`, `RSK_*`, `BM_*`, `DOC_*`,
`NOTE_*`). Synthetic IDs are acceptable only where the template says so (e.g. "synthetic
regulatory id").

## Units

Read the units instruction in **both** the prompt and the template; they can differ in
precision and the template's own `units` block governs its fields.

- **Currency** — integer dollars. No cents, no strings, no separators, no symbols.
- **Percent points** — a number in percent points (`12.50`, not `0.125`). Decimal places
  vary by task and sometimes by field within one task (two decimals, one decimal, whole
  points, and four-decimal *fractions* for cap-table holder percentages have all appeared).
- **Months** — integers.
- **Dates** — `YYYY-MM-DD`, copied from the record.
- **Booleans** — real JSON `true`/`false`, not `"yes"`/`"no"`, when the template's type says
  boolean. Conversely, keep `"yes"`/`"no"` strings where the enum lists them.

## Null policy

- Field applies but has no value in the workbench → `null` (or the template's explicit
  "not found" enum, if it offers one — prefer the enum).
- Field does not apply to this issue → `null`.
- **Never omit a key** that the template declares, and never add keys it does not.
- Arrays with no members → `[]`, not `null` and not a placeholder row.

## Ordering

Honor any `ordering` instruction literally (ascending by ID, or explicit priority order).
Absent an instruction, sort arrays by their stable ID so the output is deterministic.

## Emission

Return one JSON object and nothing else: no markdown fences, no preamble, no trailing
notes, no comments, no trailing commas, English only. If the task also expects a file, write
the identical bytes there.

## Self-check

```bash
python3 scripts/validate_answer.py answer.json input/payloads/answer_template.json --percent-dp 2
```

Then read your own JSON once more against the template key list. The validator catches
mechanical faults; only you can catch a row that cites the wrong `term_id`.
