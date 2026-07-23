# Field Families — how recurring fields are sourced and filled

Templates vary by clinical domain, but the same field families recur. This maps each family to its source in the runtime and how to fill it. Use the task's `answer_template.json` for the exact allowed values; this file is the "where from / how to think about it" layer.

## Identifiers
- `task_id` — from the template's constant or the task directory name.
- `case_id` — from the prompt, verbatim.
- `patient_id` — from `GET /api/cases/{case_id}` (or the case record), verbatim. Never guessed from the case id string.
- `evidence_ids` — stable ids of resources you actually relied on: case, encounter, observation, imaging, medication, protocol, registry. Follow the template's ordering rule (case-id-first, descending relevance, or set). Don't pad the list with resources you didn't use.

## Assessment / risk / disposition
- `primary_assessment` / `risk_level` / `risk_tier` — chosen from the protocol's criteria applied to the evidence (vital bands, lab thresholds, risk-score cut-offs).
- `disposition` — outpatient vs ED transfer vs home observation, per protocol thresholds.
- `imaging_recommendation` — driven by protocol red-flag criteria (e.g. PECARN-style), not by gestalt.

## Red flags
- `red_flags` — only flags the evidence supports.
- `absent_red_flags` (when requested) — the specific high-risk flags the record does NOT show, drawn from the template's `absent_red_flags` enum. Asserting absence is still a claim; only list flags you actually checked the evidence for.

## Medication / order plan
- Choose the `antibiotic_strategy` / `potassium_plan` / `medication_order.status` enum first; that decision governs whether med details are populated or null.
- Fill `medication`, `dose`, `route`, `frequency`, `duration_days` (or `oral_dose_mEq`, `ndc`) only when the plan prescribes; otherwise null per spec.
- `avoid_allergens` — from `GET /api/allergies`. Cross-check every recommended drug against the patient's allergens; if a conflict exists, switch strategy or defer (e.g. `defer_antibiotic_selection_to_ed`, `hold_due_to_contraindication`).
- Contraindication screen (`contraindications` object): dialysis dependence, arrhythmia symptoms, eGfr — pulled from observations / problems / registry.

## Stabilization / urgent actions
- `stabilization_actions` / `urgent_actions` — only when the protocol's thresholds trigger them (e.g. SpO₂ < 90 → supplemental oxygen + ED transfer; critical K → EKG now + telemetry/ED). Empty list when none apply. Sort urgent actions by clinical sequence if the template asks.

## Follow-up / return precautions
- `follow_up.timeframe_hours` — whole-hour integer from the protocol, keyed to risk tier.
- `follow_up.route` — from the allowed enum, matched to disposition.
- `return_precautions` — the warning signs that should bring the patient back, from the protocol's enum.

## Observation-window retrieval (lab/protocol-gate tasks)
- `window` — inclusive `from`, exclusive `to`, ISO-8601 UTC `Z`. Derive from the case's named window (e.g. "March 2026").
- `target_code` — the lab code (e.g. `K`).
- `lab_found` — true iff ≥1 final, target-code, in-window observation belongs to the patient.
- `matched_observation_ids` / `excluded_observation_ids` — qualified vs date/code/status-disqualified; both sorted per the template.
- `latest_final` — the chronologically latest matched observation; required when `lab_found`.
- `protocol_gate` — derived from `latest_final.value_mmol_l` band (normal / low-repletion / critical-urgent) or `no_final_lab_in_window`.
- `repeat_lab` — `recommended` + `scheduled_time` per protocol; null scheduled_time when not recommended.

## Care-management routing
- `risk_tier`, `program` — from registry risk score and problem burden per protocol cut-offs.
- `priority_problems` — from `problems`, `care-registry`, `sdoh`; each code at most once.
- `numeric_anchors` — risk score, HbA1c, phosphorus, BP, active med count, pulled directly from observations / registry / medications. Precision per spec.
- `referrals` — disciplines warranted by the problem set (pharmacist, social worker, dialysis coordination, behavioral health, transportation benefits…).
- `outreach_stance` — communication mode keyed to member preference / sensitivity.
- `care_plan_minima` — minimum problem count, weekly follow-up flag, member-stated-priority flag, minimum disciplines, per program rules.
- `escalation_conditions` — the events that should trigger re-contact, from the protocol's enum.
- `source_provenance` — split facts into `chart_facts` (objective, from the chart) vs `member_disclosure_needed` (sensitive SDOH/goals that require the member's own disclosure). This split matters: don't put a transportation barrier in `chart_facts`.

## Safety checks (recurring pattern)
Each template ships booleans that guard against fabricated findings. The pattern is always: the boolean is `true` when the answer contains no unsupported claim of that type. Examples seen:
- respiratory: `no_penicillin_or_sulfa`, `no_normal_cxr_claim`, `no_clear_lungs_claim`.
- head injury: `no_false_loc`, `no_false_vomiting`, `no_false_photophobia`.
Fill them by checking the evidence, not by defaulting to `true`. If a check would be `false`, fix the underlying claim first.
