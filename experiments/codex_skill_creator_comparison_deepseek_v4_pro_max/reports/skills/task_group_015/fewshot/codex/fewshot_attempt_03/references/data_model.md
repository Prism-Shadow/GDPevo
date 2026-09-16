# Data Model Reference

## Normalized Clinical Keys

Conditions, medications, and allergies are represented by normalized_key fields. The normalization rules:

- Convert to lowercase.
- Replace spaces and special characters with underscores.
- Strip leading/trailing whitespace.

Examples: Type 2 Diabetes -> diabetes_type_2, Right Knee OA -> right_knee_oa, Peanut Allergy -> peanut.

When forming clinical unions (merge or handoff packets), combine the normalized keys from both sources into a deduplicated, sorted set.

## ICD-10 Code Structure

Every ICD-10 code has a code, description, and chapter field from /api/icd10/{code}.

### Chapter Validation by Service Line

| Service Line | Expected Primary Chapter | Expected Chapter Code Range |
|---|---|---|
| orthopedics | Musculoskeletal | M00-M99 |
| cardiology | Circulatory | I00-I99 |
| pulmonology | Respiratory | J00-J99 |
| neurology | Nervous System | G00-G99 |

An ICD-10 code whose chapter does not match the service line expected chapter is **out of range**. The issue_type is out_of_range_chapter unless the code is not found in the ICD-10 directory, in which case it is unknown_code.

**Orthopedic special case:** S83 codes (meniscus tears) live in the Injury chapter, not Musculoskeletal. They are out-of-range for orthopedics even though the anatomic site is the knee.

### Laterality Conventions in ICD-10

Character positions encode laterality:

- Final digit 1 -> right (e.g., M17.11 = right knee OA, S83.241A = right medial meniscus tear)
- Final digit 2 -> left (e.g., M17.12 = left knee OA, S83.242A = left medial meniscus tear)
- M25.561 -> right knee pain
- M25.562 -> left knee pain
- M16.11 -> right hip OA

Code the expected terms from the ICD-10 directory description. When the referral narrative mentions a different laterality than the code, flag as laterality_mismatch. When the narrative talks about a different body site or condition entirely than what the code describes, flag as narrative_mismatch. When the narrative omits laterality while the code implies it, flag as missing_laterality.

## Service Lines

| Value | Label |
|---|---|
| orthopedics | Orthopedics |
| cardiology | Cardiology |
| pulmonology | Pulmonology |
| neurology | Neurology |
| skilled_nursing | Skilled Nursing |
| oncology | Oncology |
| primary_care | Primary Care |

## Provider Roles

Providers have role, service_line, and facility. Common roles: Primary Care, Cardiologist, Orthopedic Surgeon.

## Encounter Types

Common types: office_visit, care_transition, follow_up, surgical_consult. Signed status values: signed, unsigned, amended, draft.

## Document Types

Common types: echocardiogram, office_note, radiology_report, chart_summary, discharge_summary. Status values: final, preliminary, cancelled, missing.

## Disclosure Statuses

permitted, pending, denied, expired.

## Authorization & Referral Statuses

- authorization_status: approved, pending, denied, not_required, unknown
- referral_status: open, closed, cancelled, draft
- urgency: routine, urgent, stat

## Risk Flags for Care Transitions

Derived from active clinical evidence:

| Condition/Allergy Signal | Risk Flag |
|---|---|
| Memory loss condition | cognitive_memory_loss |
| Hip OA + knee OA conditions | fall_risk_note_required |
| Hypertension condition | hypertension |
| Diabetes + insulin medication | insulin_dependent_diabetes |
| Diabetes + insulin medication | perioperative_glucose_plan_needed |
| Latex allergy | latex_allergy |

Multiple conditions can contribute to the same risk flag (e.g., hip OA and knee OA both support fall_risk_note_required).
