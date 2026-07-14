# EHR Quality & Data Governance — Reusable Skill

## Environment

Use the remote API at the URL given in environment_access.md:
- `GET /health` — connectivity check
- `GET /api` — available endpoints index
- All endpoints are read-only `GET`.

## API Endpoints Reference

### Patient Data
| Endpoint | Returns |
|---|---|
| `GET /api/patients` | Array of all patient summary objects |
| `GET /api/patients/{patient_id}` | Full patient object with inline clinical lists, encounters, immunizations, disclosures, documents |
| `GET /api/patients/{patient_id}/problems` | Array of problem objects |
| `GET /api/patients/{patient_id}/medications` | Array of medication objects |
| `GET /api/patients/{patient_id}/allergies` | Array of allergy objects |
| `GET /api/patients/{patient_id}/encounters` | Array of encounter objects |
| `GET /api/patients/{patient_id}/immunizations` | Array of immunization objects |
| `GET /api/patients/{patient_id}/disclosures` | Array of disclosure objects |
| `GET /api/patients/{patient_id}/documents` | Array of document objects |

**Note:** The inline lists on the patient object (e.g., `patient.allergies`) contain the same data as the dedicated sub-resource endpoints. Either source is valid; prefer the sub-resource endpoint when you need only one list, or use the patient object when you need everything at once.

### Patient Object Fields
```
patient_id, first_name, last_name, dob (YYYY-MM-DD), address, phone, email,
enterprise_mrn, primary_provider_id,
problems[], medications[], allergies[], encounters[], immunizations[], disclosures[], documents[]
```

### Clinical Item Fields
**Problem:** `id`, `code` (ICD-10), `label`, `status` ("active" | "inactive")
**Medication:** `id`, `code` (RXN-*), `label`, `dose`, `status` ("active" | "inactive")
**Allergy:** `id`, `code` (ALG-*), `label`, `reaction`, `severity`, `status` ("active" | "inactive")
**Encounter:** `id`, `date` (YYYY-MM-DD), `diagnoses[]` (array of ICD-10 codes), `care_plan`
**Immunization:** `id`, `name`, `date` (YYYY-MM-DD)
**Disclosure:** `id`, `recipient`, `purpose`, `date`, `status` ("active" | "inactive")

### Quality Records
| Endpoint | Returns |
|---|---|
| `GET /api/duplicate-candidates` | Array of all duplicate candidates |
| `GET /api/duplicate-candidates/{candidate_id}` | Single duplicate candidate with patient_ids, match_reasons, risk_flags, suggested_action |
| `GET /api/referrals` | Array of **all** referral objects across all batches |
| `GET /api/referral-batches` | Array of batch summary objects |
| `GET /api/referral-batches/{batch_id}` | Batch metadata + `referrals[]` array |
| `GET /api/handoff-packets` | Array of all handoff packets |
| `GET /api/handoff-packets/{packet_id}` | Single packet with included_sections[], receiving/sending provider, clinical fields |
| `GET /api/service-requests` | Array of all service requests |
| `GET /api/service-requests/{request_id}` | Single request with SBAR note_text, linked_encounter_ids, order fields |

**Important:** `GET /api/referrals/{referral_id}` returns 404. To look up a single referral, fetch `GET /api/referrals` and filter client-side by `referral_id`. The same applies to individual patient lookup from the referrals list — match by `patient_first_name` + `patient_last_name` + `patient_dob`.

### Codebook & Providers
| Endpoint | Returns |
|---|---|
| `GET /api/codebook/icd10` | Full ICD-10 codebook array |
| `GET /api/providers` | Array of provider objects |
| `GET /api/audit-log` | Array of all audit events |

**ICD-10 Code Fields:** `code`, `description`, `body_site`, `laterality` ("left" | "right" | "bilateral" | null), `chapter_prefix`, `in_musculoskeletal_tracking_range` (boolean)

**Provider Fields:** `provider_id`, `name`, `specialty`, `fax`

**Audit Event Fields:** `event_id`, `event_type`, `patient_ids[]`, `status`, `timestamp`, `user`

---

## Task Type 1: Duplicate Candidate Reconciliation

### Workflow
1. `GET /api/duplicate-candidates/{candidate_id}` → get patient_ids[] and match_reasons
2. For each patient_id, fetch the patient object and/or sub-resources
3. `GET /api/providers` → reference provider details
4. `GET /api/audit-log` → find audit events whose `patient_ids` match the candidate's patient_ids

### Business Rules

**Canonical Target Selection:**
- When both patients share the same name, DOB, and phone but have different enterprise MRNs, designate the patient with the lower/older MRN number (the "A" record) as canonical target.
- The canonical target is the surviving record; the other is the source to be merged.

**Merge Disposition:**
- `"MERGE_READY"` when the audit event status is `"ready_for_merge"` and there are no blocking risk flags.
- `"BLOCKED"` when risk flags exist or audit status indicates a conflict (e.g., `"blocked_address_conflict"`).
- Reason codes: `"STABLE_MRN_MATCH"` when MRNs differ but all other identifiers converge; `"FULL_MATCH"` when all identifiers including MRN match.

**Preserved Clinical Lists (the merge union):**
- Combine **active-only** items from **both** patient records.
- Deduplicate by code (problems), by id (medications), by label (allergies).
- Output fields:
  - `preserved_active_problem_codes`: string array of unique ICD-10 codes, sorted alphanumerically
  - `preserved_active_medication_ids`: string array of unique medication IDs, sorted alphanumerically
  - `preserved_active_allergy_labels`: string array of unique allergy labels, sorted alphabetically

**Excluded Patients:**
- If all patient_ids are included in the merge, `excluded_patient_ids` is `[]`.

**Audit Status:**
- Match the audit event by finding the event whose patient_ids exactly match (set equality) the candidate's patient_ids.
- Map status: `"ready_for_merge"` → `"READY_FOR_MERGE"`; `"blocked_address_conflict"` → `"BLOCKED_ADDRESS_CONFLICT"`, etc.

**Contact Action:**
- `"NONE_REQUIRED"` when no patient/provider contact is needed (standard merge).
- Set `action_required: false` and `target_provider_id: ""`.

---

## Task Type 2: Referral Batch Quality Audit

### Workflow
1. `GET /api/referral-batches/{batch_id}` → batch metadata + referrals[] array
2. `GET /api/codebook/icd10` → build lookup map by code
3. `GET /api/providers` → reference for provider validation

### Business Rules

**Duplicate Detection:**
- Two or more referrals are duplicates when they share the same `patient_first_name`, `patient_last_name`, AND `patient_dob`.
- Group duplicate referral_ids into arrays; output as `duplicate_groups` (array of string arrays).

**Laterality Mismatch:**
- Compare the `laterality` field from the ICD-10 codebook entry against the `diagnosis_description` text.
- A mismatch exists when the codebook laterality says "right" but the description says "left" (or vice versa), OR when the codebook laterality is "bilateral" but the description is unilateral, OR when the code is non-lateralized (null laterality) but the description explicitly mentions a side.
- Flag the referral_id in `laterality_mismatch_referral_ids`.

**Corrected Code Suggestions:**
- When the ICD-10 code's laterality or body_site contradicts the `diagnosis_description`, find the correct code from the codebook whose `description` matches the body_site and laterality expressed in the diagnosis description.
- Map: `{referral_id: corrected_code}` in `corrected_code_suggestions`. Only include referrals that need correction.

**Narrative Mismatch:**
- When clinical narrative is inconsistent — e.g., the ICD-10 code points to a non-orthopedic body system while the batch is orthopedic, or the diagnosis code is for pain/chronic conditions but the narrative implies a fracture/acute injury (or vice versa).
- Flag in `narrative_mismatch_referral_ids`.

**Out-of-Range Codes:**
- An ICD-10 code is out-of-range when `in_musculoskeletal_tracking_range` is `false` for an orthopedic batch. Also flag codes where the `chapter_prefix` is not "M" or "S" (for orthopedic context).
- Build `out_of_range_code_referral_ids`.

**Insurance Anomalies:**
- The same `insurance_id` appearing on duplicate referrals (same patient) is **expected** — do not flag.
- The same `insurance_id` appearing on referrals for **clearly different** patients is an anomaly. For each anomalous insurance_id, record:
  - `insurance_id`: the ID
  - `related_duplicate_referral_ids`: the duplicate group sharing this insurance
  - `unrelated_referral_ids`: other referrals using the same insurance_id that do NOT belong to the duplicate group

**Missing Counts:**
- `auth_not_submitted`: count of referrals where `auth_status == "Not Submitted"`
- `imaging_missing`: count of referrals where `imaging_received == "No"`
- `records_missing`: count of referrals where `records_received == "No"`

**Priority Queues:**
- `tier1_immediate`: Urgent referrals with missing imaging or records, pathological fractures, or oncology coordination requests (check `notes` field for "PRIORITY" keyword).
- `tier2_short_term`: Referrals with laterality mismatch, narrative mismatch, or needing code correction.
- `tier3_administrative`: Auth not submitted, patient rescheduling requests, routine referrals with minor documentation gaps.
- A referral appears in at most one tier. Assign to the highest applicable tier.

---

## Task Type 3: Handoff Packet Completeness Review

### Workflow
1. `GET /api/handoff-packets/{packet_id}` → packet metadata, included_sections[], clinical fields
2. `GET /api/patients/{patient_id}` + sub-resources for clinical validation
3. `GET /api/providers` → validate receiving/sending provider

### Handoff Packet Fields
- `packet_id`, `patient_id`, `created_date`, `receiving_facility`, `receiving_provider_id`, `sending_provider_id`, `transfer_reason`, `notes`
- `included_sections[]` — enumerates which standard sections are present
- `cognitive_status` (string, may be empty), `functional_status` (string)

### Business Rules

**Standard Handoff Sections (the expected set):**
```
demographics, active_problems, active_medications, allergies, recent_encounters,
immunizations, functional_status, cognitive_status, transfer_plan, disclosure
```

**Missing Section Detection:**
- A section is missing if it does NOT appear in `included_sections[]`.
- Additionally, if a section IS in `included_sections[]` but the corresponding field on the packet object is empty/blank, treat it as missing.
- Output `missing_packet_sections` as an array of lowercase snake_case section names.

**Risk Flags:**
- Generate one risk flag per missing section: `"MISSING_<SECTION_NAME_UPPER>"` (e.g., `"MISSING_COGNITIVE_STATUS"`).

**Readiness Determination:**
- `"BLOCKED_INCOMPLETE_PACKET"` if any standard section is missing or blank.
- `"READY"` only when all standard sections are present and populated.

**Active Clinical Lists from Patient Chart:**
- Extract active (`status == "active"`) problems, medications, and allergies from the patient record.
- Output as `active_problem_codes` (ICD-10 codes), `active_medication_ids`, `active_allergy_labels`.
- Sort codes and IDs alphanumerically; sort labels alphabetically.

**Most Recent Immunization:**
- Sort patient immunizations by `date` descending; pick the first. Output its `id`.

**Recent Encounters:**
- Sort patient encounters by `date` descending. Include all encounters within the recent care episode (typically the last 2-3 months from the packet creation date, or the most recent 4 if many exist). Output their `id` values.
- Use chronological ordering within the output: most recent first.

**Disclosure Status:**
- Check the patient's disclosures for an active disclosure matching the receiving facility or care-transition purpose.
- Output `"ACTIVE"` if found; `"MISSING"` or `"INACTIVE"` otherwise.

---

## Task Type 4: Service Request Order Validation

### Workflow
1. `GET /api/service-requests/{request_id}` → full request with note_text, linked_encounter_ids
2. `GET /api/patients/{patient_id}/encounters` → validate linked encounter evidence
3. `GET /api/codebook/icd10` → validate codes in encounter diagnoses

### Service Request Fields
- `request_id`, `patient_id`, `status`, `priority`, `intent`, `specialty`, `service_code`, `service_display`
- `note_text` — contains SBAR-structured clinical narrative
- `linked_encounter_ids[]` — encounters providing evidence for the request
- `authored_on` (ISO 8601), `occurrence_datetime` (ISO 8601)

### Business Rules

**SBAR Section Parsing:**
- Parse `note_text` for the four SBAR components using case-insensitive keyword matching:
  - `SITUATION:` or `Situation:`
  - `BACKGROUND:` or `Background:`
  - `ASSESSMENT:` or `Assessment:`
  - `RECOMMENDATION:` or `Recommendation:`
- A section is **present** if the keyword is found AND the content after the keyword (up to the next section keyword or end of string) is non-empty (not just whitespace).
- Output `sbar_sections_present` as a map with uppercase keys: `SITUATION`, `BACKGROUND`, `ASSESSMENT`, `RECOMMENDATION`, each boolean.

**Missing SBAR Sections:**
- Any SBAR section that is missing or empty → add its uppercase name to `missing_sbar_sections[]`.

**Blocker Codes:**
- One blocker per missing SBAR section: `"MISSING_<SECTION>"` (e.g., `"MISSING_RECOMMENDATION"`).

**Ready to Sign:**
- `true` only when ALL four SBAR sections are present and non-empty, AND no other order-quality blockers exist.
- `false` otherwise.

**Evidence Encounters:**
- From `linked_encounter_ids[]`, include those that are clinically relevant to the service request's specialty and contain diagnoses matching the request's clinical context.
- Output as `evidence_encounter_ids`.

**Laterality Consistency:**
- Compare the laterality of diagnoses in the linked encounter(s) against the service specialty and service_display.
- `true` when the encounter diagnoses and service request refer to the same anatomical side.
- `false` when there is a laterality conflict (e.g., encounter describes left shoulder but request is for right shoulder surgery).

**Order Validation Object:**
```json
{
  "priority": "<from request>",
  "service_code": "<from request>",
  "specialty": "<from request>",
  "status": "<from request>"
}
```
These fields are copied directly from the service request.

---

## Task Type 5: Referral Quality Decision & Letter Prep

### Workflow
1. `GET /api/referrals` → filter client-side by `referral_id` to find the target referral
2. `GET /api/patients/{patient_id}` + sub-resources for chart review
3. `GET /api/providers` → identify the appropriate referral target provider
4. `GET /api/codebook/icd10` → validate referral diagnosis code

### Business Rules

**Referral Target Selection:**
- Match the referral's diagnosis/condition to the most appropriate specialist from the providers list.
- The referral target includes `provider_id` and `specialty` of the matched provider.
- For cardiac conditions → Advanced Heart Failure or Cardiology specialist. For orthopedic → Orthopedic Surgery.

**Diagnosis Update:**
- Extract the primary diagnosis from the referral: `icd10_code` → `code`, `diagnosis_description` → `description`.
- This is the diagnosis that should be confirmed/added to the patient's problem list.

**Allergy Update (from referral notes):**
- Check the referral `notes` field for instructions to add allergies.
- Cross-reference the patient's existing allergy list to confirm the allergy is NOT already recorded.
- If a new allergy is indicated, construct an allergy_update object: `allergen`, `reaction`, `severity`, `status: "active"`.
- If the allergy already exists in the patient chart, do not include an allergy update.

**Letter Merge Fields:**
- Standard fields required for a referral cover letter. Include: `Patient_Name`, `DOB`, `Referral_Reason`, `Active_Problems`, `Allergies`.
- These are PascalCase underscore-delimited strings.
- Always verify the field is relevant before including (e.g., include `Allergies` only if patient has active allergies or a new allergy is being added).

**Recent Encounters:**
- From the patient's encounter list, sort by `date` descending. Include encounters relevant to the referral reason (typically those within the last 3 months). Output their `id` values.

**Safety Flags:**
- Flag critical missing data that must be resolved before the referral can be sent.
- Example: `"CONTRAST_ALLERGY_REQUIRED"` when the referral notes mention adding a contrast allergy that is not yet in the patient chart and the planned procedure involves contrast.
- Other flags: `"MISSING_DIAGNOSIS_CONFIRMATION"`, `"MEDICATION_RECONCILIATION_NEEDED"`.

**Send Ready:**
- `"READY"` when all quality issues are resolved or no blocking issues exist.
- `"BLOCKED"` when unresolved quality issues remain.
- `unresolved_quality_issues[]`: list of issues that must be addressed before sending. Empty if `send_ready == "READY"`.

---

## Cross-Cutting Conventions

### Identifier Naming Patterns
| Prefix | Entity | Example |
|---|---|---|
| `PAT-TR-` | Train patient | `PAT-TR-001A` |
| `PAT-TE-` | Test patient | `PAT-TE-0401` |
| `DUP-TR-` | Duplicate candidate | `DUP-TR-001` |
| `REF-TR-` | Referral (train) | `REF-TR-0301` |
| `REF-TE-` | Referral (test) | `REF-TE-0401` |
| `SR-TR-` | Service request | `SR-TR-004` |
| `HANDOFF-TR-` | Handoff packet | `HANDOFF-TR-003` |
| `BATCH-` | Referral batch | `BATCH-ORTHO-2026-03` |
| `ENC-TR` | Encounter | `ENC-TR003-01` |
| `MED-TR` | Medication | `MED-TR001-01` |
| `ALG-TR` | Allergy | `ALG-TR001-01` |
| `PR-TR` | Problem | `PR-TR001-01` |
| `IMM-TR` | Immunization | `IMM-TR003-01` |
| `DISC-TR` | Disclosure | `DISC-TR001-01` |
| `AUD-TR` | Audit event | `AUD-TR001-01` |
| `PROV-` | Provider | `PROV-001` |

### List Ordering Rules
| Context | Ordering |
|---|---|
| Problem codes | Alphanumeric sort by code string |
| Medication IDs | Alphanumeric sort by ID string |
| Allergy labels | Alphabetical sort by label string |
| Encounter IDs | Chronological by date, newest first |
| Immunization IDs | Chronological by date, newest first |
| Referral IDs in priority queues | In the order they appear in the batch |

### Clinical List Filtering Rules
- **Active-only filtering:** When aggregating problems, medications, or allergies for quality review, include ONLY items with `status == "active"`. Ignore `"inactive"`, `"resolved"`, or `"completed"` items.
- **Deduplication:** When merging clinical lists from multiple sources (e.g., two duplicate patients), deduplicate by the canonical key: `code` for problems, `id` for medications, `label` for allergies.
- **Union semantics:** The preserved list is the deduplicated union of active items from all included sources. Never take an intersection.

### Source Precedence
- **Patient chart** (from `/api/patients/{id}`) is authoritative for clinical history: problems, medications, allergies, encounters, immunizations.
- **Referral data** (from batch or referrals list) is authoritative for the referral's administrative fields: insurance, auth_status, referring physician, urgency.
- **Codebook** is authoritative for ICD-10 code validity, laterality, and body site.
- **Audit log** is authoritative for governance workflow status.
- **Handoff packet** is authoritative for what sections are included; compare against the **standard section set** (defined above) to detect omissions.
- When a patient object's inline clinical lists and the dedicated sub-resource endpoint differ (should not happen), prefer the sub-resource endpoint response.

### Common Pitfalls
1. **Don't use `/api/referrals/{id}`:** The individual referral lookup returns 404. Always fetch `/api/referrals` and filter by `referral_id` client-side.
2. **MRN vs patient_id:** The `enterprise_mrn` is a separate identifier from `patient_id`. Use `patient_id` for API calls; use `enterprise_mrn` only for disambiguation during merge decisions.
3. **Audit log is global:** The `/api/audit-log` endpoint returns ALL events. Filter by `patient_ids` intersection to find the relevant event.
4. **Empty string ≠ missing:** In handoff packets, a section listed in `included_sections[]` but with an empty string value (e.g., `"cognitive_status": ""`) counts as missing.
5. **Duplicate insurance on same patient is normal:** When detecting insurance anomalies, the same `insurance_id` on duplicate referrals for the SAME patient is expected — only flag cross-patient reuse.
6. **Laterality comparison is directional:** The laterality in the codebook must match what the diagnosis description says. A code with no laterality applied to a description that mentions "right" or "left" is a mismatch.
7. **SBAR parsing is whitespace-sensitive:** Content after a section keyword is considered empty if it is only whitespace or if the next section keyword immediately follows.
8. **Referral `notes` field contains actionable instructions:** Always inspect the `notes` field of referrals for allergy updates, priority flags, and quality instructions.
9. **Patient suffix letters matter:** In duplicate candidates, patient IDs may have suffixes like "A" and "B" (e.g., `PAT-TR-001A`, `PAT-TR-001B`). The "A" record is typically the older/more-established record.
10. **Don't assume batch_id scoping:** The `/api/referrals` endpoint returns ALL referrals regardless of batch. When working with a specific batch, always filter by `batch_id`.

### Output Field Conventions
- All IDs and codes are strings, never numbers.
- Boolean fields use JSON `true`/`false`, not strings.
- Empty arrays use `[]`, not `null`.
- Empty strings use `""`, not `null`.
- Dates are ISO 8601 strings or YYYY-MM-DD format as provided by the API.
- Enum/status values are UPPER_SNAKE_CASE strings.
- Section names in output arrays are lowercase_snake_case.
- Risk flag and blocker code values are UPPER_SNAKE_CASE.
