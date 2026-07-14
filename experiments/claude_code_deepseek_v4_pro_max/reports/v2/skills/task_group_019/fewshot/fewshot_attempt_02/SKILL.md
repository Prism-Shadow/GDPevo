# Cascadia Licensing Review Portal (CLRP) — Reusable Skill

## 1. Environment Setup

The CLRP base URL is provided via the `<TASK_ENV_BASE_URL>` placeholder or
an `environment_access.md` file.  Always resolve the runtime URL from
`environment_access.md` first; that value overrides any `localhost`, `127.0.0.1`,
`env/setup.sh`, or inline `<TASK_ENV_BASE_URL>` reference.

Example resolved base URL (from environment_access.md):
```
ENV_BASE_URL = http://34.46.77.124:9019
```

Never inspect local files, databases, manifests, setup scripts, or hidden task
files.  All data comes from the CLRP API and public CSV exports at the resolved
base URL.

---

## 2. API Endpoint Reference

All endpoints are `GET` requests.  Responses are JSON unless noted otherwise.
Replace `<ENV_BASE_URL>` with the resolved URL from §1.

### 2.1 Contractor Records
| Endpoint | Purpose |
|---|---|
| `/api/contractors/applications?batch_id=<BATCH>` | List every application in a batch |
| `/exports/contractor_batch_<BATCH>.csv` | Batch CSV export (text/csv) |
| `/api/contractors/bonds?name=<legal_or_principal_name>` | Active bond records |
| `/api/contractors/insurance?name=<legal_name_or_policy>` | Insurance policies |
| `/api/contractors/violations?name=<legal_or_principal_name>` | Violation history |
| `/api/contractors/complaints?name=<legal_name>` | Complaints filed |
| `/api/contractors/field-notes?name=<legal_name>` | Inspector field notes |
| `/api/contractors/correspondence?batch_id=<BATCH>` | Batch correspondence items |
| `/api/contractors/bulletins?effective_on=YYYY-MM-DD` | Bulletins effective on or before date |

### 2.2 Alcohol Licensing Records
| Endpoint | Purpose |
|---|---|
| `/api/alcohol/applications?review_month=YYYY-MM` | Alcohol applications in month |
| `/api/alcohol/premises?premises_id=<ID>` | Premises detail (address, prior licensees) |
| `/api/alcohol/incidents?premises_id=<ID>` | Incidents linked to the premises |
| `/api/alcohol/settlements?premises_id=<ID>` | Settlement / enforcement actions |
| `/api/alcohol/restrictions?premises_id=<ID>` | Current location-specific restrictions |
| `/api/alcohol/standard-obligations?license_type=<TYPE>` | Standard obligations for license type |

### 2.3 Renewal Records
| Endpoint | Purpose |
|---|---|
| `/api/renewals/licensees?release_batch=<BATCH>` | Licensees in a release batch |
| `/api/renewals/violations?city=<CITY>` | Violations by city |
| `/api/search/address?address=<ADDR>` | Address search / canonicalization |
| `/exports/renewal_roster_<BATCH>.csv` | Roster CSV export (text/csv) |

### 2.4 Health Check
| Endpoint | Purpose |
|---|---|
| `/health` | Liveness / connectivity check |

---

## 3. Task-Type Workflows

### 3.1 Contractor Eligibility Review (batches HS-*)

**Goal:** Produce an eligibility determination (APPROVE / HOLD / DENY) for every
application in the batch, plus deficiency counts and bulletin-impact summary.

**Data-collection order:**
1. `GET /api/contractors/applications?batch_id=<BATCH>` — master application list.
2. `GET /api/contractors/bulletins?effective_on=<CUTOFF_DATE>` — active bulletins.
3. `GET /api/contractors/correspondence?batch_id=<BATCH>` — batch correspondence.
4. For every application in the batch, call the following endpoints using the
   contractor's legal name (and principal name where relevant) from the
   application record:
   - `GET /api/contractors/bonds?name=<name>`
   - `GET /api/contractors/insurance?name=<name>`
   - `GET /api/contractors/violations?name=<name>`
   - `GET /api/contractors/complaints?name=<name>`
   - `GET /api/contractors/field-notes?name=<name>`

**Determination rules (check in this order of severity):**

| Condition | Determination | Reason Code | Next Action |
|---|---|---|---|
| Complaint or violation record shows disqualifying conduct | DENY | `DISQUALIFYING_CONDUCT` | `DENY_APPLICATION` |
| Prior registration disposition is adverse | HOLD | `ADVERSE_PRIOR_REGISTRATION` | (via manual followup) |
| Active bond status is cancelled | HOLD | `BOND_CANCELLED` | `REQUEST_REPLACEMENT_BOND` |
| Active bond coverage amount < required minimum | HOLD | `BOND_SHORTFALL` | `REQUEST_BOND_RIDER` |
| Insurance policy is expired/lapsed or coverage < required | HOLD | `INSURANCE_VERIFY` | `REQUEST_INSURANCE_VERIFICATION` |
| Outstanding unresolved penalties on violations | HOLD | `UNRESOLVED_PENALTY` | `REFER_UNRESOLVED_PENALTY` |
| Field note with unresolved/hold flag | HOLD | `FIELD_NOTE_HOLD` | `REQUEST_FIELD_CLEARANCE` |
| Experience / work-history documentation missing | HOLD | `EXPERIENCE_VERIFY` | `REQUEST_EXPERIENCE_DOCUMENTATION` |
| Material batch correspondence unresolved | HOLD | `CORRESPONDENCE_HOLD` | (via manual followup) |
| Financial statement missing | HOLD | `FINANCIAL_STATEMENT_MISSING` | (via manual followup) |
| No deficiency found | APPROVE | `NO_DEFICIENCY` | `NO_ACTION` |

- Multiple HOLD reasons on the same application → `COMBINED_HOLD_REVIEW` as next action.
- Reason codes must be listed in the **enum order** defined by the answer template, not discovery order.
- `DISQUALIFYING_CONDUCT` takes precedence over other codes — a DENY should list only that reason code.
- HOLD takes precedence over APPROVE — any HOLD-level finding blocks approval.

**Bulletin-impact analysis:**
- List every bulletin ID returned by the bulletins endpoint as `applicable_bulletin_ids`.
- Compare each application's determination against pre-2026 baseline rules: if a
  2026 bulletin changes the required bond/insurance/exam/experience thresholds
  and that change is what triggered a deficiency, the application was *changed
  by 2026 bulletins*.
- `deficiency_count_by_rule_type` counts applications where the deficiency was
  caused by a 2026 bulletin rule change in each category:
  `EXAM_MINIMUM`, `BOND_MINIMUM`, `INSURANCE_MINIMUM`, `EXPERIENCE_MINIMUM`.
- `unchanged_by_bulletins_count` = total applications − count of applications
  changed by 2026 bulletins.

**When `manual_followup_required` is requested:**
- `true` for every application with determination HOLD or DENY.
- `false` for APPROVE.
- Followup reason codes map from deficiency reason codes (see §5).

### 3.2 Alcohol License Review

**Goal:** Assess risk, identify verification gaps, enumerate standard obligations
and location-specific controls, and make a licensing recommendation.

**Data-collection order:**
1. `GET /api/alcohol/applications?review_month=<YYYY-MM>` — get the target
   application and all other applications in the month for comparison context.
2. `GET /api/alcohol/premises?premises_id=<ID>` — address, prior licensees,
   successor risk indicators.
3. `GET /api/alcohol/incidents?premises_id=<ID>` — incident history.
4. `GET /api/alcohol/settlements?premises_id=<ID>` — settlement/enforcement.
5. `GET /api/alcohol/restrictions?premises_id=<ID>` — current location-specific restrictions.
6. `GET /api/alcohol/standard-obligations?license_type=<TYPE>` — obligations
   tied to the license type (use the license type from the target application).

**Risk assessment logic:**
- `same_premises_basis`: `SAME_ADDRESS_OVERLAP` if prior licensee occupied the
  same address; `PRIOR_SETTLEMENT_AT_ADDRESS` if settlements exist at the
  address but no direct prior-licensee overlap; otherwise `NONE`.
- `prior_incident_level`: derive from incident count and severity — `HIGH` for
  ≥5 incidents or any high-severity incident; `MODERATE` for 2-4 incidents with
  no high-severity; `LOW` for 1 minor incident; `NONE` for zero.
- `settlement_posture`: `PRIOR_WARNING_WITH_CONTROLS` if prior settlements
  imposed controls; `PRIOR_RESTRICTED_OR_DENIAL` if prior license was restricted
  or denied; `CURRENT_SETTLEMENT` if an active settlement is open; `NONE` if no
  settlements found.
- `control_coverage`: `STANDARD_ONLY` if existing restrictions don't cover all
  needed controls; `ADEQUATE_LOCATION_SPECIFIC` if they do; `NO_CONTROLS` if no
  restrictions found.
- `overall_risk`: `ELEVATED` if `prior_incident_level` is HIGH and
  `control_coverage` is not ADEQUATE; `SEVERE` if disqualifying conduct or prior
  denial; `MODERATE` for moderate incident level with gaps; `LOW` otherwise.

**Verification gaps:** Compare:
- Controls implied by incident patterns (e.g., age-related incidents → need
  AGE_CHECK control) against existing restrictions.
- Settlement conditions against currently active restrictions.
- Any incident with pending/blank disposition → `PENDING_POLICE_CALL_DISPOSITIONS`
  or `PENDING_INCIDENT_DISPOSITIONS`.
- Controls needed but not in current restrictions → gap entries.

**Recommendation:**
- Gaps exist but none are blocking → `REQUEST_FOLLOWUP`
- All controls verified, risk is LOW/MODERATE → `ISSUE_RESTRICTED`
- Blocking gap (disqualifying conduct, severe risk) → `DENY`

**Monitoring-plan variant (train_005 pattern):**
- Adds `successor_risk_classification` (LOW / MODERATE / HIGH) based on prior
  licensee linkage at the premises.
- `premises_specific_controls` include `first_90_day_check: true` for controls
  needing early verification.
- `records_requests` document what evidence must be collected before final
  issuance.
- `escalation_triggers` define conditions that would escalate the license to
  enforcement review.

### 3.3 Renewal Manual-Review Queue

**Goal:** Build a ranked queue of exactly 10 licensees requiring manual review
before the release boundary date.

**Data-collection order:**
1. `GET /api/renewals/licensees?release_batch=<BATCH>` — licensee roster.
2. For each licensee, extract the city from their address and call
   `GET /api/renewals/violations?city=<CITY>`.
3. Match violation records to licensees by facility name. If exact match fails,
   try `GET /api/search/address?address=<ADDR>` to resolve shared-address
   relationships for `close` or `shared_address_manual` confidence.

**Filtering and ranking:**
1. Exclude all violation records whose `violation_date` is **strictly after**
   the release boundary date. Count these as `excluded_post_boundary_count`.
2. For each licensee, compute:
   - `violation_count_used` = count of matched violations with date ≤ boundary.
   - `most_recent_date_used` = latest `violation_date` among those matched.
3. Primary sort: `violation_count_used` descending.
4. Secondary sort: `most_recent_date_used` descending.
5. Tertiary sort (tiebreaker): `license_id` ascending.
6. Select the top 10 and assign ranks 1–10.
7. If fewer than 10 licensees have violations, fill remaining slots with the
   highest-risk zero-violation licensees (by recency of last renewal or similar).

**Match confidence:**
- `exact` — facility name matches violation respondent name exactly.
- `close` — facility name fuzzy-matches or address matches with different name.
- `shared_address_manual` — same address as a matched licensee but different
  facility name; requires manual address-link review.

**Next-step assignment:**
- `board review` — highest violation count and/or most recent (default for top ranks).
- `manual fine check` — moderate violations, older dates, or fine-amount patterns.
- `manual ALERT check` — specific ALERT-flagged violations or older records.
- `additional record check` — lowest risk tier.

---

## 4. Output Conventions

1. **JSON only.** Never wrap output in markdown fences, prose, or narrative.
   Return a single JSON object matching the answer template schema exactly.
2. **Output schema source of truth** is `input/payloads/answer_template.json`.
   Every required key must be present; every enum must use a value from the
   allowed list; every count must be an integer.
3. **List ordering:**
   - Default: ascending by primary identifier (application_id, license_id,
     bulletin_id, source_id, obligation_code, control_code, request_code,
     trigger_code, gap_code).
   - Exception: `queue` ranks are business-significant (1 = highest priority).
   - Exception: reason_codes follow the enum declaration order in the template,
     NOT discovery order.
   - Follow explicit ordering rules in the template when present (e.g.,
     `"ordering": "not significant"` means any stable order is acceptable but
     ascending by code is safe).
4. **Empty collections:** Use `[]` (empty JSON array), never `null`, for list
   fields with no entries.
5. **Enum values are case-sensitive** and must match the template character for
   character.
6. **source_ids** always reference actual record IDs returned by the API
   (application IDs, premises IDs, bulletin IDs, incident IDs, settlement IDs,
   restriction IDs, obligation IDs).  Never invent IDs.
7. **Dates** use `YYYY-MM-DD` format; months use `YYYY-MM`.
8. **Booleans** are JSON `true` / `false`, not strings.

---

## 5. Deficiency → Followup Reason-Code Mapping (Contractor)

When a `manual_followup` section is required, map deficiency reason codes to
followup reason codes as follows:

| Deficiency Reason Code | Followup Reason Code |
|---|---|
| `ADVERSE_PRIOR_REGISTRATION` | `PRIOR_REGISTRATION_FILE_REVIEW` |
| `BOND_CANCELLED` | `BOND_REPLACEMENT_REQUIRED` |
| `BOND_SHORTFALL` | `BOND_INCREASE_REQUIRED` |
| `INSURANCE_VERIFY` | `CARRIER_VERIFICATION_REQUIRED` |
| `UNRESOLVED_PENALTY` | `PENALTY_LEDGER_REVIEW` |
| `FIELD_NOTE_HOLD` | `INSPECTOR_CLEARANCE_REQUIRED` |
| `EXPERIENCE_VERIFY` | `EXPERIENCE_DOCUMENTATION_REQUIRED` |
| `CORRESPONDENCE_HOLD` | `MATERIAL_CORRESPONDENCE_REVIEW` |
| `FINANCIAL_STATEMENT_MISSING` | `FINANCIAL_STATEMENT_REQUIRED` |

Followup entries appear only for applications where `manual_followup_required`
is `true`.  Followup reason codes are listed in the enum order from the
template, not discovery order.

---

## 6. Common Pitfalls

1. **Using the wrong base URL.** Always resolve `<TASK_ENV_BASE_URL>` to the
   value in `environment_access.md`. Never connect to `localhost` or
   `127.0.0.1` unless that file explicitly says so.
2. **Forgetting an application.** The applications endpoint returns the
   authoritative list. Every application in the response must have a decision
   entry; no application outside the batch should appear.
3. **Wrong enum ordering for reason_codes.** Follow the template's enum
   declaration order (e.g., `NO_DEFICIENCY` before `BOND_SHORTFALL`, etc.),
   not the order in which you discovered the deficiencies.
4. **Including post-boundary violations.** The renewal queue and any date-filtered
   analysis must exclude records dated strictly after the cutoff/boundary date.
5. **Confusing similar IDs.** Application IDs (`CA-*` / `AA-*`), bulletin IDs
   (`CB-*`), premises IDs (`PM-*`), incident IDs (`AI-*`), settlement IDs
   (`AS-*`), restriction IDs (`AR-*`), obligation IDs (`AO-*`), and license IDs
   (`LIC-*`) are distinct namespaces.  Never mix them.
6. **Using null for empty lists.** JSON `null` ≠ `[]`.  Always use `[]` when
   a list field has no entries.
7. **Including narrative.** The evaluator expects pure JSON.  Markdown fences,
   explanatory text, or comments outside the JSON object will cause failures.
8. **Skipping the comparison context.** In alcohol reviews, fetching other
   applications in the same review month is required for the
   `review_month_comparison` section.  Don't only fetch the target.
9. **Name-matching for contractor endpoints.** Some endpoints accept
   `legal_name`, others accept `principal_name` or `legal_or_principal_name`.
   Try the legal name first; if no results, also try the principal name from
   the application record.
10. **Bulletin effective_on semantics.** The date parameter is inclusive — bulletins
    effective on or before the cutoff date are returned.  Use the review cutoff
    date, not the current date.
