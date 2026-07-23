# Licensing Examination Skill

Reusable operating rules for State Licensing Board examination tasks — contractor batch eligibility, restricted liquor-license staff packages, and alcohol renewal queue screening.

---

## 1. Environment Access

| Item | Value |
|------|-------|
| Base URL | `http://task-env:9019/` |
| SQL auth header | `X-Task-Token: licensing-review-019` |

Every HTTP request must use the Base URL as prefix. The token header is **only** required on `POST /api/sql`; GET endpoints need no auth header.

### Allowed Endpoints

**Shared**
- `GET /api/policies` — current policy baseline; always fetch first
- `POST /api/sql` — ad-hoc SQL queries (requires token header)

**Contractor domain**
- `GET /api/contractor/applications`
- `GET /api/contractor/bonds`
- `GET /api/contractor/insurance`
- `GET /api/contractor/license-history`
- `GET /api/contractor/violations`
- `GET /api/contractor/correspondence`
- `GET /api/contractor/inspections`

**Liquor domain**
- `GET /api/liquor/applications`
- `GET /api/liquor/settlements`
- `GET /api/liquor/privileges`
- `GET /api/liquor/incidents`
- `GET /api/liquor/site-evidence`

**Alcohol / Renewal domain**
- `GET /api/alcohol/licensees`
- `GET /api/alcohol/violations`
- `GET /api/renewal/rules`

> **Important:** Never attempt paths not listed above. The server will reject them.

---

## 2. Universal Workflow

1. **Fetch policies first.** The `/api/policies` endpoint returns the current policy baseline. This is required for determining `policy_impacted` flags and understanding the rules that govern deficiency and risk classification.

2. **Fetch all relevant domain endpoints.** For the task type, call every listed endpoint to gather complete records. Do not skip any — each endpoint contributes data the answer template requires.

3. **Cross-reference records by application/license ID.** Join data across endpoints using the shared application or license identifiers to build the full picture per target.

4. **Evaluate against policy baseline.** Determine whether the current policy creates deficiencies or flags that would not have applied under the prior baseline. If so, `policy_impacted` is `true` for that application.

5. **Evaluate financial coverage against the review date.** Bond and insurance status (current, expired, shortfalls) is assessed relative to the stated review date, not the current calendar date. If no review date is stated, use the current date.

6. **Classify determination / posture / next-step.** Apply the policy rules and evidence to arrive at a determination, posture, or next-step label per the answer template's allowed values.

7. **Conform strictly to the answer template.** Return **only** a JSON object matching the provided answer_template.json. No prose, no markdown, no comments, no extra keys.

---

## 3. Contractor Batch Eligibility Pattern

**Triggers when:** task references contractor application IDs (pattern `C-TR*-*`) and asks for an eligibility decision, deficiency codes, required actions, risk tier, and policy_impacted.

### Steps

1. Fetch: `/api/policies`, `/api/contractor/applications`, `/api/contractor/bonds`, `/api/contractor/insurance`, `/api/contractor/license-history`, `/api/contractor/violations`, `/api/contractor/correspondence`, `/api/contractor/inspections`. Optionally use `POST /api/sql` for complex joins.

2. For each target application ID:
   - **License history:** Check for active suspensions → `active_suspension` deficiency, `DENY` or `HOLD`.
   - **Bond:** Verify a bond exists, is not cancelled, and meets the required amount. Gaps → `bond_cancelled`, `bond_shortfall`, `no_active_bond` (task-specific codes vary). Actions: `obtain_current_bond`, `file_active_bond`, `increase_bond_amount`, `increase_bond`.
   - **Insurance:** Must be current as of the review date and meet coverage minimums. Gaps → `insurance_expired`, `insurance_not_current`, `insurance_pending`, `insurance_shortfall`. Actions: `provide_current_insurance`, `renew_insurance`, `increase_insurance_amount`, `increase_insurance`, `verify_insurance_binding`.
   - **Endorsements:** Check specialty endorsements required by policy. Gaps → `endorsement_missing`, `endorsement_pending`, `endorsement_not_verified`. Actions: `obtain_required_endorsement`, `verify_pending_endorsement`, `verify_endorsement`.
   - **Experience:** Verify documented experience meets requirements. Gaps → `experience_shortfall`. Actions: `submit_experience_evidence`, `document_experience`.
   - **Violations:** Open serious violations → `open_serious_violation` or `unresolved_serious_complaint`. Open minor → `open_minor_violation`. Actions: `resolve_serious_violation`, `resolve_minor_violation_review`, `resolve_complaint`.
   - **Inspections:** Document gaps or safety rechecks → `inspection_doc_gap`, `inspection_safety_recheck`. Actions: `clear_document_gap`, `complete_safety_recheck`.
   - **Correspondence:** Identify stale or unverified correspondence; collect IDs for the summary.

3. **Determination logic:**
   - `DENY` if active_suspension is present or a disqualifying condition is met.
   - `HOLD` if deficiencies exist that can be remediated (e.g., pending insurance, minor violations, missing endorsements).
   - `APPROVE` only if no deficiency codes apply.

4. **Risk tier:**
   - `high` — active suspension, serious violation, or multiple deficiencies.
   - `medium` — one or two remediable deficiencies, no serious violations.
   - `low` — no deficiencies (APPROVE applications are low).

5. **Policy impacted:** `true` when the current 2025 policy baseline creates a deficiency or review flag that would not have existed under the prior baseline.

6. **Summary:** Count approve/hold/deny. List high-risk IDs, policy-impacted IDs, and stale/unverified correspondence IDs — all sorted ascending.

### Sorting rules
- `application_decisions`: ascending by `application_id`.
- Deficiency codes and required actions within each application: ascending lexical order.
- All summary ID lists: ascending lexical order.
- Use empty arrays when no items apply.

---

## 4. Restricted Liquor-License Staff Package Pattern

**Triggers when:** task references a liquor application ID (pattern `L-TR*-*`) at a location ID (pattern `LOC-TR*`) and asks for a staff package covering posture, risks, gaps, obligations, monitoring plan, and escalation triggers.

### Steps

1. Fetch: `/api/policies`, `/api/liquor/applications`, `/api/liquor/settlements`, `/api/liquor/privileges`, `/api/liquor/incidents`, `/api/liquor/site-evidence`. Optionally `POST /api/sql`.

2. Determine **recommended_posture**:
   - `issue_restricted` — all verification gaps are minor or can be addressed by standard conditions.
   - `request_follow_up` — significant gaps exist that must be resolved before issuance.
   - `deny` — disqualifying conditions (e.g., unresolved serious incidents, tax holds that cannot be cleared).

3. **same_premises_basis_applies:** `true` when the applicant is operating at the same premises as a prior license holder and the transfer qualifies under the same-premises rule. Check settlement and privilege history for the location.

4. **covered_risk_codes:** From the set of allowed values, include each risk that is adequately addressed by current controls (CCTV, signage, security, food service, tax clearance, etc.). Cross-reference privileges and site-evidence.

5. **verification_gap_codes:** Include each gap where evidence is missing, conflicting, or stale. Sources: site-evidence conflicts, missing signage, stale floor plans, missing neighbor notices, open incident follow-ups, conflicting police memos, missing tax clearance.

6. **standard_obligation_codes:** Obligations that apply to this license class generally (e.g., ID_CHECK, HOURS, SECURITY, FOOD_SERVICE, CCTV, PATIO, NOISE, DELIVERY). Include only those required for the class.

7. **location_specific_control_codes:** Obligations that are imposed specifically for this location, beyond the standard set. Only include controls actually tied to the location record.

8. **first_90_day_plan:** Construct a monitoring schedule with `check_code` / `timing` pairs. Distribute checks across `first_30_days`, `days_31_60`, `days_61_90`. Prioritize high-risk checks (camera tests, food service, late-night visits) in the first 30 days. Follow-up and less urgent checks in later windows.

9. **escalation_trigger_codes:** Conditions that would escalate the license to board review or enforcement action. Include each trigger that is relevant based on the risk profile, evidence gaps, and policy requirements.

### Sorting rules
- Arrays of code strings (covered_risk_codes, verification_gap_codes, standard_obligation_codes, location_specific_control_codes, escalation_trigger_codes): sort ascending by code, remove duplicates.
- `first_90_day_plan`: sort ascending by `check_code`; remove duplicate `check_code`/`timing` pairs.
- Some templates accept any order — sort ascending anyway for consistency.

---

## 5. Alcohol Renewal Manual Review Queue Pattern

**Triggers when:** task references alcohol license IDs (pattern `AL-TR*-*`) and asks for a ranked manual-review queue with a boundary date.

### Steps

1. Fetch: `/api/alcohol/licensees`, `/api/alcohol/violations`, `/api/renewal/rules`. Optionally `POST /api/sql`.

2. **Boundary date filtering:** The prompt specifies a release boundary date. Only violations dated **on or before** the boundary count for the queue. Violations after the boundary are excluded and listed in `post_boundary_violation_ids_excluded`.

3. **Match violations to licenses.** For each target license, find violations matched by license number. If the violation address is close but not exact, assign `match_confidence` accordingly:
   - `exact` — license number matches directly.
   - `close_address` — address is very similar but license number match is not exact.
   - `uncertain` — weak match, needs manual verification.

4. **Rank the queue.** More violations and more recent violations → higher risk → lower rank number (rank 1 = highest priority). Tiebreak by most recent violation date, then license number ascending.

5. **Risk tier:**
   - `high` — multiple violations or serious violations.
   - `medium` — one or two minor violations.
   - `low` — no matched violations (should not appear in a risk-priority queue unless required by target count).

6. **next_step_label:**
   - `board_review` — serious or pattern violations require board attention.
   - `manual_ALERT_check` — ALERT-flagged violations need manual check.
   - `manual_fine_check` — outstanding fines need verification.
   - `additional_record_check` — uncertain matches need further investigation.

7. **Summary:**
   - `queue_size` — number of entries (equals target count from prompt).
   - `boundary_date` — the stated release boundary.
   - `post_boundary_violation_ids_excluded` — violations after the boundary, sorted by violation_id ascending.
   - `close_or_uncertain_match_license_numbers` — licenses with non-exact confidence, sorted ascending.
   - `board_review_license_numbers` — licenses flagged for board review, sorted ascending.

### Sorting rules
- Queue entries: ascending by `rank` (1 through N, no gaps).
- `matched_violation_ids` within each entry: by violation date ascending, then violation_id ascending.
- All summary ID lists: ascending.

---

## 6. SQL Fallback Usage

When endpoint data is insufficient for complex cross-referencing (e.g., joining violations to licenses across address variations), use:

```
POST /api/sql
Header: X-Task-Token: licensing-review-019
Body: { "query": "<SQL>" }
```

Use SQL sparingly — as a complement to endpoint fetches, not a replacement. The endpoints provide the canonical record shapes.

---

## 7. General Conventions

| Convention | Rule |
|------------|------|
| Output format | JSON only, no prose, no markdown, no comments, no extra keys |
| Date format | `YYYY-MM-DD` |
| Financial coverage | Evaluate against the stated review date, not the current date |
| Empty values | Use `[]` for empty lists; never omit required keys |
| Array ordering | Ascending lexical/code sort unless the template specifies otherwise |
| Rank values | Sequential integers starting at 1, no gaps |
| Duplicates | Remove duplicate codes within any array field |
| policy_impacted | `true` only when the **current** policy baseline changes the eligibility analysis vs. the **prior** baseline |

---

## 8. Supporting File Reference

| File | Purpose |
|------|---------|
| `skill/policy_crosswalk.md` | How to determine `policy_impacted` from the policy baseline |
| `skill/deficiency_action_mapping.md` | Maps each deficiency code to its corresponding required action |
| `skill/risk_tier_decision_tree.md` | Decision tree for risk-tier classification |

These supporting files provide task-agnostic decision logic that applies regardless of which specific application IDs or license numbers appear in a future task.
