---
name: licensing-review
description: Review regulatory licensing applications and produce structured JSON decisions for contractor eligibility, liquor license staff packages, and alcohol renewal queues. Use when the user mentions contractor applications, liquor license review, alcohol renewal screening, licensing board decisions, compliance review, or any task that requires cross-referencing licensing REST API endpoints to produce structured JSON determinations. Also use when the user provides target application IDs and a TASK_ENV_BASE_URL with licensing data endpoints.
---

# Licensing Review

This skill covers three regulatory licensing review workflows:

1. **Contractor eligibility batch review** — cross-reference applications against bonds, insurance, license history, violations, inspections, and correspondence to produce APPROVE / HOLD / DENY decisions.
2. **Liquor license staff package** — build a single-application review package with risk coverage analysis, verification gaps, monitoring plans, and escalation triggers.
3. **Alcohol renewal review queue** — rank licensees for manual review using violation matching against a boundary date.

All workflows share a common environment pattern. Every prompt provides `<TASK_ENV_BASE_URL>` and the relevant API endpoints. Use the `references/api_patterns.md` reference for the standard fetch pattern, credential, and SQL access rules.

## Universal Environment Setup

Before any domain-specific work, read the `environment_access.md` file staged alongside the task for the base URL, allowed endpoints, and the `X-Task-Token` credential value. Note the following:

- All GET endpoints return JSON arrays. Fetch them in parallel when they are independent.
- `POST /api/sql` accepts `{"query": "<SQL>"}` with the header `X-Task-Token: <token-value>`. Use it for cross-dataset joins or filtered lookups when the GET endpoints alone cannot disambiguate records.
- The `<TASK_ENV_BASE_URL>` placeholder in the prompt must be replaced with the actual base URL from `environment_access.md`.
- Templates provided under `input/payloads/answer_template.json` define the exact output structure, allowed enum values, ordering rules, and empty-value conventions. Never deviate from the template's schema.

## Domain 1: Contractor Eligibility Batch Review

This domain covers batch-review tasks: reviewing a batch of contractor applications with IDs like `C-XXXX-###`.

### Data Sources

Fetch all of these in parallel:

| Endpoint | What it provides |
|---|---|
| `GET /api/policies` | Current policy baselines, effective dates, new 2025 standards |
| `GET /api/contractor/applications` | Application records (endorsements, experience claims, status) |
| `GET /api/contractor/bonds` | Bond amounts, statuses, effective/cancellation dates |
| `GET /api/contractor/insurance` | Insurance coverage amounts, expiry dates, carrier status |
| `GET /api/contractor/license-history` | Prior licenses, suspensions, revocations |
| `GET /api/contractor/violations` | Violation records with severity and resolution status |
| `GET /api/contractor/correspondence` | Communication records, stale/unverified flags |
| `GET /api/contractor/inspections` | Inspection reports, safety flags, documentation gaps |
| `POST /api/sql` | Use when a record needs filtering by application ID that the GET endpoint doesn't directly support |

### Decision Procedure

For each application in the batch, inspect these dimensions in order:

**1. License History Check**

Look at `/api/contractor/license-history` for the applicant. If any entry shows an `active_suspension`, assign `active_suspension` as a deficiency code and record `risk_tier: "high"`. An active suspension alone is sufficient to recommend DENY.

**2. Bond Check**

Look at `/api/contractor/bonds` for the applicant. Check:
- Is there an active bond on file? If not, assign `no_active_bond` or `bond_cancelled` depending on whether a bond existed but was cancelled.
- Is the bond amount sufficient compared to the policy-required minimum? If short, assign `bond_shortfall`.
- Is the bond expired or cancelled as of the review date? If so, assign `bond_cancelled` or `bond_shortfall`.

**3. Insurance Check**

Compare each insurance record against the review date given in the prompt:
- Expired as of review date → `insurance_expired`
- Not yet effective / pending → `insurance_pending`
- Coverage amount below policy minimum → `insurance_shortfall`
- No record found or coverage gap → `insurance_not_current`

**4. Endorsement Check**

From the application record and any related data:
- Required endorsement not obtained → `endorsement_missing`
- Application in progress → `endorsement_pending`
- Status cannot be verified → `endorsement_not_verified`

**5. Experience Check**

From the application record:
- Insufficient documented years or project count → `experience_shortfall`

**6. Violation / Complaint Check**

- Unresolved serious violations → `open_serious_violation`
- Unresolved minor violations → `open_minor_violation`
- Unresolved serious complaints → `unresolved_serious_complaint`

**7. Inspection Check**

- Missing required inspection documentation → `inspection_doc_gap`
- Failed safety inspection requiring recheck → `inspection_safety_recheck`

### Determination Rule

| Determination | Condition |
|---|---|
| `DENY` | `active_suspension` is present, OR `open_serious_violation`/`unresolved_serious_complaint` combined with multiple additional deficiencies from other categories |
| `APPROVE` | Zero deficiency codes found |
| `HOLD` | Deficiencies exist but none of the DENY triggers apply |

### Risk Tier Assignment

| Tier | Condition |
|---|---|
| `low` | Zero deficiencies (APPROVE) |
| `high` | `active_suspension`, `open_serious_violation`, `unresolved_serious_complaint`, or deficiencies crossing three or more of the check categories above |
| `medium` | Other deficiency patterns |

### Policy Impact

`policy_impacted: true` when the current policy baseline (`GET /api/policies`) introduces a 2025-or-later standard that creates a deficiency or material review flag that would not have applied under prior rules. Compare each deficiency against the policy effective dates and scope descriptions.

### Required Actions

Map each deficiency code to required actions using the reference table in `references/contractor_code_mappings.md`. Sort actions alphabetically.

### Summary Construction

After deciding all applications:
- Count APPROVE, HOLD, DENY.
- Collect all `high` risk tier application IDs, sorted ascending.
- Collect all `policy_impacted: true` application IDs, sorted ascending.
- Identify correspondence IDs with stale or unverified status from `/api/contractor/correspondence`, sorted ascending.

### Output

Produce only the JSON object matching the task's `answer_template.json`. Order `application_decisions` by `application_id` ascending. Use empty arrays when no codes apply.

## Domain 2: Liquor License Staff Package

This domain covers single-application liquor license review tasks. The prompt names one target application ID and one target location ID.

### Data Sources

Fetch all of these in parallel:

| Endpoint | What it provides |
|---|---|
| `GET /api/policies` | Policy rules, premises definitions, control requirements |
| `GET /api/liquor/applications` | Application details, license class, requested privileges |
| `GET /api/liquor/settlements` | Prior settlement agreements, board orders, consent decrees |
| `GET /api/liquor/privileges` | Active privilege grants and restrictions |
| `GET /api/liquor/incidents` | Police incidents, complaints, infractions at the location |
| `GET /api/liquor/site-evidence` | Floor plans, photos, CCTV specs, signage, food service evidence |
| `POST /api/sql` | Use for cross-referencing records when direct GET filtering is insufficient |

### Decision Procedure

**1. Same-Premises Basis**

Check whether the application falls under a same-premises rule (previous license at this location, prior board findings about the site). Look at `/api/liquor/settlements` and `/api/liquor/privileges` for references to the target location. Set `same_premises_basis_applies: true` when prior license or settlement records reference the same physical premises.

**2. Covered Risk Assessment**

Review all incidents, settlements, and site evidence to identify risks that have adequate existing controls or documentation coverage. Examples of covered risks:
- `AFTER_HOURS` — after-hours service risk with monitoring controls
- `ASSAULT` — assault/harassment incidents with security controls
- `MINOR_SALE` / `SALE_TO_MINOR` — age-verification controls
- `NOISE` / `PATIO_BOUNDARY` — noise or patio boundary with monitoring
- `SAME_PREMISES` — same-premises basis provides control coverage
- `FOOD_SERVICE_GAP` — food service requirements met
- `TAX_HOLD` — tax clearance obtained

The allowed codes are listed in the task's answer template. Pick only codes that are actually supported by evidence from the data.

**3. Verification Gap Assessment**

Identify what is missing, conflicting, or unverified. Common gap patterns:
- Signage documentation missing or conflicting → `CONTROL_SIGNAGE_CURRENT_MISSING`, `CONTROL_SIGNAGE_CONFLICTING`
- Floor plan stale or conflicting → `FLOOR_PLAN_CONFLICTING`, `FLOOR_PLAN_STALE`
- Open incident requiring follow-up → `OPEN_INCIDENT_FOLLOW_UP`
- Police memo with conflicting information → `POLICE_MEMO_CONFLICTING`
- Missing neighbor notice → `NEIGHBOR_NOTICE_MISSING`
- Missing site photos → `SITE_PHOTO_MISSING`
- Tax clearance missing → `TAX_CLEARANCE_MISSING`
- Camera evidence missing → `camera_evidence_missing`
- Food service evidence missing → `food_service_evidence_missing`
- Late-night monitoring needed → `late_night_monitoring_needed`

Use only codes from the template's allowed values.

**4. Standard vs Location-Specific Obligations**

- **Standard obligations**: Required for all licensees of this class regardless of location. Usually include `ID_CHECK`, `HOURS`, `FOOD_SERVICE`. Also include `CCTV`, `NOISE`, `SECURITY`, `PATIO`, `DELIVERY` when the license class or jurisdiction mandates them universally.
- **Location-specific controls**: Controls tied to this particular premises due to its history, layout, or settlement terms. Examples: `CCTV` required by a settlement at this address, `HOURS` restricted by a prior board order, `SECURITY` mandated by an incident pattern, `NOISE`/`PATIO` due to outdoor service area.

**5. Recommended Posture**

| Posture | Condition |
|---|---|
| `deny` | Unresolvable risks, board order conflicts, or evidence of unfitness |
| `request_follow_up` | Verifiable gaps exist that the applicant can resolve with additional submissions |
| `issue_restricted` | Risks are covered by existing controls and only standard obligations apply |

Default to `request_follow_up` when gaps are present but resolvable.

**6. 90-Day Monitoring Plan**

Build a list of monitoring checks with timing slots. Each check has a `check_code` and a `timing`:

- `first_30_days`: Immediate post-issuance verification (signage, ID check observation, camera export test, food service check, police memo follow-up, security walkthrough, tax clearance)
- `days_31_60`: Mid-period checks (after-hours visits, late-night closing visits)
- `days_61_90`: Late-period checks (noise/patio boundary, log reviews)

Select checks that correspond to the identified verification gaps and location-specific controls. Sort by operational sequence: immediate verifications first, then monitoring visits, then boundary checks.

**7. Escalation Triggers**

Identify conditions that should cause field staff to escalate. Map each major risk and verification gap to a trigger code from the template. Examples:
- After-hours risk → `AFTER_HOURS_VIOLATION`
- Signage unverified → `CONTROL_SIGNAGE_NOT_VERIFIED`
- Major incident → `MAJOR_INCIDENT_REPORTED`
- Minor sale unresolved → `REFERRED_MINOR_SALE_UNRESOLVED`
- CCTV control failure → `SECURITY_CCTV_CONTROL_FAILURE`
- Tax hold reopened → `TAX_HOLD_REOPENED`
- Camera coverage gap → `missing_camera_coverage` or `footage_not_produced`
- Food service gap → `food_service_not_available`
- Noise/patio breach → `noise_or_patio_breach`
- Tax hold uncleared → `open_tax_hold_uncleared`

The full code-to-evidence reference table is in `references/liquor_code_mappings.md`.

### Output

Produce only the JSON object matching the answer template schema. Include exactly the required top-level keys. Sort code arrays ascending (or as specified by the template's ordering rules). Remove duplicates.

## Domain 3: Alcohol Renewal Review Queue

This domain covers building a ranked manual-review queue for alcohol license renewals.

### Data Sources

| Endpoint | What it provides |
|---|---|
| `GET /api/alcohol/licensees` | License records with facility names, addresses, license numbers |
| `GET /api/alcohol/violations` | Violation records with dates, descriptions, license references |
| `GET /api/renewal/rules` | Renewal rules, boundary dates, ranking criteria |
| `POST /api/sql` | Use for joining licensee and violation data or filtering by date range |

### Decision Procedure

**1. Boundary Date Filtering**

The prompt specifies a boundary date (e.g., 2025-04-10). Violations dated after this boundary are excluded from the ranking calculation. Collect these excluded IDs for the summary.

**2. Violation Matching**

For each target license, match violations from `/api/alcohol/violations`:

- **Exact match**: violation record references the license number directly.
- **Close address match**: violation record references a different license number but the facility address is substantially similar (same street, nearby unit).
- **Uncertain match**: the connection is plausible but cannot be confirmed from available data alone.

Use `POST /api/sql` when the violation records use non-obvious identifiers that require a join with licensee data.

**3. Queue Ranking**

Rank licenses by a composite that prioritizes:

1. **Violation recency**: violations within the final ~30 days before the boundary date carry the most weight.
2. **Violation count**: more pre-boundary violations rank higher.
3. **Match confidence**: exact matches rank above close-address or uncertain matches when other factors are equal.

The ranking should place the most inspection-urgent licenses at the top. Licenses with recent violations just before the boundary are the highest priority.

**4. Risk Tier and Next-Step Labels**

| Risk Tier | Typical Assignment |
|---|---|
| `high` | Any matched pre-boundary violations, or close/uncertain matches suggesting additional risk |
| `medium` | Lower violation counts with older dates |
| `low` | No violations or only very old, minor ones |

| Next-Step Label | Typical Assignment |
|---|---|
| `board_review` | Highest-priority entries (top of queue), multiple recent violations |
| `manual_fine_check` | Mid-priority entries with moderate violation counts |
| `manual_ALERT_check` | Lower-priority entries |
| `additional_record_check` | Entries needing further data verification |

**5. Summary Construction**

- `queue_size`: number of entries in the queue (usually the target queue size from the prompt)
- `boundary_date`: the boundary date from the prompt
- `post_boundary_violation_ids_excluded`: all violation IDs dated after the boundary, sorted ascending
- `close_or_uncertain_match_license_numbers`: license numbers with non-exact matches, sorted ascending
- `board_review_license_numbers`: license numbers assigned `board_review`, sorted ascending

### Output

Produce the queue list with ascending ranks (1 through N, no gaps), ordered by rank. Each entry must include all fields from the answer template. Sort `matched_violation_ids` by violation date ascending, then by ID ascending.

## Cross-Domain Principles

- **Ordering**: Sort string lists ascending, integer ranks ascending, and dates chronologically unless the template says otherwise.
- **Empty values**: Use `[]` for empty arrays, never `null` or omitted keys.
- **No prose**: Return only the JSON object. Do not include narrative memos, citations, markdown wrapping, or additional commentary.
- **Template compliance**: The answer template is authoritative for allowed enum values and key names. Even if the data suggests a code not in the template, do not invent new codes. If a condition exists but no template code covers it, note it in the most applicable existing code or omit it.
- **SQL usage**: Use `POST /api/sql` when GET endpoints return broad datasets that need filtering, or when records need cross-joining. Always pass the token header.
