# Task archetypes — gather + decide

Identify the archetype from the prompt (see the routing table in `SKILL.md`), then
follow its gather list and build the template's keys from that evidence. The
cross-cutting rules are in `normalization-and-decision-rules.md`; only the
archetype-specific flow is here. Always emit the template's own keys/enums.

---

## A. Duplicate-merge readiness packet

Case objects: one duplicate-candidate ID + two patient IDs (+ maybe a
`*_request.json` listing requested outputs).

Gather: `GET /api/duplicates/{candidate}`; `GET /api/patients/{id}` for **both**;
both patients' `/conditions`, `/medications`, `/allergies`, `/documents`;
`/api/audit-logs`; `/api/providers/{id}` for the specialist implied by the evidence
(e.g. the external-continuity document's source) and each patient's PCP.

Build:
- Merge target/source + disposition + reason codes → rules §3–§5.
- `clinical_unions` / `active_key_unions` → authoritative active union (§3); the
  reconciliation block → `added_from_active_endpoints` deltas vs. `merge_preview`.
- Identity `match_signals`/`conflict_signals` from the candidate; demographic
  match/conflict from field-by-field patient comparison (§4).
- `evidence.document_ids` / `audit_ids` and `excluded_distractors` /
  `document_selection_policy` → evidence selection (§6): identity + external-
  continuity docs in, chart-summary/export docs out.
- `packet_readiness` → readiness (§10). `packet_contact` → provider directory blocks
  (specialist reason = why the packet needs them, e.g. the external continuity doc).

---

## B. Referral coordination packet

Case objects: a referral ID + patient ID (service line usually cardiology/ortho).

Gather: `GET /api/referrals/{id}`; patient `/conditions`, `/medications`,
`/allergies`, `/encounters`, `/documents`; `GET /api/icd10/{code}` for the referral
diagnosis + supporting codes; `GET /api/providers/{receiving_provider_id}`.

Build:
- `patient_referral` from the referral row (patient, referral, batch, service_line,
  requested_date).
- `active_diagnoses` from active conditions (+ any referral-intake diagnosis); mark
  `referral_relevant` for the codes tied to the referral reason vs. background
  comorbidities.
- `referral_code_set` → primary = the referral diagnosis; supporting = related
  intake codes; validate via ICD-10 (§7) for chapter, narrative match, laterality.
- `allergy_readiness` from active allergies (status/severity/source); readiness enum
  from completeness. `recent_encounter_evidence` = the most relevant recent signed
  encounter for the referral reason (id, date, type, provider, diagnoses, meds).
- `required_document_evidence` from `documents_received` + the patient's documents
  (e.g. echo present & final, office note received; list missing required docs).
- `receiving_provider` from the directory. `authorization_readiness` from the
  referral's `authorization_status`/`status`/`urgency` + blockers (§10).
- `medication_highlights` = active meds relevant to the referral (diuretic, BP,
  etc.), relevant-first. `referral_letter_fields` = pick each enum choice to match
  the evidence you assembled (diagnosis summary, allergy statement, encounter,
  document packet, medication summary, recipient, authorization, readiness).

---

## C. Care-transition (handoff) packet

Case objects: a patient ID + a recipient provider ID (a surgical service line).

Gather: `GET /api/patients/{id}`; `/conditions`, `/medications`, `/allergies`,
`/encounters`, `/immunizations`, `/disclosures`; `GET /api/providers/{recipient}`.

Build:
- `patient` + `recipient` blocks from patient + provider records.
- `active_condition_keys` / `active_medication_keys` / `active_allergy_keys` = sorted
  active normalized keys (§1–§2).
- `handoff_encounters` = the N (template-specified, e.g. 4) most relevant recent
  handoff encounters for this service line, newest→oldest; `source_selection` records
  the selection basis + selected vs. excluded encounter IDs (§6). Exclude stale /
  off-topic encounters even if newer.
- `latest_immunization` = immunization with the max date. `disclosure` = the one
  whose `recipient_provider_id` matches the recipient / purpose is this handoff;
  confirm `status == permitted`.
- `risk_flags` = the allowed-value flags supported by active conditions/meds/
  encounters (e.g. insulin-dependent diabetes from an insulin med + diabetes
  condition; latex allergy; fall risk from lower-limb OA; cognitive/HTN from a
  documenting encounter). `risk_flag_evidence` cites the supporting condition keys /
  med keys / encounter IDs per flag (evidence encounters may include excluded ones).
- `packet_readiness` → ready / ready-with-flags / not-ready + blocking codes (§10).

---

## D. Duplicate + ServiceRequest quality review

Case objects: a duplicate-candidate ID, primary + possible-duplicate patient IDs, a
draft ServiceRequest ID.

Gather: `GET /api/duplicates/{candidate}`; both patients' details + `/conditions`;
the patient's `/service-requests` (find the target SR); `GET /api/icd10/{code}` per
reason code; `GET /api/service-codes/{code}`; providers as needed.

Build:
- `duplicate_review`: `candidate_status` & `decision` from candidate status + signal
  strength (§5); copy `match_signals`/`conflict_signals`; merge target/source null
  unless a clean merge (§5).
- `service_request`: map status/intent/priority/service_code/requester/performer/
  dates/reason_codes from the SR record (note field renames in data-model);
  `service_code_valid` + `performer_service_line` (§8); `reason_code_validation`
  array (valid, chapter, matches_patient_evidence) sorted by code (§7–§8).
- `sbar_coverage` from the SR `sbar` block (§9).

---

## E. Referral-batch audit

Case objects: a referral batch ID (a service line).

Gather: `GET /api/referrals`, filter to `batch_id`; `GET /api/icd10/{code}` for every
distinct diagnosis code; `GET /api/patients/{id}` / `/api/providers/{id}` as needed
for anomalies and owners.

Build (all arrays sorted per the template; recompute counts, §11):
- `batch` = id, service_line, requested_date, `record_count` (rows), unique patient
  count.
- `invalid_or_out_of_range_code_referrals` = rows whose code is unknown (404) or out
  of the expected chapter (§7), with actual vs. expected chapter + issue_type.
- `laterality_or_narrative_mismatch_referrals` = rows failing narrative/laterality
  checks (§7), with the mismatch-type set and the ICD-10 `expected_terms`.
- `duplicate_groups` = same-patient resubmissions (consolidate under original);
  `duplicate_tiering_policy` assigns those rows as duplicate blockers.
- `insurance_patient_anomalies` = same insurance across different patients (verify,
  do-not-merge) and same-patient separate clinical referrals.
- `follow_up_queues` = authorization-missing / authorization-pending / records-request
  (missing office note) / imaging-follow-up (§10).
- `action_plan` tier 1/2/3 with `owner_provider_id = receiving_provider_id` (§10);
  `summary_counts` recomputed to agree with every list above.
