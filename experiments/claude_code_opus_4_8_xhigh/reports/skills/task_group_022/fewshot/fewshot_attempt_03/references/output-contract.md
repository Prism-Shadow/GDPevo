# Reading the answer contract

`input/payloads/answer_template.json` is a JSON-Schema-shaped contract. Your
`answer.json` must be **exactly one JSON object** that satisfies it, with **no
commentary, no extra keys, and no wrapping** (do not nest it under a "result"
key, do not emit Markdown fences).

## Field-by-field discipline

- **Emit every key in `required`, and only keys that appear in `properties`.**
  Templates set `additionalProperties: false` (sometimes spelled
  `additional_properties`), so any stray key fails the contract.
- **Types are literal.** `integer` means a JSON integer (no `.0`); `number`
  means a JSON number. Counts are integers; rates/money/hours are numbers.
- **Rounding / precision.** Look for `multipleOf`, `decimal_places`, or
  `precision`. Round **only the final reported value** to that many places.
  Keep full precision for every intermediate computation, and especially for
  sort keys and tie-breaks (templates often say "ordered by *unrounded* rate").
  - `multipleOf: 0.0001` / `decimal_places: 4` → 4 dp.
  - `multipleOf: 0.01` / `precision: 2` → 2 dp (money, hours).
- **Enums are exact strings.** Status/risk fields (`HEALTHY|WATCH|CRITICAL`,
  `STABLE|PRESSURED|AT_RISK`, `CONTROLLED|ELEVATED|SEVERE`, `LOW|MODERATE|HIGH`,
  `APPLIED|NOT_APPLIED`) must match case-for-case.
- **String `pattern`s pin ID formats.** e.g. `^ORD-[0-9]{6}$`,
  `^CASE-[0-9]{6}$`, `^ACC-[0-9]{4}$`. Preserve zero padding exactly as stored;
  never reformat an identifier.
- **Array sizing & uniqueness.** `minItems`/`maxItems` (or `min_items`/
  `max_items`) that are equal mean an exact length — return exactly that many.
  `uniqueItems: true` means de-duplicate.
- **Array ordering is graded.** The template (and/or request) states the sort,
  including tie-breaks, e.g. "order_id ascending", "rate ascending then region
  ascending", "units_per_hour desc, then employee_id asc". Apply the full
  multi-key sort. When the primary key is a rounded display value but the rule
  says to sort by the *unrounded* value, sort by the unrounded value.
- **Nested objects** (e.g. `worst_accounts[]`, `correction_target`,
  `case_state_summary`) have their own `required`/`properties` — satisfy them
  recursively with no extra keys.

## Final step

Run the validator before you finish:

    python3 skill/scripts/validate_answer.py answer.json input/payloads/answer_template.json

It flags missing/extra keys, type/enum/pattern mismatches, item-count and
decimal-place problems. A clean run only proves the **shape** is right — it does
not check business correctness.
