## FHIR resource shapes

This reference covers every resource type exposed by the API and the key fields you need for governance workflows. FHIR resources follow standard FHIR R4 structure: each resource has a resourceType, an id, and type-specific fields.

### Patient

Key fields:
- `resourceType`: "Patient"
- `id`: patient ID string (e.g., "P-12345")
- `identifier`: array of identifiers; look for `enterprise_mrn` system
- `name`: array of HumanName objects; `[0].given`, `[0].family`
- `telecom`: array of ContactPoint; `system` (phone/email), `value`
- `gender`: "male" | "female" | "other" | "unknown"
- `birthDate`: YYYY-MM-DD
- `address`: array of Address; `[0].line`, `[0].city`, `[0].state`, `[0].postalCode`
- `generalPractitioner`: array of references to provider IDs

Use the `name` array to derive display names. Use `birthDate` for DOB matching. Check `telecom` for phone and email identity signals.

### Condition

Key fields:
- `resourceType`: "Condition"
- `id`: condition ID
- `clinicalStatus`: `coding[0].code` — "active", "inactive", "resolved", "recurrence", "remission"
- `verificationStatus`: `coding[0].code` — "confirmed", "unconfirmed", "differential", etc.
- `code`: CodeableConcept with `coding[0].code` (ICD-10 code string) and `coding[0].display` (human-readable description)
- `normalized_key`: pre-computed key (e.g., "hypertension", "right_knee_oa"). Use this directly.
- `onsetDateTime`: onset date string

Filter for `clinicalStatus = "active"` and `verificationStatus = "confirmed"` when collecting active condition keys. Exclude inactive/resolved/entered-in-error conditions.

### Medication / MedicationStatement

Key fields:
- `resourceType`: "MedicationStatement" or "Medication"
- `id`: medication ID
- `status`: "active", "inactive", "completed", "entered-in-error", etc.
- `medicationCodeableConcept`: `coding[0].code` and `coding[0].display`
- `normalized_key`: pre-computed key (e.g., "metformin", "aspirin")
- `dosage`: array of dosage objects with `doseQuantity.value`, `doseQuantity.unit`, `route.text`, `timing.code.text`

Filter for `status = "active"` when collecting active medication keys. For medication highlights, extract dose, route, and frequency from the dosage array.

### AllergyIntolerance

Key fields:
- `resourceType`: "AllergyIntolerance"
- `id`: allergy ID
- `clinicalStatus`: `coding[0].code` — "active", "inactive", "resolved"
- `code`: CodeableConcept with `coding[0].display` (allergen name)
- `reaction`: array of reaction objects; `[0].manifestation[0].text`, `[0].severity`
- `normalized_key`: pre-computed key

Filter for `clinicalStatus = "active"` for readiness assessments. Use `reaction[0].severity` for severity classification.

### Encounter

Key fields:
- `resourceType`: "Encounter"
- `id`: encounter ID
- `period`: `start` date
- `type`: array of CodeableConcept; `[0].coding[0].display` (e.g., "office_visit", "care_transition")
- `status`: "planned", "arrived", "triaged", "in-progress", "finished", "cancelled"
- `diagnosis`: array of `condition.reference` with condition IDs

For signed status, look at `status`. "finished" implies signed/complete. Sort encounters by `period.start` descending for recency.

### Immunization

Key fields:
- `resourceType`: "Immunization"
- `id`: immunization ID
- `occurrenceDateTime`: YYYY-MM-DD
- `vaccineCode`: CodeableConcept with `coding[0].display`
- `status`: "completed", "entered-in-error", "not-done"

Filter for `status = "completed"`. Sort by `occurrenceDateTime` descending to find the latest.

### DocumentReference

Key fields:
- `resourceType`: "DocumentReference"
- `id`: document ID
- `status`: "current", "superseded", "entered-in-error"
- `type`: CodeableConcept with `coding[0].display` (e.g., "echocardiogram", "office_note", "chart_summary")
- `date`: date of the document
- `subject`: `reference` to patient ID

For document evidence, prefer documents with `status = "current"`. Chart summaries should be excluded from merge packets unless explicitly needed.

### Disclosure (Consent)

Key fields:
- `resourceType`: "Consent"
- `id`: disclosure ID
- `status`: "active", "proposed", "rejected", "inactive", "entered-in-error"
- `dateTime`: YYYY-MM-DD
- `category`: array; look for `coding[0].display` with purpose
- `provision`: nested consent rules

For care transitions, look for disclosures with status "active" and matching recipient provider reference.

### ServiceRequest

Key fields:
- `resourceType`: "ServiceRequest"
- `id`: service request ID
- `status`: "draft", "active", "on-hold", "revoked", "completed", "entered-in-error"
- `intent`: "proposal", "plan", "order", "original-order", "reflex-order", "filler-order", "instance-order", "option"
- `priority`: "routine", "urgent", "asap", "stat"
- `code`: CodeableConcept with `coding[0].code` (service code string)
- `subject`: `reference` to patient ID
- `requester`: `reference` to requesting provider ID
- `performer`: array of `reference` to performing provider IDs
- `reasonCode`: array of CodeableConcept with ICD-10 codes
- `authoredOn`: YYYY-MM-DD
- `occurrenceDateTime`: YYYY-MM-DD
- `note`: array of Annotation objects; check for SBAR keywords

### Audit log (AuditEvent)

Key fields:
- `resourceType`: "AuditEvent"
- `id`: audit ID (e.g., "AUD-XX-001-A")
- `type`: `coding[0].code` — audit event type
- `recorded`: timestamp
- `entity`: array of entities referenced; look for patient and candidate references

### Duplicate candidate

Key fields:
- `resourceType`: "DuplicateCandidate"
- `id`: candidate ID (e.g., "DUP-XX-001")
- `status`: "confirmed_duplicate", "needs_review", "not_duplicate"
- `primaryPatient`: `reference` to one patient ID
- `duplicatePatient`: `reference` to the other patient ID
- `matchSignals`: array of signal labels (e.g., "same_dob", "same_phone")
- `conflictSignals`: array of conflict labels (e.g., "address_abbreviation")
- `conditionUnion`: array of condition objects with `normalized_key`
- `medicationUnion`: array of medication objects with `normalized_key`
- `allergyUnion`: array of allergy objects with `normalized_key`
- `evidenceDocumentIds`: array of document ID strings
- `evidenceAuditIds`: array of audit ID strings

### Referral

Key fields:
- `resourceType`: "ReferralRequest" or "ServiceRequest"
- `id`: referral ID
- `status`: "active", "cancelled", "completed", "unknown"
- `requester`: provider reference
- `patient`: patient reference
- `diagnosisCode`: CodeableConcept (primary diagnosis)
- `supportingCodes`: array of CodeableConcept
- `narrative`: free-text reason for referral
- `serviceLine`: e.g., "cardiology", "orthopedics"
- `authorizationStatus`: "approved", "pending", "denied", "unknown"
- `batchId`: batch identifier string
- `requestedDate`: YYYY-MM-DD
- `officeNoteMissing`: boolean
- `imagingStatus`: "received", "missing", "pending"
- `urgent`: boolean
- `duplicateGroupId`: string (if part of a duplicate group)
- `providerId`: assigned/receiving provider ID
- `insuranceId`: patient insurance identifier

### ICD-10 (CodeSystem entry)

Key fields:
- `resourceType`: "CodeSystem"
- `code`: ICD-10 code string (e.g., "M17.11")
- `display`: clinical description
- `chapter`: ICD-10 chapter name (e.g., "Musculoskeletal", "Circulatory")
- `laterality`: "left", "right", "bilateral", or null

### Provider (Practitioner)

Key fields:
- `resourceType`: "Practitioner"
- `id`: provider ID (e.g., "PRV-XX-020")
- `name`: array of HumanName; `[0].text` or `[0].given` + `[0].family`
- `qualification`: array; look for role codes
- `role`: string (e.g., "Cardiologist", "Primary Care")
- `serviceLine`: string (e.g., "cardiology", "orthopedics", "primary_care")
- `facility`: string
- `telecom`: array with `system` (phone/fax), `value`

### Service Code

Key fields:
- `resourceType`: "CodeSystem"
- `code`: service code string (e.g., "ORTHO-CONSULT")
- `display`: human-readable description
