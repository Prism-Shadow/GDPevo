---
name: clinic-protocol
description: Structured clinical protocol decision support for synthetic clinic FHIR-like REST APIs. Use when the task directs you to a clinic runtime with TASK_ENV_BASE_URL and a case ID to produce protocol-bound structured JSON answers for respiratory assessment (RESP-CAP-2026), pediatric head injury (PEDS-HEAD-2026), potassium replacement (K-REPLETION-2026), care management routing (CM-HIGH-RISK-2026), or observation-window retrieval (OBS-WINDOW-2026). Also use for any task that requires reading a clinic case endpoint, applying a protocol from /api/protocols, and returning an answer conforming to a JSON template with controlled enum values.
---

# Clinic Protocol

## Overview

This skill covers structured protocol-driven clinical decision support against a synthetic clinic REST API. The solver reads a target case, retrieves protocol rules, applies those rules to clinical observations and patient context, and returns a single JSON object with controlled values.

## Core Workflow

Every task follows the same five-step pattern:

### Step 1: Read the answer template

The prompt directs you to `input/payloads/answer_template.json`. Read it first. The template defines every required top-level key, allowed enum values, field types, numeric precision rules, and output constraints. The template is the authoritative shape for your answer — never add extra keys or use prose where an enum is required.

### Step 2: Retrieve the case and protocol

Use `GET /api/cases/{case_id}` at `TASK_ENV_BASE_URL`. This endpoint returns a composite object containing the case header, patient demographics, observations, findings, imaging studies, medications, allergies, problem list, care-registry entry, and SDOH records in a single response. This is almost always the only endpoint you need for clinical data.

If the task references a specific protocol, retrieve it with `GET /api/protocols/{protocol_id}`. The protocol body contains the clinical decision rules: thresholds, trigger values, controlled LOINC/RXNORM codes, exclusion criteria, and escalation conditions. Apply protocol rules literally — protocols are deterministic, not advisory.

### Step 3: Extract and filter clinical facts

From the composite case response, extract:

- **Observations**: Filter by `status: "final"` unless the template explicitly accepts other statuses. Protocol rules always use `status: "final"`. Sort by effective_time when ordering matters.
- **Findings**: Free-text clinical facts (chief complaint, symptom presence/absence, social context). Treat negated findings (`"absent"`) the same as absent values.
- **Allergies**: Check `status: "active"` only. Map allergens to the medication class avoidance list in the template.
- **Imaging**: Check `status: "final"` for authoritative impressions.
- **Medications**: Count active medications for polypharmacy triggers.
- **Problems**: Active problems inform risk tiering and program eligibility.
- **Care registry**: When present, use risk_score and program_hint as inputs to routing logic.
- **SDOH**: SDoH domains and severity levels drive referral and outreach decisions.

### Step 4: Apply the protocol rules

Protocol documents define decision boundaries as explicit thresholds and trigger lists. Apply them mechanically:

- For numeric thresholds: compare the observation value to the protocol threshold (e.g., potassium < 3.0 triggers the urgent branch).
- For trigger lists: check whether findings/observations match any item in the protocol's trigger set.
- For dose rules: compute using the protocol's stated formula (e.g., mEq per 0.1 mmol/L below target, rounded to nearest step).
- For status filtering: treat preliminary, canceled, and entered-in-error observations as excluded unless the template explicitly says otherwise.
- For ordering: protocols specify ascending effective_time, then observation_id as tiebreaker.

### Step 5: Produce the JSON answer

Build a single JSON object with exactly the required top-level keys from the template. Follow these rules:

- Use controlled enum values from the template's allowed_values lists. Do not invent new enum values.
- Use `null` only where the template permits it (e.g., medication fields when no medication is recommended).
- Booleans never have quotes — they are JSON `true`/`false`, not strings.
- Include evidence_ids as an array of identifiers for the case and the key observations/imaging used.
- For list fields, ordering is not semantically scored unless the template explicitly states otherwise. Use a stable, reproducible order.
- Do not wrap the JSON in markdown, code fences, or explanatory text.
- Return only the JSON object.

## API Conventions

- **Base URL**: Always `${TASK_ENV_BASE_URL}` as provided in the prompt.
- **Composite case endpoint**: `GET /api/cases/{case_id}` — use this as the primary data source.
- **No authentication**: The task environment is credential-free.
- **Distractor data**: The API returns distractor records mixed with target records. Always filter by the target case_id and patient_id.

See [references/api-reference.md](references/api-reference.md) for the full endpoint listing and response shapes.

## Protocol-Specific Guidance

See [references/protocol-solver.md](references/protocol-solver.md) for detailed decision logic for each protocol type. Read it when the template reveals the protocol domain but the clinical reasoning is not obvious from the protocol endpoint alone.

## Common Pitfalls

- **Allergy-blind medication plans**: Always check active allergies before selecting an antibiotic or medication class. Map allergen strings to the avoid_allergens enum values in the template.
- **Sodium observations in potassium windows**: When the target code is `K`, observations with code `NA` are near-target distractors — exclude them.
- **Wrong-patient observations**: The case endpoint may return observations with a different patient_id. Filter strictly by the target patient_id.
- **Preliminary observations**: Never use preliminary or canceled observations as the clinical basis for a protocol gate or numeric anchor unless the template explicitly permits it.
- **Distractor records**: Generic distractor cases use IDs like `CASE-D####` and can be ignored. Target cases use semantic IDs like `CASE-RESP-102`.
- **Safety checks**: When the template requires safety-check booleans, verify each condition against the clinical data. Set `true` only when the evidence supports the constraint.
