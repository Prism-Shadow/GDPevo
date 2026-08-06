# Licensing Review Skill

## Purpose
Conduct structured eligibility and compliance reviews for state licensing board applications — contractor, liquor, and alcohol renewal — by fetching data from a shared licensing API environment, applying business rules, and returning schema-compliant JSON decisions.

## When to Use
Invoke this skill when a prompt assigns a licensing examiner role and references a task environment base URL (`<TASK_ENV_BASE_URL>`), a batch of application or license identifiers, and an answer template schema.

---

## Operating Rules

### 1. Environment Bootstrap
1. Locate `environment_access.md` in the working directory.
2. Extract `base_url`. Substitute every occurrence of `<TASK_ENV_BASE_URL>` in the prompt with this value.
3. Extract credentials. The header `X-Task-Token` and its value are required for every `POST /api/sql` call.
4. Cross-reference the endpoints listed in the prompt against `allowed_endpoints` in `environment_access.md`. Only call endpoints that appear in both.

### 2. Role and Scope
- Adopt the role stated in the prompt (e.g., "Senior Licensing Examiner").
- Identify every target identifier from the prompt: application IDs, license numbers, or location codes. These define the scope — only these targets appear in the output.
- Note any review date or boundary date (e.g., "review date 2025-07-18", "release boundary 2025-04-10"). This date governs temporal filters: insurance/bond validity, violation recency, correspondence staleness.

### 3. Data Collection
Fetch from every GET endpoint listed in the prompt that also appears in `environment_access.md`:
- Contractor domain: `/api/policies`, `/api/contractor/applications`, `/api/contractor/bonds`, `/api/contractor/insurance`, `/api/contractor/license-history`, `/api/contractor/violations`, `/api/contractor/correspondence`, `/api/contractor/inspections`
- Liquor domain: `/api/policies`, `/api/liquor/applications`, `/api/liquor/settlements`, `/api/liquor/privileges`, `/api/liquor/incidents`, `/api/liquor/site-evidence`
- Alcohol/renewal domain: `/api/alcohol/licensees`, `/api/alcohol/violations`, `/api/renewal/rules`

When `POST /api/sql` is listed and present in `allowed_endpoints`, use it for complex cross-entity queries (e.g., joining violations to licensees, filtering by date ranges) that the GET endpoints cannot express directly. Include the `X-Task-Token` header on every SQL POST.

### 4. Record Matching
Match fetched records to target identifiers:
- **Exact match on ID**: application_id, license_no, location code.
- **Name/address matching** (renewal queue): When violation records use facility names rather than license numbers, match by name and address. Record match confidence as `exact` (ID match), `close_address` (address similarity), or `uncertain` (name-only match).
- **Temporal filtering**: Apply the review/boundary date. Violations after the boundary are excluded from scoring but recorded in the summary's exclusion list. Insurance/bonds are current only if their effective dates cover the review date.

### 5. Deficiency and Risk Assessment

#### Contractor Applications
For each target application, check these dimensions and map findings to the schema's deficiency codes and required actions:

| Dimension | Data Source | Check |
|-----------|------------|-------|
| Bond | `/api/contractor/bonds` | Active bond exists; amount meets requirement |
| Insurance | `/api/contractor/insurance` | Policy is current (covers review date); coverage meets minimum |
| License history | `/api/contractor/license-history` | No active suspensions |
| Violations | `/api/contractor/violations` | No open/unresolved serious complaints |
| Endorsements | applications record | Specialty endorsements verified |
| Experience | applications record | Experience requirements documented |
| Inspections | `/api/contractor/inspections` | No outstanding document gaps or failed safety rechecks |
| Correspondence | `/api/contractor/correspondence` | No stale or unverified correspondence |
| Policies | `/api/policies` | Current policy baseline may create new deficiencies |

**Determination logic:**
- `APPROVE`: No deficiencies. All required coverage current, no unresolved violations or suspensions.
- `HOLD`: Deficiencies that can be cured (e.g., bond shortfall, expired insurance, pending endorsement, documentation gaps). The applicant can fix these.
- `DENY`: Unresolvable or severe issues (e.g., active suspension, unresolved serious complaint).

**Risk tier logic:**
- `high`: Active suspension, unresolved serious violation, or multiple concurrent deficiencies.
- `medium`: At least one deficiency or a policy-impacted flag.
- `low`: Approve with no flags.

**Policy impact**: Set `policy_impacted: true` when a current policy standard (from `/api/policies`) creates a deficiency or material review flag that would not have existed under the prior baseline.

#### Liquor License Applications
For each target application, check these dimensions:

| Dimension | Data Source | Check |
|-----------|------------|-------|
| Application | `/api/liquor/applications` | Application details, status |
| Settlements | `/api/liquor/settlements` | Tax holds, settlement status |
| Privileges | `/api/liquor/privileges` | Current privileges |
| Incidents | `/api/liquor/incidents` | Open incidents, police involvement |
| Site evidence | `/api/liquor/site-evidence` | Floor plans, signage, photos, police memos, camera evidence, food service evidence |
| Policies | `/api/policies` | Policy baseline |

**Same-premises basis**: `true` when the application is for the same physical premises as a prior license (transfer/continuation), and the location records confirm continuity. `false` for new locations or when site evidence shows material changes.

**Covered risks**: Risk codes that current controls adequately address. Uncovered risks become verification gaps.

**Verification gaps**: Controls that are required but not yet verified (missing evidence, conflicting documents, stale records).

**Standard obligations vs. location-specific controls**: 
- `standard_obligation_codes`: Obligations required by license class regardless of location.
- `location_specific_control_codes`: Controls currently active at this specific location based on site evidence and privileges.

**First-90-day plan**: Build check items from verification gaps — each gap maps to a check_code. Distribute timing across the three 30-day windows based on urgency (missing evidence → `first_30_days`, follow-ups → `days_31_60`, rechecks → `days_61_90`).

**Escalation triggers**: Conditions that should cause field staff to escalate — drawn from uncovered risks, open incidents, and unverified critical controls.

**Posture determination:**
- `issue_restricted`: All critical controls verified; risks covered. Issue with standard restrictions.
- `request_follow_up`: Verification gaps exist but are resolvable. Do not issue until gaps close.
- `deny`: Unresolvable issues (tax hold, major incidents, same-premises basis broken).

#### Alcohol Renewal Queue
For building a ranked manual-review queue:

1. Fetch all licensees from `/api/alcohol/licensees`.
2. Fetch all violations from `/api/alcohol/violations`.
3. Fetch renewal rules from `/api/renewal/rules`.
4. Match violations to licensees by name, address, or license number.
5. Exclude violations dated after the boundary date. Record excluded IDs in the summary.
6. Rank licensees by: violation count (descending), then most recent violation date (ascending), using only pre-boundary violations.
7. Assign match confidence per the matching method.
8. Assign risk tier: `high` (serious violations or ≥3 violations), `medium` (1-2 non-serious violations), `low` (no matched violations).
9. Assign next step: `board_review` for high risk, `manual_ALERT_check` or `manual_fine_check` for medium, `additional_record_check` for low/uncertain matches.
10. Fill the queue to the target size. If fewer licensees have violations than the target, pad with zero-violation licensees ranked at the bottom.

### 6. Output Construction

1. Load `input/payloads/answer_template.json` for the task.
2. Build the output object key-by-key from the template's `required_top_level_keys` or `top_level_keys` specification.
3. For each target, populate all fields using only values from the schema's `allowed_values`.
4. Apply ordering rules exactly as stated (ascending by ID, lexical order, by date then ID, operational sequence).
5. Use empty arrays (`[]`) when no codes, IDs, or actions apply — never omit a required key.
6. Verify summary counts (approve/hold/deny, queue size) are consistent with item-level decisions.
7. Return **only** the JSON object. No prose, markdown, citations, comments, or extra keys.

### 7. Validation Checklist

Before returning output, confirm:
- [ ] `<TASK_ENV_BASE_URL>` resolved from `environment_access.md`
- [ ] Only allowed endpoints called; `X-Task-Token` on every SQL POST
- [ ] Every target from the prompt appears in the output
- [ ] All field values are from the schema's allowed_values
- [ ] Ordering matches schema instructions
- [ ] Summary counts match item-level decisions
- [ ] Review/boundary date applied to temporal filters
- [ ] Empty arrays where no codes apply
- [ ] Output is pure JSON — no wrapping text
- [ ] No keys present that are not in the answer template
