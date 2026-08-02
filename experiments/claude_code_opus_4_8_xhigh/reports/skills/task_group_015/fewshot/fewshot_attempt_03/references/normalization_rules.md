# Shared normalization & evidence-selection rules

These apply across all task types. The specific values change per case; the rules do not.

## Active-list key unions

- A "clinical key" is a record's **`normalized_key`**, not its `code`, `medication`,
  `allergen`, or `description`.
- Include a record only when its **`status == "active"`**. Drop `inactive`,
  `entered-in-error`, resolved, or otherwise non-active records.
- When a union spans multiple patients (e.g. a merge), take the **set union** of
  active `normalized_key` values across every involved patient and every source,
  then **dedupe**. The same key from two patients or two sources collapses to one.
- The per-patient active-list endpoints are **authoritative over any
  `merge_preview`** embedded in a duplicate candidate. If the active endpoints
  contain active keys the preview omitted, add them; reconciliation fields
  (e.g. `*_added_from_active_endpoints`) list exactly the keys present in the active
  endpoints but missing from the preview.
- Sort the resulting arrays as the template says (usually ascending/alphabetical).

## Distractors — what to exclude

These recur as deliberate traps. Exclude them from the packet (and, where the
template asks, list them under an `excluded_*` key):

- **Inactive clinical records** — any condition/medication/allergy whose `status`
  is not `active` is excluded from the active unions (and often belongs in an
  `excluded_*` list).
- **Administrative documents** when the document policy is identity / external-
  continuity only — a general `chart_summary`/EHR-export document is excluded while
  identity or external-continuity documents (external specialty notes, imaging
  reports) are kept.
- **Records belonging to other patients** — audit logs or documents whose
  `patient_id` is not one of the case's patients are unrelated distractors.
- **Stale / out-of-window / unrelated encounters** — visits outside the handoff
  window, one-off telehealth/amended visits, and random-hex-ID visits that are not
  part of the relevant handoff series. Note: an excluded encounter may still be
  cited as *risk-flag evidence* even though it is not in the handoff list.

## Identity: match vs conflict signals

- Take `match_signals` and `conflict_signals` straight from the duplicate candidate.
- Separately compute **demographic** matches/conflicts by comparing the two
  patient detail records field by field: equal `dob`, `sex`, `phone`, `insurance_id`,
  and `primary_care_provider_id` are matches; a first-name variant
  (`given_name` differs) or an address abbreviation difference are conflicts.
- Keep the candidate-level signal lists and the demographic comparison lists
  distinct if the template has separate fields for each.

## ICD-10 validation, chapter range, and laterality/narrative checks

For any diagnosis code, look it up at `/api/icd10/{code}`:

- **Unknown code** → the lookup 404s → `unknown_code` / `invalid_code`.
- **Chapter range** — compare `chapter` to what the context expects. An orthopedic
  context expects the `Musculoskeletal` chapter; a code whose chapter is `Injury`,
  `Respiratory`, `Circulatory`, etc. is `out_of_range_chapter` /
  `wrong_service_chapter`.
- **Laterality** — if `requires_laterality` is true, the narrative must name a side.
  Missing side → `missing_laterality`. A side that contradicts the code's
  `expected_terms` (e.g. narrative says "left" but the code is the right-side code)
  → `laterality_mismatch`.
- **Narrative match** — if the `diagnosis_narrative` is not consistent with the
  code's `expected_terms`, that is a `narrative_mismatch`. A code can trigger more
  than one mismatch type at once. `expected_terms` are copied from the ICD directory.
- A code is `valid_matches_narrative` only when it exists, sits in the expected
  chapter, and its narrative agrees with `expected_terms` (including laterality).

## Provider-contact resolution

- Look up any provider by `/api/providers/{id}` for `name`, `role`, `service_line`,
  `facility`, `phone`, `fax`.
- A patient's **primary care provider** is available directly on the patient detail
  (`primary_care_provider` block / `primary_care_provider_id`).
- The **specialist / receiving provider** comes from the case object: a referral's
  `receiving_provider_id`, a ServiceRequest's `performer_id`, a disclosure's
  `recipient_provider_id`, or the source of an external-continuity document.

## Formatting & determinism

- Dates: `YYYY-MM-DD`.
- Respect each field's ordering rule (alphabetical, by `code`, by `referral_id`,
  newest→oldest, etc.). For `set_semantics` lists, sort deterministically anyway.
- Emit `null` only where the template's type allows it (e.g. a merge target when the
  decision is a review hold).
- Keep summary counts consistent with the arrays they summarize.
