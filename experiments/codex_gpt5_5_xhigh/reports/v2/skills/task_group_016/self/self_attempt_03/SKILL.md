---
name: clinic-protocol-decision-support
description: SOP for solving ClinicProtocol API clinical decision-support tasks using protocol cards, patient records, and evidence-grounded JSON outputs.
---

# ClinicProtocol Decision Support SOP

Use this skill when a task asks for a clinical protocol decision, routing recommendation, lab retrieval result, medication repletion plan, or care-plan summary using the ClinicProtocol API.

## Operating Rules

- Work from the task prompt, `environment_access.md`, and the remote ClinicProtocol API only.
- If the prompt contains `<TASK_ENV_BASE_URL>`, replace it with the base URL from `environment_access.md`.
- Treat `/api/protocols/{protocol_id}` as the source of truth for allowed output values and local rules.
- Do not use outside clinical guidelines unless the protocol card asks for them. These tasks grade local protocol adherence, not general medical knowledge.
- Return exactly the requested JSON shape. Do not add explanatory prose outside JSON when JSON is requested.
- Ground every decision in API resource fields and include evidence identifiers when the schema allows them.

## API Workflow

Start broad, then narrow with exact filters:

1. Read service context:
   - `GET /api/status`
   - Capture `synthetic_clock` and `timezone` for local-date reasoning when the prompt does not supply a better anchor.
2. Read protocols:
   - `GET /api/protocols`
   - `GET /api/protocols/{protocol_id}`
   - Use the protocol `outputs` section for controlled enums.
3. Resolve patient:
   - `GET /api/patients?identifier=<MRN-or-identifier>`
   - `GET /api/patients/{patient_id}`
   - Use exact `patient_id` after resolving; do not match by name, MRN prefix, or similar linked IDs.
4. Retrieve current encounter when relevant:
   - `GET /api/encounters?patient_id=<patient_id>`
   - Add `&encounter_id=<encounter_id>` or `&kind=<kind>` if the prompt supplies one.
   - Use current encounter `facts`, `start`, `timezone`, and `status` for acute routing.
5. Retrieve observations:
   - `GET /api/observations?patient_id=<patient_id>`
   - Useful filters: `&code=<code>`, `&status=final`, `&category=<category>`, `&date_from=<YYYY-MM-DD>`, `&date_to=<YYYY-MM-DD>`.
   - For date-window tasks, still verify `effectiveDateTime`, `status`, `panel_header`, code, and patient id in returned resources.
6. Retrieve medication requests:
   - `GET /api/medication_requests?patient_id=<patient_id>`
   - Add `&status=active` and/or `&category=<category>` for active medication logic.
   - Patient `medication_summary` is useful for quick active-medication flags; medication request IDs are better evidence when present.
7. Retrieve care cases:
   - `GET /api/care_cases?case_id=<case_id>`
   - Or `GET /api/care_cases?patient_id=<patient_id>&status=open`.
   - Use care-case fields for risk score, admissions, SDoH flags, persona, available disciplines, and referral concerns.

## Output Conventions

- `patient_id`, `encounter_id`, `case_id`, `protocol_id`: exact identifiers from the API. Never substitute MRN, name, or a similar linked identifier.
- `route`: one of the protocol card's allowed route strings.
- `evidence_ids` or protocol-specific evidence arrays: API resource identifiers only, usually `encounter_id`, Observation `id`, MedicationRequest `id`, or `case_id`.
- `matched_observation_ids`: include only resources that pass all filters; sort lexicographically unless the prompt explicitly asks for chronological order.
- `count`: the length of the final matched-resource list after exclusions.
- `tests`, `restrictions`, `assessment_domains`, `disciplines`, and `escalation_conditions`: use concise protocol-grounded strings or the controlled tokens from the protocol card if provided.
- `reasons` or `rationale`: cite clinical facts, not copied paragraphs. Keep the reason traceable to evidence IDs.
- Use JSON booleans and numbers as booleans and numbers, not strings.
- Omit optional fields that the prompt does not request unless the schema says to include them.

## Protocol Rules

### Head Injury Routing (`HEAD_INJURY_2026`)

Allowed routes are `urgent_ed`, `same_day_clinic`, and `home_observation`.

- Choose `urgent_ed` if the current encounter has any red flag:
  - repeated vomiting
  - worsening headache
  - seizure
  - focal weakness
  - slurred speech
  - increasing drowsiness, confusion, deteriorating mental status
  - amnesia over 30 minutes
  - anticoagulant use
  - abnormal gait or coordination
- Choose `same_day_clinic` for low-risk symptoms needing clinician review but no urgent red flag.
- Choose `home_observation` only when there are no red flags, neuro exam is normal, and a reliable adult observer is available.
- CT:
  - `urgent` for `urgent_ed`
  - `consider` for `same_day_clinic`, persistent symptoms, or unreliable observation
  - `not_required` for low-risk home observation
- Activity restrictions:
  - no same-day return to play
  - no high-risk activity until symptom-free and medically cleared
  - no driving if symptoms or neurologic concerns are present
- Follow-up timing:
  - 24 hours for urgent or red-flag cases
  - 48-72 hours for same-day clinic
  - 72 hours for home observation

Common lesson: current encounter facts outrank stale inactive problem-list entries.

### Acute Respiratory Infection / Pneumonia (`RESP_ACUTE_2026`)

Allowed routes are `ed_evaluation`, `outpatient_treatment`, and `supportive_care`.

- Community-acquired pneumonia is supported by fever plus cough with focal crackles, chest x-ray infiltrate, or consolidation.
- Choose `ed_evaluation` for any ED criterion:
  - oxygen saturation below 92 percent on room air
  - confusion
  - hypotension
  - respiratory rate at least 24
  - pleuritic chest pain with hypoxia
- Choose `outpatient_treatment` when stable, oxygen saturation is at least 92 percent, and no ED criteria are present.
- Choose `supportive_care` when pneumonia criteria are not met and the protocol does not require antibiotics.
- Antibiotic choices are controlled:
  - `doxycycline`
  - `respiratory_fluoroquinolone`
  - `azithromycin`
  - `no_antibiotic_protocol`
- Exclusions:
  - avoid penicillin class with active penicillin allergy
  - avoid sulfonamide class with active sulfa allergy
  - avoid macrolide or fluoroquinolone for outpatient selection when an active local QT-risk medication exists, unless ED route supersedes outpatient selection
  - cancelled antibiotic requests are not active therapy
- Tests may include:
  - `chest_xray`
  - `pulse_ox_recheck`
  - `covid_flu_testing`
  - `basic_metabolic_panel`
  - `blood_culture_if_ed`

### Oral Potassium Repletion (`POTASSIUM_REPLETION_2026`)

- Use the most recent `final` Observation with exact local code `K`.
- Ignore preliminary, entered-in-error, panel headers, wrong-code observations, and stale older results when a newer valid `K` exists.
- Target potassium is `3.5` mEq/L.
- If the valid potassium is below target, order oral potassium chloride NDC `40032-917-01`.
- Dose is `10 mEq` per `0.1 mEq/L` below target, rounded up to the next `10 mEq`.
  - Use decimal arithmetic to avoid floating-point rounding mistakes.
  - Formula: `ceil(((3.5 - value) / 0.1)) * 10`, only when `value < 3.5`.
- Follow-up lab:
  - LOINC `2823-3`
  - occurrence is the next calendar day at `08:00` in the local encounter timezone
- The LOINC `2823-3` is for the follow-up order, not the source code for dose selection.

### FHIR Lab Retrieval (`FHIR_LAB_RETRIEVAL_2026`)

- Match Observation resources by exact `patient_id` and exact `code`.
- Date windows use Observation `effectiveDateTime`.
- Month windows include the entire local month:
  - first day `00:00:00`
  - last day `23:59:59`
- Count only `status: "final"` observations.
- Exclude:
  - panel headers (`panel_header: true`)
  - preliminary records
  - cancelled records
  - entered-in-error records
  - linked or similarly named different patients
  - wrong-code records even when display text looks relevant
- Return matched resource IDs sorted lexicographically unless chronological order is explicitly requested.

Common lesson: boundary instants at the very end of the month are included; observations just before the first day are excluded.

### Complex Care Outreach (`COMPLEX_CARE_2026`)

- The complex-care program applies when either:
  - registry risk score is at least `0.75`, or
  - there is a recent high-acuity admission plus uncontrolled chronic disease
- Required chart concerns should cover:
  - active disease metrics
  - recent admissions
  - medication burden
  - SDoH flags when present
- If `member_persona` is `initially_refuses`, refusal is not final. Use a low-pressure, permission-based, voluntary explanation.
- Do not guarantee:
  - lower costs
  - ride availability
  - dialysis-slot flexibility
  - approval of assistance
- Assessment domains must be grounded in chart cues, referral cues, or member-confirmed barriers.
- A complete plan needs:
  - at least 3 problem areas
  - at least 2 disciplines
  - weekly follow-up
  - escalation conditions that cover clinical risk plus behavioral or SDoH risk when indicated

## Common Exclusion Rules

- Use active/current records for decision support unless the protocol asks for historical data.
- Do not count inactive problems as current risk factors.
- Do not count inactive allergies or cancelled medication requests as active exclusions.
- Do not use stale observations when the protocol asks for most recent final results.
- Do not mix patients with similar names, linked MRNs, prefix-overlapping patient IDs, or household relationships.
- Do not include panel headers as lab values.
- Do not infer a route from diagnosis alone; route depends on protocol red flags and stability criteria.
- Do not invent services, disciplines, tests, or guarantees absent from the protocol or API record.

## JSON Pitfalls

- Controlled tokens must match exactly: spelling, underscores, and case matter.
- Evidence arrays should contain identifiers, not copied clinical text.
- Keep arrays deterministic. Use lexicographic resource-id sorting for retrieval tasks and stable clinical-priority ordering for recommendation lists.
- Watch date anchors:
  - acute encounters use encounter `start` and `timezone`
  - lab windows use Observation `effectiveDateTime`
  - service clock is synthetic and local to the API, not the real current date
- Preserve ISO timestamps with timezone offsets when returning scheduled follow-up times.
- For potassium, do not let binary floating-point turn an exact 0.3 deficit into an extra dose increment.
- For respiratory tasks, ED criteria can determine route even when allergy or QT-risk exclusions complicate outpatient antibiotics.
- For head injury tasks, a single red flag is enough for `urgent_ed`; reliable observation only supports home care when no red flags exist.
- For complex-care tasks, do not treat initial refusal as opt-out when the protocol says to continue permission-based outreach.
