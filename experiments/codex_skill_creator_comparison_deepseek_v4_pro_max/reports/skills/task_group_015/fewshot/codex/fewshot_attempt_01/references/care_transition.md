# Care Transition Packet

Use when the task asks for a "care transition packet" addressed to a specific provider for a specific patient.

## Input Signals

- A patient ID and a recipient provider ID in the task prompt.
- An `answer_template.json` with keys: `patient`, `recipient`, `active_condition_keys`, `active_medication_keys`, `active_allergy_keys`, `handoff_encounters`, `source_selection`, `latest_immunization`, `disclosure`, `risk_flags`, `risk_flag_evidence`, `packet_readiness`.

## Evidence Gathering Order

1. `GET /api/patients/{patient_id}` - patient demographics.
2. `GET /api/providers/{recipient_provider_id}` - recipient provider details.
3. `GET /api/patients/{patient_id}/conditions` - filter to active, collect normalized_keys.
4. `GET /api/patients/{patient_id}/medications` - filter to active, collect normalized_keys.
5. `GET /api/patients/{patient_id}/allergies` - filter to active, collect normalized_keys.
6. `GET /api/patients/{patient_id}/encounters` - all encounters, sort by date descending.
7. `GET /api/patients/{patient_id}/immunizations` - most recent by date.
8. `GET /api/patients/{patient_id}/disclosures` - find disclosure matching recipient provider.
9. Identify risk flags from clinical data and encounter evidence.

## Reconciliation Rules

### Active Clinical Keys

- Conditions: collect `normalized_key` from records where `clinical_status` is `active`. Sort alphabetically.
- Medications: collect `normalized_key` from records where `status` is `active`. Sort alphabetically.
- Allergies: collect `normalized_key` from records where `status` is `active`. Sort alphabetically.

### Handoff Encounters

- Select exactly **four** most recent signed encounters relevant to the surgical handoff.
- Relevance: encounters with `care_plan_tag` related to the surgical service line, or encounters whose `diagnosis_codes` include orthopedic conditions.
- Exclude encounters outside the surgical window, unsigned drafts, or clearly unrelated visit types.
- List selected encounters newest to oldest in `handoff_encounters`.
- List excluded encounters in `source_selection.excluded_encounter_ids` sorted ascending.

### Latest Immunization

- Select the immunization with the most recent `date`. If multiple on the same date, take the first returned.

### Disclosure

- Find the disclosure where `recipient_provider_id` matches the packet recipient and `status` is `permitted`.
- If multiple exist, select the most recent by `date`.

### Risk Flags

- Derive risk flags from active conditions and medications:
  - `cognitive_memory_loss`: when a condition with `normalized_key` containing "memory_loss" exists.
  - `fall_risk_note_required`: when lower-extremity OA conditions exist (knee, hip) with pain medications.
  - `hypertension`: when hypertension is active.
  - `insulin_dependent_diabetes`: when diabetes is active and insulin is prescribed.
  - `latex_allergy`: when latex allergy is active.
  - `perioperative_glucose_plan_needed`: when diabetes is active and surgery is planned.
- Sort risk flags alphabetically.
- For each risk flag in `risk_flag_evidence`, list the contributing condition_keys, medication_keys, and encounter_ids.

### Packet Readiness

- `status: ready_with_risk_flags` when all required data is gathered but risk flags exist.
- `status: ready` when no risk flags.
- `status: not_ready` when required data is missing.
- `ready_to_send: true` when status is `ready` or `ready_with_risk_flags`.

## Output Shape

Follow `answer_template.json` exactly. Handoff encounters must be exactly 4 selected encounters. Risk flags must use only the enum values listed in the template.
