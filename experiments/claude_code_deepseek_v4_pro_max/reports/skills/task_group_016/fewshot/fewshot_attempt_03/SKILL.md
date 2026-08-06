# Synthetic Clinic Decision-Support Skill

You are an agent that produces structured clinical decision-support responses for synthetic clinic cases. You work against a read-only FHIR-like REST API that models a clinic runtime environment.

## 1. Read the environment access file

Locate `environment_access.md` in the working directory. It contains:

- `base_url` — the root URL of the clinic runtime (e.g. `http://localhost:9016/`).
- `credentials` — an object with one or more HTTP header keys and values (e.g. `X-Clinic-Token: <value>`). Attach every credential as a request header on every API call.
- `allowed_endpoints` — the permitted HTTP methods and paths (e.g. `GET /api/patients`). Do not call endpoints outside this list.

## 2. Read the task prompt

Read `input/prompt.txt` (or whatever path the prompt lives at for this run). The prompt states:

- The clinical domain and purpose of the task.
- The target case identifier (e.g. `CASE-XXX-NNN`).
- Any specific clinical questions to answer.
- A reference to the answer template at `input/payloads/answer_template.json`.

## 3. Read the answer template

Read `input/payloads/answer_template.json`. It defines the exact JSON shape you must return:

- `required_top_level_keys` — every key you must include at the top level.
- A `fields` (or equivalent) block describing each key's type, allowed enum values, nested structure, required sub-keys, and ordering rules.
- Output rules: return **only** a single JSON object with no markdown fences, no comments, and no extra keys.

Study the template thoroughly before querying the API — the template tells you exactly what data you need to collect.

## 4. Query the clinic API

Use the endpoints listed in `environment_access.md` to retrieve clinical data. The API uses REST semantics:

### Resource endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/patients` | List all patients |
| GET | `/api/patients/{patient_id}` | Single patient by ID |
| GET | `/api/cases` | List all cases |
| GET | `/api/cases/{case_id}` | Single case by ID (includes encounter and clinical context) |
| GET | `/api/observations` | List all observations (lab results, vitals, exam findings, LOINC-coded) |
| GET | `/api/medications` | List all medication records |
| GET | `/api/allergies` | List all allergy/intolerance records |
| GET | `/api/problems` | List all problem-list / condition records |
| GET | `/api/imaging` | List all imaging study records |
| GET | `/api/care-registry` | List all care-registry / risk-score records |
| GET | `/api/sdoh` | List all social-determinants-of-health records |
| GET | `/api/protocols` | List all clinical protocol definitions |
| GET | `/api/protocols/{protocol_id}` | Single protocol by ID |

### Query endpoint

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/query` | Submit a structured query (see below) |

The `POST /api/query` endpoint accepts a JSON body. Use it for targeted retrieval when list endpoints return too much data. A query body typically includes fields like `patient`, `code`, `status`, `date` range, or `category` to filter results.

Use `curl` with `-s` (silent) and include the credential headers from `environment_access.md`:

```bash
curl -s -H "X-Clinic-Token: <token>" "<base_url>/api/cases/<case_id>"
```

### Retrieval strategy

1. **Start with the case**: `GET /api/cases/{case_id}` — this gives you the patient ID, encounter details, and case-level clinical context.
2. **Pull the patient**: `GET /api/patients/{patient_id}` for demographics.
3. **Collect domain-specific data**: Based on the template's fields, query the relevant resource collections (observations, medications, allergies, imaging, protocols, care-registry, sdoh, problems). Filter in your own logic — the list endpoints return all records; you must select those matching your patient and case.
4. **Read relevant protocols**: `GET /api/protocols` or `GET /api/protocols/{id}` to understand decision thresholds, risk-tier criteria, and recommended actions.

## 5. Apply clinical reasoning

Use the data you retrieved to determine each field in the answer template:

- **Identifiers** (`task_id`, `case_id`, `patient_id`): Copy these from the prompt and from the case/patient API responses. The `task_id` is typically the train run identifier from the prompt or template.
- **Assessment / risk fields**: Derive from observations, exam findings, and protocol thresholds. Every assessment value must be traceable to a specific observation or protocol rule.
- **Enumerated fields**: Only use values from the template's `allowed_values` lists. Never invent a value.
- **Numeric fields**: Match the precision and units specified in the template. Use `null` only where the schema explicitly permits it.
- **Lists**: Unless the template specifies an ordering rule, order is not semantically meaningful — but be consistent. Sort by ID or effective_time ascending when the template asks for it.
- **Evidence IDs**: Collect the stable identifiers (case ID, observation IDs, imaging IDs, protocol IDs) that support your determinations. Include the case ID first when the template asks for it, then list clinical source IDs.
- **Safety checks**: These are boolean assertions that certain unsupported or contraindicated findings are absent. Set each to `true` only when the clinical data genuinely supports that assertion.

## 6. Return the answer

- Return **exactly one JSON object** — no markdown code fences, no surrounding prose, no comments.
- Include every `required_top_level_key` from the template.
- Do not include any key not listed in the template.
- Use `null` only where the template explicitly permits it for that field.
- Match enum values exactly as spelled in the template.
- Follow any ordering rules stated in the template.

## Common clinical patterns

These patterns recur across task types. Use them as guidance, not as hard-coded answers.

### Respiratory assessment
- Look for SpO₂ observations to determine hypoxemia red flags (92-93% vs below 90%).
- Check imaging for CXR findings (infiltrates, consolidation).
- Check allergies before recommending antibiotics (penicillin, sulfonamide, macrolide, tetracycline).
- Protocol material defines risk levels and disposition thresholds.

### Head-injury assessment
- Look for GCS scores, loss-of-consciousness documentation, vomiting, neurological exam findings.
- Distinguish red flags that **are present** from red flags that **are absent** — the template may ask for both lists.
- Restrictions cover activity, school/learn, sports, and driving.

### Electrolyte replacement (potassium)
- Identify the latest **final** (not preliminary) serum potassium observation.
- Check renal function (eGFR) and contraindications (dialysis dependence, arrhythmia symptoms).
- Protocol defines thresholds for replacement vs. no replacement vs. urgent escalation.
- Follow-up lab timing is typically protocol-driven (e.g., next-morning recheck after oral replacement).

### Care-management routing
- Pull risk scores from the care-registry, labs (HbA1c, phosphorus), vitals (blood pressure), and medication counts.
- SDOH data drives transportation, financial, and food barrier flags.
- Protocol defines risk-tier → program mapping and outreach stance.
- Source provenance distinguishes facts from the chart vs. facts requiring member disclosure.

### Observation-window retrieval
- The template defines an inclusive `from` and exclusive `to` window.
- Match observations by patient, LOINC/code, status=final, and effective_time within the window.
- Separate matched (qualifying) from excluded (wrong date, code, or status) observation IDs.
- The protocol gate value depends on the most recent final result's relationship to protocol thresholds.

## Authentication

Every API call must include the credential headers from `environment_access.md`. The runtime environment is read-only — do not attempt to create, update, or delete resources. Only `GET` and the `POST /api/query` endpoint are available.
