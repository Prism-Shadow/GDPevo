# EHR Quality-Governance Skill

Reusable entry instructions for generating normalized EHR quality-governance packets, referral coordination summaries, care transition packets, duplicate-review validations, and batch audits against a read-only FHIR-aligned REST API. These rules are distilled from five representative task archetypes (merge readiness, referral coordination, care transition, duplicate+ServiceRequest review, and batch audit) and are designed to transfer to any task expressed in the same prompt/payload idiom.

## When to apply this skill

Activate this skill when a prompt:

- References an EHR quality-governance, referral, duplicate-chart merge, care-transition, or audit queue task.
- Points at a read-only REST API reachable at `<TASK_ENV_BASE_URL>` (or a concrete `base_url` provided via `environment_access.md`).
- Asks for normalized JSON output conforming to an `answer_template.json` payload.
- Mentions clinical entities: patients, conditions, medications, allergies, encounters, documents, immunizations, disclosures, providers, referrals, duplicates, ServiceRequests, ICD-10 codes, audit logs, or service codes.

## Environment setup

1. Read `environment_access.md` for the `base_url` (default `http://task-env:9015/`) and the allowed endpoint list.
2. All endpoints are **read-only GET**. No authentication, no write operations.
3. Treat `<TASK_ENV_BASE_URL>` in prompt text as a placeholder; substitute the `base_url` from `environment_access.md`.
4. The complete endpoint catalog is documented in `api_reference.md` (alongside this skill file).

## Core operating rules

### Rule 1 — Gather all evidence before deciding

For every task, fetch the full set of relevant resources before drawing conclusions. The standard evidence-gathering order:

1. **Primary entity** — the patient(s), duplicate candidate(s), referral(s), or ServiceRequest named in the prompt.
2. **Active clinical lists** — conditions, medications, allergies (all three, always, for every patient involved). Use the `/api/patients/{id}/conditions`, `/api/patients/{id}/medications`, and `/api/patients/{id}/allergies` endpoints.
3. **Encounter history** — `/api/patients/{id}/encounters`. Filter for recency and relevance to the task's clinical domain.
4. **Documents** — `/api/patients/{id}/documents`. Assess document type, status (`final` vs `preliminary` vs `cancelled`), and date.
5. **Audit trail** — `/api/audit-logs`. Filter to entries referencing the patient(s) or task entities.
6. **Reference data** — Providers (`/api/providers`, `/api/providers/{id}`), ICD-10 codes (`/api/icd10`, `/api/icd10/{code}`), Service codes (`/api/service-codes`, `/api/service-codes/{code}`).
7. **Task-specific resources** — duplicate candidates (`/api/duplicates/candidates`, `/api/duplicates/{id}`), referrals (`/api/referrals`, `/api/referrals/{id}`), immunizations (`/api/patients/{id}/immunizations`), disclosures (`/api/patients/{id}/disclosures`), ServiceRequests (`/api/patients/{id}/service-requests`).

### Rule 2 — Reconciling active clinical lists

When building clinical key unions across patients (merge packets) or for a single patient:

- Use the **patient-specific active-list endpoints** (`/api/patients/{id}/conditions`, etc.) as the authoritative source over any preview or summary endpoint.
- Filter to **active** records only. Exclude records with statuses `inactive`, `resolved`, `entered-in-error`, or equivalent.
- Extract the `normalized_key` field from each active record.
- Deduplicate (union, not intersection) across patients for merge contexts.
- **Sort alphabetically** by `normalized_key` unless the answer template explicitly states otherwise.
- Any record excluded because it is inactive, stale, or irrelevant must be reported in the `excluded_distractors` or equivalent output section when the template provides one.

The entity model and key mapping conventions are documented in `entity_model.md`.

### Rule 3 — Match, conflict, and identity signals

When comparing two patient records (duplicate candidates):

- **Match signals** are fields or normalized business signals that align between the records. Report them sorted alphabetically.
- **Conflict signals** are fields or normalized business signals that diverge.
- **Demographic matches/conflicts** are a finer-grained subset: `dob`, `given_name`, `phone`, `address`, `insurance`, etc.
- Source identity signals from the duplicate-candidate endpoint response AND from directly comparing the full patient detail responses.
- If the duplicate-candidate endpoint provides its own signal list, augment it — do not replace it — with signals found from direct comparison.

### Rule 4 — Evidence selection

- **Documents**: include only documents with `status: final` (never `preliminary` or `cancelled`) that are relevant to the clinical question. Exclude internal-only document types (e.g., `staff_message`, `admin_note`) unless the task explicitly calls for them. Document the selection basis as `identity_or_external_continuity_documents_only`.
- **Audit logs**: include audit entries that reference the patients or task entities. Exclude system-internal entries with no clinical relevance.
- **Encounters**: select by recency AND clinical relevance to the task domain. A task about orthopedics should prefer orthopedic encounters; a task about cardiology should prefer cardiology encounters. When a count is specified (e.g., "four most relevant"), respect it exactly. Report excluded encounter IDs.

### Rule 5 — Code validation (ICD-10, service codes)

For any task involving diagnosis codes or service codes:

- **ICD-10 validation**: Look up every diagnosis code against `/api/icd10/{code}`. A code is `valid` if the ICD-10 directory returns a record for it; otherwise it is `invalid` / `unknown_code`.
- **Chapter check**: Extract the `chapter` field from the ICD-10 lookup. Compare it to the expected chapter for the task's service line:
  - Orthopedics → `Musculoskeletal`
  - Cardiology → `Circulatory`
  - Neurology → `Nervous`
  - etc.
  A code from the wrong chapter is flagged `out_of_range_chapter`.
- **Narrative/laterality mismatch**: Compare the diagnosis narrative text against the ICD-10 description and expected laterality terms from the directory. Flag `laterality_mismatch` when the patient's condition mentions a side (left/right/bilateral) that conflicts with the code's description or when laterality is missing from a code that expects it. Flag `narrative_mismatch` when the narrative does not align with the code's clinical meaning.
- **Service code validation**: Look up service codes against `/api/service-codes/{code}`. Flag as `valid: false` if the directory returns no match.

### Rule 6 — Provider matching

When a task requires identifying a specialist or receiving provider:

1. If a specific provider ID is given in the prompt or referral, fetch `/api/providers/{provider_id}`.
2. If no provider ID is given, search `/api/providers` and filter by `service_line` matching the task's clinical domain.
3. Extract: `provider_id`, `name`, `role`, `service_line`, `facility`, `phone`, `fax`.
4. For primary care providers: identify the PCP from the patient's encounter history or referral record.

### Rule 7 — Packet readiness assessment

Every packet must conclude with a readiness determination:

- **`ready`** (or `ready_to_send`, `merge_ready`): all required data is present, valid, and consistent. No blocking issues.
- **`ready_with_review_note`** (or `ready_with_risk_flags`): data is sufficient to proceed but has flags that merit attention (e.g., risk flags on a care transition, conflict signals on a merge).
- **`blocked`** (or `hold_for_*`, `not_ready`, `needs_manual_review`): one or more blocking issues prevent the packet from being sent. Enumerate the blocking issue codes.
- **Blocking issues** include: missing required documents, invalid diagnosis codes, incomplete allergy documentation, missing authorization, missing provider, disclosure not permitted, clinical mismatch.

### Rule 8 — Output conventions

- Return **JSON only**. No narrative prose outside the JSON object.
- **Dates**: YYYY-MM-DD format.
- **Arrays with set semantics**: sort alphabetically by their primary sort key (typically the string value itself, or `normalized_key` for clinical keys, or `id` for entity arrays) unless the answer template specifies a different ordering.
- **Null vs. absent**: When a field is structurally present in the template but has no value, use `null` (not absent) for nullable fields. For arrays, use `[]` (empty array) when nothing qualifies.
- **Enum values**: use the exact string from the template's vocabulary. Never invent new enum values.
- **Stable IDs**: use the API-provided IDs verbatim. Never generate synthetic IDs.
- **Task identification**: when the template includes `task_id`, set it to the exact value specified in the prompt or template (e.g., the train task identifier).

### Rule 9 — Distractor and noise exclusion

- Inactive/resolved clinical records → exclude and report.
- Irrelevant document types → exclude and report.
- Audit entries unrelated to the task entities → exclude and report.
- Encounters outside the relevant time window or clinical domain → exclude and report.
- Stale immunizations or disclosures → exclude from the primary output but note any that were reviewed.

The exclusion reporting should mirror the template's structure: if the template has `excluded_distractors`, populate each category with the normalized keys or IDs of excluded items.

### Rule 10 — Task-specific extraction patterns

**Merge readiness (train_001 style):**
- Source the duplicate candidate from `/api/duplicates/{candidate_id}`.
- Fetch full patient records for both patient IDs.
- Build active clinical key unions across both patients' active list endpoints.
- Compare demographics for match/conflict signals.
- Identify the canonical target (the patient with more complete active data or the one explicitly tagged in the duplicate candidate).
- Collect document and audit evidence relevant to both patients.

**Referral coordination (train_002 style):**
- Source the referral from `/api/referrals/{referral_id}`.
- Fetch the patient's active lists, encounters, documents.
- Validate the referral's diagnosis codes against ICD-10.
- Check allergy readiness: are allergies documented, non-conflicting, and complete?
- Identify the receiving provider from the referral or by service-line match.
- Assess authorization status.
- Construct the referral-letter field choices by matching clinical evidence to the template's enum options.

**Care transition (train_003 style):**
- Fetch patient detail, all three active clinical lists, encounters, immunizations, disclosures.
- Identify the recipient provider.
- Select exactly the N most relevant handoff encounters for the target service line, ordered newest to oldest.
- Extract the latest immunization.
- Find the applicable disclosure matching the recipient provider.
- Drive risk flags from active conditions and medications using the risk-flag evidence rules in `entity_model.md`.
- Exclude stale encounters, inactive records, and unrelated distractors.

**Duplicate review + ServiceRequest (train_004 style):**
- Fetch the duplicate candidate and both patients.
- Determine duplicate status and merge decision independently from the candidate's own signals.
- Fetch the ServiceRequest and validate its service code, reason codes, and provider alignment.
- Assess SBAR coverage (Situation, Background, Assessment, Recommendation) from the available documentation and clinical evidence.

**Batch audit (train_005 style):**
- List all referrals in the batch via `/api/referrals` (filter/search by batch ID).
- For each referral: validate its diagnosis code, check for laterality/narrative mismatches, check authorization status, check document completeness.
- Group duplicates (same patient, same clinical context, multiple referral rows).
- Detect insurance-patient anomalies (shared insurance across different patients, or same patient with separate clinical referrals).
- Assign Tier 1 (immediate: urgent coding or duplicate blockers), Tier 2 (short-term: routine coding/auth/document blockers), Tier 3 (administrative: document completion).
- Drive summary counts from the validated results, not from batch-level aggregates — every count must be traceable to individual referral rows.

## Supporting files

- `api_reference.md` — complete endpoint catalog with resource hierarchies and field notes.
- `entity_model.md` — entity relationship map, normalized key conventions, risk-flag evidence rules, and enum vocabulary cross-reference.
