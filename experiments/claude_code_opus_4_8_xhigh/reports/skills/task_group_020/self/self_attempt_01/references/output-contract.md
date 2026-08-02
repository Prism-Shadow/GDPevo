# Output contract

The answer template is the specification. Where the prompt and the template disagree on a
detail, the template's structure wins for *shape* and the prompt wins for *units and scope*;
if they truly conflict, satisfy both where possible and follow the template's explicit
`instructions` block when it has one.

## Template genres

### Skeleton templates

The template is the literal answer shape: real keys, with `null`, `0`, pipe-separated enum
strings (`"LOW | MEDIUM | HIGH"`), and descriptive placeholder strings
(`"stable consent ID"`, `"contract name"`). Arrays contain **one example element**.

Rules:

- Emit the same key set at every level.
- Replace every placeholder with a real value. A `null` in the template is a *slot*, not an
  instruction to emit null — emit null only when the data genuinely doesn't exist and the
  template allows it.
- Expand each example array to one element per real record; never emit the example element.
  If a list is genuinely empty, emit `[]`.
- Keys whose template value is already a correct literal (`"task_id": "train_00X"`,
  `"deal_id": "PRJ_X"`, `"currency": "USD"`, `"prepared_for": "M&A Committee"`,
  `"value_basis": "equity value"`) are constants — carry them through unchanged.

### Descriptor templates

The answer shape is described under meta-keys — `required_output_shape`,
`required_top_level_fields`, `issue_object_fields`, `summary_metrics_fields`,
`allowed_enums`, `possible_issue_ids`, `stable_issue_ids`, `stable_redline_ids`,
`instructions`, `units`, `schema_name`, `version`.

Rules:

- Emit the **described** object. `required_output_shape` / `required_top_level_fields` gives
  the real top-level keys; the `*_fields` blocks give the per-object keys.
- **Never emit the meta-keys themselves** — no `allowed_enums`, no `required_output_shape`,
  no `schema_name` in the answer unless it is listed as a required answer field.
- Field descriptions carry the type contract: `"integer or null"`, `"array of term_id
  strings; use an empty array for missing required terms"`, `"one value from
  possible_issue_ids"`. Honor them literally, including the empty-array instruction.
- Every object of a described type carries **all** its listed keys, using `null` where a value
  doesn't apply. Don't emit a sparse object.
- `possible_issue_ids` / `stable_issue_ids` / `stable_redline_ids` are closed vocabularies for
  those ID fields — use those exact strings, and only those. They may be supersets: emit only
  the ones the deal's evidence supports, but never invent one outside the list.
- `instructions.ordering` binds: sort arrays exactly as told (ascending by ID, or priority
  order highest→lowest where requested).

## Enums

- Extract every allowed value: from `allowed_enums`, from pipe strings (`"a | b | c"`), and
  from inline prose (`"one of: x, y, z"`).
- Emit exactly one value, byte-identical to the listed spelling. Never ship the pipe string or
  the `one of:` text — that is the single most common way these answers fail.
- Normalize source casing to the template's: source `High`/`Medium`/`Low` and `low`/`medium`
  become `HIGH`/`MEDIUM`/`LOW` when that's the enum.
- Long snake_case enum values encode the whole recommended position (e.g. a value naming both
  a preferred ask and a conditional fallback). Read them as decision candidates: the enum list
  tells you which conclusions the grader expects to be reachable, so pick the one your
  analysis actually supports rather than paraphrasing.
- Free-text fields described as "short snake_case code" are not enums — write a stable,
  descriptive snake_case code and keep it consistent across the answer.

## Units and numbers

| Kind | Rule |
| --- | --- |
| Currency | Integer dollars. No decimals, no strings, no separators, no `$`. |
| Percent | Percent **points** (`12.5` = 12.5%), rounded to exactly the decimals the prompt names — this varies per task (one, two, or four decimals, or whole points). |
| Holder share | If the template asks for a percentage from `cap_table.fully_diluted_pct`, check whether the source fractions sum to `1.0` and convert to the requested representation and decimal count. |
| Months | Integer. |
| Counts | Integer. |
| Dates | `YYYY-MM-DD`, copied from the source fields (`signing_date`, `meeting_date`, `note_date`, `effective_date`). |
| Booleans | JSON `true`/`false` when the field is typed boolean; the string `"yes"`/`"no"` when the enum says so. Source is `"yes"`/`"no"` either way — convert deliberately. |
| Null | Use `null` for genuinely inapplicable numeric slots; use the field's not-found enum (e.g. `not_found_in_current_records`) where one exists. Never use `0`, `""`, `"N/A"`, or `"unknown"` as a stand-in. |

Round half-up explicitly. Python's built-in `round()` is banker's rounding and will produce
off-by-one dollars and wrong second decimals — use `scripts/units.py`.

Derive, don't guess: if a dollar figure equals a percentage of a base, compute it from the
base rather than copying a number out of prose.

## Consistency checks before emitting

1. Valid JSON, one object, UTF-8, no markdown fence, no text before or after.
2. Key set matches the template exactly at every level — none missing, none extra.
3. No placeholder survives: no `" | "` enum strings, no `"one of:"`, no `"stable ... ID"`,
   no `"string"`, no `"YYYY-MM-DD"` literal, no `TERM_PRJ_X_00`-style example IDs.
4. No template meta-keys leaked into the answer.
5. Every enum value is in its allowed list.
6. Every ID appears in the workbench (or in the template's fixed vocabulary) and belongs to
   the target deal.
7. Counts equal array lengths; risk tallies equal assigned ratings; totals equal the sum of
   the components you emitted; distinct-value counts (e.g. a "business outcome count") equal
   the number of distinct values you actually used.
8. Ordering rules applied.
9. Output is English only, no narrative fields padded with commentary.

`scripts/validate_answer.py` automates 1–5, 7 (heuristically), and 3 in particular.
