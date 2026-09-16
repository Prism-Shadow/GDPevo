## Care transition packet

### Objective

Produce a normalized care transition packet for a patient addressed to a specific receiving provider. The output identifies the patient, recipient, active clinical keys, handoff encounters, latest immunization, disclosure, risk flags, and packet readiness.

### Step-by-step

#### 1. Fetch the patient

`GET /api/patients/{patient_id}`

Extract: `id`, `identifier` (enterprise MRN), `name` (display_name), `birthDate` (dob).

#### 2. Fetch active clinical lists

`GET /api/patients/{patient_id}/conditions`
`GET /api/patients/{patient_id}/medications`
`GET /api/patients/{patient_id}/allergies`

Filter for active records only. Collect normalized_key values and sort alphabetically.

#### 3. Fetch encounters

`GET /api/patients/{patient_id}/encounters`

Select the **four most recent** handoff-relevant encounters. The handoff window is typically the last 60-90 days before the transition date. Exclude:
- Encounters older than the window (stale)
- Encounters unrelated to the transition purpose (e.g., unrelated specialist visits)
- Encounters with status "cancelled" or "entered-in-error"

Sort the selected four newest to oldest by date. Record the selection basis (e.g., "orthopedic_surgical_handoff_window").

List excluded encounter IDs with a brief reason for exclusion.

#### 4. Fetch the latest immunization

`GET /api/patients/{patient_id}/immunizations`

Filter for `status = "completed"`. Select the most recent by date. Record immunization ID, date, and vaccine name.

#### 5. Fetch disclosures

`GET /api/patients/{patient_id}/disclosures`

Find the disclosure applicable to the transition. Look for disclosures where:
- Status is "permitted" or "active"
- Purpose matches the transition (e.g., "surgical handoff")
- Recipient matches the target provider

Record disclosure ID, date, status, purpose, and recipient provider ID.

#### 6. Fetch the recipient provider

`GET /api/providers/{provider_id}`

Extract: provider_id, name, facility, service_line.

#### 7. Derive risk flags

Risk flags are clinical signals that the receiving provider needs to know. Common orthopedic surgery risk flags:

- **cognitive_memory_loss**: active condition with normalized_key containing "memory" or related cognitive terms
- **fall_risk_note_required**: multiple joint OA conditions + pain medication (acetaminophen) + care transition encounter
- **hypertension**: active condition with normalized_key "hypertension"
- **insulin_dependent_diabetes**: active condition "diabetes_type_2" with active insulin medication
- **latex_allergy**: active allergy with allergen containing "latex"
- **perioperative_glucose_plan_needed**: diabetes condition + insulin medication + surgical transition encounter

Derive flags only from active conditions, active medications, and active allergies. Sort flags alphabetically.

#### 8. Build risk flag evidence

For each risk flag, create an evidence entry linking the flag to:
- Supporting active condition keys (sorted)
- Supporting active medication keys (sorted)
- Supporting encounter IDs (sorted)

An evidence entry with empty arrays indicates the flag is derived from a source (e.g., an allergy) that maps differently to the evidence schema. Include the flag with empty evidence arrays rather than omitting it.

#### 9. Assess packet readiness

Set `ready_to_send` to true when:
- Patient, recipient, active lists, handoff encounters, immunization, and disclosure are all available
- Disclosure status is "permitted"
- No blocking issues exist

Choose `status`:
- `ready`: no risk flags
- `ready_with_risk_flags`: risk flags present but no blockers
- `not_ready`: missing required data or disclosure not permitted

Populate `blocking_issue_codes` only when there is a true blocker. Use the allowed enum values: missing_patient, missing_recipient, missing_active_lists, missing_handoff_encounters, missing_immunization, missing_disclosure, disclosure_not_permitted.

### Output shape

The template defines these top-level keys: `patient`, `recipient`, `active_condition_keys`, `active_medication_keys`, `active_allergy_keys`, `handoff_encounters`, `source_selection`, `latest_immunization`, `disclosure`, `risk_flags`, `risk_flag_evidence`, `packet_readiness`.
