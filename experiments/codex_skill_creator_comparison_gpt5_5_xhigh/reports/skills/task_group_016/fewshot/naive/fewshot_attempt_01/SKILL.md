---
name: synthetic-clinic-json-protocol
description: Solve synthetic clinic runtime tasks that require reading a prompt, task-provided answer template, and environment_access.md, querying read-only clinic API endpoints, applying protocol material to patient/case data, and returning one schema-exact JSON object. Use for clinical decision-support, lab-window, medication, respiratory, head-injury, care-management, and similar protocol-bound structured-answer tasks.
---

# Synthetic Clinic JSON Protocol

Use this skill to produce a strict JSON answer for a synthetic clinic task. Treat the prompt, the task payload template, environment access instructions, and live read-only clinic data as the only authority.

## Required Workflow

1. Read the user prompt and the task-provided answer template before querying data.
2. Read `environment_access.md` for the base URL, required headers, and allowed endpoints. Use only listed read-only business endpoints. Do not call judge, scoring, mutation, order-entry, or unlisted endpoints.
3. Extract the target task id, case id, requested clinical domain, required output keys, constants, enum values, numeric precision, ordering rules, nullable fields, and safety booleans from the prompt and template.
4. Build an internal answer skeleton from the template. Do not invent keys. If the template forbids extra keys, return exactly the required top-level keys.
5. Retrieve the target case first, then retrieve the patient and all data needed by the case and protocol: observations, medications, allergies, problems, imaging, care-registry entries, social-context records, and protocol documents. Prefer case-linked ids when present; otherwise filter collection endpoints by patient id, case id, code, date window, protocol name, or domain.
6. Apply the protocol to the retrieved facts. Fill controlled fields with exact enum spellings from the template, not prose.
7. Return one JSON object only. Do not include markdown, comments, citations outside JSON, or explanatory text.

## Runtime Data Handling

- Send the clinic token header exactly as specified in `environment_access.md`.
- Use `GET /api/cases/{case_id}` when possible, then expand from identifiers in the case record.
- Use collection endpoints when direct links are missing; filter client-side if the API does not support query parameters.
- Use `POST /api/query` only as a read-only search helper when it is listed as allowed. Keep the query targeted to the current case, patient, protocol, or observation need.
- Preserve stable source identifiers from records that directly support scored decisions. Evidence ids should usually include the case id when the template requests case provenance, plus observation, imaging, encounter, renal-function, registry, or protocol ids that determine the answer.

## Protocol Application Rules

- Case and patient identifiers: copy the case id and task id from the prompt or template constants. Get the patient id from the runtime record, not from assumptions.
- Observations: require the right patient, code, status, and time window. Prefer final results for lab gates and medication decisions. Select the latest eligible final observation by effective time when the template asks for current status; keep excluded relevant ids when date, code, or status disqualifies them.
- Time windows: respect inclusive and exclusive bounds exactly as the template states. Emit ISO-8601 UTC timestamps in the required format. Derive follow-up or repeat-lab times from the protocol and case context, not from examples.
- Medications: screen allergies, active medications, renal function, dialysis status, pregnancy/status fields if present, and protocol contraindications before recommending medication. If a medication is unsafe or urgent escalation is required, use the template's defer, hold, or urgent enum and null only where permitted.
- Respiratory and imaging tasks: do not claim a normal image, clear lungs, or absence of disease unless the retrieved record says so. Treat hypoxemia, distress, chest pain, hemoptysis, persistent fever, confusion, or worsening dyspnea according to the active protocol.
- Head-injury tasks: distinguish present symptoms from absent red flags. Do not mark loss of consciousness, repeated vomiting, photophobia, seizure, focal weakness, worsening headache, or skull-base signs present unless documented. Use the protocol for imaging, activity, school, sport, driving, and follow-up restrictions.
- Potassium and lab-gate tasks: identify target-code serum potassium observations, exclude preliminary or out-of-window results, and use renal function and symptoms for routine versus urgent routing. Use protocol-provided medication codes, lab codes, dose, frequency, and follow-up timing.
- Care-management tasks: combine chart facts, registry risk, diagnoses, recent admissions, dialysis or chronic disease context, medication burden, social needs, and member-stated barriers. Separate chart-derived provenance from information that requires member disclosure. Use program, referrals, outreach stance, escalation conditions, and care-plan minima from the protocol.

## JSON Final Check

Before answering, verify:

- All required top-level keys and nested required keys are present.
- No extra keys are present when the template disallows them.
- Every enum value is copied exactly from the template's allowed values.
- Lists are unique; sort only when the template specifies an order. Otherwise keep a stable clinical or source order.
- Null appears only in fields whose schema permits null.
- Numeric values follow required precision without adding units inside numeric fields.
- Booleans in safety checks mean the answer avoided the unsupported claim named by that key.
- Evidence ids are stable ids from records actually used for the decision.
- The final response is valid JSON and contains no text outside the object.
