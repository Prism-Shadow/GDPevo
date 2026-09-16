# Task Pattern Reference

Every task follows the same overall flow. This reference describes the five task
families observed in training.

## Common Workflow

1. Parse the **prompt** to extract the target `case_id` and `task_id`.
2. Read `input/payloads/answer_template.json` to learn the exact response schema,
   enum values, required keys, and safety-check fields.
3. Read `environment_access.md` for the `<TASK_ENV_BASE_URL>` and endpoint list.
4. Fetch the case record: `GET /api/cases/{case_id}` → get `patient_id`.
5. Fetch the patient record: `GET /api/patients/{patient_id}`.
6. Fetch related clinical data (observations, imaging, allergies, medications,
   problems, protocols, care-registry, SDoH) as needed by the template.
7. Map the clinical facts onto the template's controlled enum values.
8. Populate `evidence_ids` with the identifiers of records used.
9. Populate `safety_checks` by verifying that the clinical data supports each claim.
10. Output only the JSON object — no markdown fences, no commentary.

## Task Families

### Respiratory Protocol

Uses observations (SpO2, respiratory rate, temperature), imaging (CXR-2V),
allergies (penicillin, sulfonamide classes), and medications.

Key mapping: SpO2 values determine `red_flags` (`hypoxemia_92_93` for 92–93%,
`hypoxemia_below_90` for <90%). CXR findings drive `primary_assessment`.
Allergy records drive `medication_plan.avoid_allergens`.

### Pediatric Head Injury

Uses GCS and neurological observations, case narrative for mechanism of injury.
Distinguishes `red_flags` (findings present) from `absent_red_flags` (findings
explicitly absent in the record). Safety checks verify that loss of consciousness,
vomiting, and photophobia are not falsely claimed.

### Potassium Replacement

Searches observations for code `"K"` with `status: "final"`. Determines the latest
result, maps the mmol/L value to the replacement protocol. Checks eGFR for
contraindications. Produces an order-ready medication recommendation with NDC,
route, frequency, and a scheduled follow-up lab.

### Care Management Routing

Combines registry risk scores, problem list, medication count, labs (HbA1c,
phosphorus, eGFR), blood pressure, and SDoH barriers. Maps to risk tier and
program eligibility. Determines referral codes, outreach stance, care-plan minima,
and escalation conditions. Separates chart-sourced facts from facts requiring
member disclosure.

### Lab Window Retrieval

Searches observations for a target code within a date window. Distinguishes
matching observations (correct patient, code, status, date) from excluded
observations (wrong date, preliminary status, or wrong code). Determines a
protocol gate and repeat-lab recommendation from the latest final result.

## Enum Selection Principle

When the template provides an allowed enum list, select **only** values whose
clinical conditions are directly evidenced in the fetched data. Do not guess or
extrapolate. When a finding is absent, use `absent_red_flags` or omit from the
active list — never invent values.
