# EHR Quality-Governance Skill

## Purpose

Complete EHR quality-governance tasks — duplicate-chart merge readiness packets, referral coordination, care transition packets, duplicate review with ServiceRequest validation, and batch referral audits — by querying a read-only EHR REST API, cross-referencing clinical records, validating codes, and producing normalized JSON output.

## When to Use

Invoke this skill when the task involves:
- A read-only EHR REST API with endpoints for patients, conditions, medications, allergies, encounters, documents, providers, ICD-10 lookup, referrals, duplicates, audit logs, immunizations, disclosures, service requests, and service codes
- Producing a normalized JSON object that conforms to a provided answer template
- Clinical data reconciliation across multiple record sources
- ICD-10 code validation against a directory
- Quality-governance decisions (merge/disposition, referral readiness, audit action plans)

## Workflow

### Phase 1 — Orient

1. Read the task prompt (`input/prompt.txt`) to identify:
   - **Task type**: merge packet, referral coordination, care transition, duplicate review + SR, or batch audit
   - **Entity IDs**: patient IDs, referral IDs, candidate IDs, provider IDs, batch IDs
   - **The answer template path** (`input/payloads/answer_template.json`)
2. Read the answer template to understand the required output shape, field types, enums, and ordering rules.
3. Read any additional payload files (e.g., `merge_packet_request.json`) for extra context or entity lists.
4. Read `environment_access.md` for the base URL and allowed endpoints.

### Phase 2 — Gather Evidence

Query the EHR API systematically. Start broad, then narrow:

- **Patient identity**: `GET /api/patients/{patient_id}` for demographics, MRN, DOB, display name, provider links.
- **Active clinical lists**: `GET /api/patients/{patient_id}/conditions`, `/medications`, `/allergies`. Filter to active records. Extract `normalized_key` values.
- **Encounters**: `GET /api/patients/{patient_id}/encounters`. Sort by date; filter by relevance window and signed status.
- **Documents**: `GET /api/patients/{patient_id}/documents`. Filter to final-status documents; classify by type (echo, office note, chart summary, etc.).
- **Audit logs**: `GET /api/audit-logs` (may accept query params). Look for entries referencing the candidate or patient IDs.
- **Duplicate candidates**: `GET /api/duplicates/{candidate_id}` for match/conflict signals, status.
- **Referrals**: `GET /api/referrals/{referral_id}` or `GET /api/referrals` for search.
- **Providers**: `GET /api/providers/{provider_id}` for name, role, facility, phone, fax, service line.
- **ICD-10**: `GET /api/icd10/{code}` for chapter, description, laterality.
- **Service requests**: `GET /api/patients/{patient_id}/service-requests` or direct lookup.
- **Immunizations**: `GET /api/patients/{patient_id}/immunizations` — pick latest by date.
- **Disclosures**: `GET /api/patients/{patient_id}/disclosures` — match by recipient provider and purpose.

Use the API exclusively through `<TASK_ENV_BASE_URL>` as the base. All endpoints are GET-only and unauthenticated.

### Phase 3 — Reconcile and Validate

**When data appears in multiple sources**, prefer the patient-level active-list endpoints over embedded previews (e.g., duplicate candidate previews). The authoritatively sourced data is always from the dedicated patient endpoints. Track what is *added* vs. what the preview already contained.

**For ICD-10 code validation:**
- Look up each code via `GET /api/icd10/{code}`.
- If the endpoint returns a result, the code is valid; check its `chapter` field.
- Compare the chapter against the expected service line chapter (e.g., musculoskeletal codes for orthopedics).
- Check for laterality mismatches: compare the code's laterality with the diagnosis narrative.
- Check for narrative mismatches: compare the code's description with the stated diagnosis narrative.
- Flag as `out_of_range_chapter` when the code's actual chapter doesn't match the expected service chapter; flag as `unknown_code` when the ICD-10 lookup returns nothing.

**For duplicate candidate evaluation:**
- Read match signals and conflict signals from the duplicate candidate endpoint.
- Cross-reference with patient demographics: compare DOB, insurance, phone, address, name, sex between the two patients.
- If the duplicate candidate endpoint already designates a target and source, validate that choice against the evidence.
- Clinical key unions: collect active condition/medication/allergy `normalized_key` values from BOTH patients, deduplicate, and sort alphabetically.
- Document selection: include only identity-relevant or external-continuity documents; exclude internal chart summaries.
- Audit selection: include only audit entries that reference the merge candidate or patient pair.

**For referral coordination:**
- Identify the primary diagnosis code from the referral's reason/intake.
- Validate it against ICD-10; classify as `valid_matches_narrative`, `valid_but_narrative_mismatch`, `invalid_code`, or `wrong_service_chapter`.
- Collect supporting codes from the same referral.
- Check allergy readiness from the patient's allergy list; classify as `complete_documented`, `incomplete_needs_clarification`, `no_known_allergies`, or `conflicting_allergy_records`.
- Identify the most recent relevant encounter (by date) that matches the referral's clinical context.
- Evaluate document evidence: check for echo, office note, and other required documents; track what's missing.
- Assess authorization: status (`approved`/`pending`/`denied`/`not_required`/`unknown`), referral status (`open`/`closed`/`cancelled`/`draft`), urgency.
- Identify medication highlights relevant to the service line.

**For care transition packets:**
- Select the 4 most recent encounters relevant to the surgical/service handoff, newest first.
- Apply a handoff window rule (e.g., ~90 days for orthopedic surgery). Exclude stale encounters outside the window and unrelated visit types.
- Identify the latest immunization by date.
- Match the disclosure record by recipient provider ID and purpose.
- Detect risk flags by mapping active conditions and medications to known perioperative risk categories (e.g., insulin-dependent diabetes → `perioperative_glucose_plan_needed`, memory loss → `cognitive_memory_loss`, latex allergy → `latex_allergy`). Each risk flag must be backed by evidence: condition keys, medication keys, and/or encounter IDs.

**For batch referral audits:**
- Iterate over every referral in the batch.
- Validate each diagnosis code against ICD-10 for:
  - Chapter out of range for the service line (codes with chapters other than the expected one).
  - Laterality mismatch (code laterality doesn't match narrative).
  - Narrative mismatch (code description doesn't match stated narrative).
- Detect duplicate groups: same patient with multiple referrals for the same clinical issue → `same_patient_resubmission` type.
- Detect insurance anomalies: different patients sharing the same insurance ID.
- Build follow-up queues for: missing authorization, pending authorization, missing records (office notes), pending imaging.
- Assign tiered action plans:
  - **Tier 1 (immediate)**: duplicate blockers and urgent coding issues.
  - **Tier 2 (short-term)**: routine coding, authorization, or document blockers.
  - **Tier 3 (administrative)**: document completion tasks.
- Compute summary counts that add up correctly across all categories.

### Phase 4 — Produce Output

Build the JSON output by populating every field in the answer template:

1. **Follow the template exactly**: every required key must be present. Use the enum values as specified.
2. **Sort set arrays alphabetically** by default, unless the template explicitly says otherwise (e.g., encounters ordered by date, referral objects by referral_id).
3. **Use stable IDs**: never invent IDs; only use values that appear in API responses.
4. **Use `null` where the template allows it** and the data is genuinely absent (not just empty).
5. **Return only the JSON object** — no explanatory prose, no markdown fences, no narrative text.
6. **Dates use YYYY-MM-DD format** from API response fields.

## API Reference

All endpoints are read-only GET requests against `<TASK_ENV_BASE_URL>`. No authentication required.

| Endpoint | Use |
|---|---|
| `GET /api/patients` | List/search patients |
| `GET /api/patients/{id}` | Patient demographics, MRN, DOB, name, provider links |
| `GET /api/patients/{id}/conditions` | Active/inactive conditions with `normalized_key`, ICD-10 `code`, status |
| `GET /api/patients/{id}/medications` | Active/inactive medications with `normalized_key`, dose, route, frequency |
| `GET /api/patients/{id}/allergies` | Allergies with `normalized_key`, allergen, reaction, severity, status |
| `GET /api/patients/{id}/encounters` | Encounters with date, type, signed_status, diagnosis codes, provider |
| `GET /api/patients/{id}/documents` | Documents with type, status, date |
| `GET /api/patients/{id}/immunizations` | Immunizations with date, vaccine name |
| `GET /api/patients/{id}/disclosures` | Disclosure records with status, purpose, recipient |
| `GET /api/patients/{id}/service-requests` | ServiceRequests with status, intent, priority, codes, provider |
| `GET /api/audit-logs` | Audit log entries |
| `GET /api/duplicates/candidates` | List duplicate candidates |
| `GET /api/duplicates/{id}` | Duplicate candidate detail with match/conflict signals, target/source |
| `GET /api/referrals` | Search/list referrals |
| `GET /api/referrals/{id}` | Referral detail with diagnosis codes, narrative, status, patient, batch |
| `GET /api/icd10` | List ICD-10 codes |
| `GET /api/icd10/{code}` | Code detail: description, chapter, laterality |
| `GET /api/providers` | List providers |
| `GET /api/providers/{id}` | Provider detail: name, role, facility, phone, fax, service_line |
| `GET /api/service-codes` | List service codes |
| `GET /api/service-codes/{code}` | Service code validity and detail |

## Key Conventions

### Normalized Keys

Clinical records carry a `normalized_key` field — a stable, lowercase, snake_case identifier (e.g., `hypertension`, `diabetes_type_2`, `right_knee_oa`). Always use these keys for set operations, comparisons, and output arrays. They are the canonical identifiers for conditions, medications, and allergies across the system.

### Active vs. Inactive Records

Every condition, medication, and allergy has a `status` field. Only records with an active status belong in active-key arrays. Inactive, resolved, or entered-in-error records go into excluded/distractor arrays if the template asks for them.

### Enum Conventions

Templates use enums extensively. Match the exact string value from the template — do not paraphrase, abbreviate, or invent values. If the template lists `ready_to_merge` as a disposition, use exactly that string.

### Sorting Rules

- Arrays described as "sets" or with `set_semantics: true`: sort alphabetically/numerically ascending by the string value.
- Arrays with explicit ordering (e.g., encounters newest-first, referrals by referral_id): follow that ordering.
- When in doubt between two conventions, alphabetical ascending is the safe default.

### Reconciliation Authority

When the same clinical data appears in both a composite record (duplicate candidate preview, referral intake) and a patient-level endpoint, the patient-level endpoint is authoritative. Report any keys found in the patient endpoints that were missing from the composite.

### Provider Identification

Providers are referenced by `provider_id` across the API. When a task names a specific provider (e.g., `PRV-ORTHO-XXX`), look them up via `GET /api/providers/{id}` to get their full profile. When a patient has a linked primary care provider, look them up the same way. For specialist providers connected to documents or referrals, trace the document/referral's provider reference.

### Evidence Traceability

Every clinical claim in the output must be traceable to an API response. Risk flags map to specific condition keys, medication keys, or encounter IDs. Document evidence cites specific document IDs. Audit findings cite specific audit IDs. Never fabricate evidence identifiers.
