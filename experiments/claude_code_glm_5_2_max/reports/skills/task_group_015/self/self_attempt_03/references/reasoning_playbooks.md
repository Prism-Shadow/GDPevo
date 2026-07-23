# Reasoning Playbooks

Five task archetypes recur across this governance domain. Identify the archetype
from the prompt + `answer_template.json`, then apply the matching playbook.
Archetypes overlap (a referral audit still validates ICD-10 codes; a merge
packet still reconciles clinical lists) — compose them.

---

## 0. Universal intake (every archetype)

1. Read `prompt.txt` and extract every object ID it names: patient(s),
   candidate, referral, batch, service-request, provider(s). Also note the
   service line / batch / requested date context.
2. Read `payloads/answer_template.json` fully. It is the contract:
   - `required_top_level_keys` / `top_level_required_keys` → emit exactly these.
   - `enum` / `allowed_values` → restrict that field to those literals.
   - `set_semantics: true` or "array ... sorted" → treat as a set, sorted.
   - `required_value` (e.g. a `task_id`) → emit verbatim.
   - Any `*_ordering` note → follow that exact ordering.
3. Read any other `payloads/*.json` (e.g. `merge_packet_request.json`) for
   requested-output scope.
4. Resolve the base URL from `environment_access.md` and gather evidence (see
   `endpoints_and_shapes.md`). Fetch by the IDs in the prompt, then fetch each
   related sub-resource.

---

## 1. Duplicate-chart merge readiness packet

**Trigger:** "duplicate candidate", "merge readiness packet", two patient IDs +
a `DUP-...` candidate, `merge_packet_request.json` present.

**Gather:** candidate detail; both patients' detail; both patients'
conditions/medications/allergies (active lists); both patients' documents; audit
logs; provider directory (specialist + PCP).

**Canonical target/source:**
- Prefer `merge_preview.preferred_target_patient_id` / `source_patient_id` when
  both are non-null and the candidate is `open` with no blocking conflict.
- When the preview target/source are null OR a blocking conflict exists
  (`opposite_laterality_problem`, `different_dob`, `different_given_name` +
  `different_phone` together, etc.), do **not** auto-assign — set disposition to
  review/`do_not_merge` and leave target/source per template rules (nullable if
  allowed).

**Disposition ladder** (use the template's exact enum; map across the two
disposition blocks the template may carry — `merge.disposition` and
`merge_decision.disposition`):
- Strong match signals (`same_dob`, `same_insurance`, `same_phone`,
  `same_address_normalized`) and only minor conflicts (`address_abbreviation`,
  `name_variant`, `suffix_discrepancy`) → ready / merge_ready, possibly
  `merge_ready_with_conflict_review` with a review note.
- Any `opposite_laterality_problem`, or `different_dob`, or null target/source
  with `needs_review` status → `needs_manual_review` / `needs_review` /
  `do_not_merge`.

**Clinical key unions (authoritative-source rule — most-missed step):**
- The **patient active-list endpoints are authoritative over the duplicate
  preview.** Compute the union of `normalized_key` values from BOTH patients'
  active (status=`active`) conditions / medications / allergies.
- The final `active_*_keys` / `clinical_unions` = that endpoint union
  (deduped, sorted) — NOT the `merge_preview`.
- `*_keys_added_from_active_endpoints` = keys present in the endpoint union but
  **missing** from `merge_preview.active_*_keys` (reconcile preview vs truth).
- Only `status=active` records count. Inactive / `entered-in-error` /
  non-merge items go to `excluded_distractors`.

**Identity signals:** copy `match_signals` and `conflict_signals` from the
candidate. Derive `demographic_matches` / `demographic_conflicts` by comparing
the two patient records field-by-field (dob, insurance_id, phone, display_name,
address). Sort all signal arrays alphabetically. If the template gives
`allowed_values`, map free signals onto them; if it says `string`, emit labels
verbatim from the candidate.

**Evidence selection:**
- `document_ids`: only identity or external-continuity documents (e.g.
  `external_import` continuity docs). Exclude chart summaries, clinical notes,
  unrelated types → record excluded types in `document_selection_policy`.
- `audit_ids`: only audit events for the involved patients that bear on this
  review (`identity_review`, `external_import` of the continuity doc). Exclude
  unrelated merges / other patients.

**Packet contact:** specialist provider = the receiving/external specialty
provider tied to the continuity document or referral; primary care provider =
the patient's PCP. Pull both from `/api/providers`.

---

## 2. Referral batch audit

**Trigger:** "audit for batch `<BATCH>`", `invalid_or_out_of_range_code_referrals`,
`duplicate_groups`, `action_plan` with tiers, `summary_counts`.

**Gather:** all referrals where `batch_id` == the batch; for each referral, the
patient detail, the ICD-10 entry for `diagnosis_code`, and the receiving
provider. Use `/api/referrals` (list, filter by batch) — there is no batch
endpoint.

**Per-referral validation:**
- **Invalid / out-of-range code:** look up `diagnosis_code` in `/api/icd10`.
  If not found → `unknown_code`. If found but `chapter` != the batch's expected
  chapter (orthopedics batch expects `Musculoskeletal`) →
  `out_of_range_chapter`. Record `actual_chapter` and `expected_chapter`.
- **Laterality / narrative mismatch:** if the code `requires_laterality`, the
  narrative must contain the correct side (right vs left) per `expected_terms`;
  wrong side → `laterality_mismatch`, missing side → `missing_laterality`. If
  narrative shares no `expected_terms` substring → `narrative_mismatch`.
  `expected_terms` in output = the directory's `expected_terms` for that code.

**Duplicate groups:** group referrals sharing the same `patient_id` with the
same clinical intent (same/similar diagnosis) = `same_patient_resubmission`.
`referral_ids` sorted ascending; `recommended_disposition` =
`consolidate_under_original`. Same patient but **different** clinical concerns
are NOT duplicates — list them in `separate_same_patient_referral_ids`.

**Insurance-patient anomalies:**
- `shared_insurance_different_patients`: two+ patients share one
  `insurance_id` → `verify_insurance_membership_do_not_merge`.
- `same_patient_separate_clinical_referrals`: same patient, distinct clinical
  concerns → `separate_clinical_review_not_duplicate`.
`patient_ids` and `referral_ids` sorted ascending.

**Follow-up queues (arrays of referral_ids, sorted):**
- `authorization_missing` → `authorization_status == missing`.
- `authorization_pending` → `authorization_status == pending`.
- `records_request` → missing `office_note` in `documents_received`.
- `imaging_follow_up` → missing/pending imaging (`mri`/`xray` absent or only
  preliminary).

**Tiered action plan:**
- **Tier 1 immediate** — `urgent_coding_or_duplicate_blocker`: `urgency !=
  routine` (urgent/stat) OR in a duplicate group (duplicate blocker).
- **Tier 2 short-term** — `routine_coding_auth_or_document_blocker`: routine
  referrals with invalid/mismatched code, missing/pending authorization, or
  missing required document.
- **Tier 3 administrative** — `administrative_document_completion`: routine,
  code valid, authorization ok, only minor document completion outstanding.
`owner_provider_id` = the receiving provider.

**Summary counts:** derive every count from the audited rows. Include
`validated_ready_no_follow_up_count` (valid code, authorization approved, no
missing required docs, not in a duplicate group).

---

## 3. Care-transition handoff packet

**Trigger:** "care transition packet", "handoff", addressed to a provider,
`handoff_encounters` (length 4), `latest_immunization`, `disclosure`,
`risk_flags`.

**Gather:** patient detail; conditions/medications/allergies (active);
encounters; immunizations; disclosures; documents; recipient provider.

**Active clinical keys:** union of `normalized_key` for `status=active`
conditions/medications/allergies, sorted ascending.

**Handoff encounter selection:** from the patient's encounters, pick the N
stated by the template (commonly 4) most relevant to the transition's service
line, preferring signed/amended over draft/unsigned, within the relevant
recency window, excluding stale / out-of-window / unrelated visits. Order
newest-to-oldest. Record `selection_basis` as a normalized rule code,
`selected_encounter_ids` (newest-to-oldest), and `excluded_encounter_ids`
(reviewed but excluded, sorted ascending).

**Latest immunization:** the immunization with the greatest `date`.

**Disclosure:** the disclosure applicable to this transition (matching
`recipient_provider_id` / purpose). Emit `status`; if not `permitted`, raise
`disclosure_not_permitted` as a blocking issue.

**Risk flags:** derive from active clinical lists and encounter notes. Map
evidence to each flag (which condition_keys / medication_keys / encounter_ids
support it). Sort flags ascending. Examples of the flag vocabulary:
`cognitive_memory_loss`, `fall_risk_note_required`, `hypertension`,
`insulin_dependent_diabetes`, `latex_allergy`, `perioperative_glucose_plan_needed`
(use the template's `allowed_values` when present).

**Packet readiness:** `ready` if no blocking issue; `ready_with_risk_flags` if
risk flags present but no blocker; `not_ready` if a blocking issue. Blocking
issue codes (per template): `missing_patient`, `missing_recipient`,
`missing_active_lists`, `missing_handoff_encounters`, `missing_immunization`,
`missing_disclosure`, `disclosure_not_permitted`. Sort blocking codes ascending.

**Exclude:** stale encounters, unrelated documents, inactive clinical items.

---

## 4. Service-request + duplicate-review validation

**Trigger:** "ServiceRequest", "draft ServiceRequest", a `DUP-...` candidate,
`sbar_coverage`.

**Duplicate review object:** from the candidate, emit `candidate_status`,
`decision` (`merge` | `review_hold` | `do_not_merge`), primary/possible
duplicate patient IDs, merge target/source (nullable when `do_not_merge` /
`review_hold`), `match_signals`, `conflict_signals`. Decision mirrors the
disposition ladder in playbook 1.

**Service-request quality:**
- Echo `status`, `intent`, `priority`, `service_code`, requester/performer
  provider IDs, `authored_on`, `occurrence_date`.
- `service_code_valid`: look up `service_code` in `/api/service-codes` — valid
  iff the code exists, `active=true`, and its `service_line` matches the
  performer's `service_line` (from `/api/providers`).
- `performer_service_line`: the performer provider's `service_line`.
- `reason_codes`: the SR's ICD-10 reason codes.
- `reason_code_validation` (sorted by code): for each reason code, `valid`
  (exists in `/api/icd10`), `chapter`, `matches_patient_evidence` (true iff the
  patient's active conditions contain a condition whose `code` equals it, or
  whose `normalized_key` corresponds).

**SBAR coverage:** determine which of `situation`, `background`,
`assessment`, `recommendation` are present in the SR/reasoning (situation =
reason for order, background = relevant history/conditions, assessment =
clinical findings, recommendation = the order itself / occurrence). Emit
`sections_present`, `missing_sections`, and `complete` = no missing sections.

**Do not** include procedural notes or narrative SOP text in the answer.

---

## 5. Referral coordination packet (single referral)

**Trigger:** "coordination packet for referral `<REF>` and patient `<P>`",
`referral_letter_fields` choice enums.

**Gather:** referral detail; patient detail; conditions/medications/allergies;
encounters; documents; ICD-10 entries for the referral `diagnosis_code` and
active condition codes; receiving provider.

**Active diagnoses:** from the patient's active conditions, each with `code`,
`description`, `normalized_key`, `source`, and `referral_relevant` (true iff the
code/condition pertains to the referral's service line / narrative).

**Referral code set:** `primary_code` = the referral's `diagnosis_code`;
`supporting_codes` = other active condition codes relevant to the letter.
`icd_validation`: `valid_matches_narrative` | `valid_but_narrative_mismatch` |
`invalid_code` | `wrong_service_chapter` (from ICD-10 lookup vs narrative vs
service line). `narrative_match` = referral narrative contains an
`expected_terms` substring.

**Allergy readiness:** `complete_documented` (active allergies with full
detail) | `no_known_allergies` (empty active list) | `incomplete_needs_clarification`
| `conflicting_allergy_records`. `ready_for_letter` and `follow_up_needed`
derived accordingly.

**Recent encounter evidence:** the most relevant recent encounter (preferring
one whose `diagnoses`/notes align with the referral reason). Emit id, date,
type, provider, signed_status, diagnosis_codes, medications_mentioned, and a
`care_plan_tag` classifying relevance to the referral.

**Required document evidence:** check `documents_received` (and the patient's
documents) for required items, e.g. `echo` (echocardiogram for cardiology) and
`office_note`. Emit `received`, `document_id`, `type`, `date`, `status`, and
`missing_required_documents` list.

**Receiving provider:** from `/api/providers` by `receiving_provider_id`.

**Authorization readiness:** map `authorization_status` + referral `status` +
`urgency` to `overall_readiness` (`ready_to_send` | `hold_for_authorization` |
`hold_for_missing_documents` | `hold_for_clinical_clarification`) and
`blocking_issues` (subset of `authorization_missing`, `echo_missing`,
`office_note_missing`, `allergy_incomplete`, `provider_missing`,
`diagnosis_code_invalid`, `clinical_mismatch`).

**Medication highlights:** referral-relevant active medications first, each with
a `highlight_reason` (e.g. `heart_failure_diuretic`,
`blood_pressure_management`, `diabetes_management`, `lipid_management`,
`other_active_medication`). Set semantics by lowercased medication name.

**Referral-letter field choices:** each `*_choice` field has a task-specific
enum **defined in that task's `answer_template.json`** — read it from the
template, do not generalize from another task. Pick the literal that matches
the evidence.
