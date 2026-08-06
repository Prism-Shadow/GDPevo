# Output Contract (how to read a template and emit a conforming object)

Every task returns **exactly one JSON object** conforming to that task's `input/payloads/answer_template.json`. Templates vary in surface syntax (`fields` vs `field_specification` vs `properties`; `allowed_values` vs `expected_constant` vs `required_value`) but all express the same contract. This file is the distilled, generalized reading procedure.

## Read order
1. `required_top_level_keys` / `required_keys` — the exact key set. Emit all of them.
2. Per-field spec under `fields` / `field_specification` / `properties`.
3. Any `output_rule` / `output_rules` / `format` line — authoritative for formatting and is the tie-breaker on conflicts.
4. `numeric_precision` blocks — precision/unit per numeric field.

## Field shapes you will encounter
- **`type: string`** with `expected_constant` / `required_value` — copy the literal verbatim (e.g. `task_id`, `case_id`).
- **`type: string`** with a `description` — a value you derive from the runtime (e.g. `patient_id`).
- **`type: enum`** with `allowed_values` — emit exactly one value from the list. Never a synonym, never prose.
- **`type: list` / `array` / `list[enum]` of enums** — each element must be from `allowed_values`; obey that field's `ordering`/`ordering_rule`.
- **`string_or_null`, `[string,null]`, `enum_or_null`, `[integer,null]`** — nullable; use `null` only when the "does not apply" condition holds (e.g. no medication recommended). For non-nullable required fields, never emit `null`.
- **`type: object`** with `required_keys` — emit a nested object with exactly those keys; recurse into its `fields`/`properties`.
- **`type: boolean`** — true/false only.
- **`type: number`** with `precision` — round to the stated precision (one or two decimals) and include the unit conceptually (units are not echoed in JSON unless the field is a string like `blood_pressure`).
- **`type: integer`** — whole number (e.g. hours, days, mEq, counts).
- **`required_when`** — a field that is conditionally required (e.g. `latest_final` required when `lab_found` is true; may be `null`/absent otherwise per the spec).
- **`additional_properties` / extra_keys** — most templates forbid extra top-level keys; a few say extras are "ignored unless they conflict." Default to emitting **only** the required keys.

## Timestamps
ISO-8601 UTC with a trailing `Z` (e.g. `2026-01-14T10:00:00Z`), unless a field says otherwise. Pull timestamps from the runtime (`effective_time`, `performed_at`, `current_time` finding) rather than fabricating them.

## List ordering — follow each field's own rule
Templates deliberately differ. Observed rules:
- "No semantic ordering; evaluators normalize as a set." → any order, no duplicates.
- "No semantic ordering; omit duplicates." → any order, dedup.
- "Sort by effective_time ascending, then observation_id ascending." → deterministic sort.
- "Descending relevance" / "case identifier first, then clinical source identifiers" → stable, semantic order.
- "Sort by clinical action sequence when required; empty list when none." → action order, `[]` if none.
Apply the rule field-by-field; do not assume one rule covers all lists in a template.

## Safety-check booleans (anti-fabrication guards)
These assert the response does **not** make a specific unsupported claim. Set them strictly from chart evidence:
- `no_penicillin_or_sulfa` — true only if the medication plan avoids penicillin and sulfonamide classes (because the patient has active allergies to them, or no antibiotic is recommended).
- `no_normal_cxr_claim` — true only if you do not assert the chest imaging is "normal"/"clear" when it is not.
- `no_clear_lungs_claim` — same direction for lung auscultation claims.
- `no_false_loc` / `no_false_vomiting` / `no_false_photophobia` — true only if you do not list the corresponding red flag as present when the chart says it is absent (and you record it under `absent_red_flags`).
When a safety boolean is false, re-examine whether you fabricated the corresponding finding; the safest correct state is usually `true` when the evidence is absent.

## Evidence identifiers
- `evidence_ids` / `evidence` is a list of stable runtime identifiers: the case id, observation ids, imaging ids, protocol id, and finding `source_id`s that justify the decision.
- Use the runtime's real ids verbatim; never invent or paraphrase them.
- Follow that field's ordering rule (set / ascending / descending relevance / case-id-first).

## Final validation checklist (run before returning)
1. Exactly the required top-level keys (no extras, unless explicitly ignored).
2. Fixed constants copied verbatim (`task_id`, `case_id`).
3. Every enum value ∈ its `allowed_values`.
4. `null` only where permitted; required fields present and non-null.
5. Numeric precision and units match; integers are whole; timestamps end in `Z`.
6. Each list obeys its own ordering rule; duplicates removed where disallowed.
7. Safety booleans reflect the absence of the named unsupported claim.
8. Output is a single bare JSON object — no markdown fence, no prose, no trailing text.
