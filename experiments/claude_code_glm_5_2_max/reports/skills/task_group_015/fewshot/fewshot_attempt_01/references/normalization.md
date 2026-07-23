# Normalization Rules

These conventions are shared by every packet type. They turn raw API records into the
normalized shape the template demands.

## `normalized_key` — read, do not derive

Conditions, medications, and allergies each carry a `normalized_key` field (snake_case,
e.g. a clinical concept slug). **Take it verbatim from the API.** Never reconstruct it
from the description or code. The duplicate candidate's `merge_preview` uses the same
normalized keys, so unions and differences are directly comparable.

## Active-only filtering

Clinical lists have a `status` field. Include only records with `status == "active"`
(case-insensitive) in unions, active-key arrays, and risk-flag evidence. Inactive
records are distractors — where the template has an `excluded_distractors` block, list
the inactive normalized keys / IDs there.

Typical distractors to exclude:
- **Inactive conditions/medications/allergies** (status ≠ active).
- **Opposite-laterality condition** for the joint in question (e.g. a `left_knee_oa`
  record when the canonical problem is the right knee) — inactive and conflicting.
- **Unrelated document types** such as `chart_summary` (merge packets exclude these;
  keep only identity / external-continuity documents).
- **Unrelated audit logs** (not on the candidate's patient_ids).
- **Synthetic-looking encounter IDs** outside the handoff selection window.

## Sets and ordering

- Arrays marked `set_semantics: true` (or described as "sets") are compared as sets —
  emit them sorted ascending (string order) for determinism.
- Other arrays follow the template's `ordering` rule: common ones are `sort_by_code`,
  `sort ascending by normalized_key`, `newest to oldest by date`, `sort by referral_id`.
- Drop empty/null entries before sorting.
- Use `sorted_set(...)` / `union_keys(...)` / `set_difference(...)` from
  `scripts/ehr_client.py`.

## Dates

Pass dates through as `YYYY-MM-DD`. Do not reformat or timezone-shift.

## Enums

Every enum field has an `allowed_values` list in the template. Only emit values from
that list. When the API uses a different vocabulary, map it:
- Referral `authorization_status` `missing` → the authorization-missing follow-up queue;
  for an `authorization_status` output enum of `approved|pending|denied|not_required|unknown`,
  map `missing` to `unknown` unless the packet's rules say otherwise.
- Map free-text service lines / chapters to the template's exact enum casing
  (`orthopedics`, `cardiology`, `Musculoskeletal`, etc.).

## Duplicate-preview vs active-list reconciliation

For merge packets, the duplicate candidate's `merge_preview` lists
`active_condition_keys` / `active_medication_keys` / `active_allergy_keys`, but it can
be a **subset** of the true active lists. The patient active-list endpoints are
authoritative.

Compute, for each clinical family, across **both** patients in the candidate:
1. `union` = sorted set of active `normalized_key` values from both patients'
   `{conditions,medications,allergies}` endpoints.
2. `added_from_active_endpoints` = `set_difference(union, preview_keys)` — keys present
   in the patient endpoints but missing from the preview.
3. `authoritative_source` = `patient_active_list_endpoints_over_duplicate_preview`.

This is the basis for `clinical_unions` / `active_key_unions` and
`active_list_reconciliation`.

## Evidence integrity

Every evidence ID you cite (`document_ids`, `audit_ids`, `encounter_ids`,
`immunization_id`, `disclosure_id`, `provider_id`) must exist in the records you
fetched for the case objects in the prompt. Never fabricate an ID.

## Output shape

One JSON object. No trailing prose, no markdown fences, no comments. Match the
template's top-level keys exactly — no extras, none missing. If a field is optional in
the template and you have no value, emit the template's prescribed empty form
(`[]`, `null`, etc.) rather than omitting the key.
