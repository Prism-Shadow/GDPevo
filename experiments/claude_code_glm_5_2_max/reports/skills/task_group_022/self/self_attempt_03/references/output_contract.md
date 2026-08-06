# Output Contract Checklist

How to read an `answer_template.json` and emit a `answer.json` that conforms to it.
Derived from the shared template shape across the train tasks; contains no
task-specific values.

## Reading a template

A template is a JSON Schema. The fields that matter for conformance:

- `required`: the object **must** contain exactly these keys.
- `additionalProperties: false` (and the snake_case variant
  `additional_properties: false`): no key outside `required`/`properties` is
  allowed. Extra keys fail. Do not invent "helpful" fields.
- `properties.<field>.type`: `integer` vs `number` vs `string` vs `object` vs
  `array`. Integers must not be emitted as floats; rates are `number`.
- `minimum` / `maximum`: bounds. Rates are constrained to `[0,1]`.
- `multipleOf` (and `decimal_places` / `precision` / `x-precision`): the rounding
  grain. `multipleOf: 0.0001` ⇒ round to 4 dp. `precision: 2` / `decimal_places: 2`
  ⇒ round to 2 dp. Emit exactly that many decimals where the grain implies it.
- array fields: `minItems`/`maxItems` (equal ⇒ exact size), `uniqueItems`,
  `items.pattern` (e.g. `^ORD-[0-9]{6}$`), and a stated `ordering`/`order`/`order`
  key describing the sort.
- enum fields: value must be one of the listed strings, character-exact.
- nested objects: recurse — they have their own `required` + `additionalProperties`.

## Canonical field families seen (apply the matching treatment)

- Counts (`*_count`, `*_task_count`, etc.): non-negative integers, exact.
- Rates/ratios (`*_rate`, `*_ratio`): `number` in `[0,1]`, rounded to the template
  grain, denominator = the fixed cohort unless specified otherwise.
- Money (`*_amount_usd`, `net_*_usd`): `number`, `precision: 2`, reported in the
  currency the payload names (USD). Convert at the per-row service-date FX rate.
- ID lists (`*_order_ids`, `*_case_ids`, `*_task_ids`): array of strings matching
  the pattern, `uniqueItems`, sorted ascending.
- Ranked entity lists (`worst_warehouse_regions`, `top_three_employee_ids`,
  `worst_accounts`): exact size = `minItems`=`maxItems`; sort by the stated key(s)
  then tie-break by the stated field; each item is itself a schema-constrained object.
- Status/risk enums (`overall_status`, `cohort_risk`, `correction_status`,
  `facility_status`, `support_risk`): one of the listed strings, from the cascading
  rule list in the request.
- Correction block (`correction_target`, `mutation_result`, `audit_record`,
  `backlog_analysis`): object-valued; echo the payload's approved-correction values
  into the audit record, and report observed (not assumed) mutation counts.

## Emission rules

1. Output is a single top-level JSON object — no array wrapper, no envelope.
2. `answer.json` contains *only* that JSON document. No prose, no markdown, no
   trailing comments, no code fences.
3. Key order is not schema-enforced, but emit in the template's `required` order for
   readability.
4. Booleans are `true`/`false`; integers have no decimal point; `null` is allowed
   only where the schema permits (e.g. `nullable` old_value in audit).
5. Rounding: half-away or banker's may differ on exact .5 boundaries — prefer the
  language's `round` to the stated decimals and, if a tie is possible, match the
  template's `multipleOf` by construction (compute to more decimals, then round once).

## Pre-write validation sequence

1. `required` set == set of keys in your object (no missing, no extra).
2. `additionalProperties:false` respected at every object depth.
3. Each value's type matches; integers not floatified.
4. Bounds held; rates in `[0,1]`.
5. Each numeric value is a multiple of its `multipleOf` (after rounding).
6. Array lengths hit the exact `minItems`==`maxItems`; items unique; items match
   pattern; array sorted per the stated order.
7. Enums exact.
8. Then — and only then — write `answer.json`.
