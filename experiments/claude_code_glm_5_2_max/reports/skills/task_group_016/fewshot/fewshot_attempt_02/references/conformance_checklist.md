# Output Conformance Checklist

Run this pass against your draft JSON and the task's `answer_template.json`
before returning. A single violation makes the answer wrong even when the
clinical reasoning is sound, so check every item.

## 1. Top-level shape

- [ ] The output is a single JSON object (not an array, not a string).
- [ ] It contains **exactly** the keys in `required_top_level_keys` — no missing
      keys, no extra keys (unless the template says extra keys are ignored).
- [ ] `task_id` and `case_id` use the template's fixed/constant values verbatim
      when `expected_constant` / `required_value` / `required_value` is present.
- [ ] `patient_id` comes from the runtime case bundle, not from memory.

## 2. Field types and enums

- [ ] Every enum field's value is one of its `allowed_values`, matched
      character-for-character (underscores, casing, singular/plural).
- [ ] Strings are strings; integers are integers (no `5.0` where an integer is
      required); numbers are JSON numbers.
- [ ] Booleans are `true`/`false`, not `1`/`0` or `"true"`.
- [ ] `null` is used **only** where the template permits it
      (`string_or_null`, `integer_or_null`, `[type, null]`, `nullable: true`).
      Required, non-nullable fields are always populated.

## 3. Numeric precision

- [ ] Each number is rounded/formatted to the template's `precision`
      (e.g. "one decimal place" → `3.2`, "two decimal places" → `0.84`,
      "whole hours" → `48`).
- [ ] Units match the template's declared `unit` where one is given.

## 4. Objects and nested required keys

- [ ] Each object field contains all of its `required_keys` / `required_keys`.
- [ ] Nested enum/null/precision rules are applied recursively (same checks as
      above for every nested field).

## 5. Lists

- [ ] Each list contains only items allowed by its `items` spec.
- [ ] "use each … at most once" / "omit duplicates" → no duplicate entries.
- [ ] "No semantic ordering" → any order is fine (still dedupe).
- [ ] Explicit ordering rule → applied exactly. Common rules:
      - "case identifier first, then clinical source identifiers" (evidence_ids).
      - "sort by effective_time ascending, then observation_id ascending"
        (matched/excluded observation lists).
      - "Sort by clinical action sequence" (urgent actions) — follow the
        protocol's stated action order.
- [ ] "use an empty list when none" → the key is present as `[]`, not omitted
      and not `null`.

## 6. Conditional presence

- [ ] Fields with `required_when` (e.g. `required_when: "lab_found is true"`)
      are present when the condition holds and handled per the template
      (nullable → `null`, otherwise omitted) when it does not.

## 7. Clinical grounding and safety

- [ ] Every `evidence_id` is a real resource id read from the runtime for **this**
      case (case id, observation id, imaging id, protocol id, visit/source id).
      No fabricated ids; no ids imported from other cases or training material.
- [ ] Distractor records (distractor source flag, `*-D…` ids) are excluded from
      evidence and from matched lists.
- [ ] Allergy-aware fields: medication class choices respect the patient's
      **active** allergies; `avoid_allergens` reflects those classes; inactive
      allergies do not bind.
- [ ] Safety-check booleans reflect the **actual content** of your answer:
      a `no_*` check is `true` only when the answer genuinely avoids that
      unsupported claim, and `false` otherwise. Do not default them all to
      `true`.
- [ ] Protocol-gate / risk / disposition values are derived by applying the
      matching protocol's thresholds to runtime findings — not from general
      clinical knowledge.

## 8. Output hygiene

- [ ] The final response body is exactly the JSON object — no markdown fences,
      no leading/trailing prose, no comments, no trailing comma.
- [ ] Valid JSON (parse it once to be sure).
