# Output contract reference

The single JSON object you submit must conform to *this task's*
`answer_template.json`. Templates come in several shapes; read the one in front
of you and mirror it exactly.

## Template variants you will see

- **`required_top_level_keys` + `template`/`response`/`fields`/`required_output`**
  — the template names the exact top-level keys and, per section, the required
  child keys, array lengths, orderings, `cardinality_rules`, enum
  `allowed_values`, and precision. Reproduce keys verbatim (including casing).
- **Type-annotated descriptors** — fields given as `{"type": "...", ...}` or as
  prose like `"integer; labels in the request"`. Replace each descriptor with a
  computed value; **omit any `template_instructions`/`submission`/`description`
  meta wrapper** and emit only the real payload object it describes (e.g. the
  contents under `required_output` / `response`).
- **Fixed values** — some fields declare a `required_value` (e.g. an echoed
  `request_id`); emit exactly that value.

Always map every template field to the module/step that produces it *before*
computing, so nothing is missing and nothing extra is added.

## Precision, types, ordering, missing

- **Precision:** default is 4 decimal places for non-integer reported statistics,
  encoded as JSON numbers (trailing zeros need not be preserved). Some tasks
  differ (e.g. 6 dp for computed reals but 4 dp for literal grids/thresholds) —
  follow the template's `numeric_rule`. Compute unrounded; round only on output.
- **Types:** integers, booleans, and enums use natural JSON types (not strings),
  unless the template says otherwise. Identifiers stay strings (keep FIPS leading
  zeros; uppercase state codes / ISO3 as instructed).
- **Ordering:** every list keeps the exact order the request/template specifies
  (year ascending, registered division order, feature order, checkpoint order,
  subset lexicographic order, state ascending, …). Aligned arrays stay
  positionally consistent; never sort one member of an aligned set independently.
  Some templates require set-like lists to be unique and sorted ascending —
  honor that where stated.
- **Cardinality:** obey `cardinality_rules` (e.g. "length equals state_n",
  "one entry per balanced state code, and no others", "must exactly match
  another array"). Verify lengths and one-to-one correspondence.
- **Missing:** use JSON `null` only for a mathematically-unavailable statistic;
  never `NaN`/`Infinity`, never a zero-fill for suppressed/blank data.

## Override resolution (only when the request carries a protocol / overrides)

Most requests are used directly. If the request has a `protocol_id` and/or keys
suffixed `_overrides` (or `module_overrides.<module>`, `reporting_overrides`),
resolve them deterministically **before any computation**:

1. Start from the effective base (the direct request; plus any inherited
   canonical defaults for that exact protocol version, if applicable).
2. Bind direct keys to the identically-named canonical key/path. A
   `<section>_overrides` root key targets canonical `<section>` (strip only the
   terminal `_overrides`); `module_overrides.<module>` targets that exact
   top-level module.
3. Apply in request document order: deep-merge objects by exact key; **replace
   whole arrays** (never concatenate/union/position-patch); replace explicit
   scalars/strings/booleans/`null` only at their exact path; inherit absent paths.
4. Reject unknown targets, inferred aliases, key renames, and type coercions.
   Task-local direct/resolved values win at the same path.
5. Freeze one effective contract and use it consistently in every module.

## Optional `protocol_registry_record` provenance block

Some *reference answers* carry a top-level `protocol_registry_record`
(`portable_protocol_profile`) describing the reusable method. Per its own text it
is **optional solved-answer provenance only**: it is not solver-visible input,
is not required or expanded by the answer template, and is **ignored in full by
the evaluator**. Therefore:

- You do **not** need to produce it. Focus on the template's required keys.
- If you choose to include such a block, it must contain **method semantics
  only** — never task-specific analytical values (coefficients, counts, cohorts,
  p-values, entity lists). It must not substitute for recomputing every reported
  field from the live portal for the current task.

## Final validation checklist

- Exactly the template's top-level keys — no extras, none missing.
- Every required child key present; correct JSON types; enums within
  `allowed_values`.
- Array lengths and orderings match; aligned arrays stay positionally consistent.
- Precision applied only at output; unrounded values used for gates/medians/
  extrema.
- No `NaN`/`Infinity`; `null` only where mathematically unavailable.
- The response is a single JSON object and nothing else (no prose, no code fence
  required by the grader — emit raw JSON).
