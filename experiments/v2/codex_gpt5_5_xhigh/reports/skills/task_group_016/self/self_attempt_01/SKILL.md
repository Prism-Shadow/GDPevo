---
name: clinic-protocol-json
description: Produce protocol-bound structured JSON answers from a synthetic clinic runtime. Use when a task asks Codex to review patient, case, observation, medication, allergy, imaging, registry, social-context, or protocol data from a provided clinic environment and return exactly the JSON object specified by an answer template, including evidence identifiers, disposition or routing decisions, safety checks, medication or lab recommendations, red flags, restrictions, and follow-up timing.
---

# Clinic Protocol JSON

## Operating Rules

Read the task prompt, every provided payload, and the answer template before querying the runtime. Treat the template as the output contract: required keys, constants, enum spellings, nullability, ordering rules, timestamp formats, and numeric precision must be followed exactly.

Use only the task's environment access document for runtime access. Do not browse externally. Do not invent endpoints, credentials, identifiers, protocols, observations, or medication details. Keep runtime actions read-only unless the task explicitly requires mutation; clinical decision-support and order-entry support tasks should not place orders.

Return one JSON object only. Do not include markdown, comments, narrative text, or extra top-level keys when the template disallows them.

## Runtime Review Workflow

1. Identify the target task identifier, case identifier, patient identifier source, clinical topic, and required output schema from the prompt and template.
2. Read the environment access file and derive the base URL and allowed endpoints from it.
3. Retrieve the target case first, then the linked patient and relevant supporting resources:
   - observations and labs for values, status, code, effective time, and eligibility windows
   - allergies and medications for medication safety and contraindications
   - problems, imaging, encounter facts, registry entries, and social-context data when relevant
   - protocol lists and protocol details for thresholds, routing rules, follow-up timing, escalation criteria, and allowed interventions
4. Use a read-only query endpoint only when listed and when it helps filter or join runtime data. Prefer targeted requests over broad dumps when identifiers are known.
5. Record stable evidence identifiers while reading. Include the sources that directly support case identity, patient identity, key clinical findings, protocol decisions, and safety constraints.

## Clinical Reasoning

Apply the runtime protocol, not general medical memory, whenever protocol material is available. If case facts and protocol rules conflict with generic expectations, follow the task protocol and preserve evidence identifiers.

For observation and lab tasks:
- Match the target patient, target code, required status, and time window exactly.
- Treat inclusive and exclusive window boundaries as stated by the template or protocol.
- Sort matched and excluded observation ids using the template's ordering rule.
- Select "latest" only from eligible final observations, not from pending, wrong-code, wrong-patient, or out-of-window distractors.

For assessment, disposition, imaging, routing, and follow-up tasks:
- Map documented findings to the allowed enum values exactly.
- Separate present red flags from explicitly absent red flags when the schema asks for both.
- Do not claim absence, normal imaging, clear lungs, no loss of consciousness, no vomiting, no photophobia, or similar negative findings unless the runtime evidence supports that claim.
- Choose escalation, emergency evaluation, imaging, or urgent notification when protocol red flags or thresholds require it.
- Use protocol-defined follow-up timing and route; express timing in the template's required unit and precision.

For medication or order-entry support:
- Check allergies, contraindications, renal function, active medications, urgent symptoms, and protocol thresholds before recommending therapy.
- Avoid medications that conflict with documented allergens or contraindications.
- Populate order-ready fields only when the template and protocol support a recommendation. Use nulls only where allowed when no medication or lab is recommended.
- Keep recommendations advisory when the prompt says not to mutate the runtime or place orders.

For care-management routing:
- Distinguish chart-derived facts from member-disclosed or outreach-dependent facts.
- Use numeric anchors from the record with the requested precision.
- Select program, risk tier, priority problems, referrals, outreach stance, care-plan minima, and escalation conditions from protocol criteria and documented evidence.

## Output Construction

Build the JSON from the template outward:

- Include every required top-level key.
- Preserve required constants from the prompt or template.
- Use allowed enum values verbatim.
- Use arrays as sets unless the template defines an ordering rule; omit duplicates.
- Use ISO-8601 UTC timestamps with a trailing `Z` when required.
- Round numeric values only to the requested precision.
- Place `null` only in fields whose type allows it.
- Put evidence ids in the requested order, or in descending relevance when no stricter rule exists.

Safety-check booleans should reflect the final answer, not just the source data. Set them to true only when the answer avoids the unsupported or prohibited claim named by the check, and ensure the clinical fields do not contradict those booleans.

## Final Validation

Before responding:

1. Parse the JSON mentally or with a local checker if available.
2. Compare top-level keys against the template.
3. Check each enum, nullable field, timestamp, numeric precision, and array ordering rule.
4. Confirm every clinical decision has runtime or protocol evidence.
5. Confirm the response contains no prose outside the JSON object.
