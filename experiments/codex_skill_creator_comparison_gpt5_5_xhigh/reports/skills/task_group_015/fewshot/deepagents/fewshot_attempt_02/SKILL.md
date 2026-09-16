---
name: ehr-quality-governance
description: Reusable workflow for solving read-only EHR quality-governance JSON tasks against a task API. Use when prompts ask for normalized duplicate-chart merge readiness packets, referral coordination packets or audits, care transition packets, ServiceRequest quality checks, active-list reconciliation, ICD/service-code validation, provider contacts, evidence ID selection, risk flags, follow-up queues, action tiers, or summary counts from patient/referral/provider/duplicate records.
---

# EHR Quality Governance

## Overview

Produce normalized JSON answers for read-only EHR quality tasks by reconciling the prompt, answer template, and task API evidence. Treat the template as the output contract and the API as the source of truth for current records.

## Required First Pass

1. Read the task prompt, every file under `input/payloads/`, and especially `answer_template.json`.
2. Read `environment_access.md` only to obtain the base URL and allowed endpoints.
3. Extract requested IDs from the prompt and payloads: patient IDs, duplicate candidate IDs, referral IDs or batch IDs, ServiceRequest IDs, provider IDs, ICD-10 codes, and service codes.
4. Fetch only the evidence needed from allowed GET endpoints. If a list/search endpoint returns more than requested, filter locally by the prompt's IDs, batch, service line, or date.
5. Read [references/ehr-quality-rules.md](references/ehr-quality-rules.md) before classifying any duplicate review, referral packet, care transition, ServiceRequest, or batch audit.
6. Fill the template exactly. Return one JSON object only; do not include prose, markdown, comments, or unrequested keys.

## API Evidence Checklist

Use these endpoint families as needed:

- `GET /api/patients/{patient_id}` for demographics, canonical status, PCP, insurance, and contact signals.
- `GET /api/patients/{patient_id}/conditions`, `/medications`, `/allergies` for active normalized keys and clinical evidence.
- `GET /api/patients/{patient_id}/encounters`, `/documents`, `/immunizations`, `/disclosures`, `/service-requests` for packet evidence.
- `GET /api/duplicates/{candidate_id}` for match/conflict signals and merge preview.
- `GET /api/referrals/{referral_id}` or `GET /api/referrals` for referral detail and batch audits; filter locally.
- `GET /api/providers/{provider_id}` for receiving, performer, requester, or PCP contact fields.
- `GET /api/icd10/{code}` and `GET /api/service-codes/{code}` for code validation.
- `GET /api/audit-logs` for audit evidence; filter locally to the requested patient IDs, candidate, merge/import/identity events, and relevant summaries.

## Normalization Rules

Use `status == "active"` records for active clinical lists unless the template asks for inactive or excluded distractors. De-duplicate by `normalized_key`, sort set-like arrays ascending, and preserve object ordering only when the template specifies it.

Validate every emitted ID and contact field against the API. For nullable fields, use `null`, not an empty string. For booleans and counts, compute from the emitted evidence, not from narrative impressions.

Do not reuse values from previous tasks or examples. Recompute patient IDs, provider names, dates, evidence IDs, dispositions, and counts from the current prompt and API data.

When the prompt names a specialist or recipient provider, emit that provider from the directory. When a referral or ServiceRequest names a provider ID, dereference it before outputting name, facility, service line, phone, or fax.
