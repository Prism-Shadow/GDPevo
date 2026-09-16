---
name: ehr-quality-governance
description: Prepare normalized EHR quality-governance packets and audits against a read-only FHIR-aligned API. Use when the task involves duplicate-chart merge readiness, referral coordination, care transition summaries, ServiceRequest quality validation, or referral batch audits. Trigger on mentions of EHR, FHIR, duplicate candidates, merge packets, referral coordination, care transitions, quality governance, referral audits, ICD-10 validation, or clinical list reconciliation against a patient API.
---

# EHR Quality Governance

This skill covers five families of EHR quality-governance workflows that all
operate against the same read-only API surface. The workflows produce
normalized JSON packets used for merge approval, referral coordination, care
transitions, ServiceRequest quality review, and batch audits.

## Key Principles

**One-pass data gathering.** Before writing any output, gather every record the
task needs in parallel across the API. Read the answer template first and map
every required field to the endpoint calls that will supply it. Then fetch
everything in one burst. Re-reading a record later because a field was missed
is the most common failure mode.

**Answer template is the schema.** The task always ships an answer template
JSON file under `input/payloads/answer_template.json`. Read it first. It
defines required keys, enum values, ordering rules, and set semantics. Emit
only the shape it asks for -- no extra keys, no narrative prose outside the JSON
object.

**Normalized keys, not raw strings.** Condition, medication, and allergy lists
use `normalized_key` values (lowercase, underscores, no codes). When the
template says an array is a set, sort alphabetically unless the template
explicitly says otherwise.

**Exclude distractors.** Every task includes records that do not belong in the
output: inactive conditions, stale encounters, unrelated documents, wrong
service-line referrals. Identify and exclude them. The template often expects
an explicit `excluded_distractors` or `excluded_*` section -- read the template
to know whether it is required.

**Service-line awareness.** The task always names a service line (cardiology,
orthopedics, etc.). Use it to filter records, select providers, validate ICD-10
chapters, and determine which encounters are relevant. The service line is your
lens for every filtering decision.

## Endpoint Quick Reference

All endpoints live at `<TASK_ENV_BASE_URL>` (shown in the prompt, usually
`http://task-env:9015/`). The full details are in
[references/endpoints.md](references/endpoints.md).

### Patient & Clinical Records

| Endpoint | Returns |
|---|---|
| `GET /api/patients` | Patient search/index |
| `GET /api/patients/{id}` | Patient demographics (id, name, dob, sex, mrn, address, phone, insurance, pcp) |
| `GET /api/patients/{id}/conditions` | Condition/problem list with `normalized_key`, `clinical_status`, `code` |
| `GET /api/patients/{id}/medications` | Medication list with `normalized_key`, `status` |
| `GET /api/patients/{id}/allergies` | Allergy list with `normalized_key`, `clinical_status`, `reaction`, `severity` |
| `GET /api/patients/{id}/encounters` | Encounters with date, type, signed_status, diagnosis codes, care plan tags |
| `GET /api/patients/{id}/immunizations` | Immunization records with date, vaccine name |
| `GET /api/patients/{id}/documents` | Clinical documents with type, status, date |
| `GET /api/patients/{id}/disclosures` | Disclosure/consent records with status, purpose, recipient |
| `GET /api/patients/{id}/service-requests` | ServiceRequest/order records |

### Quality & Governance

| Endpoint | Returns |
|---|---|
| `GET /api/audit-logs` | Audit trail entries |
| `GET /api/duplicates/candidates` | Duplicate candidate index |
| `GET /api/duplicates/{candidate_id}` | Single duplicate candidate with match/conflict signals |
| `GET /api/referrals` | Referral search/index |
| `GET /api/referrals/{id}` | Single referral detail (diagnosis code, narrative, status, authorization, provider refs) |
| `GET /api/icd10` | ICD-10 directory index |
| `GET /api/icd10/{code}` | Single code detail (description, chapter) |
| `GET /api/providers` | Provider directory index |
| `GET /api/providers/{id}` | Provider detail (name, role, service_line, facility, phone, fax) |
| `GET /api/service-codes` | Service code directory |
| `GET /api/service-codes/{code}` | Single service code detail |

## Workflow Dispatch

Identify the workflow family from the prompt, then follow the detailed
instructions in [references/workflows.md](references/workflows.md).

| Prompt signals | Workflow | Reference section |
|---|---|---|
| "duplicate-chart," "merge readiness," "duplicate candidate" | Duplicate Merge Packet | workflows.md#duplicate-merge-packet |
| "referral coordination," "referral letter," a single referral ID | Referral Coordination Packet | workflows.md#referral-coordination-packet |
| "care transition," "handoff," a single patient + recipient provider | Care Transition Packet | workflows.md#care-transition-packet |
| "quality-governance queue," "ServiceRequest," a single SR ID | ServiceRequest Quality Review | workflows.md#servicerequest-quality-review |
| "referral audit," a batch ID, "audit" + multiple referrals | Referral Batch Audit | workflows.md#referral-batch-audit |

## Common Patterns

The [references/patterns.md](references/patterns.md) reference covers these
reusable operations in detail:

- **Active list reconciliation** -- building union sets across two patients or
  verifying that active-endpoint lists match a preview
- **Identity signal analysis** -- extracting match and conflict signals from
  demographic comparisons and shared documents
- **ICD-10 validation** -- looking up codes, checking chapter vs. service-line
  expectations, detecting laterality and narrative mismatches
- **Encounter selection** -- filtering encounters by service-line relevance and
  date window, ordering newest-to-oldest, excluding stale records
- **Risk flag derivation** -- mapping clinical conditions/medications to
  perioperative or transition risk flags with encounter evidence
- **Distractor exclusion** -- identifying and documenting inactive, stale, or
  unrelated records
- **Readiness assessment** -- determining whether a packet is ready, blocked, or
  needs review, with blocking-issue codes where the template expects them

## Output Rules

1. Read the answer template first -- every required key, enum, and ordering rule
   lives there.
2. Emit exactly one JSON object. No markdown fences, no trailing prose, no
   `// comments`.
3. For arrays marked as sets, emit items sorted alphabetically unless the
   template states a different order (e.g. newest-to-oldest for encounters).
4. For arrays of objects sorted by a key (e.g. `referral_id`), follow the
   template's ordering rule exactly.
5. Use `null` for optional fields when the data is absent -- do not omit the key.
6. Dates use `YYYY-MM-DD` strings.
7. Enum fields must match one of the template's `allowed_values` exactly;
   never invent a new enum variant.
