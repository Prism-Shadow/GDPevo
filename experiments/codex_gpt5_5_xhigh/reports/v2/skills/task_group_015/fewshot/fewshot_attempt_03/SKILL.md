---
name: ehr-quality-governance
description: Support healthcare EHR quality-governance tasks that require inspecting a remote EHR API and returning strict JSON decisions for duplicate chart reconciliation, referral batch audits, handoff packet readiness, service request validation, and referral send-readiness. Use when prompts mention EHR quality review, duplicate candidates, referrals or referral batches, handoff packets, service requests, ICD-10 codebook checks, chart-update decisions, SBAR completeness, disclosure status, or provider/contact validation.
---

# EHR Quality Governance

## Core Workflow

1. Read the task prompt, `task_scope.json`, and `answer_template.json` first. Treat the template as the contract for keys, object nesting, enum casing, booleans, ordering, dates, and numeric precision.
2. Set `BASE` to the task's remote API base URL. Use only the remote HTTP API; do not inspect local environment source code.
3. Call `GET $BASE/health` and `GET $BASE/api`, then fetch only relevant collections. Endpoints are collection-oriented arrays, so filter locally by IDs from `task_scope.json`.
4. Cross-check every target ID against the relevant collection, then pull supporting records from patients, providers, codebook, documents, and audit log as needed.
5. Build the final answer from evidence, then validate it against `answer_template.json`. Return exactly one JSON object and no prose.

Useful API habits:

```bash
BASE="${TASK_ENV_BASE_URL:-$GDPEVO_ENV_BASE_URL}"
curl -fsS "$BASE/api"
curl -fsS "$BASE/api/patients" | jq --arg id "$PATIENT_ID" '.[] | select(.patient_id==$id)'
curl -fsS "$BASE/api/referrals" | jq --arg batch "$BATCH_ID" '.[] | select(.batch_id==$batch)'
curl -fsS "$BASE/api/codebook/icd10" | jq --arg code "$ICD10" '.[] | select(.code==$code)'
```

Common endpoints: `/api/patients`, `/api/duplicate-candidates`, `/api/referrals`, `/api/referral-batches`, `/api/handoff-packets`, `/api/service-requests`, `/api/providers`, `/api/codebook/icd10`, `/api/documents`, `/api/audit-log`.

## Output Contract

- Include `task_id` from `task_scope.json` when the expected answer family includes it, even if the domain schema section focuses on clinical fields.
- Preserve exact field names and nesting from the template. Do not add explanatory keys.
- Use exact enum strings from `allowed_enums`; do not invent casing. API values may be lowercase or title case while output enums are often uppercase.
- Use JSON booleans, integers for counts, `YYYY-MM-DD` dates, and ISO 8601 timestamps.
- Use `[]` for no items. Use `""` for a required string that is intentionally blank; avoid `null` unless the template explicitly allows it.
- Sort stable identifier lists ascending unless the field is an explicit ranked/priority order. Sort IDs inside duplicate groups and sort groups by their first ID.
- Preserve codebook ICD-10 decimal/case style and provider/patient/referral IDs exactly.
- Dynamic maps such as corrected-code suggestions should contain only records that need entries; omit clean records.

## Shared Clinical Rules

- Active clinical lists: include only records with `status == "active"` when collecting active allergies, medications, or problems. Exclude inactive/resolved chart items.
- Allergy fields may require labels, not allergy IDs. Medication fields usually require medication IDs. Problem fields usually require ICD-10 codes. Follow the field name.
- Recent encounters come from `patient.encounters`; include clinically relevant recent encounters and exclude old/resolved-only history when the task asks for recent evidence.
- Most recent immunization is the immunization with the latest `date`.
- Disclosure status should be tied to the requested recipient/purpose when possible; normalize only to the output convention required by the template.
- Provider fields should be verified through `/api/providers`; do not infer provider IDs from names when the specialty match is ambiguous.
- Code validation should use `/api/codebook/icd10`, not string similarity alone. Compare `code`, `description`, `body_site`, `laterality`, `chapter_prefix`, and any tracking-range flag.

## Duplicate Candidate Reconciliation

Inspect the duplicate candidate, all listed patient charts, providers/disclosures if relevant, and matching audit-log events.

- Confirm demographics, contact fields, address, MRN, clinical overlap, and candidate risk flags before deciding merge readiness.
- Use audit-log `duplicate_review` events for the same patient set to populate merge audit status and event ID. If no matching event exists, report the no-event condition rather than fabricating an ID.
- Choose canonical/source patients from evidence such as chart completeness, task hints, audit event, and stable identifiers; do not choose solely by lexical ID order.
- Preserve the union of active allergies, active medication IDs, and active problem codes from all records that will be merged.
- Put patients that should not be merged in `excluded_patient_ids`.
- Use contact actions only for real provider/patient follow-up. If no action is required, use a false boolean, a clear no-action code, and an empty target provider string if the template requires one.
- Block or clarify the merge when addresses, demographics, audit status, or risk flags conflict.

## Referral Batch Audit

Filter referrals by `batch_id`, then evaluate each row independently. A referral can appear in multiple issue sets.

- Missing counts are independent counts: `records_received == "No"`, `imaging_received == "No"`, and `auth_required == "Yes"` with `auth_status == "Not Submitted"`. Do not count `Pending` as not submitted.
- Duplicate referral groups are based on the same patient identity and same/overlapping clinical reason, not merely shared insurer.
- Insurance anomalies occur when an insurance ID is shared between a duplicate-related group and unrelated referral rows. Separate related duplicate IDs from unrelated IDs.
- Out-of-range codes are codes absent from the codebook or present with a tracking-range flag that excludes them for the queue being audited.
- Laterality mismatches occur when the codebook laterality conflicts with diagnosis/referral narrative laterality.
- Narrative mismatches occur when codebook body site or diagnosis meaning does not match the row's narrative, even if the code is otherwise in range.
- Corrected-code suggestions should be emitted only when the codebook has an unambiguous replacement matching the narrative body site, diagnosis, and laterality.
- Priority queues should reflect the most operationally urgent follow-up per referral: immediate for urgent safety/oncology/severe-code issues, short-term for clinical correction or missing evidence, and administrative for auth/scheduling-only cleanup. Do not assume every issue-list member must be queued if the template separates informational findings from work queues.
- Check referring physician/fax/contact fields against available provider data when the prompt asks for contact review.

## Handoff Packet Review

Inspect the handoff packet, linked patient chart, disclosures, immunizations, encounters, and sending/receiving providers.

- Required packet content commonly includes demographics, active problems, active medications, allergies, recent encounters, immunizations, functional status, cognitive status, transfer plan, and disclosure.
- A section is missing if it is absent from `included_sections` or if the corresponding packet field is blank.
- `missing_packet_sections` should use the section names expected by the template or packet data, often snake_case.
- Risk flags should be concise uppercase reason codes derived from missing or unsafe items.
- `readiness` should be blocked for missing required packet content, ready with warnings for nonblocking issues, and ready only when required sections and disclosure evidence are complete.
- Use active chart lists for allergies/medications/problems; do not trust packet sections without checking the patient chart.

## Service Request Validation

Inspect the service request draft, linked patient evidence, and codebook.

- Copy `priority`, `service_code`, `specialty`, and `status` into `order_validation` exactly from the service request unless the template asks for normalization.
- Parse SBAR from `note_text`: Situation, Background, Assessment, and Recommendation are present only when the heading exists and has non-empty content after the colon.
- Populate `sbar_sections_present` with booleans for all four SBAR sections and list missing sections using the template's uppercase names.
- `evidence_encounter_ids` should be linked encounter IDs that exist in the patient chart and support the request.
- `laterality_consistent` requires agreement among request note text, linked encounter diagnoses/care plan, active problems, and codebook laterality.
- `ready_to_sign` is false when required SBAR content, evidence, laterality, safety, or code validation is incomplete. Use blocker codes that name the actual blocker.

## Single Referral Send-Readiness

Inspect the referral row, patient chart, encounters, providers, and codebook.

- Cross-check patient ID against referral name/DOB when both are available.
- Determine `referral_target` from explicit referral fields or an unambiguous provider specialty match. Do not guess a provider when multiple providers fit.
- `diagnosis_update` should use the referral/chart/codebook diagnosis code and description exactly when the chart needs that structured update.
- `allergy_update` should represent a required chart allergy addition from referral notes or evidence, with allergen, reaction, severity, and status. Do not add an allergy update if the chart already contains an equivalent active allergy unless the template asks for reconciliation.
- `letter_merge_fields` should list the merge fields required for the referral letter, sorted consistently by field name unless the template specifies a different order.
- Keep `safety_flags` separate from `unresolved_quality_issues`: a safety flag can document a required update, while unresolved issues should contain only remaining blockers after planned updates.
- `send_ready` is `READY` only when required records/auth/evidence are present and planned structured updates resolve safety requirements. Use clarification or blocked statuses when data is ambiguous or essential requirements are missing.

## Pitfalls

- Do not scrape or inspect local API source code; the remote API is the source of truth.
- Do not answer from the prompt alone. Many decisions require joining several endpoints.
- Do not include inactive medications/problems/allergies in active fields.
- Do not treat shared insurance as a duplicate by itself.
- Do not treat `auth_status: Pending` as `Not Submitted`.
- Do not suggest ICD-10 corrections by free text alone; require a codebook-backed match.
- Do not omit empty arrays or required nested objects just because there are no findings.
- Do not output Markdown, comments, trailing commas, or prose outside the JSON object.
