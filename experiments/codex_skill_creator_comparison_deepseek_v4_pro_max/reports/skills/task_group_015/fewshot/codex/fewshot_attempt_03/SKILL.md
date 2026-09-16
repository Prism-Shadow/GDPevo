---
name: ehr-quality-governance
description: Solving EHR quality-governance tasks that prepare normalized JSON packets against a shared FHIR/REST API. Use when the task involves duplicate merge readiness, referral coordination, care transition packets, service request quality review, batch referral audits, or any clinical-data reconciliation workflow that requires structured output conforming to a supplied answer template. Also use when the prompt references patient/duplicate/referral/encounter/ICD-10/provider/immunization/disclosure/audit-log endpoints and expects normalized clinical keys, match/conflict signals, chapter-based code validation, laterality checks, authorization readiness, follow-up queues, or tiered action plans.
---

# EHR Quality-Governance

Solve clinical quality-governance tasks by collecting evidence from a shared REST API, applying deterministic decision rules, and returning normalized JSON that conforms to a supplied answer template.

## Core Workflow

1. Read the prompt, the answer template (under `input/payloads/answer_template.json`), and any supporting payload documents.
2. Map the task to one of the task families described below.
3. Call the task-environment endpoints (see [api_endpoints.md](references/api_endpoints.md)) to gather every relevant record.
4. Apply the decision rules in [decision_rules.md](references/decision_rules.md) to compute normalized values.
5. Populate every required key in the template, using the field types and enums the template defines. Sort set-arrays alphabetically unless the template says otherwise. Use `null` for unknown optional string fields.

## API Conventions

- Base URL is given as `<TASK_ENV_BASE_URL>` in the prompt. Use it exactly.
- All endpoints are read-only `GET`.
- See [api_endpoints.md](references/api_endpoints.md) for the full endpoint catalog and typical FHIR resource shapes.

## Data Model

- Normalized keys (conditions, medications, allergies) follow snake_case: lowercase, spaces to underscores, special characters stripped. See [data_model.md](references/data_model.md).
- ICD-10 codes map to chapters. Orthopedics expects Musculoskeletal (M00-M99) primary codes; Injury (S00-T88) codes not in the S80-S89 knee range are out-of-chapter. See [data_model.md](references/data_model.md).

## Task Families

### Duplicate Merge Readiness

Produce a merge packet for a duplicate-candidate pair. Query the duplicate candidate, both patients' active lists, documents, audit logs, and providers. Determine canonical target/source, match/conflict signals, clinical key unions, excluded distractors, and packet readiness.

### Referral Coordination

Produce a referral coordination packet for a single referral-patient pair. Query the referral, patient, all clinical lists, encounters, documents, ICD-10 codes, and the provider directory. Validate diagnosis codes, assess allergy readiness, select the recent encounter that matches the referral narrative, check required documents per service line, classify authorization readiness, pick referral-letter field choices.

### Care Transition Packet

Produce a handoff packet for a patient-recipient-provider pair. Query the patient, clinical lists, encounters, immunizations, disclosures. Select the most-recent handoff-relevant encounters (apply the service-line window), identify the latest immunization, validate the disclosure, derive risk flags from active conditions/medications/allergies, and classify packet readiness.

### Duplicate Review with ServiceRequest

Cross-validate a duplicate candidate and a draft ServiceRequest. Query the duplicate candidate, both patients, the ServiceRequest, and ICD-10/service-code endpoints. Produce a duplicate decision, validate service code and reason codes against patient evidence, check SBAR coverage.

### Batch Referral Audit

Audit a referral batch. Query the referral search/detail, ICD-10 lookup, and patient/provider records for every referral. Identify invalid chapter codes, laterality/narrative mismatches, duplicate groups, insurance anomalies, follow-up queues, and action-plan tier assignments. Produce summary counts.

## Decision Rules

See [decision_rules.md](references/decision_rules.md) for the full rule catalog covering merge disposition, match/conflict signals, clinical union reconciliation, document selection, ICD-10 chapter validation, laterality/narrative mismatch detection, authorization readiness, referral-letter field selection, encounter selection, risk-flag derivation, disclosure validation, service-code validation, reason-code validation, SBAR coverage, duplicate group detection, insurance anomaly detection, follow-up queue classification, and action-plan tier assignment.

## Output Discipline

- Return only the JSON object. No narrative, no markdown fences unless the prompt explicitly allows them.
- Prefer `null` for absent optional fields; use empty arrays `[]` for empty sets.
- Sort array sets alphabetically by their natural string key.
- Use the exact key names from the answer template.
