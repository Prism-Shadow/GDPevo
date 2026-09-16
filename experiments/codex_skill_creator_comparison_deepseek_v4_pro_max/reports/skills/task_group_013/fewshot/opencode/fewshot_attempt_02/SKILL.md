---
name: cedar-ridge-intake
description: Complete Cedar Ridge Intake Coordination Portal tasks — patient access verification, referral readiness audits, dialysis transfer reviews, chronic-care enrollment panels, and referral-to-chart activation. Use this skill whenever the user mentions Cedar Ridge, intake coordination, patient access verification, referral audit, dialysis transfer review, enrollment panel, DMHTN, chart activation, or any healthcare batch/review task with a JSON answer template and a REST API.
---

# Cedar Ridge Intake Coordination

Use this skill to solve Cedar Ridge Intake Coordination Portal tasks end to end. These tasks all share the same API surface, the same template-driven output protocol, and overlapping clinical/administrative rule sets.

## The 3-step process

Every Cedar Ridge task follows the same shape:

1. **Discover the batch and template** — find the batch/roster/program identifier in the prompt and read the answer template JSON
2. **Fetch all needed data from the portal** — hit every relevant endpoint; gather more than you think you need because cross-referencing is essential
3. **Derive results and assemble the response** — apply the business rules, fill the template exactly, and return JSON only

Do not skip steps. Do not return prose outside the JSON.

## Resolving the base URL

The task prompt contains `<TASK_ENV_BASE_URL>`. Replace it with the actual portal base URL. If an `environment_access.md` file is present, read it for the exact URL and list of allowed endpoints. If no such file exists, ask the user for the base URL before proceeding.

Every API call originates from this base. All endpoints return JSON.

## API reference

The portal exposes these endpoints. Call them with GET unless noted otherwise.

### Core entity endpoints

| Endpoint | Returns | When to use |
|---|---|---|
| `/patients` | All patient records | Whenever patient data is needed |
| `/patients/{patient_id}` | Single patient record | Deep-dive on a specific patient |
| `/referrals` | All referral records | Referral audit, chart activation tasks |
| `/referrals/{referral_id}` | Single referral record | Detailed referral investigation |
| `/transfers` | All transfer records | Dialysis transfer review tasks |
| `/transfers/{transfer_id}` | Single transfer record | Focused transfer review |
| `/chart/{patient_id}` | Patient chart data (problems, vitals, labs, medications, allergies, consent, demographics) | Enrollment panels, chart activation, risk assessment |
| `/documents` | Document metadata (type, patient, received date) | Document completeness/staleness checks |

### Metadata & lookup endpoints

| Endpoint | Returns | When to use |
|---|---|---|
| `/icd/{code}` | ICD-10 code metadata (description, chapter) | ICD discrepancy detection |
| `/pharmacies` | Network pharmacy list | Pharmacy network status checks |
| `/programs/{program_code}/candidates` | Candidate list for a program | Enrollment panel tasks |

### Cross-cutting endpoint

| Endpoint | Method | Returns | When to use |
|---|---|---|---|
| `/query` | POST | SQL query results against the portal's read-only database | Reconciling records, complex cross-references, verifying counts |

Send a JSON body: `{"sql": "SELECT ..."}`. Use this endpoint when the GET endpoints don't directly support the cross-reference you need — for example, joining referrals to patients, or counting documents per patient.

## Answer template protocol

Every task has an `answer_template.json` in `input/payloads/`. This file is the authoritative schema for the response. Treat it as a contract.

### How to use the template

1. **Top-level shape**: Note every required key at the top level and their expected constant values (`task_id`, `batch_id`, `program_code`, etc.). Fill these exactly.

2. **Enum fields**: Every field that says `allowed_values` or `allowed` must contain only values from that list. Never invent a value. Never use a value from a different domain's enum set.

3. **Ordering**: When the template says `ascending by patient_id`, `ascending referral_id`, `alphabetical by code`, comply. When it says `unordered set` or `order is not meaningful`, you may use any order but the evaluator treats the list as a set.

4. **Required keys**: Every list item must contain every `required_key` or `item_required_key` the template lists. Missing keys will cause the output to fail validation.

5. **Nullable fields**: If a field's type is `enum_or_null` or `integer_or_null`, produce `null` (JSON null, not the string `"null"`) when there is no applicable value.

6. **Cohort summaries**: Derive all summary counts from the per-patient/per-referral results you computed. Do not guess or hard-code them. If the total doesn't add up, recheck your per-item results.

### JSON-only output

The final response must be pure JSON. No markdown fences, no leading or trailing prose, no `Here is the result:` preamble. The evaluator parses the raw response as JSON.

## Domain rules

The portal data is raw. You must derive every status, code, and decision by applying clinical and administrative rules. These rules are organized by domain in [references/rules.md](references/rules.md).

### When to read rules.md

Read the full rules reference before you start deriving outputs. Then use specific sections as you work through each patient/referral/transfer:

- **Patient access verification**: Insurance & PBM rules, Pharmacy network rules, Risk classification rules, Registration status rules
- **Referral readiness audit**: Referral readiness rules, ICD discrepancy rules, Duplicate detection rules, Authorization rules, Insurance anomaly rules
- **Dialysis transfer review**: Document completeness & staleness rules, Capacity & feasibility rules, Transfer decision rules
- **Enrollment panel**: Program eligibility rules, Chart activation rules, Monitoring package rules
- **Referral-to-chart activation**: Referral readiness rules, ICD discrepancy rules, Duplicate detection rules, Chart activation rules, Priority tier rules

### Applying rules systematically

For each patient/referral/transfer in the batch:

1. Fetch all related data first (patient, referrals/transfers, chart, documents, ICD codes, pharmacies)
2. Work domain by domain: insurance first, then clinical status, then risk, then blockers
3. Collect all applicable reason codes before assigning the final status
4. The final registration/readiness/enrollment status depends on the most severe finding

## Edge cases and common pitfalls

### Data not found
If a patient, referral, or document is referenced but absent from the API, note it as missing — do not fabricate data. Check the portal carefully: some records exist under unexpected IDs.

### Duplicate referrals
When the same patient appears with multiple referrals for similar services, check for true duplicates. A group of referrals sharing a patient and service line may be duplicates. The primary referral is the earliest or most complete one.

### Shared insurance IDs
If two different patients share an insurance ID, flag it unless there's a legitimate reason (family plan, documented linkage). Most same-ID cases across different patients are anomalies that need verification.

### Stale documents
A document is stale when `as_of_date − received_date > freshness_limit_days`. The freshness window varies by document type. Check every required document; a packet is `incomplete` if any required document is missing, and `complete` only when all required documents are present and fresh.

### ICD chapter mismatches
The ICD-10 code structure determines chapter. For example, codes starting with S belong to Chapter 19 (Injury, poisoning, S00-T88), while codes starting with M belong to Chapter 13 (Musculoskeletal, M00-M99). The expected chapter depends on the service line: orthopedic referrals expect musculoskeletal codes, pulmonary referrals expect respiratory codes (J00-J99), etc. A referral whose ICD code belongs to a different chapter than the service line expects has an `icd_chapter_mismatch`.

### Capacity arithmetic
Sum `open_chairs_total` across all locations returned by the portal for the requested date. Capacity is `available` when open chairs >= 1 at any location in the network. Capacity is `unavailable` when all locations show 0 open chairs for that date.

### Enum discipline
The most common failure mode is using a value outside the template's allowed set. Before finalizing, scan every field against its `allowed_values` list. This is especially important for `blocked_reason_codes`, `issue_codes`, `action_codes`, and `reason_codes` — these are domain-specific and do not overlap between task types.

## Quality checklist

Before submitting, verify:

- [ ] Base URL resolved and all relevant endpoints called
- [ ] Answer template read and understood
- [ ] Every top-level required key present
- [ ] Every list ordered as the template specifies
- [ ] Every enum value matches an `allowed_values` entry
- [ ] Every reason/blocker code comes from the template's allowed list (not a different domain)
- [ ] All summary counts derived from per-item results
- [ ] No markdown fences or prose in the output
- [ ] Valid JSON (run through a parser if unsure)
- [ ] `null` used for nullable fields with no value (not `"null"`, not `""`, not omitted)
