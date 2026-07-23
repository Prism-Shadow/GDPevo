# Normalization Playbook

Reusable rules for turning API evidence into a template-conformant JSON packet.
Every ID, key, code, count, and enum choice is derived from the environment at
runtime and placed into the shape the current `answer_template.json` defines —
nothing here is a hardcoded answer.

## 1. `normalized_key` is the unit of clinical identity
Conditions, medications, and allergies each expose a `normalized_key`. Wherever
the template asks for "condition keys", "medication keys", or "allergy keys",
emit the `normalized_key` string — not the code and not the free-text name.

## 2. "Active" means active-status only
Filter clinical records by status before unionizing. Inactive, entered-in-error,
or otherwise non-active records are **distractors**: they never enter an
active-list union. If the template has an `excluded_*` / distractors section,
list their keys there.

## 3. Active-list unions (duplicate-merge packets)
- Union the active `normalized_key` sets across **both** patients named by the
  duplicate candidate.
- De-duplicate, then sort (alphabetically by default, or by the key the
  template names).
- The union is over **active** records only (rule 2).

## 4. Authoritative source = patient active-list endpoints
Patient active-list endpoints (conditions / medications / allergies) are
**authoritative** over any duplicate-preview or chart-summary view. Where the
template asks for reconciliation:
- Build the union from the active-list endpoints.
- Report the keys the active endpoints contributed that the preview/summary
  lacked (the "added from active endpoints" delta).
- Do not let a stale preview drop an active key, and do not let a preview-only
  stale key leak into the union.

## 5. Set semantics vs ordered arrays
- **Set-semantic arrays** (template says "set", "any order", "evaluators
  normalize"): sort them — alphabetically by default, or by the key the
  template names. Sorting is safe even when evaluators normalize order, and it
  makes the output deterministic.
- **Ordered object arrays**: follow the template's ordering rule exactly (e.g.
  "sort by referral_id ascending", "newest to oldest by date", "length: 4").
  Honor any fixed-length constraint and selection rule.

## 6. Distractor exclusion
Identify and exclude:
- stale / outside-the-window encounters (wrong date band, unrelated type),
- inactive clinical records,
- unrelated documents (e.g. summary/aggregate documents when the policy
  restricts evidence to identity or continuity documents),
- distractor patients or records planted to test filtering.
Where the template provides an `excluded_distractors` / `excluded_*` block,
list the excluded IDs or keys (sorted). Excluded items must **not** also appear
in the included sets.

## 7. Enum derivation (never invent enum values)
Disposition, readiness, decision, validation, and "choice" fields are enums
whose allowed values are listed **in the template**. Derive the correct value
from evidence and emit a template-listed member only. If no listed member fits
the evidence, use the template's most permissive catch-all member rather than
inventing a string not in the vocabulary.

Common derivations:
- **Merge readiness** from candidate status + identity match/conflict signals +
  whether the source already points at the target.
- **Authorization / packet readiness** from authorization status + missing
  documents + clinical clarity + whether all required blocks resolved.
- **Code validation** from the ICD-10 directory: valid/invalid, chapter
  in/out of range, narrative match, laterality match.
- **Encounter care-plan / selection tags** from encounter type, date window,
  and clinical relevance to the transition or referral.

## 8. ICD-10 and service-code validation
- Use the ICD-10 endpoint to resolve each code: chapter, `expected_terms`,
  `requires_laterality`.
  - **Invalid / out-of-range**: code unknown, or its chapter is outside the
    expected service-line chapter.
  - **Laterality mismatch**: code requires a side and the narrative names the
    opposite side (or omits the required side).
  - **Narrative mismatch**: narrative terms do not overlap the code's
    `expected_terms`.
- Use the service-code endpoint to confirm a service code exists and is valid.
- Where the template asks whether a code matches patient evidence, compare the
  code against the patient's active conditions / encounter diagnoses.

## 9. Provider contact blocks
Resolve every contact block (specialist, primary care, receiving provider,
action-plan owners) from the provider directory: `provider_id`, name, role,
service_line, facility, phone, fax. Copy these fields verbatim from the API
record — do not reformat phone/fax. Include a `contact_reason` only where the
template asks for one, stated in normalized terms.

## 10. Evidence IDs and document selection
- For evidence sections, emit the **IDs** (document_ids, audit_ids,
  encounter_ids, immunization_id, disclosure_id) — not the record contents.
- Apply the document-selection policy the template implies: identity or
  continuity documents in; unrelated document types out. Prefer final
  documents over preliminary where status matters, and only count a required
  document as received when its status is final (or whatever the template
  treats as sufficient).

## 11. Counts must reconcile
For audit tasks, every summary count must equal the number of rows you placed
in the corresponding bucket. Re-derive counts from your own output arrays
immediately before emitting — do not compute them independently and risk a
mismatch with the arrays above them.

## 12. Required-value and nullability
- Template fields marked `required_value` must be that exact literal (e.g. a
  `task_id`).
- Fields typed `string | null` may be `null` only when evidence is genuinely
  absent (e.g. no merge target because the decision is a hold). Do not use null
  as a placeholder for "I did not look" — fetch the record first.
