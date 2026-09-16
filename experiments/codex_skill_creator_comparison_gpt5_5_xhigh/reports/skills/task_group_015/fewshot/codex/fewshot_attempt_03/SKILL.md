---
name: ehr-quality-governance
description: Use for read-only EHR quality-governance tasks that require querying a task environment API and returning strict normalized JSON for duplicate reviews, merge readiness, referral coordination, ServiceRequest validation, care-transition packets, or referral batch audits using patient, provider, ICD-10, document, audit, and active-list evidence.
---

# EHR Quality Governance

## Core Rules

- Treat the prompt, `answer_template.json`, and any request payload as the output contract. Return JSON only, with exactly the requested shape, enum values, nullability, and ordering.
- Derive every answer value from the current task environment. Do not reuse IDs, dates, names, codes, or packet values from examples.
- Use only read-only endpoints made available by the task environment. Prefer the base URL from `TASK_ENV_BASE_URL`; if absent, read the task's environment access file.
- Read [references/evidence-playbook.md](references/evidence-playbook.md) before solving. It contains the reusable reconciliation and classification rules.
- Use [scripts/fetch_ehr_evidence.py](scripts/fetch_ehr_evidence.py) when it helps collect common EHR records consistently. The script is optional; direct `curl`/HTTP requests are fine when faster.

## Workflow

1. Parse the task.
   - Extract patient IDs, duplicate candidate IDs, referral IDs, ServiceRequest IDs, provider IDs, batch IDs, requested service line, and any named payload files.
   - Read the answer template first. List required top-level keys, nested required keys, set semantics, explicit sort rules, enum domains, count fields, and fields that may be `null`.

2. Gather evidence from the environment.
   - For each patient, fetch demographics plus active-list families: conditions, medications, allergies, encounters, documents, immunizations, service requests, and disclosures as needed by the template.
   - For duplicate tasks, fetch the duplicate candidate record and relevant patient records for both sides.
   - For referral tasks, fetch referral detail or referral search/list records, related patients, requester/performer/receiving providers, documents, ICD-10 code lookups, and authorization/document signals.
   - For ServiceRequest tasks, fetch the ServiceRequest record, service-code lookup, requester/performer providers, reason-code ICD-10 lookups, patient conditions, and supporting encounters.
   - For audit tasks, fetch the whole requested batch, then fetch only the patient/provider/ICD records needed to validate rows and compute counts.

3. Reconcile before writing JSON.
   - Prefer patient active-list endpoints over preview or summary fields for condition, medication, and allergy keys.
   - Include only active clinical records unless the template explicitly asks for inactive, excluded, stale, or distractor evidence.
   - Validate diagnosis and reason codes with ICD-10 lookup data; compare chapter, laterality, and narrative terms against the service line and patient evidence.
   - Resolve providers from the provider directory, not from copied prose in documents.
   - Select documents, encounters, audit logs, disclosures, and immunizations by relevance, status, date, and recipient requirements from the template.

4. Classify readiness and queues.
   - Duplicate merge tasks: separate identity match signals from conflict signals; merge only when the candidate status and evidence support it. Hold for manual review when identity or clinical conflicts remain.
   - Referral coordination tasks: classify authorization, required-document completeness, allergy readiness, diagnosis-code validity, recipient resolution, and final readiness.
   - Care-transition tasks: select relevant handoff encounters in the requested window/order, derive risk flags from active chart evidence, and require permitted disclosure for the recipient.
   - Batch audits: compute invalid code rows, narrative/laterality mismatches, duplicate groups, insurance/patient anomalies, follow-up queues, action tiers, and summary counts from the audited rows.

5. Normalize and verify.
   - Sort arrays exactly as instructed. For set arrays without a custom rule, sort strings alphabetically and objects by the stable ID or key named by the template.
   - Keep IDs stable and exact. Do not replace required IDs with display names.
   - Recompute all summary counts from emitted arrays and audited records.
   - Run `python -m json.tool` on the final answer before submitting, and check that no explanatory text appears outside the JSON object.
