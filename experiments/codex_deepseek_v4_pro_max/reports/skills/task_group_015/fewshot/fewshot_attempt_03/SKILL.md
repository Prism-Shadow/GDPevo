 # EHR Healthcare Data Quality & Referral Governance Skill

This skill covers completing normalized JSON packets for EHR healthcare-data
governance tasks — duplicate-chart merge readiness, specialty referral
coordination, care-transition handoffs, duplicate-review / ServiceRequest
validation, and batch referral audits.  Every task follows the same core
loop: read the staged task input, call a read-only FHIR-flavored EHR API,
normalize the evidence, and emit a single JSON object that conforms to the
supplied answer template.

## API Environment

All tasks target a shared EHR API.  The base URL is injected via the
`<TASK_ENV_BASE_URL>` (or equivalently `GDPEVO_ENV_BASE_URL`) placeholder.
No authentication is required — all listed endpoints accept unauthenticated
GET requests.

### Endpoint Catalog

| Endpoint | Notes |
|---|---|
| `GET /api/patients` | Search: `q`, `family`, `given`, `dob`, `insurance_id` |
| `GET /api/patients/{patient_id}` | Single patient detail |
| `GET /api/patients/{patient_id}/conditions` | Query: `status` |
| `GET /api/patients/{patient_id}/medications` | Query: `status` |
| `GET /api/patients/{patient_id}/allergies` | Query: `status` |
| `GET /api/patients/{patient_id}/encounters` | Query: `status`, `limit` |
| `GET /api/patients/{patient_id}/immunizations` | |
| `GET /api/patients/{patient_id}/documents` | |
| `GET /api/patients/{patient_id}/service-requests` | |
| `GET /api/patients/{patient_id}/disclosures` | |
| `GET /api/audit-logs` | Query: `patient_id`, `event`, `date_from`, `date_to` |
| `GET /api/duplicates/candidates` | |
| `GET /api/duplicates/{candidate_id}` | Single duplicate-candidate detail |
| `GET /api/referrals` | Search: `batch`, `urgency`, `patient`, `status` |
| `GET /api/referrals/{referral_id}` | Single referral detail |
| `GET /api/icd10` | |
| `GET /api/icd10/{code}` | Single ICD-10 code detail |
| `GET /api/providers` | |
| `GET /api/providers/{provider_id}` | Single provider detail |
| `GET /api/service-codes` | |
| `GET /api/service-codes/{code}` | Single service-code detail |

Always replace `{patient_id}`, `{referral_id}`, `{candidate_id}`, `{code}`,
and `{provider_id}` with runtime IDs extracted from the staged input or from
prior API responses.

## Task File Layout

A task directory contains:
- `prompt.txt` — natural-language task description with the specific case
  identifiers and the `<TASK_ENV_BASE_URL>` placeholder.
- `payloads/answer_template.json` — the JSON schema that the output must
  satisfy.  It declares the top-level required keys, field types, enum
  literals, array ordering / set-semantics rules, and whether `null` is
  permitted.
- `payloads/` may contain additional staged input files (e.g. a merge-packet
  request JSON, a referral batch manifest, or a ServiceRequest spec).  Read
  every file in `payloads/` — they carry runtime identifiers and constraints
  that the prompt references.

## General Workflow

### 1.  Ingest the task

1. Read `prompt.txt`.  Replace `<TASK_ENV_BASE_URL>` with the runtime base URL
   (read from `environment_access.md` or injected by the harness).
2. Read every file under `payloads/`.  Note the `task_id` required by the
   template, the case identifiers (patient IDs, candidate IDs, referral IDs,
   provider IDs, etc.), and any other structured input.
3. Study `answer_template.json` carefully.  Identify:
   - All required top-level keys.
   - The exact enum literals allowed for every field.
   - Whether arrays are treated as **sets** (order does not matter to the
     evaluator) or **ordered** (a specific sort order is required).
   - Which fields permit `null`.
   - Date-format expectations (always `YYYY-MM-DD`).

### 2.  Gather evidence from the API

Use `curl` (or an equivalent HTTP client) to call the EHR API.  The
evidence-gathering order matters — later steps often depend on IDs discovered
in earlier responses.

**Standard evidence-collection order:**

1. **Patient demographics** — `GET /api/patients/{patient_id}` for every
   patient ID in the case.  Also search by name/DOB/insurance when needed.
2. **Active clinical lists** — `GET /api/patients/{patient_id}/conditions`,
   `…/medications`, `…/allergies`.  Use `?status=active` to fetch only
   active records.  Parse the `normalized_key` field from each record.
3. **Encounters** — `GET /api/patients/{patient_id}/encounters`.  Filter by
   `status` and `limit` as instructed.  Apply task-specific windowing rules
   (e.g. "last 90 days", "newest 4 signed encounters").
4. **Duplicate candidates** — `GET /api/duplicates/{candidate_id}`.  Inspect
   `match_signals`, `conflict_signals`, `primary_patient_id`,
   `possible_duplicate_patient_id`, and the `candidate_status`.
5. **Referrals** — `GET /api/referrals/{referral_id}` or
   `GET /api/referrals?batch=…`.  Collect diagnosis codes, authorization
   status, provider assignments, urgency, and narrative fields.
6. **ICD-10 validation** — `GET /api/icd10/{code}` for every diagnosis code.
   Record the `chapter` and `description`.  Use these to flag
   out-of-range-chapter, narrative-mismatch, laterality-mismatch, or
   unknown-code issues.
7. **Provider directory** — `GET /api/providers/{provider_id}` for every
   provider referenced in the case.  Collect name, role, service_line,
   facility, phone, and fax.
8. **Supporting evidence** — Documents (`GET …/documents`), audit logs
   (`GET /api/audit-logs?patient_id=…`), immunizations
   (`GET …/immunizations`), disclosures (`GET …/disclosures`),
   service-requests (`GET …/service-requests`), and service-codes
   (`GET /api/service-codes/{code}`).  Collect only when the template
   explicitly requires them.

### 3.  Synthesize and normalize

Produce a single JSON object whose top-level keys match the
`top_level_required_keys` (or `required_top_level_keys`) listed in the
answer template.  Follow these rules:

- **Use exact enum values** — never invent or approximate.  If the template
  says `"disposition": "enum: ready_to_merge | needs_review | do_not_merge"`,
  output one of those three strings literally.
- **Sort set-semantics arrays alphabetically** (ascending) unless the
  template explicitly states a different order.  Sort by the key the
  evaluator uses (e.g. `code`, `referral_id`, `normalized_key`).
- **Ordered arrays** must obey the stated sort rule (e.g. newest-to-oldest
  by date, ascending by `referral_id`, ascending by `risk_flag`).
- **Dates** — always `YYYY-MM-DD` strings.
- **Null fields** — when a field is `[string, null]` and no value exists,
  emit `null`, not `""`.
- **Booleans** — use JSON `true` / `false`, never strings.
- **Empty arrays** — emit `[]`, never `null`, for array-typed fields.

### 4.  Distinguish evidence from distractors

Many tasks include **distractor records** — stale encounters, inactive
conditions, unrelated documents, or audit-log entries from other patients.
Apply these filtering heuristics:

- **Active vs. inactive** — only active-status conditions, medications, and
  allergies belong in clinical unions.  Inactive records go to
  `excluded_*` arrays.
- **Time windows** — encounters outside the task's stated window (e.g.
  > 90 days or not in the "last 4 signed") are excluded.
- **Relevance** — documents and audit logs that do not reference either
  patient in a merge pair, or that fall outside the referral's scope,
  are excluded.
- **Duplicate shells** — when a duplicate candidate record itself carries
  clinical data, cross-check with the authoritative patient endpoints;
  items found only via the duplicate preview but absent from the patient
  endpoints are flagged as `added_from_active_endpoints`.

### 5.  Write the answer

Emit the JSON object to the output file specified by the task harness (often
`answer.json`).  Use compact or pretty-printed JSON — the evaluator accepts
both.  Do **not** include explanatory prose, Markdown fences, or narrative
outside the JSON object.

## Task-Type Specific Guidance

### Merge Readiness Packet (duplicate-chart)

1. Fetch the duplicate candidate and both patient records.
2. Determine `merge.target_patient_id` (the canonical/active record) and
   `merge.source_patient_id` (the duplicate shell).
3. Collect active condition/medication/allergy keys from both patients;
   compute the sorted union.
4. Cross-reference the duplicate candidate's `match_signals` and
   `conflict_signals` against the demographic data from the patient
   endpoints.
5. Select evidence documents that establish identity or external continuity
   (e.g. shared imaging reports).  Exclude internal chart summaries.
6. Select audit-log entries that reference the merge or the duplicate
   detection event.
7. Identify the specialist provider associated with any external
   continuity document, and the primary-care provider for the target
   patient.

### Referral Coordination Packet

1. Fetch the referral, patient, and active clinical lists.
2. Validate every diagnosis code against `/api/icd10/{code}`.
3. Assign `referral_relevant` true/false to each diagnosis based on whether
   it matches the referral's service line and narrative.
4. Reconcile allergies between the referral form and the patient's active
   allergy list.
5. Select the most recent encounter that matches the referral narrative
   (look for matching diagnosis codes and care-plan tags).
6. Identify required documents (echo, office note) and check their status
   (`final`, `preliminary`, `missing`).
7. Determine authorization and overall readiness by composing
   authorization status, referral status, document availability, and
   allergy completeness.
8. Highlight medications relevant to the referral's service line.
9. Populate `referral_letter_fields` by matching the evidence against the
   enum choices provided in the template.

### Care Transition Packet

1. Fetch the patient, recipient provider, and active clinical lists.
2. Collect encounters; select the N most recent signed encounters within the
   surgical-handoff window.  Exclude stale or irrelevant encounters.
3. Fetch the latest immunization and the relevant disclosure.
4. Evaluate risk flags by cross-referencing active conditions, medications,
   and encounters against the allowed `risk_flags` enum.
5. For each risk flag, build an evidence object citing the condition keys,
   medication keys, and encounter IDs that support it.
6. Determine `packet_readiness` — if risk flags are present, the status is
   `ready_with_risk_flags` (but still `ready_to_send: true` unless a
   blocking issue exists).

### Duplicate Review & ServiceRequest Validation

1. Fetch the duplicate candidate detail.
2. Classify the candidate status and merge decision from the candidate's own
   signals, not from template guessing.
3. Fetch the ServiceRequest; validate each field against the API evidence:
   - Check `service_code` against `/api/service-codes/{code}`.
   - Check each `reason_code` against `/api/icd10/{code}`.
   - Verify the performer's `service_line` matches the provider directory.
4. Evaluate SBAR coverage: check the ServiceRequest for presence of
   situation, background, assessment, and recommendation sections.

### Batch Referral Audit

1. Fetch all referrals in the batch via `GET /api/referrals?batch=…`.
2. For each referral, validate the diagnosis code against ICD-10:
   - `out_of_range_chapter` — the ICD-10 chapter does not match the
     expected service-line chapter (e.g. Injury or Respiratory instead of
     Musculoskeletal for orthopedics).
   - `unknown_code` — a code not found in the ICD-10 directory.
3. Check for laterality and narrative mismatches by comparing the referral's
   `diagnosis_narrative` with the ICD-10 code's description and expected
   terms.
4. Detect duplicate groups — referrals sharing the same patient and the same
   clinical scenario (not separate clinical reviews).
5. Detect insurance anomalies — different patients sharing the same
   insurance ID.
6. Populate follow-up queues by scanning authorization and document status
   across all referrals.
7. Assign each referral to Tier 1 (urgent coding/duplicate blockers),
   Tier 2 (routine coding/auth/document blockers), or
   Tier 3 (administrative document completion) based on the issues found.
8. Compute `summary_counts` by counting the rows in each result array.
   `validated_ready_no_follow_up_count` = total rows minus rows assigned to
   any follow-up queue or action tier.

## Common Pitfalls

- **Hard-coding answer values** — never copy a specific patient ID,
  provider ID, or diagnosis code from a training example into the answer.
  Every value must come from the API evidence for the current task.
- **Using the wrong enum casing** — `ready_to_merge` is not `ReadyToMerge`.
  Match the template's enum literals character-for-character.
- **Omitting empty arrays** — if a field is typed `array`, emit `[]` when
  there are no items, not `null` or a missing key.
- **Including inactive / stale records in active unions** — always filter
  by `status=active` for clinical union fields.
- **Forgetting to sort** — every array with set semantics must be sorted
  alphabetically; every array with ordering rules must obey them.
- **Mixing up primary / source in merge tasks** — the canonical target is
  the patient with the active, authoritative record; the source is the
  shell marked as a duplicate.

## Example: Skeleton Execution

```
# 1. Ingest
PROMPT=$(cat input/prompt.txt)
TEMPLATE=$(cat input/payloads/answer_template.json)
# extract IDs: CANDIDATE_ID, PATIENT_IDS, etc.

# 2. Gather evidence
BASE="${TASK_ENV_BASE_URL}"
curl -s "${BASE}/api/patients/${PATIENT_A}"
curl -s "${BASE}/api/patients/${PATIENT_B}"
curl -s "${BASE}/api/patients/${PATIENT_A}/conditions?status=active"
curl -s "${BASE}/api/duplicates/${CANDIDATE_ID}"
# ... continue for all required evidence

# 3. Synthesize — build the JSON object in code,
#    applying sorting, enum matching, and distractor filtering.

# 4. Emit answer
echo "$JSON" > answer.json
```

This skill applies to any EHR healthcare-data governance task that follows
the "read prompt + template → query API → normalize → emit JSON" pattern.
Always defer to the task-specific `prompt.txt` and `answer_template.json`
for exact field requirements and enum values.
