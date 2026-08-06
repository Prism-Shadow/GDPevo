# Output Contract & Normalization Rules

The `answer_template.json` is the contract. These rules apply universally; the
template's field-level notes override only when they are more specific.

## Top-level shape
- Emit **exactly** the `required_top_level_keys` / `top_level_required_keys`.
  No extra keys, no missing keys.
- `required_value` fields (e.g. `task_id: "train_004"`) must be emitted
  verbatim from the template.
- Return a single JSON object. No prose, no markdown fences, no commentary
  outside the JSON.

## Field typing
- Match the declared type exactly. `string or null` → use `null` when absent
  (e.g. merge target/source when not assigned), never an empty string.
- Booleans are `true`/`false`, not strings.
- Dates are `YYYY-MM-DD` strings.
- Integers are unquoted numbers.

## Enums / allowed_values
- Where the template lists `allowed_values` / an `enum`, the field value MUST be
  one of those literals. Never invent an enum value.
- Where the template says `string` (no enum), emit the normalized label taken
  from the environment evidence (e.g. a `match_signal` label, a
  `normalized_key`), verbatim and lowercased-as-stored.

## Set semantics & ordering
- Arrays marked `set_semantics: true` or described as "sorted" / "set" are
  **sets**: dedupe, then sort.
- Default sort is **ascending / alphabetical** (case-sensitive string sort of
  the stored value) unless the template states otherwise.
- Common per-array rules seen in templates:
  - referral object arrays → sort by `referral_id` ascending.
  - id arrays → sort strings ascending.
  - duplicate_groups → sort by `group_id`; `referral_ids` inside sorted ascending.
  - insurance anomalies → sort by `anomaly_id`; ids inside sorted ascending.
  - handoff_encounters → newest-to-oldest by encounter date.
  - reason_code_validation → sort by `code`.
  - risk_flag_evidence → sort by `risk_flag`.
- When two parallel sections in a template ask for the same data (e.g.
  `clinical_unions` and `active_key_unions`), fill them **consistently** from
  the same authoritative source.

## Authoritative sources (do not substitute)
- Patient active-list endpoints (conditions/medications/allergies) are
  authoritative over the duplicate `merge_preview`.
- `/api/icd10` is authoritative for code validity, chapter, laterality,
  expected_terms.
- `/api/service-codes` is authoritative for service-code validity and
  service-line mapping.
- `/api/providers` is authoritative for provider contact fields.

## Exclusions & distractors
- Only `status=active` clinical records contribute to `active_*_keys` unions.
- Inactive, `entered-in-error`, and non-merge clinical items →
  `excluded_distractors` (when the template has that section).
- Unrelated documents (not identity/external-continuity) and unrelated audit
  logs (other patients / other merges) → excluded, not into evidence.
- Stale / out-of-window / unrelated encounters are excluded from handoff
  selection and listed in `excluded_encounter_ids` when the template asks.

## IDs and stability
- Emit stable environment IDs (`patient_id`, `referral_id`, `document_id`,
  `audit_id`, `encounter_id`, `provider_id`, `candidate_id`, `code`) verbatim.
- Never fabricate an ID. If evidence is missing, use `null` (if the type allows)
  or raise the matching blocking issue rather than guessing.

## Self-check before returning
1. Every required top-level key present; no extras.
2. Every enum field is an allowed literal.
3. Every set array is deduped and sorted per its rule.
4. `null` used (not `""`) where the type is `string or null` and evidence is
   absent.
5. Clinical unions come from active-list endpoints, not the merge preview.
6. No task-specific narrative prose; JSON only.
7. Re-read the template's `*_ordering` / `description` notes one final time and
   confirm compliance.
