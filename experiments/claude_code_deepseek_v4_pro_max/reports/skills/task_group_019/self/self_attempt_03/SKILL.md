# Licensing Review Skill

You are a structured licensing decision engine. When invoked, you operate in a standardized licensing review environment. Follow these phases in order.

---

## Phase 1: Environment Bootstrap

1. Read `environment_access.md` from the working directory to obtain:
   - `base_url` — the root URL of the licensing data service (substitute this wherever you see `<TASK_ENV_BASE_URL>` in prompts).
   - `credentials` — any required headers (e.g., `X-Task-Token`) and the endpoints they apply to. Apply these headers only when calling the specified methods and paths.
   - `allowed_endpoints` — the full list of available API routes. Prefer GET endpoints for data collection; use POST `/api/sql` only when GET endpoints cannot answer a question and the credentials grant SQL access.

2. If `environment_access.md` is missing or does not declare a `base_url`, stop and report the gap — do not guess.

---

## Phase 2: Task Intake

For every task, read two files:

1. **`prompt.txt`** (or the task prompt provided in context):
   - Extract the **domain** — one of `contractor`, `liquor`, or `alcohol` (renewal). The domain is signaled by the API paths listed (`/api/contractor/…`, `/api/liquor/…`, `/api/alcohol/…`).
   - Extract the **target identifiers** — application IDs, license numbers, or location codes. These are the entities you must produce decisions for.
   - Extract any **operational parameters** — review date, boundary date, target queue size, or domain-specific focus areas.
   - Note which GET endpoints the prompt lists and treat that as the **minimum fetch set**.

2. **`input/payloads/answer_template.json`** (or the schema provided in the prompt):
   - This is the **contract**. Every top-level key, every allowed enum value, every ordering rule, and every structural constraint is mandatory.
   - Note `required_length` on lists, `allowed_values` on enums, and `ordering` directives.
   - Read the `additional_output` / prose restriction: return **only** the JSON object. No markdown, no comments, no keys outside the schema.

---

## Phase 3: Data Collection

### Always fetch first
```
GET {base_url}/api/policies
```
Policy documents define the current baseline. A policy change can create deficiencies that would not have existed under a prior baseline — this controls the `policy_impacted` flag on contractor tasks and informs risk posture on liquor tasks.

### Fetch domain endpoints
Collect all records from every GET endpoint listed in the prompt. Do not skip any. Results from different endpoints may cross-reference each other (e.g., a bond references an application_id, a violation references a license_no). Treat every response as a set of facts — never assume a fact is absent just because one endpoint did not mention it.

### Use SQL only as a fallback
POST `/api/sql` with header `X-Task-Token` (value from `environment_access.md`) is available. Use it when:
- You need to join or filter across datasets in ways the GET endpoints do not support.
- You need aggregate queries (counts, groupings, max dates).
- The domain rules below explicitly call for it.

Do **not** use SQL to bypass the GET endpoints — collect the base data first, then enrich with SQL if needed.

### Cache intermediate results
Hold all fetched records in memory. The analysis phase cross-references them extensively.

---

## Phase 4: Domain Decision Rules

### 4A — Contractor Batch Eligibility (domains: `contractor`)

For each target application, evaluate these dimensions:

| Dimension | Data Source(s) | Defect Conditions |
|---|---|---|
| **Bond** | `/api/contractor/bonds` | No active bond → deficiency. Bond amount below required minimum → shortfall. Bond cancelled → cancelled. |
| **Insurance** | `/api/contractor/insurance` | Policy expired as of review date → expired. Policy not yet bound → pending. Coverage below required minimum → shortfall. |
| **Endorsement** | `/api/contractor/applications` | Required specialty endorsement not verified → endorsement_not_verified / endorsement_missing. |
| **Experience** | `/api/contractor/applications` | Documented experience below required threshold → experience_shortfall. |
| **License History** | `/api/contractor/license-history` | Active suspension on record → active_suspension. Prior revocations may elevate risk. |
| **Violations** | `/api/contractor/violations` | Open/unresolved violation → deficiency. Serious violations → escalate to DENY or board_review. Minor violations → HOLD with resolve action. |
| **Inspections** | `/api/contractor/inspections` | Missing required inspection documents → inspection_doc_gap. Failed safety inspection needing recheck → inspection_safety_recheck. |
| **Correspondence** | `/api/contractor/correspondence` | Stale or unverified correspondence items → record their IDs for the summary. |

**Determination logic:**
- `DENY` when: active_suspension, unresolved_serious_complaint, or multiple critical deficiencies with no path to cure.
- `HOLD` when: fixable deficiencies exist (bond/insurance can be updated, endorsement can be verified, minor violations can be resolved).
- `APPROVE` when: no deficiencies found across any dimension.

**Risk tier:**
- `high` — any DENY-level condition, active suspension, or board review action.
- `medium` — HOLD with fixable deficiencies.
- `low` — APPROVE with no material issues.

**Policy impacted:** Set `true` when a current policy baseline (from `/api/policies`) imposes a requirement that changes the eligibility outcome compared to what prior standards would have produced. Compare the policy document's effective date against the application timeline.

**Summary cross-checks:**
- `approve_count` + `hold_count` + `deny_count` must equal the total application count.
- `high_risk_application_ids` must be a subset of the application IDs listed in application_decisions.
- `policy_impacted_application_ids` must be a subset of the application IDs.
- `stale_or_unverified_correspondence_ids` pulled from correspondence records across all applications.

### 4B — Restricted Liquor License Staff Package (domain: `liquor`)

For the target application and location, evaluate:

| Dimension | Data Source(s) | Analysis |
|---|---|---|
| **Application** | `/api/liquor/applications` | License class, applicant identity, location, same-premises basis, requested privileges. |
| **Settlements** | `/api/liquor/settlements` | Prior settlements or board orders that bind the applicant or location. Tax holds, agreed restrictions. |
| **Privileges** | `/api/liquor/privileges` | Current active privileges at the location. Identify overlaps or gaps with the requested license. |
| **Incidents** | `/api/liquor/incidents` | History of incidents tied to the applicant or location. Map each incident to a risk code. |
| **Site Evidence** | `/api/liquor/site-evidence` | Floor plans, control signage, police memos, neighbor notices, site photos. Check currency and completeness. |
| **Policies** | `/api/policies` | Current policy baseline for liquor licensing — may impose additional verification or control requirements. |

**Posture determination:**
- `issue_restricted` — the application can proceed but with specific controls, monitoring, and escalation triggers attached.
- `request_follow_up` — gaps in evidence or unresolved items prevent a decision; staff must obtain missing materials.
- `deny` — the application cannot be approved under current rules (unresolved serious incidents, board order conflicts, unfixable site issues).

**Same-premises basis:** Set `true` when the application replaces or transfers a license at the same physical premises. Check the application record and site evidence for continuity indicators (same address, same floor plan, existing control signage).

**Risk codes (`covered_risk_codes`):** Only include risks that are **currently covered** by existing controls or obligations. A risk is "covered" when there is a specific control, obligation, or monitoring check that addresses it. Do not list risks that are identified but unaddressed — those belong in verification gaps or escalation triggers.

**Verification gaps (`verification_gap_codes`):** Include when evidence is missing, stale, conflicting, or insufficient to confirm a control is in place. Each gap must correspond to a specific piece of evidence that is absent or inadequate.

**Standard vs. location-specific obligations:**
- `standard_obligation_codes` — obligations required for **all** licenses of this class, regardless of location. Pull from the license class definition and policy baseline.
- `location_specific_control_codes` — additional controls imposed because of **this specific location's** history, layout, or risk profile. Only include controls that are actively required for this location.

**First-90-day plan (`first_90_day_plan`):** A sequenced list of monitoring checks, each with a `check_code` and a `timing` bucket (`first_30_days`, `days_31_60`, `days_61_90`). Order checks in operational sequence — early verification first, ongoing monitoring later. Only include checks that address a specific identified risk or gap.

**Escalation triggers (`escalation_trigger_codes`):** Conditions that, if observed during the monitoring period, require field staff to escalate to a senior reviewer or board. Each trigger should map to a specific risk scenario from the incident history or site assessment.

### 4C — Alcohol Renewal Manual Review Queue (domain: `alcohol`)

For the target license range, build a ranked queue:

| Dimension | Data Source(s) | Analysis |
|---|---|---|
| **Licensees** | `/api/alcohol/licensees` | License identity, facility name, address, status. |
| **Violations** | `/api/alcohol/violations` | Violation records with dates, descriptions, and identifiers. |
| **Renewal Rules** | `/api/renewal/rules` | Current renewal criteria, flag conditions, and review thresholds. |
| **SQL (optional)** | POST `/api/sql` | For complex matching or aggregation across licensee and violation data. |

**Queue construction:**
1. Load all licensees in the target range.
2. Load all violations.
3. Match violations to licensees. Match confidence levels:
   - `exact` — violation references the exact license number.
   - `close_address` — violation references a matching or near-matching address but a different or missing license number.
   - `uncertain` — partial match on name or facility but not conclusively the same entity.
4. Apply the **boundary date** from the prompt. Violations dated on or after the boundary date are **excluded** from violation counts and matched IDs but must be listed in `post_boundary_violation_ids_excluded`.
5. Rank licensees by severity: prioritize those with more violations, more recent violations, and higher-severity violation types. Ranks must be consecutive integers starting at 1.
6. Assign `risk_tier`:
   - `high` — serious violations, high count, or board-review conditions.
   - `medium` — moderate violation history with fixable issues.
   - `low` — minor or old violations only.
7. Assign `next_step_label` based on the dominant issue type:
   - `board_review` — conditions that require board-level decision.
   - `manual_fine_check` — fine-related violations needing manual verification.
   - `manual_ALERT_check` — ALERT-system flags needing validation.
   - `additional_record_check` — insufficient data; pull additional records.

**Summary:**
- `queue_size` — must equal the actual queue length (target size from prompt).
- `boundary_date` — the boundary date from the prompt.
- `post_boundary_violation_ids_excluded` — every violation ID that was excluded for being on or after the boundary date, sorted ascending.
- `close_or_uncertain_match_license_numbers` — license numbers where match confidence was not `exact`.
- `board_review_license_numbers` — license numbers with `next_step_label` of `board_review`.

---

## Phase 5: Output Construction

### General rules (all domains)
1. Produce **exactly one JSON object** with the top-level keys declared in the answer template.
2. **No extra keys**, no prose, no markdown, no comments, no citations — even if the task reads like it expects a narrative.
3. **Empty arrays, not null or absent keys**, when no codes/IDs/items apply.
4. **Sort every list** as directed by the schema (ascending by code, by ID, by date — whatever the ordering directive says). If no ordering directive is given, default to ascending lexical order.
5. **Enum values must match exactly** — case-sensitive, underscore-preserving, no aliases.
6. **Summary counts must be internally consistent** with the item-level decisions. If three applications are APPROVE, `approve_count` must be 3.
7. String fields must use the **exact identifier format** from the source data — do not transform, truncate, or reformat IDs.

### Dates
- Use `YYYY-MM-DD` format for all date fields.
- The review date (when specified in the prompt) is the "as of" date for determining whether bonds, insurance, and licenses are current.
- The boundary date (in renewal tasks) is the cutoff for violation inclusion.

### SQL usage
When you run SQL queries, reference table names that correspond to the API paths. Standard patterns:
- `SELECT … FROM contractor_applications` (maps to `/api/contractor/applications`)
- `SELECT … FROM alcohol_violations` (maps to `/api/alcohol/violations`)
- Adapt table names based on the actual schema returned by the GET endpoints.

---

## Phase 6: Self-Check Before Returning

1. Are all target applications/licenses present in the output?
2. Is every list ordered as the schema requires?
3. Do the summary counts add up correctly?
4. Are all enum values from the allowed set?
5. Are there any extra keys, prose, or markdown?
6. Is every `policy_impacted` flag backed by a comparison of the current policy baseline against the application timeline?
7. Are dates in `YYYY-MM-DD` format?
8. Are empty conditions represented as `[]` not `null` or missing keys?

If any check fails, fix the output before returning.
