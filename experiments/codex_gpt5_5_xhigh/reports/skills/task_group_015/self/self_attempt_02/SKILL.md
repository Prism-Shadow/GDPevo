---
name: ehr-quality-governance
description: Use when solving EHR quality governance tasks that require a remote HTTP EHR API plus answer_template.json to reconcile duplicate charts, audit referral batches, review handoff packets, validate service request drafts, or prepare referral/chart-update readiness JSON.
---

# EHR Quality Governance

## Core workflow

1. Read the prompt, `task_scope.json`, and `answer_template.json` first. Treat the template schema and enum casing as authoritative.
2. Get the API base URL from the task environment placeholder or environment variable. Verify the index with `GET /api`; use only the exposed HTTP API, not local service code.
3. Fetch whole collections and filter locally by target IDs. Endpoints are usually collection-shaped arrays:
   - `/api/patients`
   - `/api/duplicate-candidates`
   - `/api/referrals`
   - `/api/referral-batches`
   - `/api/handoff-packets`
   - `/api/service-requests`
   - `/api/providers`
   - `/api/codebook/icd10`
   - `/api/documents`
   - `/api/audit-log`
4. Build small lookup maps by stable ID: patients, referrals, providers, ICD-10 codebook entries, audit events. Join from the target record outward through patient IDs, referral IDs, packet IDs, linked encounter IDs, provider IDs, and batch IDs.
5. Return only one JSON object matching the answer template. Do not include prose, comments, markdown, or template metadata.

Useful command pattern:

```bash
BASE="$GDPEVO_ENV_BASE_URL"
curl -sS "$BASE/api" | jq .
curl -sS "$BASE/api/patients" | jq 'map(select(.patient_id == "TARGET"))'
```

## Output conventions

- Include the top-level keys requested by the template schema, including empty arrays or empty objects when the field is in scope but has no findings.
- Use exact enum casing from `allowed_enums`. Convert API source statuses when needed, for example lowercase audit statuses to uppercase answer enums.
- Stable identifier lists sort ascending unless the field explicitly represents ranked order. For priority tiers, put items in the correct tier first, then sort IDs within each tier unless the template says otherwise.
- Counts are integers. Booleans are JSON booleans, not `"Yes"`/`"No"` strings.
- Dates stay `YYYY-MM-DD`; timestamps stay ISO 8601.
- Dynamic-key objects should include only positive findings. For example, corrected-code maps should omit referrals with no correction.
- Preserve code formatting from source systems and codebooks, including ICD-10 decimals and case.

## Duplicate chart reconciliation

Fetch the duplicate candidate, its patient records, related providers, disclosures, and audit log.

- Confirm demographics across candidate patients: legal name, DOB, phone, address, email, and MRN/enterprise identifiers. Shared name/DOB/phone is strong evidence; conflicting current address or explicit risk flags should block or require clarification.
- Match audit events by `event_type` and the unordered set of candidate `patient_ids`. If no matching event exists, use the template's no-event status and leave event ID empty if the schema requires a string.
- Preserve active clinical content across both charts: active problems by ICD-10 code, active medications by medication ID, and active allergy labels. Exclude inactive entries.
- Choose canonical/source patients from API evidence such as suggested action, audit readiness, disclosure/continuity record, and richer established chart. Do not choose solely because an ID appears first unless no stronger clue exists.
- A merge-ready decision still needs preserved active lists; merging must not drop active allergies, medications, or problems from either record.

Pitfalls:

- Do not merge when current addresses conflict unless the task data explicitly resolves the conflict.
- Do not treat expired disclosures as active.
- Do not include inactive allergies, medications, or problems in preserved active fields.

## Referral batch audits

Filter referrals by exact `batch_id`. Use the ICD-10 codebook for code range, body site, description, and laterality; do not rely on chapter prefix alone.

- Duplicate groups: group referrals for the same patient identity and same condition or code. Same insurance ID alone is not a duplicate.
- Insurance anomalies: flag an insurance ID when it appears on related duplicate referrals and also on unrelated referral rows for different patient identities. Split IDs into related duplicate IDs and unrelated IDs.
- Laterality mismatch: compare left/right words in the referral diagnosis or narrative against the codebook `laterality`. A blank codebook laterality is not automatically a mismatch.
- Narrative mismatch: flag when the referral diagnosis/body site is inconsistent with the codebook description/body site, or source notes explicitly call out a mismatch.
- Out-of-range code: use `in_musculoskeletal_tracking_range` or the equivalent codebook field. Codes outside the tracked range are out of range even when clinically orthopedic; in-range codes can still have narrative mismatch.
- Corrected code suggestions: suggest only when the codebook contains a clear replacement for the same condition/body site/laterality. Do not invent ICD-10 codes.
- Missing counts: count `records_received == "No"`, `imaging_received == "No"`, and `auth_required == "Yes"` with `auth_status == "Not Submitted"`. Do not count `Pending` authorization as not submitted.
- Priority tiers: put clinically urgent safety issues first, especially urgent referrals, fractures, oncology/pathologic fracture coordination, and laterality/body-site errors that can send care to the wrong site. Put missing clinical material and blocking operational gaps next. Put duplicate cleanup, rescheduling, routine authorization, and administrative-only issues in lower tiers unless urgency or safety elevates them.

Pitfalls:

- One referral can contribute to multiple issue sets and multiple missing counts.
- Notes are evidence, but verify them against structured fields and the codebook.
- Sort each issue list by referral ID unless the template explicitly wants a ranked queue.

## Handoff packet review

Fetch the handoff packet, patient chart, providers, and any disclosures/documents referenced by the packet.

- Required packet sections commonly include demographics, active problems, active medications, allergies, recent encounters, immunizations, functional status, cognitive status, transfer plan, and disclosure. A section can be missing because it is absent from `included_sections` or because the corresponding content is blank.
- Active problems, medications, and allergies come from chart entries with `status == "active"` only.
- Recent encounter IDs should reflect the current transition episode or recent care window, not old resolved encounters. Use dates relative to packet creation and clinical relevance.
- Most recent immunization is the immunization with the latest date, not the last item in the array.
- Disclosure readiness requires an active disclosure matching the transfer purpose and recipient/facility/provider. Expired or unrelated disclosures do not satisfy readiness.
- Readiness should be blocked for incomplete required packet sections or missing required disclosure; use warnings only for nonblocking issues.

Pitfalls:

- Do not include inactive conditions just because they appear in the chart.
- Do not count a section as complete when the section name exists but its value is empty.

## Service request and order validation

Fetch the service request draft, linked patient, linked encounters, active problems, providers, and codebook entries for encounter diagnoses.

- Parse SBAR text into `SITUATION`, `BACKGROUND`, `ASSESSMENT`, and `RECOMMENDATION`. A label with no substantive text after it is missing.
- Echo order validation fields from source values where requested: status, priority, service code, and specialty. Use the raw `service_code`, not the display string.
- Laterality consistency compares note text, linked encounter diagnoses, chart problems, and codebook laterality/body site. Contradictory left/right or body-site evidence is an order-safety blocker.
- `ready_to_sign` is true only when SBAR is complete, laterality/body site is consistent, the order is still a signable draft/order, and no blocker codes remain.
- Evidence encounter IDs come from the service request's linked encounters; verify they exist in the patient chart.

Pitfalls:

- Do not mark `RECOMMENDATION` present when the note ends at `Recommendation:`.
- Do not infer a procedure/site from specialty alone; use diagnosis and encounter evidence.

## Referral and chart-update readiness

Fetch the referral row, target patient chart, providers, recent encounters, and codebook. Cross-check referral demographics against the patient before deriving updates.

- Diagnosis update should be supported by referral diagnosis, codebook, and recent encounter/problem evidence. Use the codebook description when the template asks for a description tied to an ICD-10 code.
- Allergy update should be created only when referral notes or chart evidence support adding/updating an allergy. Preserve explicit allergen, severity, reaction, and active/inactive status from evidence; if a required reaction is not specified, use the most conservative supported wording rather than inventing a clinical reaction.
- Referral target should be selected from `/api/providers` by matching requested specialty and clinical context, not by free-text provider names in the referral alone.
- Safety flags capture unresolved risks such as missing severe allergy documentation, missing records, code/laterality conflict, or unsupported target specialty.
- `send_ready` is `READY` only when required chart updates are represented and no unresolved quality issue remains. Use `NEEDS_CLARIFICATION` for ambiguous or contradictory evidence and `BLOCKED` for safety or completeness blockers that cannot be resolved from the API data.

Pitfalls:

- Do not add unresolved quality issues for items already handled in structured update fields unless they still block sending.
- Do not assume a referral is ready because records and imaging are present; chart safety updates and specialty targeting can still block readiness.
