# Output Assembly Reference

The deliverable is **one JSON object** that conforms exactly to the current task's
`input/payloads/answer_template.json`. The template is the binding contract; this
reference describes how to honor it. Violations are the most common failure mode.

## The template is the contract

Before emitting anything, extract from `answer_template.json`:

1. **Required top-level keys** — every one must be present; add no extras.
2. **Constant / required-value fields** — e.g. `task_id`, `batch_id`,
   `roster_id`, `program_code` often have a fixed `required_value` /
   `expected_value` / `constant`. Emit that exact string.
3. **Per-list ordering rule** — usually "ascending by `<id>`"; sometimes
   "alphabetical by code/string"; sometimes "unordered set" / "order is not
   meaningful"; sometimes a custom order ("urgency then readiness_status",
   "highest priority first, non-ready referrals only"). Follow it literally.
4. **Per-item required keys** — emit every required key on every item.
5. **Enum allowed values** — every enum field may take *only* values the template
   lists. Never invent a value. If unsure whether a value is allowed, re-read the
   template's `allowed_values` / `allowed` list for that field.
6. **Summary count keys & value types** — integers, keyed by the exact member
   strings the template lists (include zero-valued keys).

## Enum discipline

- Emit only template-listed enum members. If the evidence doesn't cleanly map to
  an allowed value, choose the closest allowed value and re-examine the evidence
  rather than inventing a new string.
- `enum_or_null` / `integer_or_null` fields: use `null` only where the template
  explicitly permits it (e.g., `priority_tier` null when not applicable;
  `first_checkin_days` null for deferred/reject packages).
- Booleans stay booleans; integers stay integers (no quoted numbers).

## Ordering rules

- **"ascending by `<id>`"** → sort items by that id ascending (string/numeric
  order matching the id's natural form). Referral/patient/transfer ids sort as
  strings.
- **"alphabetical by code/string"** → sort by the enum string itself (e.g.,
  `artifacts_to_create` sorted alphabetically by artifact name).
- **"unordered set" / "order is not meaningful"** → any order is accepted, but
  emit a stable, sorted order to be safe and deterministic.
- **Cross-tab / custom orders** (e.g., "urgency then readiness_status", "highest
  priority first") → follow the stated precedence exactly; only include the rows
  the rule scopes to (e.g., non-ready only).

## Identifiers

- Echo ids **exactly as the portal returns them** — uppercase, same spelling.
  Do not lowercase, reformat, or pad.
- Use the scope id (`batch_id` / `roster_id` / `program_code`) the prompt names,
  in the exact casing the portal uses.

## Counts reconciliation

- Derive every count from your **final per-entity lists**, after classification.
- `total_*` = number of per-entity rows.
- Status/keyed counts must sum to the total. Include every key the template lists,
  even when 0.
- Cross-tab lists must sum to the total and must not double-count an entity.
- Re-check: if `counts_by_X` sums differ from the total, re-derive before
  submitting.

## Empty / missing values

- Empty sets → `[]` (never `null` for a list field, unless the template says so).
- An item with no blockers → `blocker_codes: []`, `issue_codes: []`, etc.
- "ready" referrals carry empty blocker/issue lists.
- A field the template marks required is still required when empty — emit the
  empty form, don't omit the key.

## Output format

- **JSON only.** No prose before or after. No markdown code fences. No trailing
  commentary. No "Here is the answer:".
- The entire response must parse as a single JSON object.
- Do not include the answer_template itself, explanations, or normalization notes
  in the output.

## Self-check before submitting

Run this checklist against your draft:

- [ ] Every required top-level key present; no extra top-level keys.
- [ ] Constant fields (`task_id`, `batch_id`, `program_code`, …) match their
      required values exactly.
- [ ] Every list sorted per its ordering rule.
- [ ] Every enum value is in the template's allowed list for that field.
- [ ] Every item carries all its required keys.
- [ ] Ids match portal casing exactly.
- [ ] All summary counts are integers; status counts sum to totals; zero-valued
      keys present.
- [ ] Empty sets are `[]`; nulls used only where permitted.
- [ ] Reference dates (`requested_service_date`, `as_of_date`) and
      `service_line`-type fields come from the environment, not the prompt.
- [ ] Response is JSON only — no prose, no fences.
