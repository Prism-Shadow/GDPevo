# Cedar Ridge Intake Coordination — Reusable Operating Rules

## When to use this skill

Invoke this skill whenever the task involves the **Cedar Ridge Intake Coordination Portal** — a healthcare intake system that exposes patient, referral, transfer, chart, document, ICD, pharmacy, and program-candidate records through a REST API plus a read-only SQL endpoint. The skill applies to any intake workflow: patient access verification, referral audit, transfer review, chronic-care enrollment, or referral-to-chart activation.

## Portal overview

All endpoints live under the base URL provided as `<TASK_ENV_BASE_URL>`. Credentials are not required.

### Available endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Health / connectivity check |
| GET | `/patients` | List all patients |
| GET | `/patients/{patient_id}` | Single patient identity/demographics |
| GET | `/referrals` | List all referrals |
| GET | `/referrals/{referral_id}` | Single referral record |
| GET | `/transfers` | List all transfer requests |
| GET | `/transfers/{transfer_id}` | Single transfer request |
| GET | `/documents` | Document/packet inventory |
| GET | `/chart/{patient_id}` | Clinical chart for a patient |
| GET | `/programs/{program_code}/candidates` | Candidates for a program |
| GET | `/icd/{code}` | ICD-10 code metadata (chapter, description, laterality) |
| GET | `/pharmacies` | Pharmacy network directory |
| POST | `/query` | Read-only SQL endpoint — submit `{"sql": "<query>"}` |

### Entity relationships

- **Patients** are the core identity. They link to referrals, transfers, charts, and documents.
- **Referrals** carry a patient_id, ICD codes, insurance/policy references, authorization fields, and document flags.
- **Transfers** carry a patient_id, requested-start date, and document packet references.
- **Documents** are referenced by transfers and referral records; they carry document-type codes and received-date timestamps.
- **Charts** (via `/chart/{patient_id}`) contain active problems, vitals, labs, medications, allergies, and consent status.
- **ICD codes** resolve to chapter names, clinical descriptions, and laterality markers.
- **Pharmacies** provide network-status lookup for prescription-benefit verification.

## Operating rules (distilled from train evidence)

### Rule 1: Template-first orientation

Before issuing any API call, read the answer template (`input/payloads/answer_template.json`). The template is the contract:

- It defines every required top-level key, every per-item required key, every allowed enum value, every sort order, and every expected data type.
- Use **only** the enum values listed in the template. Never invent a code, status, or reason string.
- Treat reason-code and blocker-code arrays as **unordered sets** unless the template specifies otherwise.
- Treat entity-ID lists as **ascending sort** unless the template specifies otherwise (e.g., priority-ranked lists).

### Rule 2: Start with portal discovery

1. Call `GET /` to confirm the portal is reachable.
2. Fetch the primary entity collection for the task (e.g., `GET /referrals` for a referral audit, `GET /patients` for access verification, `GET /transfers` for transfer review, `GET /programs/{code}/candidates` for enrollment).
3. Filter the collection to the target batch/roster/program using the identifier from the prompt.

If the REST collections include more records than the target batch, use `POST /query` with a SQL `WHERE` clause to narrow results, or filter client-side after fetching.

### Rule 3: Enrich each entity with supporting data

For every entity in scope, fetch its related records:

- **Patient context**: `GET /patients/{patient_id}` and `GET /chart/{patient_id}`
- **Referral context**: `GET /icd/{code}` for each ICD on the referral; `GET /patients/{patient_id}` for the linked patient
- **Transfer context**: `GET /patients/{patient_id}`; cross-reference document records from `GET /documents` against the transfer's packet requirements
- **Program context**: `GET /chart/{patient_id}` for chart artifacts, vitals, labs, medications, active problems, and consent

### Rule 4: Use SQL for cross-entity reconciliation

When the REST endpoints do not directly expose a join (e.g., "which referrals share the same insurance policy across different patients?"), use `POST /query`. The SQL endpoint accepts standard `SELECT` queries. Use it to:

- Find duplicate referrals (same patient, same service, overlapping dates)
- Detect shared insurance anomalies (same policy ID on different patients)
- Cross-reference documents against transfer packet requirements
- Aggregate counts for cohort summaries

Do not use SQL for mutations — the endpoint is read-only.

### Rule 5: Assess each entity against template rules

For each entity, apply the classification logic implied by the template enums:

- **Readiness / status**: Determine the correct enum value by checking preconditions (e.g., insurance valid → eligible; all documents present and fresh → complete; no blockers → ready).
- **Reason / blocker codes**: Assign every applicable code from the template's allowed list. An entity can have zero, one, or multiple codes.
- **Priority tier**: Assign based on clinical urgency signals (e.g., acute ICD chapter, recent hospitalization, missing critical documents).
- **Follow-up / routing**: Assign cadence, owner, channel, and template from the template's allowed values based on the entity's status and blocker profile.

When evidence is ambiguous, prefer the more conservative classification (e.g., `hold` over `approved`, `under_review` over `ready`).

### Rule 6: Sort every list as specified

Default sort orders unless the template overrides:

| List type | Default sort |
|-----------|-------------|
| Entity IDs (patient, referral, transfer) | Ascending lexicographic |
| Document types / artifact codes | Alphabetical by code string |
| Priority / rank lists | As specified (rank 1 first, or tier-1 before tier-2) |
| Reason-code sets | Order not meaningful; choose a stable order for reproducibility |

### Rule 7: Build cohort summaries from individual assessments

Every template includes a summary/cohort_summary section. Compute it by aggregating the per-entity decisions, not by querying the API separately:

- Count entities by each status, risk level, decision, or cadence bucket.
- Verify that counts sum to the total (e.g., `enroll + hold + reject == total_candidates`).
- Use integer counts.

### Rule 8: Validate before returning

Before writing the final answer:

1. Every required top-level key is present.
2. Every per-item required key is present on every item.
3. Every enum field uses only allowed values.
4. Every list is sorted as the template requires.
5. Count objects in the summary sum correctly to their totals.
6. All IDs match the case and format returned by the portal.

### Rule 9: Return JSON only

The final response must be a single JSON object with no surrounding prose, markdown fences, or commentary. The template is the schema — the output must conform to it exactly.

## Task-type patterns

The five train tasks reveal three distinct intake patterns:

### Pattern A: Entity verification (train_001)

- **Goal**: Validate each entity's attributes against external references.
- **Flow**: Fetch roster → for each patient: check insurance validity, pharmacy network status, prescription benefit → compute risk scores → decide registration status → aggregate.
- **Key endpoints**: `/patients`, `/pharmacies`, `/chart/{patient_id}`

### Pattern B: Batch audit (train_002, train_005)

- **Goal**: Find discrepancies and blockers across a referral batch.
- **Flow**: Fetch referral list → for each referral: validate ICD codes against `/icd/{code}`, check for duplicates, detect shared-insurance anomalies, identify missing records/imaging, check authorization → classify readiness → build action plan and correspondence queue.
- **Key endpoints**: `/referrals`, `/icd/{code}`, `/patients/{patient_id}`, `/documents`, `POST /query`

### Pattern C: Readiness assessment (train_003, train_004)

- **Goal**: Determine whether each entity is ready for the next step.
- **Flow**: Fetch entity list → for each: check document packet completeness and freshness, verify capacity/preconditions, assess eligibility criteria → decide intake/enrollment disposition → assign follow-up routing and monitoring.
- **Key endpoints**: `/transfers`, `/documents`, `/chart/{patient_id}`, `/programs/{code}/candidates`
