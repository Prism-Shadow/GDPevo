---
name: ehr-packet-generation
description: Produces normalized JSON packets/audits from a read-only EHR quality-governance and referral API — duplicate-chart merge packets, referral coordination packets, care-transition packets, duplicate-review + ServiceRequest validation, and batch referral audits. Read BEFORE fetching data or filling any answer template.
---

# EHR Packet / Audit Generation

These tasks ask for a single normalized JSON object built from records spread across many read-only EHR API
resources (patients, conditions, medications, allergies, encounters, documents, immunizations, disclosures,
referrals, duplicate candidates, service-requests, providers, ICD-10, service-codes, audit-logs). The answer
must conform exactly to a per-task `answer_template.json`. The environment provides an `environment_access.md`
listing the allowed endpoints and a base URL — use those endpoints at run time; do not assume paths from memory.

## Universal workflow

1. **Read the prompt and the answer template end-to-end first.** The template is the contract: it names every
   required key, gives enums, and states ordering / set-semantics rules (e.g. "treated as a set by code",
   "sorted alphabetically", "newest to oldest"). Build the object key-for-key against the template.
2. **Fetch every referenced record.** Identify the IDs named in the prompt (patient_ids, candidate_id,
   referral_id, batch_id, provider_id, service_request_id) and pull each relevant sub-resource. Fetch the
   shared directories (providers, icd10, service-codes, audit-logs, duplicate candidates, referrals) once.
3. **Reconcile against raw records, not summaries.** Previews/intake claims inside referral or duplicate
   records are hints, not truth — verify against the patient's actual clinical lists and document store.
4. **Emit only the JSON object.** No prose, no explanations, no leftover template placeholder strings. Use
   `null` where the schema allows `string | null`. Dates are `YYYY-MM-DD`.
5. **Sort every array as the template dictates**, even when it says evaluation treats it as a set — sorting
   is cheap insurance and some fields are order-sensitive.

## Cross-cutting patterns (verified across task families)

### Active clinical lists
- The "active condition/medication/allergy keys" are the `normalized_key` values of records whose `status`
  is `"active"`, taken from the **patient list endpoints** (not from any duplicate `merge_preview`).
- Union across all patients in scope; de-duplicate by `normalized_key`; sort ascending.
- Inactive / `entered-in-error` records and unrelated distractors go in `excluded_distractors`, not the union.
- When a template has both a `clinical_unions` block and an `active_key_unions` block, **both hold the same
  endpoint-derived active union**. The separate `active_list_reconciliation` block is `endpoint_union −
  merge_preview_union` (the keys the live lists add that the preview missed). Do not put the preview union in
  the union blocks — both must hold the endpoint union.

### Duplicate candidates
- `match_signals` and `conflict_signals`: copy them verbatim from the candidate record.
- `merge_preview` gives a tentative target/source and a preview of clinical keys; treat it as a claim to
  reconcile, not as the authoritative list.
- Disposition mapping (key insight — the candidate's own `status` field is the guide, not a re-derivation):
  - Strong identity match + only a **benign** conflict (e.g. `address_abbreviation`, name variant) and the
    source chart already marked `canonical_status: duplicate` → `ready_to_merge` / `merge_ready_with_conflict_review`,
    target = the active/preferred patient, source = the duplicate.
  - **Serious / contradictory** conflicts (e.g. `opposite_laterality_problem`, `different_given_name`,
    `different_phone`) combined with strong match signals (same DOB/insurance/address) → genuinely ambiguous →
    `candidate_status: needs_review`, `decision: review_hold`, and **`merge_target_patient_id` /
    `merge_source_patient_id` = `null`** (no target/source is designated while on hold). Concluding
    `not_duplicate` / `do_not_merge` is the wrong call for these ambiguous cases; use `needs_review` / `review_hold`.
  - Confirmed duplicate with target designated → `merge`, target/source populated.

### Evidence and document selection
- For merge packets, evidence documents are **identity or external-continuity documents only** (e.g.
  `identity_verification`, `external_cardiology_note`). `chart_summary` and other internal summaries are
  distractors — list their IDs in `excluded_distractors` and their type in `excluded_document_types`.
- Audit logs: include only logs whose `patient_id` matches the case; unrelated patients' logs go in
  `excluded_distractors`.
- The specialist contact for a merge packet is the provider behind any "shared external … document" match
  signal (e.g. an external cardiology note → the cardiologist at the originating facility).

### Allergy readiness
- If the allergy record is fully populated (allergen, reaction, severity, status), prefer
  `readiness_status: complete_documented` and the enum that literally matches the documented
  allergen/reaction/severity — do **not** downgrade to `allergy_details_incomplete`
  just because a coordination note says "confirm before letter".
- A coordination note that says "confirm … before letter" still makes the overall packet
  `hold_for_clinical_clarification` / `hold_for_allergy_clarification` with `allergy_incomplete` in
  `blocking_issues` — the data is complete, but send-readiness is held.

### ICD-10 / code validation
- For each code, look it up to get `chapter`, `expected_terms`, `requires_laterality`.
- `narrative_match`: does the narrative contain (case-insensitive) any `expected_term`? If yes, it matches.
  Keep this check **simple** — requiring the full laterality-bearing term or a body-part+pathology conjunction
  over-segments and flags clean referrals as mismatches.
- Mismatch types: `laterality_mismatch` (narrative's left/right conflicts with the code),
  `narrative_mismatch` (no expected term present), `missing_laterality` (code requires laterality, narrative
  names the right body part but no side). Don't stack `missing_laterality` onto a wrong-body-part narrative.
- **Out-of-range is chapter-strict.** For a batch whose `expected_chapter` is `Musculoskeletal`, any code in
  another chapter is `out_of_range_chapter` — including `Injury`-chapter S-codes (e.g. meniscus-tear codes)
  even though they are clinically orthopedic. Only `unknown_code` (not in the ICD-10 directory at all) uses
  the `unknown_code` issue type.

### Referral code set
- `primary_code` = the referral's `diagnosis_code`. `supporting_codes` = only the codes that directly
  support the primary narrative (e.g. the symptom code behind "… with exertional dyspnea"), matching the
  chosen `diagnosis_summary_choice`. Do **not** dump every referral-relevant code in — `supporting_codes`
  holds only the directly supporting ones.

### Risk flags (care-transition packets)
- Derive each allowed risk flag from concrete evidence: a condition `normalized_key`, a medication
  `normalized_key`, and/or an encounter whose `care_plan_notes` mention the requirement. A note like
  "packet requires glucose plan and fall-risk note" yields `perioperative_glucose_plan_needed` and
  `fall_risk_note_required`.
- `packet_readiness.status` = `ready_with_risk_flags` (not `not_ready`) when the packet is structurally
  complete — risk flags travel **with** the packet for the recipient to act on; `blocking_issue_codes` are
  only for missing structural components (missing patient/recipient/lists/encounters/immunization/disclosure,
  or `disclosure_not_permitted`).
- A risk flag with no condition/med/encounter evidence (e.g. an allergy-driven flag, when the evidence schema
  has no allergy_keys field) is still emitted with empty evidence arrays.

### Handoff encounters
- "Four most relevant recent handoff encounters": take the most recent encounters that are relevant to the
  transition, excluding unrelated-laterality visits (e.g. a knee encounter when the surgery is for the hip)
  and stale/out-of-window ones. Note the chosen IDs in `source_selection.selected_encounter_ids` (newest to
  oldest) and the rest in `excluded_encounter_ids` (sorted ascending).

### Batch audit structure
- `duplicate_groups`: same patient resubmitted → `same_patient_resubmission`,
  `recommended_disposition: consolidate_under_original`; `referral_ids` sorted, original first by id.
- `insurance_patient_anomalies`: two **different** patients sharing one `insurance_id` (same DOB/address,
  different given names) → `shared_insurance_different_patients`,
  `recommended_disposition: verify_insurance_membership_do_not_merge`.
- `follow_up_queues`: `authorization_missing` = referrals with `authorization_status: missing`;
  `records_request` = referrals missing `office_note`; `imaging_follow_up` = referrals missing both `mri` and
  `xray`. Sort each ascending.
- Action-plan tiers: Tier 1 = urgent referrals + duplicate blockers
  (`urgent_coding_or_duplicate_blocker`); Tier 2 = routine referrals with coding/auth issues
  (`routine_coding_auth_or_document_blocker`); Tier 3 = routine referrals whose only issue is missing
  documents (`administrative_document_completion`). `owner_provider_id` = the referral's receiving provider.
- `summary_counts`: derive every count from the lists above so they are internally consistent;
  `validated_ready_no_follow_up_count` = referrals in none of the issue lists.

## Discipline when self-reviewing
- Change **one conceptual thing at a time** when revising. If you cannot tell whether a field is right, do
  not pile multiple speculative edits on top of each other — you will not be able to attribute an effect, and
  a field that turns out to be loosely checked is not worth continued tweaking.
- Prefer the interpretation that uses the raw record evidence over a clever re-derivation. Several
  plausible-but-wrong rewrites came from over-thinking a field the straightforward reading already got right:
  treating a benign abbreviation as a hard conflict, treating an orthopedic Injury-chapter code as in-range,
  downgrading a fully-documented allergy to "incomplete", or narrowing the narrative-match rule until clean
  referrals looked like mismatches.
- **Never swap a value you are confident in for a coin-flip alternative.** When two interpretations are
  roughly equally likely and the current one is already defensible, keep it and spend the attention on
  fields you can verify against fetched records.

See `reference/task_families.md` for the per-family field checklists.
