# Task Archetypes — Fetch → Derive → Emit Plans

The five archetypes observed across the train tasks. Each plan is a **reusable procedure**: which endpoints to fetch and which fields to derive. They contain no task-specific answer values — apply them to the IDs each new task names and derive every value fresh from the API.

Recognize the archetype from the prompt + `answer_template.json` top-level keys, then run the matching plan.

---

## Archetype A — Duplicate-chart merge readiness packet
**Signals:** prompt names a duplicate `candidate_id` (pattern `DUP-…`) and the two `patient_id`s it pairs; optional `merge_packet_request.json` payload lists `requested_outputs`.

**Fetch**
- `GET /duplicates/{candidate_id}` (target/source, signals, preview, status).
- For each of the two `patient_id`s: `GET /patients/{id}`, `/conditions`, `/medications`, `/allergies`, `/documents`.
- `GET /audit-logs` → filter client-side by `patient_id ∈ pair` and identity/import/merge-relevant `event`.
- `GET /providers` (or detail calls) for the specialist (service-line match to the evidence) and the PCP (from patient `primary_care_provider`).

**Derive**
- Canonical target/source from `merge_preview` (see derivation_rules §1).
- `merge.disposition` and `merge_decision.disposition` by signal strength + `status` (§2); `reason_codes`/`canonical_reason_codes` from signal labels, sorted.
- `clinical_unions` / `active_key_unions`: active `normalized_key` unions across both patients (§3).
- `active_list_reconciliation`: keys present in active endpoints but missing from `merge_preview` (§3).
- `identity_signals`: copy `match_signals` / `conflict_signals`; derive `demographic_matches`/`demographic_conflicts` by comparing the two patient detail objects field by field (dob, phone, insurance_id, address, names).
- `evidence.document_ids` / `evidence.audit_ids`: relevant only (§8); the rest → `excluded_distractors`.
- `document_selection_policy`: identity/external-continuity docs only; list excluded types.
- `packet_readiness`: ready/blocked from disposition + missing evidence.
- `packet_contact`: specialist_provider (service-line match + `contact_reason`) and primary_care_provider (from patient detail).

**Emit** one JSON object conforming to the template; all set arrays sorted alphabetically.

---

## Archetype B — Care-transition handoff packet
**Signals:** prompt names a `patient_id` and a recipient `provider_id` (e.g. a surgeon); template has `handoff_encounters`, `latest_immunization`, `disclosure`, `risk_flags`, `packet_readiness`.

**Fetch**
- `GET /patients/{id}`; subresources `/conditions`, `/medications`, `/allergies`, `/encounters`, `/immunizations`, `/disclosures` (and `/documents` if needed).
- `GET /providers/{recipient_id}`.

**Derive**
- `patient` block from patient detail; `recipient` from provider detail (validate `service_line` enum).
- `active_condition_keys` / `active_medication_keys` / `active_allergy_keys`: active `normalized_key` sets, sorted ascending.
- `handoff_encounters`: the N most relevant recent encounters for the recipient's service line (template fixes N). Sort newest-to-oldest. `source_selection.selected_encounter_ids` (newest-to-oldest) and `excluded_encounter_ids` (stale/out-of-window/unrelated, ascending).
- `latest_immunization`: max `date` immunization.
- `disclosure`: the disclosure whose `recipient_provider_id` matches the recipient (or the applicable one); check `status == permitted`.
- `risk_flags` + `risk_flag_evidence` from clinical evidence, allowed-set only (§10).
- `packet_readiness`: status + `blocking_issue_codes` (allowed set) when required sections missing.

**Emit** conforming to the template; ordering per `ordering` fields.

---

## Archetype C — Referral coordination packet
**Signals:** prompt names a `referral_id` and `patient_id` for a service line (e.g. cardiology); template has `referral_code_set`, `allergy_readiness`, `required_document_evidence`, `authorization_readiness`, `referral_letter_fields`.

**Fetch**
- `GET /referrals/{referral_id}`.
- `GET /patients/{id}`; `/conditions`, `/medications`, `/allergies`, `/encounters`, `/documents`.
- `GET /providers/{receiving_provider_id}`.
- `GET /icd10/{diagnosis_code}` (and any supporting codes).

**Derive**
- `patient_referral` from the referral object (validate `service_line` enum, `requested_date`).
- `active_diagnoses`: active conditions; set `referral_relevant` per the referral context.
- `referral_code_set`: primary code validation (valid/mismatch/invalid/wrong-chapter), `primary_code_chapter`, `narrative_match` (§5).
- `allergy_readiness`: aggregate active allergies → readiness enum; `ready_for_letter`; `follow_up_needed` (e.g. conflicting or incomplete records).
- `recent_encounter_evidence`: the supporting recent encounter + `care_plan_tag` classification (§9).
- `required_document_evidence`: echo / office_note received flags; `missing_required_documents` list (§11).
- `receiving_provider` contact from provider lookup.
- `authorization_readiness`: status/urgency/overall_readiness/blocking_issues (§11).
- `medication_highlights`: referral-relevant meds first (heart_failure_diuretic / blood_pressure_management / …), then other active meds.
- `referral_letter_fields`: choose each enum value from the assembled evidence (§11).

**Emit** conforming to the template; sets as sets, derivations per ordering notes.

---

## Archetype D — Duplicate + ServiceRequest quality review
**Signals:** prompt names a `candidate_id`, a primary `patient_id`, a possible-duplicate `patient_id`, and a `service_request_id`; template has `duplicate_review`, `service_request`, `sbar_coverage`.

**Fetch**
- `GET /duplicates/{candidate_id}`.
- `GET /patients/{primary_id}`, `GET /patients/{possible_duplicate_id}`.
- `GET /patients/{<SR patient id>}/service-requests` → filter by `service_request_id` (the SR belongs to the primary patient unless the prompt says otherwise).
- `GET /service-codes/{service_code}`; `GET /providers/{performer_id}`, `GET /providers/{requester_id}`.
- For each `reason_code`: `GET /icd10/{code}`.
- `GET /patients/{<SR patient id>}/conditions` (to test `matches_patient_evidence`).

**Derive**
- `duplicate_review`: `candidate_status` (map to template enum), `decision` by signal strength (§2), `merge_target/source` from `merge_preview` (null if not_duplicate), `match_signals`/`conflict_signals` (allowed-set filter).
- `service_request`: rename `requester_id`→`requester_provider_id`, `performer_id`→`performer_provider_id`; `performer_service_line` from provider lookup; `service_code_valid` from service-code lookup; `reason_code_validation[]` (§6); pass through `status, intent, priority, service_code, authored_on, occurrence_date, reason_codes`.
- `sbar_coverage`: from `sbar` non-empty keys (§7).

**Emit** conforming to the template; **no procedural notes or narrative SOP text**.

---

## Archetype E — Batch referral audit
**Signals:** prompt names a `batch_id` (pattern `<MONTH>26-<SERVICE>-<suffix>`, e.g. an orthopedic monthly batch); template has `invalid_or_out_of_range_code_referrals`, `laterality_or_narrative_mismatch_referrals`, `duplicate_groups`, `insurance_patient_anomalies`, `follow_up_queues`, `action_plan`, `summary_counts`.

**Fetch**
- `GET /referrals` → filter client-side by `batch_id`.
- For each referral: `GET /icd10/{diagnosis_code}` (404 = unknown); `GET /patients/{patient_id}` (for uniqueness + insurance); `GET /providers/{receiving_provider_id}` (action-plan owner).

**Derive**
- `batch`: `record_count` = rows in batch; `unique_patient_count` = distinct `patient_id`; `service_line` (expected enum, e.g. `orthopedics`); `requested_date`.
- `invalid_or_out_of_range_code_referrals`: chapter ≠ expected (`Musculoskeletal`) or 404 (§5).
- `laterality_or_narrative_mismatch_referrals`: `requires_laterality` + `expected_terms` vs `diagnosis_narrative` (§5); `mismatch_types` from {laterality_mismatch, narrative_mismatch, missing_laterality}.
- `duplicate_groups`: same `patient_id` resubmissions → group; `referral_ids` sorted ascending; `duplicate_tiering_policy` (tier all group rows as duplicate blockers; list same-patient referrals that are separate clinical reviews).
- `insurance_patient_anomalies`: shared `insurance_id` across different patients (verify, do not merge) and same-patient separate clinical referrals (separate review). Sort by `anomaly_id`; inner ids ascending.
- `follow_up_queues`: `authorization_missing` / `authorization_pending` referral ids; `records_request` (missing `office_note`); `imaging_follow_up` (missing/pending imaging). All sorted ascending.
- `action_plan`: Tier 1 = urgent coding/duplicate blockers; Tier 2 = routine coding/auth/document blockers; Tier 3 = administrative document completion. `owner_provider_id` = receiving provider.
- `summary_counts`: recompute every count from the arrays above (never hard-code).

**Emit** conforming to the template; arrays sorted per `ordering_rules` (referral-object arrays and id arrays ascending by `referral_id`; groups by `group_id`; anomalies by `anomaly_id`).

---

## Cross-archetype reminders
- Always read `answer_template.json` first — it is the contract. Field names, enums, and ordering rules vary per task.
- Fetch only documented endpoints; filter client-side; treat 404 as the not-found signal.
- Derive, never copy from prior tasks. Sort sets alphabetically by default; follow template overrides.
- Output one JSON object only — no prose, no fences, stable IDs.
