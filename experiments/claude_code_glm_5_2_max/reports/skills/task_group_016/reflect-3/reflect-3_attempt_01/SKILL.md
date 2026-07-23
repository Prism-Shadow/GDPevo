---
name: synthetic-clinic-protocol-cds
description: Produce a single protocol-bound JSON decision-support object for a synthetic clinic case. Use when a task names a clinic case id, points to a clinic runtime environment whose access is listed separately, supplies an answer_template.json, and asks you to return only a JSON object driven by clinic protocol rules. Covers respiratory, pediatric head-injury, potassium repletion, care-management routing, and observation-window retrieval task families.
---

# Synthetic Clinic Protocol Decision Support

This skill solves tasks of the form: given a clinic **case id**, a **runtime environment** (access details provided separately per run), and an **answer template**, return exactly one JSON object whose fields are derived from the case record and the matching **clinic protocol** — not from general medical knowledge alone.

The protocol is the source of truth for thresholds, codes, and allowed enum values. The template is the source of truth for required keys, types, and precision. General clinical reasoning fills the gaps, but never overrides an explicit protocol rule.

## 0. Inputs you receive

- **Task prompt** — names the target `case_id` (and sometimes the target patient/code/window) and lists what the response must contain.
- **answer_template.json** — the schema: `required_top_level_keys`, per-field `type`/`allowed_values`/`required_keys`, `ordering`/`ordering_rule` notes, and `numeric_precision`/`output_rule` notes. Treat it as a strict contract.
- **Runtime environment access** — provided **separately** for the run (base URL, allowed endpoints, any required auth header/token). Do not assume endpoints or credentials; read them from the access material each run.
- **Protocols** — live in the runtime, keyed by `protocol_id`; each has a `body` of rules.

## 1. Procedure

1. **Read the template first.** Before touching any data, enumerate every required key, its type, allowed enum values, and any ordering/precision rule. Note which fields are `string_or_null` / `integer_or_null` and where `null` is permitted. Note which list fields are "sets" (ordering irrelevant) vs. "ordered" (semantic order required).
2. **Retrieve the case bundle.** Fetch the case by id. The case bundle typically bundles: `case`, `patient`, `findings` (key/value/source_id triples — the curated clinical facts), `observations`, `imaging`, `allergies`, `medications`, `problems`, `sdoh`, and `care_registry`. The `findings` array is the most important section: it is the case author's curated, protocol-relevant fact set, often phrased as present/absent.
3. **Find the matching protocol.** List protocols, then fetch the one whose `title`/`scope` matches the case type (respiratory/CAP, pediatric head injury, potassium repletion, care-management routing, observation-window). Read its `body` fully: `controlled_codes`, thresholds (`*_min`, `*_less_than`, `*_at_least`), `urgent_*` triggers, `routine_*` rules, `authoritative_statuses`, `excluded_statuses`, ordering, and follow-up windows.
4. **Derive each field from protocol + findings** using the heuristics in §2 and the task-family playbook in `references/task_playbooks.md`. Never invent a value the protocol/template does not support.
5. **Emit exactly one JSON object.** No markdown, no comments, no prose, no extra top-level keys. Respect types, nulls, and numeric precision exactly.

## 2. Field-derivation heuristics (transferable)

These held across the task families and are the main levers for a correct answer.

### Identifiers and constants
- `task_id`, `case_id`, `patient_id`: copy `task_id` and `case_id` from the prompt; `patient_id` from the case/registry record (it may differ from any distractor patient ids appearing inside observations).
- When a template marks a field `expected_constant`/`required_value`, echo that exact value.

### Enum assessments and tiers
- Map the assessment enum to the **protocol section that describes the case**, not to the closest generic clinical term. Protocol section names often mirror enum values (e.g. a `mild_tbi_support` band with "no urgent trigger" maps to the mild-TBI-without-LOC enum, distinct from a "concussion features" enum).
- Risk/tier is gated by the protocol's **urgent/escalation triggers**: any trigger present → the highest tier; otherwise tier tracks symptom burden (symptomatic but stable → intermediate; trivial/no features → low). Do not lower a tier just because disposition is home observation.
- Disposition and imaging recommendations follow the same trigger logic: urgent trigger → ED/urgent imaging; otherwise home observation / no immediate imaging.

### Set fields are exact-matched — do not over-include
This is the single most common error source. List fields (red flags, recommended tests, restrictions, problems, referrals, escalation conditions, evidence ids) are checked as **sets**: an extra or missing member makes the whole field wrong.
- Include **only** members that are explicitly documented in the case `findings` or directly required by the protocol.
- Do **not** add "standard of care" items that are not actually present/ordered (e.g. a lab test that was never resulted, a red flag whose finding is stated "absent", a restriction triggered by a medication class the patient is not on).
- Use the `findings` present/absent language literally: a finding value of "absent" means that red flag is **absent** (list it under absent-flags if the schema has one, never under present red flags). A "mild"/"stable" symptom is present-but-mild where the enum has a mild variant; a "worsening" variant requires worsening explicitly.
- Distractor medications matter: if a restriction clause keys on "sedating medicine" and the patient's med is a stimulant, the clause does **not** fire.

### Numeric fields — copy verbatim with the stated precision
- Pull numeric anchors straight from the case `findings`/observations (risk score, HbA1c, phosphorus, BP, med count, eGFR, lab values). Round to the precision the template demands (e.g. risk_score two decimals, HbA1c/phosphorus one decimal, K one decimal).
- Blood pressure is a `"systolic/diastolic"` string, not a number.
- Dose math is protocol-driven: apply the protocol's `routine_dose_rule` (per-0.1-mmol/L multiplier and round-to-nearest) only when the urgent branch is false; compute the deficit from the protocol `target`, not from a generic normal range.

### Codes and identifiers — use protocol `controlled_codes` verbatim
- Medication NDC, follow-up lab LOINC, and test/order codes come from the protocol's `controlled_codes`. Echo them exactly (do not substitute a "more correct" LOINC/NDC from memory).
- For `evidence_ids`, follow the template's ordering rule when one exists (e.g. "case identifier first, then clinical sources"; "descending relevance"). If no ordering is stated, order does not matter but membership still must be exact — prefer the curated source_ids named in `findings` over speculative extras.

### Allergy-aware medication plans
- Read **active** allergies only (inactive ones do not constrain). Avoid the implicated medication classes and select the protocol's allergy-aware alternative strategy. Set `avoid_allergens` to exactly the active allergen classes that map to the enum.

### Timing
- Follow-up hours: use the protocol's `outpatient_follow_up_hours` / `follow_up_hours` value. Where the protocol gives a list (e.g. `[24, 48]`), choose the value matching the case's acuity (more symptomatic → sooner).
- "Next morning" follow-up lab / recheck = the **next calendar day at 08:00:00Z** (ISO-8601 with trailing `Z`), not the current time plus 24h and not a guessed draw time.
- `current_time` comes from the `current_time` finding; echo it as-is with trailing `Z`.

### Observation-window retrieval (special family)
Filter candidate observations by **all four** of: target `code` (e.g. serum potassium code `K`, distinct from whole-blood/POC potassium codes), `status` = final (exclude preliminary/entered-in-error/canceled per protocol `excluded_statuses`), target `patient_id`, and the window bounds (inclusive `from`, exclusive `to`).
- `matched_observation_ids`: every observation passing all four filters, sorted by `effective_time` ascending then `observation_id` ascending.
- `excluded_observation_ids`: **only** relevant distractors that fail on **date, code, or status** (per the template's stated reasons). An observation that fails on *patient* mismatch is not listed here — it is simply not matched and not excluded. Sort by `effective_time` then `observation_id`.
- `latest_final` = the matched observation with the greatest `effective_time` (protocol `same_code_selection`).
- `protocol_gate` derives from that latest final value: normal → `satisfies_recent_final_normal`; low but non-urgent → `recent_final_low_repletion_needed`; critical/urgent → `recent_final_critical_or_urgent`; no qualifying final in window → `no_final_lab_in_window`.
- `repeat_lab`: recommended only when the gate calls for action (low/critical/no-lab); when the gate is `satisfies_recent_final_normal`, `recommended` is false and `scheduled_time` is null.

### Safety-check booleans
- These assert you did **not** make a specific unsupported claim (e.g. "no false LOC", "no normal-CXR claim", "no penicillin/sulfa"). Set them true when your answer correctly avoids the false claim. They exist to catch hallucinated findings — if the case says a finding is absent, never list it as present, and set the corresponding safety check true.

## 3. Cross-check with the read-only query endpoint (when available)
If the runtime exposes a SQL-style read-only query endpoint (it requires the run's auth header), use it only to verify facts already implied by the case bundle — e.g. confirm registry rows (`risk_score`, `medication_count`, `chronic_condition_count`, `dialysis_schedule`) or re-read a protocol's `body_json`. It is not a source of answer values the case/protocol don't already support. Schema-introspection queries are typically blocked; query known resource tables directly.

## 4. Output discipline checklist
- Exactly one top-level JSON object; no markdown fence, no trailing prose.
- Every `required_top_level_keys` present; no extra top-level keys.
- All enum values match `allowed_values` exactly (spelling/case).
- `null` used only where the spec permits; required sub-keys present inside objects.
- Numeric precision matches the template (whole hours/days, one/two decimals as specified).
- List ordering matches the template's `ordering`/`ordering_rule` (set vs. ordered).
- No candidate-specific or task-instance values leaked from training — every value is re-derived from the current case and protocol.

## 5. Supporting reference
See `references/task_playbooks.md` for the per-task-family derivation walkthroughs (respiratory/CAP, pediatric head injury, potassium repletion, care-management routing, observation-window). The playbooks describe the reasoning pattern for each family without containing any specific case answer.
