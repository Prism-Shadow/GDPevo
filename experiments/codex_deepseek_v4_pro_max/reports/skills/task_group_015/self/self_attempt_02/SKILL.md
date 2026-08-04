## When to Use

Use this skill whenever the task involves preparing a normalized clinical data packet from an EHR quality-governance or clinical-operations REST API. Typical task shapes include duplicate-chart merge readiness, referral coordination, care-transition handoff, quality-governance case review, and batch audit packets. The shared environment provides read-only GET endpoints for patients, clinical lists, encounters, documents, providers, ICD-10 codes, duplicate candidates, referrals, service requests, and related FHIR-style resources.

## Operating Procedure

### 1. Orient to the Task

Read the prompt to identify:
- The task category (merge readiness, referral coordination, care transition, quality review, batch audit).
- The runtime object IDs (patient IDs, referral IDs, candidate IDs, batch IDs, service-request IDs, provider IDs).
- Which answer-template schema applies.

Locate and parse the answer template file referenced in the prompt. The template defines every required top-level key, field types, enum sets, and ordering rules. Your output must conform exactly to that shape.

### 2. Survey Available Endpoints

Read `environment_access.md` for the base URL and the list of allowed GET endpoints with their supported query parameters. Every API call must use the base URL from that file. Replace path placeholders (`{patient_id}`, `{referral_id}`, `{candidate_id}`, `{code}`, `{provider_id}`) with runtime values obtained from the prompt or from prior API results.

### 3. Gather Clinical Data

Query endpoints in this order to build a complete picture:

1. **Primary entity**: Fetch the main object first (duplicate candidate, referral, service request, or batch listing).
2. **Patient demographics**: For every patient ID in scope, call `GET /api/patients/{patient_id}`.
3. **Clinical lists**: For every patient, fetch active conditions (`/api/patients/{patient_id}/conditions`), medications (`/api/patients/{patient_id}/medications`), and allergies (`/api/patients/{patient_id}/allergies`). Prefer query parameters like `status=active` when the endpoint supports them.
4. **Encounters**: Fetch encounters for each patient; apply `status` and `limit` parameters when available. Sort by date descending to identify the most recent relevant encounters.
5. **Documents**: Fetch documents for each patient. Filter to final-status documents relevant to the task scope.
6. **Audit logs**: When the task requires audit evidence, query `/api/audit-logs` with relevant `patient_id`, `event`, and date-range filters.
7. **Ancillary resources**: Query immunizations (`/api/patients/{patient_id}/immunizations`), disclosures (`/api/patients/{patient_id}/disclosures`), and service requests (`/api/patients/{patient_id}/service-requests`) when the answer template demands them.
8. **Reference directories**: Look up ICD-10 codes via `/api/icd10/{code}`, providers via `/api/providers/{provider_id}`, and service codes via `/api/service-codes/{code}`.

### 4. Normalize and Reconcile

#### Clinical Keys

- Extract `normalized_key` from every active condition, medication, and allergy record.
- When building union sets across patients, collect keys from both patients' active lists.
- Exclude records whose status is inactive, entered-in-error, or resolved unless the template explicitly asks for them.

#### ICD-10 Code Validation

- For every diagnosis code, call `GET /api/icd10/{code}` to retrieve the official chapter, description, and laterality.
- Classify validation results as:
  - `valid_matches_narrative` — code exists and description aligns with the clinical narrative.
  - `valid_but_narrative_mismatch` — code exists but narrative/laterality disagrees.
  - `invalid_code` or `unknown_code` — code not found in the ICD-10 directory.
  - `wrong_service_chapter` or `out_of_range_chapter` — code chapter does not match the expected service line (e.g., a non-MSK code in an orthopedic referral).
- Check laterality by comparing the ICD-10 laterality field against referral narratives; flag `laterality_mismatch` or `missing_laterality` when they conflict.

#### Identity and Duplicate Analysis

- Read match signals and conflict signals directly from the duplicate-candidate endpoint (`GET /api/duplicates/{candidate_id}`).
- Map observed signals to the controlled enum values defined in the answer template (e.g., `same_dob`, `same_insurance`, `different_given_name`, `different_phone`).
- Determine merge disposition: `merge`/`ready_to_merge` when match signals dominate and conflicts are minor; `needs_review`/`review_hold` when conflicts exist but may be resolvable; `do_not_merge` when conflicts are irreconcilable.
- The merge target is the patient with the richer or more authoritative chart; the source is merged into the target.

#### Active List Reconciliation

- When both a duplicate-candidate preview and direct patient endpoints provide clinical lists, the patient active-list endpoints are authoritative.
- Identify keys present in the patient endpoints that are missing from the duplicate preview; report those as `_added_from_active_endpoints`.

#### Evidence Selection

- Include document IDs that are final-status and relevant to the clinical workflow (identity documents, external continuity-of-care documents, office notes, echocardiograms, imaging reports).
- Exclude document types that are not clinically relevant to the packet (internal administrative forms, billing records, superseded versions).
- Include audit-log IDs that substantiate merge or referral decisions.
- Exclude unrelated audit events.

#### Distractor Exclusion

- When the answer template includes `excluded_distractors` sections, identify records that are inactive, entered-in-error, or from unrelated clinical contexts and place them there instead of the main evidence arrays.

### 5. Assess Readiness

Determine packet readiness by checking these dimensions:

- **Documents**: Are all required documents (echo, office note, imaging) received and in final status?
- **Allergies**: Are allergy records complete, documented, and non-conflicting?
- **Authorization**: Is the referral/service-request authorization approved, pending, denied, or missing?
- **Disclosure**: Is the applicable disclosure in `permitted` status?
- **Provider**: Has the receiving/specialist provider been resolved from the directory?
- **Codes**: Are all diagnosis codes valid and chapter-aligned?

Map findings to readiness values defined in the template (`ready`, `ready_with_review_note`, `blocked`, `hold_for_authorization`, `hold_for_missing_documents`, `hold_for_clinical_clarification`, `not_ready`). List specific blocking-issue codes when the template provides an enum for them.

### 6. Build Follow-Up Queues and Action Plans (Audit Tasks)

For batch-audit tasks, construct follow-up queues:

- **Authorization missing**: Referrals with no authorization record.
- **Authorization pending**: Referrals awaiting authorization decision.
- **Records request**: Referrals missing required office-note documents.
- **Imaging follow-up**: Referrals missing or pending imaging.

Assign to tiers:
- **Tier 1 (immediate)**: Urgent coding errors or duplicate blockers requiring same-day resolution.
- **Tier 2 (short-term)**: Routine coding, authorization, or document gaps.
- **Tier 3 (administrative)**: Administrative document completion.

### 7. Format the Output

- Return **only** the normalized JSON object. No explanatory prose, narrative text, or markdown fences outside the JSON.
- Every top-level key from the answer template must be present.
- Use `null` when a value is genuinely absent; do not omit keys.
- Dates in `YYYY-MM-DD` format.
- Booleans as `true`/`false`, never as strings.
- Enums: use exactly the string values defined in the template.

### 8. Apply Ordering Rules

- Arrays with set semantics (conditions, medications, allergies, match signals, conflict signals): sort alphabetically ascending.
- Arrays of referral objects: sort by `referral_id` ascending.
- Arrays of encounter objects: sort newest-to-oldest by date.
- ID-only arrays: sort strings ascending.
- Duplicate groups: sort by `group_id` ascending; referral IDs within each group sorted ascending.
- Risk-flag evidence arrays: sort ascending by `risk_flag`.
- Follow the template's explicit `ordering_rules` or `ordering` notes when they differ from these defaults.

## Common Pitfalls

- **Stale records**: Always filter to active or final status unless the task explicitly includes historical data.
- **Unrelated distractors**: Do not include documents, audits, encounters, or clinical items that belong to patients or episodes outside the task scope.
- **Template drift**: The answer template is the contract; every key, type, and enum value must match. Do not invent keys or omit required ones.
- **Narrative output**: Never wrap the JSON in markdown code fences or precede it with explanatory text when the prompt says "Return only normalized JSON."
- **Sorting**: Even when the template says "evaluators normalize order," always emit arrays in the canonical sort order described in the template or these rules.
- **ID stability**: Use stable IDs from the API (patient_id, referral_id, document_id, audit_id, encounter_id, immunization_id, disclosure_id, candidate_id, provider_id) — never generate synthetic IDs.
