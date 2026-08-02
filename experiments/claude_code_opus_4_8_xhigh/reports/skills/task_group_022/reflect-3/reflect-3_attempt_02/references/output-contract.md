# Satisfying the answer template exactly

The `answer_template.json` is a JSON Schema. `answer.json` must validate against
it with zero slack. Before writing the file, walk this checklist.

## Keys

- Output contains **exactly** the keys listed in `required` — no more, no fewer.
- `additionalProperties:false` (or `additional_properties:false`) applies at every
  object level, including nested objects (e.g. per-account or per-region entries,
  a `case_state_summary`, a `correction_target`, an `audit_record`). Nested
  objects must also carry only their own required keys.
- Do not add explanatory or debug fields. The file is the JSON object and nothing
  else — no comments, no prose, no trailing text.

## Types and precision

- Integers are integers (counts of orders/tasks/cases/shipments/rows), numbers are
  numbers.
- Round rates to the exact decimals stated (`multipleOf: 0.0001` → 4 dp;
  `decimal_places: 4`; money `precision: 2` / `net_refund_display_decimals: 2`).
- Rounding happens only on the final reported value. Do not round intermediate
  values used for ordering, tie-breaks, or band classification.
- Respect `minimum`/`maximum` (e.g. rates in `[0,1]`).

## Arrays

- Match `minItems`/`maxItems` exactly (e.g. exactly two worst regions, exactly
  three top employees/accounts). If the data cannot fill a fixed-size list, re-read
  the scope — the shortfall usually means an eligibility filter is wrong.
- Honor `uniqueItems`.
- Apply the ordering the request specifies, computed on unrounded values.
- Every element matches its `pattern` (e.g. `^ORD-[0-9]{6}$`, `^ACC-[0-9]{4}$`,
  `^CASE-[0-9]{6}$`) and any nested required keys.
- Some templates forbid arrays entirely (a note like "No arrays are permitted in
  this output"). Respect it — such answers are all scalars and nested objects.

## Enums

- Use the exact allowed spelling from the `enum` (status/risk bands, reason codes,
  correction status). Case and punctuation must match.

## Final self-check

1. Parse `answer.json` — is it valid JSON and a single object?
2. Diff its key set against the template's `required` at every level.
3. Re-confirm each numeric field's precision and each array's size/order/uniqueness.
4. Re-confirm each enum value is an allowed literal.
5. Confirm no stray keys, comments, or trailing content.
