# Derivation, Validation & Normalization Rules

Template fields that are **not present verbatim** in the API must be derived by cross-referencing endpoints. This file lists the reusable derivation rules.

## 1. Canonical merge target / source (duplicate tasks)
- `target_patient_id` / `canonical_target_patient_id` = `duplicate.merge_preview.preferred_target_patient_id`.
- `source_patient_id` = `duplicate.merge_preview.source_patient_id`.
- Confirm both are in `duplicate.patient_ids`. If `preferred_target_patient_id` is null/absent, fall back to the patient with the lower enterprise_mrn or the active canonical record — and flag for manual review.

## 2. Merge disposition / decision (by signal strength)
Classify `conflict_signals` and `match_signals`:
- **Soft / reconcilable** (lean merge-ready): address abbreviation, name variant, similar address, same phone, same insurance, same DOB, shared external document.
- **Hard / blocking** (lean needs-review or do-not-merge): different DOB, different given name, different phone, different insurance, different address, opposite laterality problem.
Decision rule:
- `do_not_merge` / `not_duplicate` when hard identity conflicts dominate (especially different DOB or opposite laterality).
- `needs_review` / `needs_manual_review` when `candidate.status == "needs_review"` or signals are mixed.
- `ready_to_merge` / `merge_ready` (possibly `_with_conflict_review` when soft conflicts remain) when `status == "open"` and only soft/reconcilable signals are present.
Always defer to the template's exact disposition enum and populate `reason_codes` from the signal labels (sorted alphabetically).

## 3. Active clinical-list unions and reconciliation
- Pull each patient's `/conditions`, `/medications`, `/allergies`; keep `status == "active"` only.
- The set element is `normalized_key` (not `code`, not `description`).
- **Union** = sorted-ascending set of `normalized_key` across both patients (for a merge) or across the single patient (for a transition/referral packet).
- **Reconciliation vs `merge_preview`**: `*_keys_added_from_active_endpoints` = active-endpoint keys **missing** from `merge_preview.active_*_keys`. The patient active-list endpoints are authoritative; the preview may be stale or incomplete.
- `authoritative_source` = `patient_active_list_endpoints_over_duplicate_preview`.
- Inactive / entered-in-error / non-merge keys go to `excluded_distractors`.

## 4. Provider / service-code derivations (ServiceRequest & referral tasks)
- `requester_provider_id` ← service-request `requester_id`; `performer_provider_id` ← `performer_id` (rename on emit).
- `performer_service_line` ← `GET /providers/{performer_id}.service_line`.
- `service_code_valid` ← `GET /service-codes/{service_code}` returns 200 **and** `active == true` (404 or `active==false` → false).
- Receiving / specialist provider contact fields (`name, role, facility, phone, fax, service_line`) ← `GET /providers/{receiving_provider_id}` (or the patient's embedded `primary_care_provider` for the PCP block).
- For a merge packet's `specialist_provider`, pick the provider whose `service_line` matches the clinical context (e.g. cardiology when the duplicate concerns a shared cardiology import) and who is referenced by the evidence; fill `contact_reason` from the scenario.

## 5. ICD-10 validation (referral audit & coordination tasks)
For a referral `diagnosis_code`:
- `GET /api/icd10/{code}`:
  - **404** → `invalid_code` / `unknown_code`; `issue_type = unknown_code`.
  - **200**, `chapter` ≠ expected chapter for the batch service line (e.g. `Musculoskeletal` for an `orthopedics` batch) → out-of-range / `wrong_service_chapter`; `issue_type = out_of_range_chapter`.
  - **200**, chapter matches → proceed to laterality/narrative checks.
- Laterality / narrative (only when `requires_laterality == true`, or always check narrative):
  - `laterality_mismatch`: narrative asserts one side (e.g. "left knee") but `expected_terms` assert the other ("right knee").
  - `missing_laterality`: code requires laterality but narrative has no laterality term.
  - `narrative_mismatch`: narrative shares no `expected_terms` token with the code.
  - `expected_terms` to emit = the code's `expected_terms[]` from the directory.
- `narrative_match` (boolean) = any `expected_terms` token appears (case-insensitive) in `diagnosis_narrative`.
- `primary_code_chapter` = looked-up `chapter`.

## 6. reason_code_validation (ServiceRequest tasks)
For each code in `service_request.reason_codes[]`:
- `code` = the reason code.
- `valid` = `GET /api/icd10/{code}` returned 200.
- `chapter` = looked-up chapter (null/empty if invalid).
- `matches_patient_evidence` = the code appears in the SR patient's active condition `code` values.
Sort the resulting array by `code` ascending.

## 7. SBAR coverage (ServiceRequest tasks)
From `service_request.sbar`: a section (situation / background / assessment / recommendation) is **present** iff its value is a non-empty string. `complete` = all four present. `missing_sections` = the absent ones. Both arrays use set semantics.

## 8. Document & audit evidence selection (merge packets)
- Relevant `document_ids`: documents belonging to a candidate's `patient_ids` whose `type`/`source` indicate identity or external-continuity content (e.g. external import, chart summary tying the two charts). Exclude clinical-result / unrelated document types — list them in `document_selection_policy.excluded_document_types` and `excluded_distractors.document_ids`.
- Relevant `audit_ids`: audit logs where `patient_id ∈ candidate.patient_ids` and `event` is identity/import/merge-relevant. Exclude unrelated merges (different patient pairs) → `excluded_distractors.audit_ids`.
- `packet_document_basis` = `identity_or_external_continuity_documents_only`.

## 9. Encounter selection (care-transition & referral tasks)
- Handoff encounters: among the patient's encounters, select the N most recent that are relevant to the recipient's service line / transition (template fixes N, e.g. 4). Sort selected **newest-to-oldest**. Record `excluded_encounter_ids` (stale, out-of-window, unrelated) sorted ascending.
- Recent encounter evidence (referral): pick the encounter that supports the referral (matching diagnosis codes, recent date, signed). Classify `care_plan_tag` from encounter content per the template enum (e.g. `cardiology_referral_for_hfpef_dyspnea`, `unrelated_recent_visit`).
- `signed_status` maps directly from the encounter field (validate against the template enum).

## 10. Risk flags & readiness (care-transition tasks)
- `risk_flags`: map clinical evidence to the template's **allowed** risk-flag set only (e.g. insulin_dependent_diabetes ← active insulin/metformin + diabetes condition; latex_allergy ← active latex allergy; fall_risk_note_required ← fall-risk encounter note; hypertension ← active hypertension condition). Do not emit flags outside the allowed set.
- `risk_flag_evidence`: for each emitted flag, list the `condition_keys` / `medication_keys` / `encounter_ids` that justify it (sorted ascending).
- `packet_readiness.status`: `ready` if no blockers and no risk flags; `ready_with_risk_flags` if risk flags present but no blockers; `not_ready` if any blocking_issue_code applies. `blocking_issue_codes` come from the allowed set when a required section is missing (missing patient/recipient/active-lists/handoff-encounters/immunization/disclosure, or disclosure_not_permitted).

## 11. Authorization / document readiness (referral tasks)
- `authorization_status`, `referral_status`, `urgency` map from the referral object.
- `overall_readiness`: `ready_to_send` if auth approved + required documents received + diagnosis valid + no allergy blocker; else `hold_for_authorization` / `hold_for_missing_documents` / `hold_for_clinical_clarification`.
- `blocking_issues` from the allowed enum: `authorization_missing | echo_missing | office_note_missing | allergy_incomplete | provider_missing | diagnosis_code_invalid | clinical_mismatch`.
- `required_document_evidence`: per document type, `received` = type in `documents_received`; `missing_required_documents` lists any required type not received.
- `referral_letter_fields`: for each field, choose the enum value that matches the assembled evidence (diagnosis summary, allergy statement, recent encounter, document packet, medication summary, recipient, authorization statement, readiness). If no enum fits, use `other`.

## 12. Sorting & set semantics (all tasks)
- Default for any array marked as a set: **sort ascending, case-sensitive alphabetical** unless the template says otherwise.
- Override when the template's `ordering` field specifies: by `referral_id`, `group_id`, `anomaly_id`, `risk_flag`, `code`, or by date (newest-to-oldest for selected encounters; oldest/newest as stated).
- Inside grouped objects (duplicate_groups, anomalies), sort the inner id arrays ascending.
- "Evaluation treats this list as a set by X" → order is not scored, but emit sorted for safety and determinism.
- Counts in `summary_counts` must equal the lengths of the corresponding arrays (recompute, do not hard-code).

## 13. Output purity
- Emit exactly one JSON object matching the template's top-level required keys and field types.
- No markdown fences, no commentary, no narrative SOP. Stable IDs only.
- When a template field requires a fixed `task_id` value (e.g. the task's own id), set it; otherwise populate from the task identifier.
