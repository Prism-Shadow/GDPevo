---
name: ehr-quality-governance
description: Build normalized JSON packets for EHR quality-governance tasks that require reading a task EHR API, reconciling patient charts, duplicate candidates, referrals, service requests, ICD-10, providers, documents, audit logs, disclosures, encounters, immunizations, and active clinical lists. Use this skill whenever the prompt asks for duplicate-chart merge readiness, referral coordination, referral batch audits, service-request quality validation, care-transition handoff packets, or normalized healthcare packet JSON from an answer_template.
---

# EHR Quality Governance

Use this skill to produce one normalized JSON answer from a read-only EHR task environment and the task's `input/payloads/answer_template.json`.

## Required Workflow

1. Read the user prompt and the local `answer_template.json` before fetching data.
2. Extract every case identifier from the prompt: patient IDs, duplicate candidate IDs, referral IDs, batch IDs, ServiceRequest IDs, provider IDs, service line, and named packet type.
3. Read the API base URL from the prompt or `environment_access.md`. Use only the endpoints allowed there.
4. Fetch evidence from the API. You may use `scripts/ehr_case_fetch.py` to collect a case bundle:

```bash
python skill/scripts/ehr_case_fetch.py \
  --base-url "$TASK_ENV_BASE_URL" \
  --patient P-... \
  --duplicate DUP-... \
  --referral REF-... \
  --batch BATCH-... \
  --service-request SR-... \
  --out /tmp/ehr_case_evidence.json
```

Pass only the IDs that appear in the current task. For ServiceRequest-only tasks, pass the patient ID if known; otherwise the helper will scan patient-scoped ServiceRequest endpoints.

5. Read [references/ehr_quality_rules.md](references/ehr_quality_rules.md) before drafting the answer. Apply those rules through the schema and enums in the current task template.
6. Build the answer from API evidence, not from assumptions. Cross-check list endpoints against detail endpoints when both are available.
7. Return only the JSON object requested by the template. Do not include markdown, explanatory prose, source notes, or extra top-level schema metadata.

## Template Handling

- If the template has `top_level_required_keys` or `required_top_level_keys`, emit exactly those answer keys unless the prompt explicitly adds another required key.
- If the template itself is the answer skeleton with placeholder strings, preserve the skeleton's keys and replace placeholders with normalized values.
- Do not emit helper/template-only keys such as `description`, `schema`, `types`, `ordering_rules`, or `*_ordering` unless the required answer keys explicitly include them.
- Use exact enum strings from the template. If multiple enum labels seem plausible, choose the one supported by the strongest API evidence and the packet family rules.
- Populate duplicate conceptual sections consistently when the template asks for both legacy and normalized forms of the same data.

## Evidence Priorities

- Treat patient-scoped active list endpoints as authoritative for active condition, medication, and allergy keys. Use only records whose `status` is `active` unless the template asks for excluded or inactive records.
- Use duplicate candidate details for candidate status, match/conflict signals, preview target/source, and preview clinical keys, then verify demographics and active lists against patient endpoints.
- Use referral details or batch referral rows for referral status, urgency, authorization, diagnosis, narrative, documents received, patient, and receiving provider.
- Validate diagnosis and reason codes with `/api/icd10/{code}`. Use the returned chapter, expected terms, and laterality requirement to classify coding and narrative issues.
- Validate ServiceRequest service codes with `/api/service-codes/{code}` and provider/service-line details with `/api/providers/{provider_id}`.
- Select documents, audit logs, encounters, disclosures, and immunizations by relevance to the requested packet, final/permitted/signed status where applicable, and recency when the template asks for latest/current evidence.

## Output Discipline

- Sort arrays as the template requires. For sets, sort strings ascending; for referral-object arrays, sort by `referral_id`; for code-validation objects, sort by `code`; for handoff encounter lists, use newest-to-oldest among selected encounters.
- Use `null` only where the template allows it or where an absent value is explicitly represented as nullable.
- Keep stable IDs in evidence fields. Avoid narrative explanation when the schema asks for normalized codes or IDs.
- Before final output, self-check that every required field is present, every enum value is legal, no inactive/unrelated distractor is included, and the JSON parses.
