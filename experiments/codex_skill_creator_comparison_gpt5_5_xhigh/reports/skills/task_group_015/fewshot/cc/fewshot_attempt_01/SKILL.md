---
name: ehr-quality-packet-solver
description: Use this skill for EHR quality-governance tasks that ask for normalized JSON packets from a read-only task API, including duplicate-chart merge readiness, referral coordination or audit packets, care-transition summaries, ServiceRequest quality review, ICD/service-code validation, active-list reconciliation, document evidence selection, provider contact lookup, and packet readiness classification. Use it whenever the prompt mentions an EHR/referral/quality environment, TASK_ENV_BASE_URL, answer_template.json, patient/referral/duplicate/service-request IDs, or returning normalized JSON from healthcare API records.
---

# EHR Quality Packet Solver

Use this skill to produce a single normalized JSON object from a read-only EHR task environment. The target tasks are evidence-reconciliation problems: collect the API records named in the prompt, reconcile them against the supplied template, and emit JSON only.

## Required Inputs

Before answering, read:

1. The user prompt.
2. `input/payloads/answer_template.json`.
3. Any other files under `input/payloads/`, such as packet request metadata.
4. `environment_access.md` if it is present, to get the base URL and allowed endpoints.

Do not rely on memory of prior task examples. Treat the current API records and current answer template as authoritative.

## Fetch Workflow

Use only endpoints allowed by `environment_access.md`. If the prompt uses `<TASK_ENV_BASE_URL>`, replace it with the `base_url` from that file.

You may use the bundled helper to gather records:

```bash
python skill/scripts/ehr_fetch.py --base-url "$TASK_ENV_BASE_URL" \
  --patient PATIENT_ID \
  --duplicate DUPLICATE_ID \
  --referral REFERRAL_ID \
  --service-code SERVICE_CODE \
  --icd10 ICD10_CODE \
  --provider PROVIDER_ID \
  --include-audit-logs \
  --include-referrals-list \
  --out /tmp/ehr_context.json
```

The script is optional. Plain `curl` or equivalent HTTP calls are fine when faster.

Fetch broadly enough to verify, not just to fill obvious IDs:

- Patient detail for every patient ID in the prompt or linked records.
- Active conditions, medications, and allergies from patient-specific endpoints.
- Encounters, immunizations, documents, service requests, and disclosures when the template asks for them.
- Duplicate candidate detail when a duplicate candidate ID appears.
- Referral detail by referral ID; for batch audits, fetch the referral list and filter by batch ID.
- ICD-10 lookup for each diagnosis or reason code that affects validation.
- Service-code lookup for ServiceRequest service codes.
- Provider directory records for requester, performer, recipient, PCP, or specialist IDs needed in output.
- Audit logs only when the template asks for audit evidence or merge history.

## Evidence Rules

Follow the template's exact shape, enum vocabulary, nullability, and ordering rules. Return no prose outside the JSON object.

General reconciliation:

- Prefer patient-specific active-list endpoints over preview snippets embedded in duplicate or referral records.
- Include only active/current clinical records unless the template explicitly asks for excluded, stale, inactive, or distractor evidence.
- Use `normalized_key` values for condition, medication, and allergy key arrays.
- Sort arrays marked as sets. Sort object arrays by the template rule, commonly by ID or code.
- Preserve stable IDs from the API. Do not substitute names where an ID is requested.
- If a required fact is missing after checking the relevant endpoint, use the template's null, missing, blocked, or follow-up enum rather than inventing a value.

Duplicate review and merge readiness:

- Start with the duplicate-candidate record, then verify demographics and active lists from both patient records.
- A merge is ready only when the candidate status and identity signals support a duplicate and there are no material identity/clinical conflicts requiring human review.
- Minor formatting differences, such as address abbreviations or name variants, are weaker conflicts than different DOB, phone, insurance, given name, or opposite-laterality clinical evidence.
- When merge-ready, choose the canonical target/source from explicit candidate direction or canonical/duplicate patient status, then preserve the union of active condition, medication, and allergy keys.
- When review is required, leave merge target/source null if the template permits it and set the review/hold disposition.
- For merge packet evidence, select identity, external-continuity, or merge-history documents and relevant audit records. Exclude unrelated chart summaries or clinical distractors unless the template asks to list them as excluded.

Referral coordination and audit:

- Reconcile referral records with the active patient chart; do not accept diagnosis text, authorization, documents, or allergy status from a single record without checking the relevant endpoint when available.
- Validate each diagnosis/reason code with the ICD endpoint. Use the ICD chapter and terms from the lookup for chapter validation and narrative/laterality checks.
- Apply the expected service-line chapter from the template or prompt. A code can be valid ICD-10 yet still out of range for the service line.
- For narrative matching, compare the referral narrative to ICD terms and patient evidence. Classify laterality mismatch separately from a broader narrative mismatch; use missing-laterality only when the expected code/term has laterality and the narrative omits it.
- For duplicate referral batches, group same-patient resubmissions; treat shared insurance across different patients as an insurance anomaly, not automatic chart merge evidence.
- Build follow-up queues from explicit blockers: missing or pending authorization, missing required office notes, missing/final-status imaging requirements, invalid/out-of-range codes, clinical mismatch, incomplete allergy evidence, or missing provider.
- Assign action tiers from urgency and blocker severity: urgent coding or duplicate blockers first, routine coding/auth/document blockers second, administrative document completion third, unless the template defines a different policy.

Care transitions:

- Select handoff encounters by relevance to the requested transition, signed/amended status, recency, and any count/window in the template.
- Keep source selection separate from risk evidence. An encounter can be excluded from the handoff list but still support a risk flag if the template asks for risk evidence.
- Use the latest immunization by date when requested.
- Match disclosures to the requested recipient/provider, purpose, and permitted/current status. A missing, denied, pending, or expired disclosure should block readiness when disclosure is required.
- Derive risk flags from active conditions, active medications, active allergies, and relevant encounter content. Emit only allowed risk flag codes.

ServiceRequest quality review:

- Fetch the ServiceRequest from the patient endpoint, then validate its service code and performer/requester providers.
- Validate reason codes with ICD lookups. `matches_patient_evidence` means the code is supported by active conditions, encounters, documents, or request narrative, even if its chapter is outside the expected service-line chapter.
- For SBAR coverage, inspect the relevant request narrative, encounter note, or document content for situation, background, assessment, and recommendation sections. Report present and missing sections using the template enums.

## Output Discipline

Construct the answer from the template outward:

1. Copy the top-level key structure from `answer_template.json`.
2. Fill each field from verified API evidence.
3. Normalize enum strings exactly as the template specifies.
4. Sort all set-like arrays and any object arrays with stated ordering.
5. Validate the final JSON parses.
6. Remove all comments, markdown fences, and explanatory text.

When uncertain, make the uncertainty visible through the template's readiness, blocker, missing, review, or follow-up fields. Do not add extra keys to explain uncertainty unless the template explicitly provides a place for them.
