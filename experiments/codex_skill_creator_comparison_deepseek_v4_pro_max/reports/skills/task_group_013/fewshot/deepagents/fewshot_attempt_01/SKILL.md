---
name: cedar-ridge-intake
description: "Cedar Ridge Intake Coordination Portal workflows covering patient access verification, referral auditing, dialysis transfer review, chronic-care enrollment panels, and referral-to-chart activation. Use when the task references the Cedar Ridge Intake Coordination Portal, a TASK_ENV_BASE_URL, or any Cedar Ridge intake batch/roster (e.g. NPI-, ORTHO-, DIAL-, PULM-, DMHTN-). Trigger on phrases like intake coordination, Cedar Ridge, patient access verification, referral readiness, transfer review, enrollment panel, chart activation, or when a JSON answer template requires controlled healthcare-intake vocabularies."
license: MIT
compatibility: designed for codex
---

# Cedar Ridge Intake Coordination

## Overview

The Cedar Ridge Intake Coordination Portal exposes a set of REST endpoints for
healthcare intake workflows: patient demographics, insurance, pharmacy networks,
referrals, transfers, clinical documents, ICD-10 metadata, program candidates,
chart records, and a read-only SQL query endpoint. Every task follows the same
pattern: read the input prompt, read the answer template, fetch live data from
the portal at `<TASK_ENV_BASE_URL>`, cross-reference values across endpoints,
derive decisions from the controlled vocabularies, and output a single JSON
object matching the template exactly.

## Portal Endpoints

| Endpoint | Returns |
|---|---|
| `GET /` | Portal root / health |
| `GET /patients` | All patients |
| `GET /patients/{patient_id}` | Single patient record |
| `GET /referrals` | All referrals |
| `GET /referrals/{referral_id}` | Single referral record |
| `GET /transfers` | All transfers |
| `GET /transfers/{transfer_id}` | Single transfer record |
| `GET /documents` | All documents |
| `GET /chart/{patient_id}` | Patient chart data |
| `GET /programs/{program_code}/candidates` | Program candidate list |
| `GET /icd/{code}` | ICD-10 code metadata (chapter, description) |
| `GET /pharmacies` | Pharmacy directory |
| `POST /query` | Read-only SQL (body: `{"sql": "SELECT ..."}`) |

See [references/api_reference.md](references/api_reference.md) for field-level
schemas of every endpoint response.

## Universal Workflow

1. Read `input/prompt.txt` for the task description and the batch/roster/program
   identifier. Note the `<TASK_ENV_BASE_URL>` placeholder.
2. Read `input/payloads/answer_template.json` for the exact JSON shape,
   controlled vocabularies, ordering rules, and required keys.
3. Replace `<TASK_ENV_BASE_URL>` with the actual base URL given in the task
   environment. Use `curl -s` for every GET call.
4. Collect all referenced records: fetch the collection endpoint first, then
   individual records, then related data (patients for referrals, chart for
   patients, ICD for codes, documents for transfers/referrals).
5. Cross-reference fields across endpoints. For example, referral records link
   to patients and ICD-10 codes; transfer records link to documents and patients.
6. Apply the domain-specific rules documented below and in the references.
7. Assemble the output JSON exactly as the template specifies. Respect every
   ordering rule (ascending IDs, alphabetical for doc types). Use only the
   controlled values from the template.

## ICD-10 Chapter Matching

ICD-10 codes encode chapters in the first character and numeric range:

| Chapter | Code Range | Typical Service Lines |
|---|---|---|
| J00-J99 | Diseases of the respiratory system | Pulmonary |
| M00-M99 | Diseases of the musculoskeletal system | Orthopedics, Spine, Joint |
| S00-T88 | Injury, poisoning, external causes | Trauma (not ortho) |
| I00-I99 | Diseases of the circulatory system | Cardiology |
| E00-E89 | Endocrine, nutritional, metabolic | Diabetes, HTN management |
| N00-N99 | Diseases of the genitourinary system | Dialysis, Nephrology |

A code belongs to chapter X if its leading character and numeric range fall
within the chapter bounds. When a referral's ICD-10 code does not match the
expected chapter for its service line (e.g., an S-code for an orthopedic
referral), flag it as `icd_chapter_mismatch`. The portal's `GET /icd/{code}`
endpoint returns the actual chapter for any code — always validate against that
response, not from memory.

## Insurance, Pharmacy, and Registration Status

Patient records include insurance plan details, prescription benefit (PBM)
information, and preferred pharmacy assignments. When assessing access:

- **insurance_status**: `valid` when coverage is active and includes the service
  line; `invalid` when expired, pending, or excludes the service line; `missing`
  when no record exists.
- **prescription_status**: `valid` when PBM is active and plan matches; `invalid`
  when PBM is inactive or plan mismatches; `missing` when no PBM record exists.
- **pharmacy_status**: `in_network` when preferred pharmacy matches the plan
  network; `out_of_network` when it does not; `unknown` when pharmacy or plan
  data is absent.
- **registration_status** is a function of all status fields plus risk:
  `approved` only when all statuses are valid/in_network and risk is low;
  `rejected` when coverage is expired, service line excluded, or multiple
  hard blockers; `clinical_review` when risk is high or soft blockers exist;
  `hold` when coverage is pending and nothing is expired.

Blocked reason codes map directly to specific conditions found in the data:
`coverage_expired` when plan end date is past, `coverage_pending` when start
date is in the future, `excluded_service_line` when the plan does not cover the
service, `pbm_invalid` / `pbm_missing` / `pbm_policy_mismatch` for PBM issues,
`pharmacy_out_of_network` / `pharmacy_unknown` for pharmacy issues,
`overall_risk_high` when risk is high, and additional codes for missing
demographics/contacts. Only include codes that actually apply to the patient.

## Document Freshness Rules

Dialysis and transfer packets contain lab/vaccine documents with validity windows:

| Document Type | Freshness Limit |
|---|---|
| `hbsag` | 30 days |
| `monthly_labs` | 30 days |
| `ppd_or_cxr` | 30 days |
| `history_physical` | 365 days |
| `hep_b_antibody_core` | No fixed expiry (one-time) |

A document is stale when `(as_of_date - received_date) > freshness_limit_days`.
Use the date implied by the task context or the requested start date as the
reference date for staleness checks.

## Referral Readiness and Chart Activation

Referral audit workflows check multiple conditions:

- **ICD discrepancy**: Compare the ICD-10 chapter to the expected service-line
  chapter. Also check narrative/laterality when the template requests it.
- **Document blockers**: `missing_records` when a referral has no associated
  documents or chart record; `missing_imaging` when required imaging is absent.
- **Authorization blockers**: Check the auth status field on the referral
  (`pending`, `denied`, `not_submitted`).
- **Duplicate handling**: When two referrals share the same patient and
  clinically overlap, flag as duplicate. The earlier-created referral is
  typically the primary. Recommend `consolidate_to_primary` unless they are
  distinct service episodes.
- **Shared insurance anomalies**: When two different patients share the same
  insurance policy ID, flag for verification.
- **Already scheduled**: When a referral shows an appointment date before
  clearance, flag as `scheduled_before_clearance`.

Priority tiers: `tier_1_immediate` for clinical safety issues (wrong chapter
with active schedule), `tier_2_short_term` for missing records/imaging/auth,
`tier_3_administrative` for insurance verification and non-urgent paperwork.

## Controlled Vocabularies Quick Reference

See [references/vocabularies.md](references/vocabularies.md) for the complete
set of controlled values organized by workflow type.

## SQL Reconciliation

When records need cross-referencing beyond what individual GET calls provide,
use `POST /query` with a read-only SQL statement. The endpoint accepts standard
SQL SELECT. Use this to reconcile referral-patients, find missing documents by
patient, or identify duplicate insurance IDs across patients.
