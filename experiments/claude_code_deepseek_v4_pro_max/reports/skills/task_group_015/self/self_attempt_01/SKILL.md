# EHR Quality Governance Skill

## Purpose

Produce a normalized, evidence-based JSON packet from a read-only EHR FHIR-style REST API. The skill covers duplicate-chart merge readiness, referral coordination, care-transition handoff, ServiceRequest quality validation, and batch audit tasks.

## When to Use

Invoke this skill when the task involves:
- An EHR quality-governance or referral-coordination workflow
- A `prompt.txt` describing case objects (patients, duplicate candidates, referrals, ServiceRequests, audit batches)
- An `input/payloads/answer_template.json` specifying the required output JSON shape
- An `environment_access.md` listing the available API base URL and endpoints

## Operating Rules

### 1. Environment Bootstrap

1. Read `environment_access.md` to discover `base_url` and the `allowed_endpoints` list.
2. Resolve `<TASK_ENV_BASE_URL>` in `prompt.txt` to `base_url`.
3. All API calls are **GET only**, no authentication, no request body.

### 2. Read the Answer Template First

1. Read `input/payloads/answer_template.json` **before** making any API call.
2. Understand every required top-level key, nested object shape, enum domain, and array ordering rule.
3. Note which arrays carry **set semantics** (order-independent; evaluation normalizes) and which have explicit ordering rules (newest-to-oldest, ascending by key, etc.).

### 3. Fetch Primary Entities First

1. Start with the case objects named in `prompt.txt` — the patient, referral, duplicate candidate, ServiceRequest, or batch.
2. Use the relevant detail endpoint to fetch the primary record:
   - `/api/patients/{patient_id}` for patients
   - `/api/duplicates/{candidate_id}` for duplicate candidates
   - `/api/referrals/{referral_id}` for referrals
   - `/api/patients/{patient_id}/service-requests` for ServiceRequests
3. From the primary record, extract all foreign-key references (provider IDs, code references, document IDs, audit IDs) that will need follow-up fetches.

### 4. Drill Into Related Clinical Sub-Resources

For each patient involved, fetch the active clinical lists:
- `/api/patients/{patient_id}/conditions`
- `/api/patients/{patient_id}/medications`
- `/api/patients/{patient_id}/allergies`
- `/api/patients/{patient_id}/encounters`
- `/api/patients/{patient_id}/immunizations` (when relevant)
- `/api/patients/{patient_id}/documents` (when relevant)
- `/api/patients/{patient_id}/disclosures` (when relevant)

### 5. Validate Codes Against Lookup Endpoints

1. For every ICD-10 code encountered, validate against `/api/icd10/{code}`:
   - Confirm the code exists (not invalid/unknown).
   - Record its chapter.
   - Check whether the chapter matches the expected service line (e.g., Musculoskeletal for orthopedics).
2. For every service code encountered, validate against `/api/service-codes/{code}`.
3. Mark codes as valid/invalid and note chapter mismatches.

### 6. Cross-Reference Between Data Sources

When the same information appears in multiple sources (e.g., duplicate-candidate preview vs. patient active-list endpoints):

1. Treat the **patient active-list endpoints** as authoritative over duplicate-candidate previews for clinical data.
2. Identify keys present in the authoritative source but missing from the secondary source.
3. Reconcile identity signals (demographics, phone, address, insurance) between candidate pairs.
4. When a duplicate candidate provides match/conflict signals, verify them against the raw patient records rather than trusting the candidate summary blindly.

### 7. Separate Active from Inactive / Stale Records

1. Filter clinical lists to **active** records only unless the template explicitly asks for a broader set.
2. Identify **stale encounters** — those outside the relevant clinical window or unrelated to the task's service line.
3. Exclude documents, audit entries, and encounters that are unrelated to the task's clinical context.
4. Document excluded items in the output where the template provides `excluded_distractors` or equivalent fields; otherwise exclude silently.

### 8. Classify Readiness

For every packet, produce a structured readiness determination:
- **ready / ready_to_send** — all required evidence present, codes valid, no blockers.
- **ready_with_review_note / ready_with_risk_flags** — can proceed but carries noted concerns.
- **hold / not_ready / blocked** — missing required evidence, invalid codes, or unresolved conflicts.
- Identify specific **blocking issue codes** from the template's allowed values.

### 9. Cite Evidence

1. Every decision component (merge disposition, diagnosis selection, risk flag, readiness status) must reference specific evidence IDs:
   - `document_ids` for documents
   - `audit_ids` for audit log entries
   - `encounter_ids` for encounters
   - `condition_keys`, `medication_keys`, `allergy_keys` for clinical data
2. Do not fabricate IDs — only use values returned by the API.

### 10. Look Up Provider Directory Details

When the output requires provider contact information:
1. Fetch `/api/providers/{provider_id}` for each provider referenced.
2. Extract: `provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, `fax`.
3. Match providers to the correct role (specialist, primary care, receiving, requesting, performing).

### 11. Output Formatting Rules

1. Return **only** the JSON object — no markdown fences, no explanatory prose, no narrative text.
2. Dates in `YYYY-MM-DD` format.
3. Arrays with **set semantics**: sort alphabetically by the natural key (code, key, ID) unless the template explicitly overrides ordering.
4. Arrays with **explicit ordering rules**: follow the template's instruction (newest-to-oldest by date, ascending by referral_id, etc.).
5. Enum fields must use **exactly** the allowed values from the template — no synonyms, no abbreviations.
6. Use `null` (not `"null"`, not omitted) for nullable fields when data is genuinely absent.
7. Use `boolean` values (`true`/`false`), not strings.

### 12. Task-Type-Specific Patterns

#### Duplicate Merge Readiness
- Determine canonical target (retained record) and source (retired record).
- Compute clinical key unions across both patients' active lists.
- Classify merge disposition from identity match/conflict signals.
- Include specialist and primary care provider contacts.

#### Referral Coordination
- Reconcile the referral's diagnosis codes with the patient's active conditions and ICD-10 directory.
- Determine allergy readiness and whether the patient is clear for the referral letter.
- Identify the single most relevant recent encounter.
- Map required documents (echo, office note) to actual document records.
- Select normalized referral-letter field values from the template's enum choices.

#### Care Transition
- Identify patient, recipient provider, and their details.
- Select exactly the four most recent relevant handoff encounters for the target service line.
- Exclude stale or unrelated encounters; document the selection rule and excluded IDs.
- Include the latest immunization, applicable disclosure, and risk flags with supporting evidence.

#### Quality Governance (Duplicate + ServiceRequest)
- Validate duplicate-candidate outcome (confirmed_duplicate / needs_review / not_duplicate).
- Validate ServiceRequest fields: status, intent, priority, service code validity, reason code validity against ICD-10.
- Assess SBAR (Situation, Background, Assessment, Recommendation) coverage completeness.

#### Batch Audit
- Scan every referral in the batch against ICD-10 chapter expectations.
- Detect laterality mismatches (left vs. right) and narrative-code mismatches.
- Group duplicate referrals (same patient, same clinical context).
- Build follow-up queues: authorization_missing, authorization_pending, records_request, imaging_follow_up.
- Assign Tier 1/2/3 action plans based on severity and urgency.
- Compute summary counts for every category.

### 13. Error Handling

1. If an API endpoint returns a 404, treat the resource as absent — use `null` for nullable fields, omit from arrays, and note the absence in readiness/blocking issues.
2. If an API endpoint returns a 5xx error, retry once after a short delay; if it persists, note the endpoint as unavailable and mark the packet as `not_ready` with an appropriate blocking code.
3. If the answer template references fields not present in any API response, use `null` for nullable fields and `[]` for array fields — never fabricate data.

### 14. Verification Checklist

Before returning the JSON, confirm:
- [ ] Every required top-level key from the answer template is present.
- [ ] All enum values match the template's allowed-value lists exactly.
- [ ] All arrays with set semantics are sorted alphabetically.
- [ ] All dates are in YYYY-MM-DD format.
- [ ] No narrative prose, markdown, or commentary is included.
- [ ] Every cited ID (document, audit, encounter, provider) was actually returned by the API.
- [ ] All ICD-10 and service codes have been validated against their lookup endpoints.
- [ ] Clinical lists are filtered to active records unless otherwise specified.
- [ ] Blocking issues and readiness status are consistent with the evidence.
