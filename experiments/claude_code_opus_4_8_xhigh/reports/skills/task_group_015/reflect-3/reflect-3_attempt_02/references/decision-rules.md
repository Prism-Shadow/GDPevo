# Decision-rules playbook

Field-by-field rules for building each answer-template section. These are
archetypes — match them to whatever keys the current template actually defines.
Always let the template override: use its exact key names, enum tokens, and
ordering. Nothing here is a fixed answer; every value must come from the
environment records you fetch for the current task.

## Resolving entities

- **Patient identity:** a patient record carries `canonical_status`
  (`active` / `duplicate` / `possible_duplicate`) and `canonical_patient_id`
  (the record it points to). The active record with `canonical_patient_id == null`
  is the canonical/target; a record whose status marks it a duplicate is the
  source.
- **Active clinical lists:** each condition/medication/allergy record has a
  `status` and a `normalized_key`. "Active" = `status == "active"`. Unions and
  "keys to preserve" use `normalized_key`, deduplicated, sorted per the template.
- **Directories:** provider, ICD-10, and service-code directories are lookups;
  copy their fields verbatim into contact/validation sections.

## Duplicate-merge readiness packet

- `target` / canonical = active record; `source` = duplicate/possible_duplicate
  record. Cross-check against the candidate's `merge_preview` preferred
  target/source, but trust the patient records.
- **Active key unions** = union of `normalized_key` over active
  condition/medication/allergy records from *both* patients. Include every active
  key. Sort per template.
- **Reconciliation / added-from-active-endpoints** = active keys that appear in
  the patient endpoints but are missing from the candidate's preview.
- **Excluded distractors** = non-active records' keys, and unrelated documents /
  audit rows (see evidence rules).
- **Identity signals:** copy the candidate's `match_signals` / `conflict_signals`
  (sorted). Where the template also wants demographic matches/conflicts, derive
  them by comparing the two patient records field-by-field (dob, phone, insurance,
  family/given name, address, sex).
- **Disposition:** a clean strong match → merge-ready; a conflict signal present
  (even a benign one like an address abbreviation) → the "merge-ready with
  conflict review" disposition and a review note, `manual_review_required = true`;
  a genuine identity failure → do-not-merge.
- **Evidence documents** = `final` documents that are identity-verification or
  external clinical-continuity notes tied to the merge. Exclude generic
  `chart_summary` / `ehr_export` documents (list them under excluded document
  types / distractors).
- **Evidence audit rows** = audit-log entries that reference this candidate's two
  patients / this merge. Exclude rows about other candidates or other patients.
- **Contact** = the specialist tied to the external continuity document's
  facility/service line, plus the patient's primary care provider, from the
  provider directory.

## Duplicate-review + ServiceRequest QA

- **Recompute** `match_signals` / `conflict_signals` from the two patients'
  demographics and problem lists, mapped to the template's allowed enum.
  `opposite_laterality_problem` = each patient's active problem is on the opposite
  side (e.g. right-knee vs left-knee).
- **Classification vs action are separate keys.** Strong identity match with
  conflicts → identity status can be "confirmed duplicate" while the action is
  "review hold". Do-not-merge is for genuine non-duplicates; do not choose it just
  because a conflict exists.
- **Merge target/source** stay `null` when the action is a hold and the
  environment's preferred target/source are null.
- **ServiceRequest fields** copy verbatim (status, intent, priority, authored/
  occurrence dates, requester/performer IDs, reason codes). `performer_service_line`
  = the performer provider's directory service line. `service_code_valid` = the
  service-code directory entry is active. For each reason code: `valid` = it
  resolves in the ICD directory; `chapter` = the lookup's chapter;
  `matches_patient_evidence` = that code appears as an active condition on the SR
  patient. Sort reason-code validation by code.
- **SBAR coverage** = which of situation/background/assessment/recommendation are
  non-empty in the SR's SBAR; `complete` iff all four present.

## Specialty referral coordination packet

- **patient_referral** from the referral record (patient, referral, batch,
  service line, requested date).
- **Referral code set** = the referral's primary `diagnosis_code` + the narrative's
  symptom code only. Comorbidities on the chart are *not* referral-relevant and
  *not* supporting codes. Validate the primary code via the ICD directory: chapter
  vs service line, `expected_terms` vs narrative → the matching validation enum;
  set `narrative_match` accordingly (clinical synonyms count as a match).
- **active_diagnoses:** list active conditions; mark `referral_relevant = true`
  only for the primary + narrative-symptom codes.
- **Allergy readiness / overall readiness:** follows actual data completeness.
  A fully populated active allergy → documented/ready even if a coordination note
  says "confirm". Blocking issues and hold statuses come from genuinely
  missing data (auth, required documents, provider), not from soft notes.
- **Recent-encounter evidence** = the encounter whose diagnoses/care-plan match
  the referral reason, even if a more recent unrelated encounter exists.
- **Required documents** = cross-check the referral's `documents_received` and the
  patient's documents; nothing missing when the required set is present and auth
  is approved.
- **Medication highlights** = only the referral-relevant active meds, with the
  clinical highlight reason; skip generic filler meds. The letter's medication /
  diagnosis / allergy / encounter / document / recipient / authorization /
  readiness "choice" enums mirror the structured fields you just computed.
- **Receiving provider** = the referral's receiving provider, from the directory.

## Care-transition handoff packet

- **patient / recipient** from patient detail and the provider directory.
- **Active key unions** (condition/medication/allergy `normalized_key`, all active,
  sorted) — same rule as merge packets; include filler keys.
- **Handoff encounters** = the N most recent encounters tied to the transition's
  target problem/joint (often a deliberately-designed same-series set sharing the
  surgical condition and consistent meds). Exclude the oldest/out-of-window rows
  and unrelated-diagnosis distractors. Order newest→oldest; list every reviewed
  encounter not selected under the exclusion field (sorted ascending).
- **Latest immunization** = max date. **Disclosure** = the one whose
  `recipient_provider_id` equals the recipient and whose status is permitting.
- **Risk flags** = every template-allowed flag with chart evidence: conditions
  (e.g. a memory-loss condition → cognitive flag; hypertension present →
  hypertension flag), med+condition pairs (insulin + diabetes → insulin-dependent
  flag), allergies (latex → latex flag), and care-plan notes (a "requires glucose
  plan / fall-risk note" note → the corresponding perioperative flags). Do not
  drop an evidenced flag. Provide the per-flag evidence structure.
- **Packet readiness is structural:** all components present (patient, recipient,
  active lists, handoff encounters, immunization, permitted disclosure) → ready
  (with-risk-flags if any), `ready_to_send = true`, no blocking codes. Risk flags
  do not block; blocking codes are for structurally missing components only.

## Referral-batch audit

- **Scope:** filter referrals to the batch. `record_count` = rows;
  `unique_patient_count` = distinct patient IDs.
- **Chapter validation:** the service line has a *single* expected ICD chapter
  (e.g. orthopedics → Musculoskeletal). Any code whose ICD chapter is anything
  else — *including clinically adjacent chapters such as Injury* — is
  out-of-range. A code that will not resolve is an unknown code.
- **Laterality/narrative mismatch (in-chapter codes only):** from the ICD
  `expected_terms` get the code's side (right/left) and region (knee/hip/…).
  Compare to the narrative text:
  - laterality_mismatch — both name a side and they differ;
  - narrative_mismatch — the narrative names a different body region than the code;
  - missing_laterality — same region but the narrative states no side.
  Emit `expected_terms` from the directory.
- **Duplicate groups:** a patient with more than one referral in the batch →
  a same-patient-resubmission group (referral IDs sorted); disposition
  "consolidate under original"; both rows are Tier-1 duplicate blockers.
- **Insurance anomalies:** different patient IDs sharing one insurance ID →
  shared-insurance-different-patients (verify membership, do not merge). Same
  display name but different insurance IDs is *not* an anomaly.
- **Follow-up queues (data-driven):** authorization-missing / -pending from the
  referral's authorization status; records-request = office-note missing from
  `documents_received`; imaging-follow-up = no imaging on file (no MRI and no
  X-ray) **or** a coordination note indicating imaging pending (the "missing or
  pending" union).
- **Tiering:** Tier 1 = duplicate blockers, or urgent rows that also have a coding
  issue; Tier 2 = routine coding / authorization / document blockers; Tier 3 =
  administrative document completion (a document gap with no coding issue);
  validated-ready = no issue at all. Owner = the referral's receiving provider.
- **Summary counts** are the lengths of the sets you produced — compute them from
  your own lists so they are always consistent.

## Notes on ambiguity

Some fields are free-form controlled strings (group/anomaly IDs, selection-basis
codes, some reason-code vocabularies) whose exact spelling is not derivable from
the data alone. Choose a clear, consistent, environment-aligned token and move on;
get the data-derived fields (IDs, keys, codes, counts, enums, orderings) exactly
right, since those carry the weight.
