---
name: cedar-ridge-intake
description: Analyze patient intake, referral, transfer, and chronic-care enrollment records using the Cedar Ridge Intake Coordination Portal API. Use this skill whenever the user mentions Cedar Ridge, patient access verification, referral readiness, dialysis transfer review, chronic-care enrollment panels, intake coordination, provider roster validation, referral-to-chart activation, or any healthcare intake workflow operating against the Cedar Ridge portal endpoints. The portal exposes patients, referrals, transfers, program candidates, charts, ICD codes, pharmacies, documents, and a read-only SQL query endpoint.
---

# Cedar Ridge Intake Coordination Portal Skill

Use this skill to work with any Cedar Ridge intake coordination task: patient access verification, referral auditing, dialysis transfer review, chronic-care enrollment panels, and referral-to-chart activation.

## Core workflow

Every Cedar Ridge task follows the same pattern:

1. **Read the answer template** from the task payload if one is provided. The template defines the required output shape and controlled vocabulary. Follow it exactly, using only the enumerated values it specifies.
2. **Fetch the target data** from the portal API. Start with the batch/roster endpoint for your target, then pull patient-level detail for every patient involved.
3. **Cross-reference related records** such as ICD code metadata, documents, pharmacies, and chart data from the other portal endpoints.
4. **Apply the business rules** for the operation type you are working on (see [references/business_rules.md](references/business_rules.md)).
5. **Aggregate cohort summaries** with integer counts for every dimension the template requires.
6. **Return a single JSON object** with no prose outside it. Order list items as the template specifies (ascending by ID unless stated otherwise). Treat reason-code and blocker-code arrays as unordered sets. Use uppercase IDs exactly as the portal returns them.

The complete API reference is in [references/api_reference.md](references/api_reference.md). Read it when you need endpoint details, parameters, or SQL query syntax.

## How to approach a task

### Step 1: Understand what is being asked

Read the user's prompt and the answer template carefully. Identify:
- The operation type (patient access, referral audit, transfer review, enrollment panel, referral-to-chart activation)
- The batch/roster/program identifier
- Every required output field and its allowed values

### Step 2: Fetch the primary dataset

Pull the batch/roster list first to know which patients are in scope. Use the appropriate endpoint:
- `/referrals?batch_id=<id>` for referral batches
- `/transfers?batch_id=<id>` for transfer batches
- `/patients/<id>` endpoint for each patient on a roster (roster info is embedded in the patient detail response)
- `/programs/<code>/candidates` for enrollment panels

### Step 3: Pull patient-level detail

For every patient or referral in scope, fetch the full patient record at `/patients/<patient_id>`. This returns the combined view: patient demographics, insurance coverage, PBM records, pharmacies, lifestyle data, clinical history, roster records, referral records, transfer records, documents, and program candidates.

For referral/transfer tasks, you also need the full `/patients/<id>` response for each patient referenced in those records.

### Step 4: Cross-reference supporting data

Depending on the operation, pull the additional data you need:

- `/icd/<code>` for every distinct ICD-10 code on the referrals. This gives you chapter, description, laterality, and service family.
- `/chart/<patient_id>` for enrollment panels and chart-activation tasks, to see existing chart artifacts, clinical history, medications, allergies, vitals, and labs.
- `/pharmacies` (list endpoint) for pharmacy network lookups.
- `/documents` and `/referrals/<referral_id>` or `/transfers/<transfer_id>` for document-level detail.

Do the ICD lookups in parallel -- there is one call per distinct code, and distinct codes across a batch are few.

### Step 5: Apply business rules

Use the reference in [references/business_rules.md](references/business_rules.md). The rules follow the data model laid out in [references/data_model.md](references/data_model.md). Read both when you need the exact field mappings.

Key principle: derive every status, code, and decision from the raw API data. Do not fabricate values. If the API lacks information needed for a determination, use the appropriate controlled value for that case (for example, `"missing"` for insurance when no coverage record exists).

### Step 6: Assemble the output

Build the JSON object to match the template exactly:
- Use only the enumerated values from the template
- Order list items ascending by ID unless the template says otherwise
- Treat reason-code arrays as unordered sets (order within them does not matter)
- Count all summary fields from the patient-level results you produced

### Step 7: Validate and return

Before returning, check that:
- Every required top-level key is present
- Every patient/transfer/referral listed in the batch has a corresponding entry
- All string values are from the allowed enum sets
- All counts are integers and sum correctly
- Referral/patient/transfer IDs are uppercase exactly as returned by the API

Return only the JSON object. Do not add explanation, markdown fences, or commentary.

## Parallelism

The portal is fast for individual lookups. Fetch patient details in parallel for all patients in the batch. Fetch ICD metadata in parallel for all distinct codes. This keeps total latency low even for large batches.

## When answers differ from what you expect

The API data is the source of truth. If a patient's coverage shows `"expired"` and the template allows `"invalid"` for insurance status, use `"invalid"`. Do not second-guess the data. The business rules in [references/business_rules.md](references/business_rules.md) cover the exact mappings from raw API values to template enums.
