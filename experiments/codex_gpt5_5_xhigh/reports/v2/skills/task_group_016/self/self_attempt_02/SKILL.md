---
name: clinical-protocol-decision-support
description: Solve ClinicProtocol API clinical decision-support tasks by retrieving protocol cards and patient clinical resources, applying local routing/repletion/retrieval/care-management rules, and returning strict JSON with evidence identifiers.
---

# Clinical Protocol Decision Support

Use this SOP for ClinicProtocol API tasks that ask for protocol-based JSON decisions from patients, encounters, observations, medication requests, or care cases.

## Workflow

1. Read `environment_access.md`, set the base URL, and call `/api/status` for service health, synthetic clock, and timezone.
2. Fetch the relevant protocol card before deciding: `/api/protocols` or `/api/protocols/{protocol_id}`. Treat `protocol.outputs` as the allowed vocabulary.
3. Resolve the patient from the prompt. If given an MRN/identifier, call `/api/patients?identifier=<identifier>`, then `/api/patients/{patient_id}` for allergies, active problems, and medication summary.
4. Fetch only task-relevant resources:
   - Current encounter: `/api/encounters?patient_id=<id>&encounter_id=<enc>&kind=<kind>`
   - Labs/vitals/imaging: `/api/observations?patient_id=<id>&code=<code>&status=final&category=<category>&date_from=<date>&date_to=<date>`
   - Medications/orders: `/api/medication_requests?patient_id=<id>&status=active&category=<category>`
   - Care management: `/api/care_cases?case_id=<case>&patient_id=<id>&status=<status>`
5. Apply exact filters yourself even when the API query is narrow: exact `patient_id`, exact `code`, correct status, date window, `panel_header == false`, and current encounter/case context.
6. Return only the requested JSON fields. Use protocol vocabulary exactly, stable key names from the prompt, booleans for yes/no decisions, arrays for multiple tests/restrictions/evidence, and ISO datetimes with offsets when timing is requested.

## Evidence and Identifiers

- Evidence IDs should be API resource identifiers, not display names: `patient_id`, `encounter_id`, Observation `id`, MedicationRequest `id`, and `case_id`.
- Prefer an `evidence_ids` object keyed by decision area when the prompt allows it, e.g. `route`, `diagnosis`, `lab_source`, `exclusions`, `care_plan`.
- For lab retrieval outputs, return matched Observation `id` values and `count`. Sort IDs lexicographically unless the prompt explicitly asks for chronological order.
- For protocol choices, copy enum strings exactly from the protocol card: routes, CT recommendations, antibiotic plan choices, and test option names.
- Do not cite stale, inactive, cancelled, preliminary, entered-in-error, panel-header, or wrong-patient resources as supporting evidence.

## API Habits

- Start broad only for discovery (`/api/protocols`, `/api/status`); then use narrow query parameters to avoid mixing patients or encounters.
- Use patient detail for active allergies, active problem status, and current medication summary. Use MedicationRequest resources for order status and authored orders.
- For observations, always inspect `effectiveDateTime`, `status`, `category`, `code`, `patient_id`, `encounter_id`, `panel_header`, `value`, and `unit`.
- Date windows use the local timestamps in `effectiveDateTime`. Month windows include first day `00:00:00` through last day `23:59:59`.
- Current encounter facts supersede stale problem-list notes. Inactive problems and notes marked stale/conflict are exclusions unless the prompt asks about history.

## Protocol Rules

### Head Injury `HEAD_INJURY_2026`

- `urgent_ed` if the current encounter has any red flag: repeated vomiting, worsening headache, seizure, focal weakness, slurred speech, increasing drowsiness, confusion, amnesia over 30 minutes, anticoagulant use, abnormal gait/coordination, or deteriorating mental status.
- `same_day_clinic` for low-risk symptoms needing clinician review without urgent red flags.
- `home_observation` only when there are no red flags, the neuro exam is normal, and reliable adult observation is available.
- CT recommendation: `urgent` for `urgent_ed`; `consider` for `same_day_clinic` with persistent symptoms or unreliable observation; otherwise `not_required`.
- Activity restrictions: no same-day return to play; no high-risk activity until symptom-free and medically cleared; no driving if symptoms or neurologic concerns are present.
- Follow-up timing: 24 hours for urgent/red-flag cases, 48-72 hours for same-day clinic, 72 hours for home observation.

### Acute Respiratory/Pneumonia `RESP_ACUTE_2026`

- Community-acquired pneumonia requires fever and cough plus focal crackles or chest x-ray infiltrate/consolidation.
- `ed_evaluation` for room-air oxygen saturation below 92%, confusion, hypotension, respiratory rate at least 24, or pleuritic chest pain with hypoxia.
- `outpatient_treatment` when stable with O2 at least 92% and no ED criteria. Use `supportive_care` when pneumonia criteria are not met.
- Antibiotic choices are only `doxycycline`, `respiratory_fluoroquinolone`, `azithromycin`, or `no_antibiotic_protocol`.
- Avoid penicillin-class agents with active penicillin allergy and sulfonamide-class agents with active sulfa allergy. Avoid macrolides and fluoroquinolones when an active local QT-risk medication is present unless ED routing supersedes outpatient selection.
- Tests may include `chest_xray`, `pulse_ox_recheck`, `covid_flu_testing`, `basic_metabolic_panel`, and `blood_culture_if_ed`; use only controlled names from the protocol.

### Potassium Repletion `POTASSIUM_REPLETION_2026`

- Use the most recent final Observation with exact code `K`; ignore LOINC follow-up-code observations, preliminary, cancelled, entered-in-error, and stale older final values.
- Target is 3.5 mEq/L. If the selected value is below target, order oral potassium chloride with NDC `40032-917-01`.
- Dose in mEq: `ceil((3.5 - value) / 0.1) * 10`, rounded up to the next 10 mEq. Use decimal arithmetic to avoid floating-point over-rounding.
- Follow-up serum potassium LOINC is `2823-3`. Schedule the next calendar day at 08:00 in the local encounter timezone; include the timezone offset.
- If the selected value is at or above target, do not invent a repletion order.

### FHIR Lab Retrieval `FHIR_LAB_RETRIEVAL_2026`

- Match Observation resources by exact `patient_id` and exact `code`.
- Count only `status: final` resources with `panel_header: false`.
- Exclude panel headers, preliminary, cancelled, entered-in-error, wrong linked-patient records, wrong codes, and observations outside the requested `effectiveDateTime` window.
- Month windows are inclusive for the whole local month. Verify boundary instants manually after using API date filters.
- Return matched resource IDs sorted lexicographically unless the prompt asks for chronological sorting.

### Complex Care `COMPLEX_CARE_2026`

- Eligible for complex care when registry risk score is at least 0.75, or when recent high-acuity admission plus uncontrolled chronic disease is present.
- Required chart concerns include active disease metrics, recent admissions, medication burden, and SDoH flags when present.
- If `member_persona` is `initially_refuses`, refusal is not final; recommend low-pressure, permission-based outreach explaining voluntary scope.
- Do not guarantee lower costs, ride availability, dialysis-slot flexibility, or approval of assistance.
- Assessment domains must be grounded in chart/referral cues and member-confirmed barriers.
- A compliant care plan has at least 3 problem areas, at least 2 available disciplines, weekly follow-up, and escalation conditions covering clinical plus behavioral or SDoH risk when indicated.

## JSON Pitfalls

- Do not add prose around JSON when the prompt asks for JSON only.
- Do not use display text where enum strings are required.
- Do not mix `identifier`/MRN with `patient_id`; API joins and evidence should use `patient_id`.
- Do not treat a cancelled medication request as active or a patient allergy as inactive unless its status says so.
- Do not let a normal stale vital/lab override a current abnormal encounter value.
- Do not count linked charts with similar IDs; exact patient ID matching is mandatory.
- Do not omit offset/timezone on scheduled follow-up datetimes.
- Do not over-select tests or antibiotics outside the protocol's controlled option lists.
