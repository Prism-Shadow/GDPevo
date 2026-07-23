---
name: synthetic-clinic-protocol-cds
description: Reusable entry instructions for solving protocol-bound clinical decision-support (CDS) tasks against the Harborview Synthetic Clinic REST runtime. Use whenever a task points at a target case id and a <TASK_ENV_BASE_URL> placeholder, ships an answer_template.json output contract, and asks for a single structured JSON result (assessments, risk tiers, dispositions, medication/order plans, lab/observation windows, care-management routing, etc.). Covers runtime access, evidence gathering, protocol application, and strict template conformance.
---

# Synthetic Clinic Protocol CDS — Operating Rules

These rules are distilled from the train-task family. They are **generic**: they never hardcode a specific case, patient, medication, dose, or numeric result. Every value in a final answer must come from the live runtime or from protocol material fetched at run time.

## 0. What a task looks like

Every task in this family has the same three inputs:

1. **A prompt** (`prompt.txt`) that names a target `case_id`, references the runtime via a `<TASK_ENV_BASE_URL>` placeholder, and states the clinical question.
2. **An answer template** (`payloads/answer_template.json`) — the hard output contract.
3. **The runtime access file** (`environment_access.md` at the work root) — the **only** source of truth for how to reach the network.

If any of these is missing, or if extra/unexpected files appear in the work directory, **stop** and surface it (do not invent access or fabricate values).

## 1. Resolve runtime access (from environment_access.md, never from memory)

Do not assume URLs, endpoints, or tokens. Open `environment_access.md` and read it literally.

- Take the **Base URL** from that file and substitute it for every `<TASK_ENV_BASE_URL>` in the task prompt.
- Use **only** the endpoints listed as allowed for the run. Treat the list as a closed set — do not call any endpoint not listed.
- For any endpoint requiring authentication, copy the header/value verbatim from the file (e.g. `POST /api/query` requires the clinic token header). Do not paraphrase or re-derive the token.
- All network access for the task comes from this one file. Do not use external/network knowledge to fill clinical content.

## 2. Read the answer template first and treat it as law

Before fetching anything, read `answer_template.json` end to end. It defines what the result must look like and is the thing the evaluator checks against. Extract:

- **Required top-level keys** — emit exactly these, no more, no fewer (unless the template explicitly says extra keys are ignored).
- **Enums** — every status/tier/disposition/plan/action field has a fixed `allowed_values` list. Only use strings from that list. Never invent or paraphrase an enum value.
- **Null rules** — some fields are `string_or_null` / `integer_or_null` / nullable. Use `null` only where permitted, and use it whenever the clinical situation makes the value not applicable. Never put `null` where a real value is required, and never put a placeholder string where `null` is expected.
- **Numeric precision** — honor stated precision exactly (e.g. "one decimal place", "whole hours", "two decimal places", integer). Round/trim to the requested precision; do not carry extra digits.
- **Units** — include units only where the schema expects a unit-bearing number; for string fields formatted as `systolic/diastolic` or ISO-8601, follow the stated format.
- **List ordering rules** — most lists are "set-like" (order not meaningful, no duplicates). A few mandate a specific sort (e.g. ascending by `effective_time` then `observation_id`, or descending by relevance). Read each list's ordering note and obey it; do not assume all lists are unordered.
- **Expected/required constants** — some fields carry an `expected_constant` / `required_value` (e.g. the task id, the case id). Echo those exactly.
- **Output rule** — the template always requires **exactly one JSON object**, no markdown, no comments, no prose, no extra top-level keys.

## 3. Gather evidence from the runtime

General order (skip any endpoint not allowed for the run):

1. `GET /api/cases/{case_id}` — confirm the case exists; read the `patient_id` and encounter context from it. The `patient_id` returned here is the one to put in the answer.
2. `GET /api/patients/{patient_id}` — patient demographics/context.
3. Pull every clinical resource relevant to the clinical question, from the allowed endpoints: `observations`, `medications`, `allergies`, `problems`, `imaging`, `care-registry`, `sdoh` as applicable.
4. `GET /api/protocols` (list) then `GET /api/protocols/{protocol_id}` for the protocol(s) governing this case. Protocol material defines thresholds, red-flag sets, gating rules, and recommended actions — apply it instead of generic medical knowledge.
5. For targeted queries the prompt asks for, use `POST /api/query` with the required auth header (see §1). Use it for filtered searches (e.g. "all final serum-potassium observations for this patient in a window") rather than paging through broad lists when a precise query is available.

When fetching lists, page/filter to the case or patient under review; do not conflate other patients' data. Capture the **stable identifier** of every resource you rely on (case id, patient id, observation id, imaging id, protocol id, encounter id) — these become `evidence_ids`.

## 4. Observation-window logic (when the question is lab/observation retrieval)

Several tasks ask whether a final result of a specific code exists inside a time window:

- Determine the window bounds from the prompt/case (inclusive start, exclusive end as stated).
- Select observations that match **all** of: the patient, the target code, the window, and the required **status** (e.g. `final`). Exclude results that fail any of these (wrong code, outside window, non-final/prelim/cancelled status, different patient). Keep excluded-but-relevant distractor ids in the excluded list.
- "Latest final" = the qualifying observation with the greatest effective_time (tie-break by observation_id as the template directs).
- The downstream `protocol_gate` value follows from the latest final's value vs. protocol thresholds (normal / low-repletion / critical-urgent), or `no_final_lab_in_window` when nothing qualifies. Let the protocol fetched in §3 define the thresholds.

## 5. Apply the protocol; do not import outside medicine

Reach the assessment, risk tier, disposition, medication/order plan, restrictions, escalation set, and routing **from the protocol material and the case facts in the runtime** — not from general medical training. If the protocol and your general knowledge disagree on a threshold or action, follow the protocol. This keeps answers reproducible and evaluator-aligned.

## 6. Allergy / contraindication safety

When recommending any medication or order:

- Read `allergies` for the patient and carry the allergen classes into `avoid_allergens` / contraindication fields.
- Never recommend a medication whose class matches a documented allergen unless the protocol explicitly permits it. If the only protocol-appropriate agent is contraindicated, choose the `defer_*` / `supportive_care` / escalation enum rather than forcing a contraindicated drug.
- Screen renal/function contraindications the protocol names (e.g. eGFR, dialysis dependence, arrhythmia symptoms) before committing to a dose plan; if contraindicated, switch the plan enum to `hold_due_to_contraindication` / escalation as the template allows.

## 7. Safety-check booleans must be truthful

`safety_checks` fields are guards against unsupported claims. Set each boolean to reflect the actual answer:

- A "no false X" check is `true` only if your answer genuinely does **not** assert X. If you assert a finding (e.g. loss of consciousness, vomiting, photophobia, a normal chest X-ray, clear lungs, penicillin/sulfa use) that the check forbids, set that boolean `false`. Do not default every safety check to `true` — it must match the rest of your object.
- "no normal CXR claim" / "no clear lungs claim" type checks: `true` only if your assessment/tests do **not** state the imaging or exam is normal/clear. If imaging actually shows a finding, you must not claim normality, and the corresponding boolean reflects that.

## 8. evidence_ids and provenance

- `evidence_ids` (and any provenance/source groupings) must contain **real identifiers** returned by the runtime — case id, patient id, observation ids, imaging ids, protocol ids, encounter ids. Never fabricate an id.
- Prefer the target case id first when included, then the clinical source ids, in whatever order the template's ordering rule specifies (some want descending relevance, some want case-id-first stable order).
- Provenance/source-group fields: only list fact keys the template enumerates, and only those actually supported by chart facts vs. member-disclosure facts as the template distinguishes them.

## 9. Disposition, follow-up, stabilization, escalation

- Disposition / imaging / routing enums follow directly from the risk tier and red-flag set under the protocol. If any high-risk red flag is present, escalate disposition and stabilization/urgent actions accordingly; do not hold an outpatient disposition against a present red flag.
- `follow_up` timing is an integer in the stated unit (hours). Pick the timeframe the protocol assigns for the chosen risk tier; use whole units.
- `stabilization_actions` / `urgent_actions`: use the empty list when none are required — do not pad with low-acuity items.
- For order-entry tasks: produce an order-ready `medication_order` only when replacement/medication is actually recommended; otherwise set the order fields to `null`/`not_recommended`/`defer_to_urgent_clinician` exactly as the template's null/enum rules permit. **Never place an order or mutate the runtime** — recommend only.

## 10. Final output discipline

- Emit **exactly one JSON object**, top-level keys = the required set, nothing else.
- No markdown fences, no trailing prose, no comments, no extra keys.
- Validate against the template one more time before returning: every required key present, every enum value in its allowed set, every nullable field correctly null or typed, every numeric field at the right precision, every list ordered per its rule, every expected constant echoed exactly, every safety-check boolean consistent with the rest of the object.
- Do not include task-specific final values learned from any prior task; recompute every value from the live runtime and protocol for the case at hand.

## 11. Do not mutate

These tasks are read-only decision support. Never POST/PUT/DELETE to any endpoint that changes state, never place an order, never write to the runtime. The only write-style call you may make is the read-only `POST /api/query` (filtered retrieval) with the required auth header.

---

Supporting references in this skill directory:
- `runtime_access.md` — how to read `environment_access.md` and call the runtime safely.
- `output_contract.md` — a checklist for conforming to any `answer_template.json`.
