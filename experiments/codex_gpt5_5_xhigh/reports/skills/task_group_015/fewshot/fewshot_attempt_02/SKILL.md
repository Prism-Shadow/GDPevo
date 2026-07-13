---
name: ehr-quality-governance
description: Solve healthcare EHR quality-governance tasks that require reconciling duplicate charts, auditing referral batches, reviewing handoff packets, validating service requests, or preparing referral readiness decisions from a remote EHR quality API.
---

# EHR Quality Governance Skill

Use this skill when a task asks for a structured EHR quality decision from the shared healthcare quality API. The work is evidence reconciliation: collect the target records, cross-check chart, referral, provider, codebook, document, and audit evidence, then return only JSON conforming to the task's `answer_template.json`.

## Source And API Discipline

- Read the task prompt, `input/payloads/task_scope.json`, and `input/payloads/answer_template.json` first. The scope file gives the target IDs and the required response contract.
- Use the remote base URL supplied by the task or environment access file. Query `GET /api` to confirm available endpoints, then use list endpoints and filter locally by target IDs.
- Do not rely on unstated detail endpoints. The observed API is list-oriented: `/api/patients`, `/api/duplicate-candidates`, `/api/referrals`, `/api/referral-batches`, `/api/handoff-packets`, `/api/service-requests`, `/api/providers`, `/api/codebook/icd10`, `/api/documents`, and `/api/audit-log`.
- Fetch broad reference lists once per task, then filter precisely. Typical filters are `candidate_id`, `patient_id`, `referral_id`, `batch_id`, `packet_id`, `request_id`, `provider_id`, and audit `patient_ids`.
- Keep separate notes for direct evidence versus inference. Prefer explicit API fields; infer only from consistent cross-record evidence such as diagnosis text matching a codebook row, a blank required note section, or a chart problem matching referral reason.

Example access pattern:

```bash
BASE="$TASK_ENV_BASE_URL"
curl -sS "$BASE/api"
curl -sS "$BASE/api/referrals" | jq '[.[] | select(.batch_id == $batch)]' --arg batch "$BATCH_ID"
```

## Output Contract

- Start from `answer_template.json`. Use exactly the required keys, nested shape, enum spelling, and scalar types.
- If `task_scope.json` contains `task_id`, include it as a top-level field unless the specific answer template explicitly forbids extra top-level keys.
- Return one JSON object only. Do not include explanatory prose in the final answer for a solver task.
- Sort stable identifier lists ascending unless the field is explicitly a ranking or priority queue. Sort IDs inside duplicate groups and anomaly lists. Within named priority tiers, sort IDs ascending.
- Use real booleans, not `"Yes"` or `"No"`. Counts are integers. Use empty arrays or empty objects for "none" list/map fields, and empty strings for absent scalar IDs when the template uses strings.
- Preserve codebook spelling and punctuation for ICD-10 codes and descriptions. Preserve API strings exactly for copied values such as provider specialty, service code, request status, priority, allergen, reaction, and severity.
- Dates should remain `YYYY-MM-DD`; timestamps should remain ISO 8601. Do not invent dates.

## Duplicate Chart Reconciliation

For duplicate candidates, gather:

- the candidate row from `/api/duplicate-candidates`;
- all patient charts listed in `patient_ids`;
- relevant `/api/audit-log` rows whose `patient_ids` cover the candidate pair;
- providers if contact escalation is needed.

Decision rules:

- A merge can be ready only when identity anchors align strongly: legal name, DOB, phone/address or other stable demographics, and no conflicting risk flags. Use the audit log to confirm a ready duplicate-review event when the output asks for audit status/event ID.
- Treat conflicting current address, different DOB, materially different demographics, or explicit candidate risk flags as blockers or clarification needs according to the allowed enum.
- Choose the canonical target as the chart that is current, more complete, or otherwise supported by the candidate/audit evidence. The other chart is the source. Do not merge unrelated lookalikes.
- Preserve the union of active clinical facts across the charts: active allergy labels, active medication IDs, and active problem ICD codes. Exclude inactive problems, inactive medications, and inactive allergies.
- If no provider contact is needed, use `action_required: false`, `action_code: "NONE_REQUIRED"` when that code is in use, and an empty `target_provider_id`.
- Audit status usually derives from the audit event status: ready event becomes `READY_FOR_MERGE`; unresolved address conflict becomes the address-blocked enum; no matching event becomes `NO_EVENT_FOUND`.

Common pitfalls:

- Do not let matching name alone drive a merge.
- Do not drop active allergies or medications from the source chart just because that chart is not canonical.
- Do not fabricate an audit event ID if no matching audit row exists.

## Referral Batch Quality Audit

For referral batches, gather:

- the batch row from `/api/referral-batches`;
- all referrals with the target `batch_id`;
- `/api/codebook/icd10`;
- providers only if the answer shape asks for contact or routing details.

Field interpretation:

- `missing_counts.records_missing`: count referrals whose `records_received` is not `"Yes"`.
- `missing_counts.imaging_missing`: count referrals whose `imaging_received` is not `"Yes"`.
- `missing_counts.auth_not_submitted`: count referrals where `auth_required` is `"Yes"` and `auth_status` is `"Not Submitted"`. Do not count `"Pending"` as not submitted.
- `laterality_mismatch_referral_ids`: diagnosis narrative laterality conflicts with the ICD-10 codebook laterality.
- `narrative_mismatch_referral_ids`: diagnosis narrative or body site does not match the codebook description/body site, including overly generic codes that fail to represent the clinical narrative.
- `out_of_range_code_referral_ids`: codebook row has `in_musculoskeletal_tracking_range: false`, or the code is absent from the relevant tracking codebook.
- `corrected_code_suggestions`: include only referrals with a clear corrected ICD-10 code from the codebook, usually same condition/body site with corrected laterality or a more specific matching diagnosis. Do not suggest a replacement when the code is merely out of range and no exact codebook match is evident.
- `duplicate_groups`: group referrals for the same patient and same clinical condition, usually matching name, DOB, diagnosis, and referral context. Sort each group by referral ID.
- `insurance_anomalies`: when an insurance ID appears across a duplicate group and also on unrelated referrals, separate `related_duplicate_referral_ids` from `unrelated_referral_ids`. Shared insurance ID alone is not a duplicate.

Priority queue habits:

- Tier 1 is for immediate safety/clinical escalation, such as urgent high-risk findings, oncology coordination, or severe laterality/code errors on an urgent referral.
- Tier 2 is for short-term clinical cleanup, such as missing records/imaging combined with clinical review needs, laterality mismatch, or narrative/code mismatch.
- Tier 3 is for administrative follow-up only, such as authorization not submitted without a clinical safety issue.
- Do not automatically queue every issue. Use the queue fields for work-priority routing, while the issue lists remain the complete audit inventory.

Common pitfalls:

- A fracture or pain code can match the narrative but still be out of tracking range.
- A code with the right body site but wrong side belongs in laterality mismatch and often gets a corrected-code suggestion if the opposite-side code exists.
- Keep dynamic object keys, such as correction maps, limited to referrals that truly require that field.

## Handoff Packet Review

For handoff packets, gather:

- the packet row from `/api/handoff-packets`;
- the linked patient chart;
- sending and receiving providers if routing or disclosure evidence needs confirmation.

Completeness rules:

- Required packet content commonly includes demographics, active problems, active medications, allergies, recent encounters, immunizations, functional status, cognitive status, transfer plan, and disclosure. A section can be missing because it is absent from `included_sections` or because the corresponding packet field is blank.
- `active_problem_codes`, `active_medication_ids`, and `active_allergy_labels` come from the linked patient chart and include active items only.
- `recent_encounter_ids` should include the current transition episode and recent relevant care, not stale unrelated encounters.
- `most_recent_immunization_id` is the immunization with the latest date.
- `disclosure_status` should reflect the relevant patient disclosure for the transfer recipient/facility. Use the API status casing from the chart when the template allows free strings.
- `missing_packet_sections` should use stable section names consistent with the packet fields, such as `cognitive_status`.
- `risk_flags` should encode actionable uppercase flags for missing or unsafe items, such as `MISSING_COGNITIVE_STATUS`.

Readiness rules:

- `READY` means required sections are present and safety/disclosure evidence is sufficient.
- `READY_WITH_WARNINGS` fits minor nonblocking concerns when the enum is available.
- `BLOCKED_INCOMPLETE_PACKET` fits missing required packet sections.
- `NEEDS_CLARIFICATION` fits ambiguous evidence that cannot be resolved from the chart.

Common pitfalls:

- Do not include inactive problems in active problem code lists.
- Do not treat a blank packet field as complete just because adjacent sections exist.
- Do not use the packet's included-section list as a substitute for checking the patient chart.

## Service Request Validation

For service request drafts, gather:

- the service request row from `/api/service-requests`;
- the linked patient chart and linked encounter IDs;
- `/api/codebook/icd10` when diagnosis, body site, or laterality needs validation.

Validation rules:

- `order_validation` is a normalized copy of key order fields: `service_code`, `specialty`, `status`, and `priority`.
- `evidence_encounter_ids` are linked or chart encounters that substantiate the requested service and diagnosis.
- Parse SBAR from `note_text` by headings: `Situation:`, `Background:`, `Assessment:`, and `Recommendation:`. A heading with no content after it is missing.
- `sbar_sections_present` uses uppercase keys from the template and booleans for each section.
- `missing_sbar_sections` lists the uppercase missing section names.
- `laterality_consistent` compares note text, diagnosis/problem code, encounter evidence, and codebook laterality. A side mismatch is a blocker.
- `ready_to_sign` is false if required SBAR sections are missing, laterality is inconsistent, evidence does not support the order, or order safety is otherwise blocked.
- `blocker_codes` should be concise uppercase codes tied to the reason, such as `MISSING_RECOMMENDATION` or `LATERALITY_MISMATCH`.

Common pitfalls:

- A present heading is not enough; the section must contain content.
- Do not change copied order fields to friendlier display values.
- Validate against the linked chart evidence, not only the prose note.

## Single Referral Readiness And Chart Update

For individual referral decisions, gather:

- the referral row from `/api/referrals`;
- the target patient chart from `/api/patients`;
- `/api/providers` for target provider and specialty;
- `/api/codebook/icd10` for diagnosis description and code validation;
- documents if the prompt mentions letters, merge fields, or authorization forms.

Decision rules:

- Confirm the referral diagnosis and reason against recent encounters and active problems. Use recent encounter IDs that support the referral, sorted ascending.
- `diagnosis_update` should use the code and description supported by chart evidence and the codebook/referral diagnosis. Do not invent a code outside the codebook when the task expects codebook-backed values.
- `allergy_update` should capture required allergy additions from referral notes or chart evidence, including allergen, reaction, severity, and status.
- `referral_target` should name the provider ID and specialty that match the referral service need, not merely the referring provider.
- `letter_merge_fields` should list the required merge variables exactly as field names with underscores/casing preserved, sorted consistently.
- `safety_flags` should capture nonnegotiable safety prerequisites, for example required contrast-allergy documentation before sending imaging-related materials.
- `send_ready` is `READY` when all needed updates are represented in the output and no unresolved blockers remain; use `NEEDS_CLARIFICATION` for ambiguous or missing evidence; use `BLOCKED` for unresolved safety/order blockers.
- `unresolved_quality_issues` must be present. Use an empty list when the structured updates resolve the issues.

Common pitfalls:

- Do not confuse referring physician/practice fields with the target specialist provider.
- Do not mark send-ready as blocked merely because an update is needed, if the answer itself records the update and no unresolved issue remains.
- Keep letter merge fields as field tokens, not descriptions.

## Final Self-Check Before Answering

1. Every target ID from `task_scope.json` appears in the appropriate output field.
2. Every output key required by `answer_template.json` is present, including empty lists/maps/strings where applicable.
3. All enums match template casing exactly.
4. Active-only clinical lists exclude inactive chart items.
5. Counts reconcile with the actual filtered records.
6. Code corrections and laterality findings are backed by the ICD-10 codebook.
7. No explanatory text surrounds the JSON.
