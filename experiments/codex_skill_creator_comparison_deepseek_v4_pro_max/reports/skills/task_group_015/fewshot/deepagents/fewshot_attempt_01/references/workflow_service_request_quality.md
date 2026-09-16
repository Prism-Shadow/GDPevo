## ServiceRequest quality review

### Objective

Produce a normalized quality review for a ServiceRequest in the context of a duplicate candidate. Validate the ServiceRequest service code, reason codes, SBAR coverage, and duplicate merge decision.

### Step-by-step

#### 1. Fetch the ServiceRequest

`GET /api/patients/{patient_id}/service-requests` and filter by the given SR ID.

The ServiceRequest may also be accessible as a standalone resource at `/api/service-requests/{sr_id}` if that endpoint exists in the task environment.

Extract: `id`, `patient`, `status`, `intent`, `priority`, `code`, `requester`, `performer`, `reasonCode`, `authoredOn`, `occurrenceDateTime`, `note`.

#### 2. Fetch the patient

`GET /api/patients/{patient_id}`

#### 3. Fetch the duplicate candidate

`GET /api/duplicates/{candidate_id}`

Extract: `status`, `primaryPatient`, `duplicatePatient`, `matchSignals`, `conflictSignals`.

#### 4. Determine the duplicate review outcome

- Map `candidate_status` directly from the duplicate candidate's `status` field.
- Determine `decision`:
  - `merge`: both match and conflict signals support merging (strong identity matches, minor conflicts)
  - `review_hold`: conflicting signals require manual review before merging
  - `do_not_merge`: strong demographic conflicts or clinical laterality conflicts
- Set `merge_target_patient_id` and `merge_source_patient_id` only when merging. Use `null` for review_hold or do_not_merge.

#### 5. Validate the ServiceRequest service code

`GET /api/service-codes/{code}`

If the code exists in the directory, `service_code_valid = true`. The code string is the `coding[0].code` from the ServiceRequest.

#### 6. Validate reason codes against ICD-10

For each ICD-10 code in `reasonCode`:
- `GET /api/icd10/{code}`
- `valid`: true if the code exists in the directory
- `chapter`: the ICD-10 chapter name from the directory
- `matches_patient_evidence`: true if the code appears in the patient's active conditions or in encounter diagnosis codes

#### 7. Determine performer service line

`GET /api/providers/{performer_id}`

Extract the provider's `serviceLine` field. If the performer reference contains multiple provider IDs, use the primary performer (first in the list).

#### 8. Evaluate SBAR coverage

Review the ServiceRequest `note` array for SBAR section labels:
- **S**ituation: what is being requested and why
- **B**ackground: relevant clinical history
- **A**ssessment: clinical findings and diagnostic reasoning
- **R**ecommendation: specific request or suggested action

Check for the presence of each section. If the ServiceRequest note contains text matching each section label, mark them as present.

Set `complete = true` only when all four sections are present. Populate `sections_present` and `missing_sections` with the enum values: situation, background, assessment, recommendation.

### Output shape

Top-level keys: `task_id`, `duplicate_review`, `service_request`, `sbar_coverage`.
