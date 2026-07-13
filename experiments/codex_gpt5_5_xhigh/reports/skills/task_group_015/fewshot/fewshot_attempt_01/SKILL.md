---
name: ehr-quality-governance
description: Use for healthcare EHR quality-governance tasks that require inspecting the remote EHR quality API and returning strict JSON decisions for duplicate patient reconciliation, referral batch audits, handoff packet readiness, service request draft validation, or referral/chart-update send readiness. Triggers include answer_template.json, task_scope.json, EHR quality API endpoints, duplicate-candidates, referrals, referral-batches, handoff-packets, service-requests, patients, providers, ICD-10 codebook, SBAR, merge_decision, priority_queues, readiness, send_ready, and safety_flags.
---

# EHR Quality Governance

Use this skill to solve structured EHR quality review tasks against the provided remote HTTP API. Produce only the JSON object requested by the task's `answer_template.json`.

## Core Workflow

1. Read the prompt, `task_scope.json`, and `answer_template.json` before querying data. Treat `target_ids` as the scope of work and the template as the output contract.
2. Read `environment_access.md` for the base URL. Use only the remote HTTP API for task data; do not inspect local environment source code.
3. Start with `GET /health` and `GET /api`, then fetch collection endpoints and filter locally. The endpoints are collection-style; target IDs may use slightly different field names in payloads, such as `duplicate_candidate_id` in the task scope versus `candidate_id` in `/api/duplicate-candidates`.
4. Pull all linked evidence, not just the target row:
   - duplicate review: duplicate candidate, all referenced patient records, providers if outreach is needed, and audit log.
   - referral batch: batch metadata, all referrals with that `batch_id`, providers, and `/api/codebook/icd10`.
   - handoff packet: packet, patient chart, disclosures, immunizations, encounters, active clinical lists, and providers.
   - service request: request draft, linked patient chart encounters/problems, providers, and codebook.
   - referral send decision: referral row, patient chart, providers, codebook, and documents if referenced.
5. Build the answer from evidence. Do not infer facts that are not present in the API. If evidence is absent but a required string field exists, use the template's apparent blank-value convention rather than inventing a value.

## Output Contract

- Return one JSON object and no prose.
- Use the exact keys, enum casing, booleans, and nested shapes in `answer_template.json`.
- Carry through the top-level `task_id` from `task_scope.json` when present; the examples use it even when the schema section omits it.
- Sort stable identifier lists ascending unless the field is explicitly a priority queue. Sort labels/codes consistently when the template asks for preserved active labels or codes.
- For dynamic maps such as corrected code suggestions, include only affected IDs. Do not include no-op entries.
- Counts are integers. Ratios or scores, if any, use 3 decimal places.
- Preserve source casing and formatting for codes, dates, timestamps, provider IDs, and specialty names.
- Use active chart entries only for active problems, medications, allergies, and disclosures. Ignore inactive entries unless the prompt explicitly asks to report them.

## Duplicate Patient Reconciliation

- Match the candidate by `candidate_id`, then load every `patient_id` listed on the candidate.
- Compare legal name, DOB, phone, address, MRN, active disclosures, active clinical lists, and candidate `risk_flags`. Demographic similarity alone is not enough if current addresses conflict, disclosures are expired/missing in a blocking way, or risk flags indicate a safety or identity conflict.
- Use `/api/audit-log` to find a `duplicate_review` event for the same patient ID set. Map audit statuses to the template enum casing, such as ready-for-merge to `READY_FOR_MERGE`; use `NO_EVENT_FOUND` and a blank event ID if no matching event exists.
- For merge-ready cases, choose canonical/source patients from audit or unambiguous chart evidence. Preserve active allergy labels, active medication IDs, and active problem codes across both records, de-duplicated and sorted.
- Fill `excluded_patient_ids` only with patient records from the candidate that should not participate in the final action.
- Use `contact_action.action_required=false`, `action_code="NONE_REQUIRED"`, and blank `target_provider_id` only when no outreach is needed. If clarification is needed, target the relevant primary/referring/receiving provider and use a concise uppercase action code tied to the blocker.

## Referral Batch Audits

- Filter `/api/referrals` by the target `batch_id`. Use `/api/codebook/icd10` as the source of truth for code description, body site, laterality, chapter prefix, and musculoskeletal tracking eligibility.
- Detect duplicates by same patient demographics plus same condition/body site, even when referrer, authorization status, or notes differ. Each duplicate group is a sorted list of referral IDs.
- Detect insurance anomalies when an `insurance_id` is shared by a true duplicate group and unrelated referrals. Put duplicate-related IDs and unrelated IDs in their separate sorted lists.
- `missing_counts.auth_not_submitted`: count rows where authorization is required and auth status is not submitted. `imaging_missing`: count rows with imaging not received. `records_missing`: count rows with records not received.
- `laterality_mismatch_referral_ids`: include referrals whose narrative laterality contradicts the codebook laterality for the ICD-10 code.
- `narrative_mismatch_referral_ids`: include referrals whose diagnosis narrative/body site/condition does not match the codebook meaning, even if the code is in tracking range.
- `out_of_range_code_referral_ids`: include referrals whose codebook row is outside the target service-line tracking range.
- `corrected_code_suggestions`: suggest a code only when the codebook contains a clear replacement matching the referral narrative's condition, body site, and laterality. Preserve decimal and case style from the codebook.
- Priority queues represent work priority, not every issue list:
  - tier 1: urgent safety-sensitive items, especially serious conditions or coordination needs combined with a blocking code/laterality issue.
  - tier 2: short-term clinical or scheduling blockers such as missing records/imaging or correctable narrative/laterality errors.
  - tier 3: administrative follow-up such as not-submitted authorization or scheduling preference without an immediate clinical blocker.

## Handoff Packet Readiness

- Match the packet by `packet_id` and load its patient chart. Use active problems, active medications, active allergy labels, current disclosures, recent relevant encounters, and the newest immunization by date.
- Compare `included_sections` and packet fields against required handoff content: demographics, active problems, active medications, allergies, recent encounters, immunizations, functional status, cognitive status, transfer plan, and disclosure.
- A section is missing if it is absent from `included_sections` or its corresponding packet value is blank. Report missing section names in the packet's snake_case style.
- Disclosure status should reflect a current disclosure appropriate to the transfer recipient/purpose. Use uppercase status text in the output when the template expects a string status.
- Readiness rules:
  - `READY`: all required sections and transfer disclosure evidence are complete.
  - `READY_WITH_WARNINGS`: non-blocking discrepancies exist but the packet can move.
  - `BLOCKED_INCOMPLETE_PACKET`: required packet sections are missing or blank.
  - `NEEDS_CLARIFICATION`: evidence conflicts or cannot identify the correct patient/recipient.
- Risk flags should be concise uppercase issue codes derived from blockers, such as `MISSING_<SECTION>`.

## Service Request Draft Validation

- Match the request by `request_id`, then verify the patient and every `linked_encounter_id`.
- Copy `order_validation.priority`, `service_code`, `specialty`, and `status` exactly from the request.
- Parse SBAR sections from `note_text`: Situation, Background, Assessment, Recommendation. A section is present only when it has substantive text after its label before the next label; a bare label with no content is missing.
- `sbar_sections_present` uses uppercase SBAR keys with booleans. `missing_sbar_sections` uses the same uppercase section names.
- `evidence_encounter_ids` should be linked encounters that exist in the patient chart and support the requested service.
- Determine `laterality_consistent` by comparing the request note, linked encounter diagnoses/care plan, active problems, and codebook laterality. Contradictions are blockers.
- `ready_to_sign` is true only when the request has supporting evidence, all required SBAR sections, consistent laterality, and no order-safety blocker. Use concise uppercase `blocker_codes`, such as missing SBAR section codes or `LATERALITY_MISMATCH`.

## Referral Chart-Update And Send Decisions

- Match the referral by `referral_id` and patient by `patient_id`; verify name/DOB consistency between referral row and chart.
- Use the referral ICD-10 code plus codebook to populate diagnosis updates. Prefer the codebook description when it matches the referral narrative; otherwise flag unresolved ambiguity instead of forcing a diagnosis.
- Choose the referral target from `/api/providers` by requested specialty/service line and clinical context. Do not confuse the referring physician/practice with the receiving provider.
- If referral notes or chart evidence require an allergy or other safety update before send, populate the structured update and add an uppercase `safety_flags` code. Do not invent allergies absent from evidence.
- `recent_encounter_ids` should include recent chart encounters relevant to the referral reason and be sorted by stable ID unless the template explicitly asks for chronology.
- `letter_merge_fields` should list only fields that must be merged into the outgoing document, using the exact field-name style shown by the template/domain and sorted consistently.
- `send_ready` can be `READY` when all required records/auth/safety updates are resolved in the structured decision. Use `NEEDS_CLARIFICATION` for ambiguous evidence and `BLOCKED` for unresolved safety, missing required records, missing authorization, or no valid receiving target.
- Keep `unresolved_quality_issues` empty only when no remaining blockers exist after the proposed structured updates.

## Common Pitfalls

- Do not assume endpoint field names match template field names.
- Do not include inactive problems, medications, allergies, or expired disclosures in active/current fields.
- Do not count `auth_status="Pending"` as not submitted; reserve auth-not-submitted counts for explicit not-submitted statuses when authorization is required.
- Do not treat an ICD-10 code as correct just because it is in the codebook; compare description, body site, laterality, and tracking range.
- Do not mark an SBAR section present when the label exists but the content is empty.
- Do not use notes alone when structured fields contradict them; report the contradiction through the appropriate blocker or mismatch field.
- Do not add explanatory text outside the JSON response.
