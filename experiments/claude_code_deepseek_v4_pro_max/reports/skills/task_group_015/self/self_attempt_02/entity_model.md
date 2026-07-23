# EHR Entity Model & Vocabularies

## Core entities

```
Patient
├── Condition[]        — diagnoses, active/inactive, indexed by normalized_key
├── Medication[]       — active/inactive, indexed by normalized_key
├── Allergy[]          — active/inactive, indexed by allergen+reaction
├── Encounter[]        — visits, signed/unsigned, with diagnosis codes and care plan tags
├── Immunization[]     — vaccine history
├── Document[]         — clinical documents (final/preliminary/cancelled)
├── Disclosure[]       — consent records (permitted/pending/denied/expired)
└── ServiceRequest[]   — orders and referrals

Referral
├── links to Patient (patient_id)
├── links to Provider (receiving_provider_id)
├── carries a diagnosis_code → validates against ICD-10
└── has authorization_status and urgency

DuplicateCandidate
├── links to two Patients (primary_patient_id, possible_duplicate_patient_id)
├── provides match_signals[] and conflict_signals[]
└── has a status (confirmed_duplicate | needs_review | not_duplicate)

Provider
├── has service_line (orthopedics | cardiology | pulmonology | neurology | skilled_nursing | oncology | primary_care)
└── has facility, phone, fax

ICD10Code
├── code, description, chapter
└── laterality (if applicable)

AuditLog
├── links to patient_id, entity_type, entity_id
└── has action and timestamp
```

## Normalized key conventions

Clinical items (conditions, medications, allergies) carry a `normalized_key` field. This key is the stable, deduplication-safe identifier:

- **Condition normalized_key**: typically derived from the ICD-10 code and a normalized form of the description (e.g., `M17.0_osteoarthritis_knee`).
- **Medication normalized_key**: typically derived from the generic medication name and dose (e.g., `furosemide_40mg_oral`).
- **Allergy normalized_key**: typically derived from the allergen name (e.g., `sulfa_antibiotics`).

When building clinical key unions:
1. Use the `normalized_key` from the patient's active-list endpoint responses.
2. If a duplicate-candidate preview provides a clinical list excerpt, treat the patient's own active-list endpoint as authoritative and reconcile differences.
3. The union set (deduplicated by `normalized_key`) is the output.

## Service line to ICD-10 chapter mapping

| Service Line | Expected ICD-10 Chapter |
|---|---|
| orthopedics | Musculoskeletal |
| cardiology | Circulatory |
| pulmonology | Respiratory |
| neurology | Nervous |
| oncology | Neoplasms |
| skilled_nursing | Various (post-acute, typically Musculoskeletal or Circulatory) |
| primary_care | Various (any chapter is permissible) |

## Risk flag evidence rules (care transition context)

Risk flags are driven from active clinical data. The following table maps each risk flag to the active-list evidence that triggers it:

| Risk Flag | Trigger Condition | Evidence Sources |
|---|---|---|
| `cognitive_memory_loss` | Active condition with normalized_key referencing cognitive impairment, dementia, or memory loss | condition_keys |
| `fall_risk_note_required` | Active condition referencing gait instability, fall history, or balance disorder; OR active medication with dizziness/orthostatic side effect profile | condition_keys, medication_keys |
| `hypertension` | Active condition with normalized_key referencing hypertension | condition_keys |
| `insulin_dependent_diabetes` | Active condition with normalized_key referencing diabetes AND active medication with normalized_key referencing insulin | condition_keys, medication_keys |
| `latex_allergy` | Active allergy with allergen referencing latex | medication_keys (allergy context) |
| `perioperative_glucose_plan_needed` | Active condition referencing diabetes AND the transition is to a surgical (orthopedic) service line | condition_keys |

For each emitted risk flag, provide the supporting `condition_keys`, `medication_keys`, and `encounter_ids` in the risk-flag evidence section.

## Disposition and readiness enum vocabulary

### Merge decisions

| Value | Meaning |
|---|---|
| `ready_to_merge` / `merge_ready` | Both records are confirmed duplicates; all clinical data reconciled; no conflicts block the merge |
| `merge_ready_with_conflict_review` | Duplicates confirmed but one or more demographic/clinical conflicts need a human review note; merge can proceed with the note |
| `needs_review` / `review_hold` / `needs_manual_review` | Uncertain duplicate status or unresolved clinical conflict; merge is paused |
| `do_not_merge` / `not_duplicate` | Records are not duplicates or merge is contraindicated |

### Packet readiness statuses

| Value | Meaning |
|---|---|
| `ready` / `ready_to_send` | All required data present, valid, and consistent |
| `ready_with_review_note` / `ready_with_risk_flags` | Packet is complete but carries review notes or risk flags |
| `blocked` / `not_ready` / `hold_for_*` | One or more blockers prevent sending; see blocking_issues |

### Authorization statuses

| Value | Meaning |
|---|---|
| `approved` | Authorization has been granted |
| `pending` | Authorization has been requested but not yet decided |
| `denied` | Authorization was requested and denied |
| `not_required` | The referral/order does not require prior authorization |
| `unknown` | Authorization status cannot be determined from available data |

### Document type exclusions

The following document types are excluded from packet evidence unless the task explicitly calls for them:

- `staff_message` — internal communication, not clinical evidence
- `admin_note` — administrative workflow artifact
- Any document with `status` other than `final`

Evidence documents must be `status: final` and clinically relevant to the task's service line.

### SBAR sections

When assessing SBAR coverage (Situation, Background, Assessment, Recommendation):

- **Situation**: present if the referral or ServiceRequest provides a clear clinical question and patient context.
- **Background**: present if recent encounters, active conditions, and relevant history are documented.
- **Assessment**: present if diagnosis codes are validated and clinical reasoning is traceable.
- **Recommendation**: present if the referral/order specifies the requested service, provider, and urgency.

SBAR is `complete` (true) only when all four sections are present.

## Distractor identification rules

For any exclusion/detractor reporting:

1. **Conditions**: `status` is `inactive`, `resolved`, or `entered-in-error` → exclude from active unions.
2. **Medications**: `status` is `inactive` or `entered-in-error` → exclude from active unions.
3. **Allergies**: `status` is `inactive` or `entered-in-error` → exclude from active unions.
4. **Documents**: `status` is `preliminary` or `cancelled` → exclude from evidence. Type is `staff_message` or `admin_note` → exclude from evidence.
5. **Audit logs**: entries with no clinical relevance (system-internal, schema migrations, etc.) → exclude from evidence.
6. **Encounters**: outside the clinically relevant time window, or with `care_plan_tag` unrelated to the task domain → exclude from handoff selection.
