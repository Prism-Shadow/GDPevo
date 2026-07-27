---
name: clinic-protocol-json
description: Produce exact schema-conformant JSON for synthetic clinic decision-support tasks that require reviewing a runtime patient case, FHIR-like clinical records, observations, medications, allergies, imaging, registry or social-context data, and applicable protocol material. Use for protocol-bound triage, medication, lab-window, care-routing, safety-check, and evidence-provenance outputs driven by an answer_template.json.
---

# Clinic Protocol JSON

## Core Workflow

1. Read the user prompt and the provided answer template before retrieving facts. Treat the template as the output contract: include every required top-level and nested key, use only allowed enum values, preserve required object shapes, and add no extra keys unless the template explicitly permits them.
2. Identify the target case, patient, clinical domain, requested decision, and any target dates, windows, codes, or current-time anchors.
3. Retrieve the target case record first, then gather only supporting records needed by the prompt and template: patient demographics, findings, observations, active medications, active allergies, problems, imaging, registry facts, social-context facts, and the relevant protocol.
4. Build a compact fact table before drafting JSON. Track value, status, effective time, patient id, code, interpretation, and source id for each fact that may affect a required field.
5. Apply the protocol before clinical intuition. Use protocol thresholds, controlled codes, authoritative statuses, routing criteria, ordering rules, and follow-up timing conventions as the primary source of truth.
6. Draft the JSON from the template outward, then validate exact enums, timestamps, numeric precision, array ordering, duplicate removal, allowed nulls, and consistency between assessment fields, safety checks, and evidence.

## Record Selection

- Match records to the target patient unless the template specifically asks for excluded or distractor records.
- Treat only protocol-authoritative statuses as qualifying for decisions. For lab and imaging gates, this usually means final results only; preliminary, canceled, entered-in-error, wrong-code, wrong-patient, and out-of-window records may be relevant only as excluded observations.
- For time windows, use the prompt or case-defined boundary exactly. Apply inclusive starts and exclusive ends when a window is described that way.
- For latest-result fields, filter first by patient, code, status, and window, then choose the greatest effective time. Use the specified secondary sort, often observation id, only for ties or output ordering.
- Do not use a nearby record merely because it has a suggestive value. Wrong specimen/code, wrong patient, wrong status, or wrong date can change the protocol branch.

## Protocol Interpretation

- Respiratory and triage tasks: separate present red flags from absent red flags. Include present findings only when charted or directly supported by final tests. Do not add stabilization, ED transfer, imaging, or urgent actions unless the protocol threshold or trigger is met.
- Injury tasks: distinguish mild symptoms requiring observation from urgent neurologic triggers. Use explicit absences and normal or near-normal exams carefully; avoid asserting absent symptoms that the chart does not support unless the protocol requires that absence for the branch.
- Medication tasks: screen urgent and contraindication branches before routine replacement or outpatient therapy. Calculate doses from protocol formulas, round exactly as instructed, and use null only where the template allows it.
- Allergy-aware plans: use active allergies only, map allergens to medication classes, and avoid implicated classes. Do not recommend a medication class that conflicts with an active allergy when the protocol offers a safer strategy.
- Care-management tasks: route from registry risk thresholds and protocol triggers, then select priority problems, referrals, and escalation conditions only from documented problems, numeric anchors, medication burden, recent utilization, social barriers, and protocol rules. Keep chart-derived facts separate from member-disclosed facts when provenance fields require it.
- Observation-window tasks: report qualifying matches and excluded distractors separately. Sort matched and excluded observation ids exactly as the template specifies.

## Set Fields And Provenance

- Treat arrays of enum codes as exact sets unless the template gives a different ordering rule. Avoid broad, aspirational, or "just in case" codes; extra unsupported codes can be as harmful as missing required ones.
- Include each selected code once. Prefer codes that are directly tied to a source fact or protocol rule.
- Evidence ids should justify the answer, not restate the entire chart. Prefer stable ids for the case, decisive observations, imaging, allergy records, registry/social-context records, visit findings, and protocol material when those sources directly determine an output field.
- Preserve any evidence ordering requested by the template, such as case first or descending relevance.

## Safety Checks

- Set safety-check booleans by auditing the completed JSON against unsupported claims. A `no_false_*` check should be true only when the answer does not assert the prohibited false finding.
- Ensure assessment, disposition, imaging, medication, follow-up, and return-precaution fields agree with each other. For example, do not combine an urgent-disposition branch with routine follow-up unless the protocol explicitly says to.
- Return exactly one JSON object. Do not include markdown, comments, explanations, or narrative outside the JSON.
