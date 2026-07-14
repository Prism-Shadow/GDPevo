# Cascadia Licensing Review Portal (CLRP) — Review Skill

## Environment

Base URL: read `environment_access.md` for the runtime URL. Replace every `<TASK_ENV_BASE_URL>` placeholder in task prompts with that value. Never use localhost or run `env/setup.sh` unless the remote URL itself points there.

## Source Precedence

Always prefer API endpoints over CSV exports for structured data. CSV exports are supplementary for batch snapshots. When an answer template is provided, conform to its schema exactly — do not add or omit keys.

---

## Domain 1: Contractor Eligibility Review

### Endpoints

| Endpoint | Parameters | Returns |
|---|---|---|
| `GET /api/contractors/applications` | `batch_id` | Application list for the batch |
| `GET /exports/contractor_batch_{batch_id}.csv` | — | CSV snapshot of batch |
| `GET /api/contractors/bonds` | `name` (substring match) | Bond records (may return distractors) |
| `GET /api/contractors/insurance` | `name` (substring match) | Insurance records (may return distractors) |
| `GET /api/contractors/violations` | `name` (substring match) | Violation records (may return distractors) |
| `GET /api/contractors/complaints` | `name` (substring match) | Complaint records (may return distractors) |
| `GET /api/contractors/field-notes` | `name` (substring match) | Field-note records (may return distractors) |
| `GET /api/contractors/correspondence` | `batch_id` | Batch-wide correspondence items |
| `GET /api/contractors/bulletins` | `effective_on` (YYYY-MM-DD) | Bulletins effective on or before that date |

### Name-Matching Rule (Critical)

Bonds, insurance, violations, complaints, and field-notes endpoints accept a **substring `name` query** over legal names. They return records whose `legal_name` contains the query string — including **distractors** (records for similarly named but different entities). You MUST filter results to the exact target entity.

**For bonds and violations**, match on BOTH `legal_name` AND `principal_name` against the application record. A bond for "Beacon Ridge Contracting Inc" is NOT a match for "Beacon Summit Contracting Inc" just because both contain "Beacon."

**For insurance, complaints, and field notes**, match on `legal_name` only (these endpoints use legal entity identity).

### Bulletin Application Logic

`effective_on` returns all bulletins with `effective_date <= the given date`. Bulletins with `trade_scope: "ALL"` apply to every trade. Trade-specific bulletins apply only when the bulletin's `trade_scope` matches the application's `trade` field.

Bulletin rule types and their application:
- **EXAM_MINIMUM**: `threshold_value` is the minimum passing exam score. Compare against `exam_score`.
- **BOND_MINIMUM**: `threshold_value` is the minimum bond amount for the trade. Compare against the **active bond's** `amount` (not the declared bond amount).
- **INSURANCE_MINIMUM**: `threshold_value` is the minimum liability coverage. Compare against the **matched active insurance's** `coverage_amount`.
- **EXPERIENCE_MINIMUM**: `threshold_value` is the minimum years. Compare against `experience_years`.

### Determination Rules

For each application, check these dimensions and assign reason codes:

#### Bond
1. Query bonds by the application's `legal_name` (use principal's last name if needed for broader search).
2. Filter to exact match: `legal_name` == application `legal_name` AND `principal_name` == application `principal_name`.
3. If no active bond found → `BOND_CANCELLED` (DENY).
4. If bond `status` is `"cancelled"` → `BOND_CANCELLED` (DENY).
5. If bond `status` is `"reduced"` → `BOND_SHORTFALL` (HOLD).
6. If active bond `amount` < bulletin BOND_MINIMUM for the trade → `BOND_SHORTFALL` (HOLD).
7. Consider the bond `note` field — "reduction notice pending review" indicates potential shortfall.
8. Otherwise bond is adequate.

#### Insurance
1. Query insurance by the application's `legal_name`.
2. Filter to exact `legal_name` match.
3. Check that insurance `carrier` matches `declared_insurance_carrier` AND `policy_number` matches `declared_insurance_policy`.
4. If no match or carrier/policy mismatch → `INSURANCE_VERIFY` (HOLD).
5. If insurance `coverage_amount` < bulletin INSURANCE_MINIMUM for the trade → `INSURANCE_VERIFY` (HOLD).
6. Check insurance `status` is `"active"` and `verification_status` is `"verified"`.

#### Violations
1. Query by application's `legal_name`.
2. Filter to exact `legal_name` AND `principal_name` match.
3. `ag_referral: 1` with `status: "unresolved"` → `DISQUALIFYING_CONDUCT` (DENY).
4. Unresolved violations with `penalty_due_cents > 0` → `UNRESOLVED_PENALTY` (HOLD).
5. Multiple unresolved violations → higher severity.
6. Resolved violations generally do not block.

#### Field Notes
1. Query by `legal_name`.
2. Filter to exact `legal_name` match.
3. `finding_type: "open hold"` → `FIELD_NOTE_HOLD` (HOLD).
4. `finding_type: "site visit"` with `recommended_action: "verify documents"` → `FIELD_NOTE_HOLD` (HOLD).
5. `finding_type: "resolved note"` → no action.

#### Complaints
1. Query by `legal_name`.
2. Filter to exact `legal_name` match.
3. Open complaints (non-closed status) → generally informational but may contribute to HOLD.

#### Correspondence
1. Query by `batch_id`.
2. Filter to the application's `application_id` via `affects_application_id`.
3. `item_type: "material notice"` with `document_status` in `["needs_review", "new"]` → `CORRESPONDENCE_HOLD` (HOLD).
4. `item_type: "certificate upload"` or `"address correction"` → generally no action unless status is `needs_review`.

#### Exam Score
1. Compare `exam_score` against the latest EXAM_MINIMUM bulletin (CB-2026-001: threshold 72 for ALL trades).
2. `exam_score < 72` → `EXAM_SCORE_SHORTFALL` (HOLD).

#### Experience
1. Compare `experience_years` against EXPERIENCE_MINIMUM bulletin for the trade.
2. At cutoff 2026-03-01, only HVAC has EXPERIENCE_MINIMUM (CB-2026-011: 3 years). Other trades have no experience minimum.

#### Financial Statement
1. `financial_statement_filed: 0` → `FINANCIAL_STATEMENT_MISSING` (HOLD).

#### Prior Registration
1. `background_status: "adverse"` → `ADVERSE_PRIOR_REGISTRATION` (DENY).
2. Non-empty `prior_registration_id` → `ADVERSE_PRIOR_REGISTRATION` (HOLD/DENY depending on severity).

#### Overall Determination
- **DENY**: Any DENY-level reason code (DISQUALIFYING_CONDUCT, BOND_CANCELLED, ADVERSE_PRIOR_REGISTRATION with adverse background).
- **HOLD**: Any HOLD-level reason code exists and no DENY reason.
- **APPROVE**: Only `NO_DEFICIENCY`.

### Next Action Mapping

| Reason Code | Next Action |
|---|---|
| `NO_DEFICIENCY` | `NO_ACTION` |
| `BOND_SHORTFALL` | `REQUEST_BOND_RIDER` |
| `BOND_CANCELLED` | `REQUEST_REPLACEMENT_BOND` |
| `INSURANCE_VERIFY` | `REQUEST_INSURANCE_VERIFICATION` |
| `UNRESOLVED_PENALTY` | `REFER_UNRESOLVED_PENALTY` |
| `FIELD_NOTE_HOLD` | `REQUEST_FIELD_CLEARANCE` |
| `DISQUALIFYING_CONDUCT` | `DENY_APPLICATION` |
| `EXPERIENCE_VERIFY` | `REQUEST_EXPERIENCE_DOCUMENTATION` |
| `CORRESPONDENCE_HOLD` | `COMBINED_HOLD_REVIEW` |
| `ADVERSE_PRIOR_REGISTRATION` | `COMBINED_HOLD_REVIEW` or `DENY_APPLICATION` |
| Multiple HOLD codes | `COMBINED_HOLD_REVIEW` |

### Bulletin Impacts Tracking

For `bulletin_impacts`:
- `applicable_bulletin_ids`: All bulletins whose rule_type matches a deficiency found in the batch.
- `applications_changed_by_2026_bulletins`: Applications where a 2026 bulletin created a deficiency that wouldn't have existed under prior rules.
- `deficiency_count_by_rule_type`: Count unique applications affected by each bulletin rule_type.
- `unchanged_by_bulletins_count`: Applications whose determination was NOT changed by any 2026 bulletin.

---

## Domain 2: Alcohol License Review

### Endpoints

| Endpoint | Parameters |
|---|---|
| `GET /api/alcohol/applications` | `review_month` (YYYY-MM) |
| `GET /api/alcohol/premises` | `premises_id` |
| `GET /api/alcohol/incidents` | `premises_id` |
| `GET /api/alcohol/settlements` | `premises_id` |
| `GET /api/alcohol/restrictions` | `premises_id` |
| `GET /api/alcohol/standard-obligations` | `license_type` |
| `GET /api/search/address` | `address` |

### Risk Assessment

From premises + incidents + settlements:
- **same_premises_basis**: Derive from premises data. `"same address and overlapping service area as prior licensee"` → `SAME_ADDRESS_OVERLAP`. Prior settlement → `PRIOR_SETTLEMENT_AT_ADDRESS`. None → `NONE`.
- **prior_incident_level**: Based on incident count and severity. 0 incidents → NONE. 1-2 low → LOW. 3+ or medium → MODERATE. Any high → HIGH.
- **incident_count**: Total incidents for the premises.
- **unresolved_incident_count**: Count of incidents where `disposition` is `"pending"` or `""` (blank).
- **high_severity_incident_count**: Count where `severity` is `"high"`.
- **settlement_posture**: From settlements. `prior_or_current: "prior"` with `original_posture: "warning"` → `PRIOR_WARNING_WITH_CONTROLS`. `original_posture: "restricted"` or `"denial"` → `PRIOR_RESTRICTED_OR_DENIAL`. `prior_or_current: "current"` → `CURRENT_SETTLEMENT`. No settlements → `NONE`.
- **control_coverage**: From restrictions. Has premises-specific category restrictions → `ADEQUATE_LOCATION_SPECIFIC`. Has only standard-obligation → `STANDARD_ONLY`. No restrictions → `NO_CONTROLS`.
- **overall_risk**: Synthesis: NONE incidents + no prior issues → LOW. Some low incidents → MODERATE. Medium/high incidents or prior restrictions → ELEVATED. High incidents + prior denials → SEVERE.

### Recommendation
- Clean premises + no incidents + standard obligations met → `ISSUE_STANDARD` or `ISSUE_RESTRICTED`.
- Moderate incidents + gaps in controls → `ISSUE_RESTRICTED_WITH_MONITORING` or `REQUEST_FOLLOWUP`.
- Severe incidents + no adequate controls → `DENY`.

### Standard Obligations
Query by the application's `license_type`. The endpoint returns obligations for that type plus `ALL`-scoped obligations. Use `obligation_code` and `evidence_required` directly.

### Location-Specific Restrictions
From the premises restrictions endpoint, filter `category: "premises-specific"`. Each gets a `status`:
- Present and recent → `CURRENT_PROPOSED`
- Evidence missing or needs verification → `FOLLOWUP_REQUIRED_BEFORE_ISSUE`
- Not present → `NOT_APPLICABLE`

### Verification Gaps (train_002)
Check that expected controls from incidents/settlements appear in current restrictions:
- Prior incidents about minors → check for AGE_CHECK or AGE_VERIFICATION controls.
- Late-night incidents → check for NO_AFTER_MIDNIGHT_SERVICE or SECURITY_LOG.
- Pending police dispositions → `PENDING_POLICE_CALL_DISPOSITIONS`.
- Security plan lapses with missing disposition → `SECURITY_PLAN_LAPSE_DISPOSITION_MISSING`.

### Verification Gaps (train_005 — Monitoring Plan)
For monitoring-focused reviews, gap codes are:
- `CONTROL_EVIDENCE_NOT_VERIFIED`: Restriction exists but evidence was not provided.
- `PENDING_INCIDENT_DISPOSITIONS`: Incidents with pending or blank disposition.
- `POST_REVIEW_SETTLEMENT_TIMING`: Settlement dated after review start.
- `STANDARD_CONTROL_OVERLAP`: Standard obligation overlaps with premises-specific control.
- `SUCCESSOR_CONTROL_SEPARATION`: Successor controls need distinct tracking from prior licensee.

### Successor Risk (train_005)
- `LOW`: No prior licensee at same address, or prior licensee with clean record.
- `MODERATE`: Prior licensee had incidents but no settlements/restrictions.
- `HIGH`: Prior licensee had settlements, restrictions, or high-severity incidents at same address.

### Escalation Triggers (train_005)
Based on monitoring findings:
- Missing age verification → `AGE_CHECK_AUDIT_MISSING_OR_FAILED`
- Missed 90-day check → `FIRST_90_DAY_CHECK_MISSED`
- New high-severity incident → `NEW_OR_CONFIRMED_HIGH_SEVERITY_INCIDENT`
- Pending incident confirmed → `PENDING_INCIDENT_CONFIRMED_VIOLATION`
- Successor link confirmed → `SUCCESSOR_LINK_CONFIRMED_TO_PRIOR_LICENSEE`

---

## Domain 3: Renewal Manual-Review Queue

### Endpoints

| Endpoint | Parameters |
|---|---|
| `GET /api/renewals/licensees` | `release_batch` |
| `GET /api/renewals/violations` | `city` |
| `GET /api/search/address` | `address` |
| `GET /exports/renewal_roster_{release_batch}.csv` | — |

### Queue Construction (train_003)

1. **Get the roster**: Fetch all licensees for the `release_batch`.
2. **Get violations by city**: Query `/api/renewals/violations?city=` for each distinct city in the roster (6 cities: Bay Crossing, Cedar Falls, Lakeview, Northport, Port Mason, Silverton).
3. **Match violations to licensees**: For each licensee, find violations where:
   - **Exact match**: `violation.historical_name` contains or matches `licensee.facility_name` (exact string match) AND same address → `"exact"` confidence.
   - **Close match**: Names are similar (differ by minor spelling/abbreviation like "Grill" vs "Grille", "Market" vs "Mkt", "Room" vs "Rm") AND same address → `"close"` confidence.
   - **Shared address**: Same address but different name → use address search to confirm → `"shared_address_manual"` confidence.
4. **Apply boundary filter**: Exclude violations with `violation_date > release_boundary`. Count excluded violations in `excluded_post_boundary_count`. Set `post_boundary_exclusion_applied: true`.
5. **Rank licensees**: Sort by:
   - Primary: Total matched violation count (descending).
   - Secondary: Most recent violation date (descending).
   - Tertiary: Severity (high > medium > low).
   - Quaternary: Fine amount (higher = higher rank).
6. **Select top 10**: Take exactly the top 10 ranked licensees.
7. **Assign next steps**:
   - ALERT violations → `"manual ALERT check"`
   - Unpaid fines → `"manual fine check"`
   - Suspension-related → `"board review"`
   - Other violation types → `"additional record check"`

### Method Flags (train_003)
- `shared_address_records_not_spread`: Set `true` if no violation-count inflation from shared-address records.

### Successor Hints (train_003)
Licensees with non-empty `successor_hint` field indicate potential entity changes. The hint suggests the prior name variant. These should be considered for manual review.

---

## General Habits

### Output Conventions
1. All output is JSON only — never include markdown fences, prose, or narrative outside the JSON object.
2. Dates use `YYYY-MM-DD` format. Months use `YYYY-MM`.
3. All counts are integers. No floats for counts.
4. Enum values are **case-sensitive**. Use exactly as specified in the answer template.
5. Lists ordered `"ascending"` use string sort order. Lists ordered `"not significant"` may use any order but prefer consistent ordering.

### Calculation Habits
1. **Count distinct applications**, not distinct deficiencies. One application with 3 deficiency codes counts as 1 in determination counts.
2. **Deficiency counts** track each unique reason-code occurrence across applications (each application can contribute at most 1 to each reason_code count).
3. **Filter before counting**: Always filter records to exact entity matches before applying business rules.
4. **Bulletin applicability**: A bulletin applies only if `effective_date <= cutoff_date`. Use the full bulletin list returned by the endpoint at that `effective_on` date.

### Common Pitfalls
1. **Name substring matching returns distractors**: The bonds/violations/insurance endpoints use SQL `LIKE '%name%'` — always filter to exact legal_name + principal_name matches before applying rules.
2. **Declared vs actual**: An application's `declared_bond_amount` is what the applicant claims. The actual bond record (from the bonds endpoint) is authoritative. Always use the bond record's amount.
3. **Bond note field**: Contains narrative like "reduction notice pending review" or "below current bulletin minimum" — these indicate issues even when status is "active."
4. **Bulletin effective_on semantics**: `effective_on=2026-03-01` returns bulletins with `effective_date <= 2026-03-01`. CB-2026-010 and CB-2026-011 (effective 2026-03-01) ARE included. CB-2026-012+ (effective 2026-03-12+) are NOT.
5. **Incident disposition blank vs "pending"**: Both count as unresolved. A blank `disposition` field (`""`) is distinct from `"pending"` but both are unresolved.
6. **Restriction categories**: `"standard-obligation"` vs `"premises-specific"` determine whether a restriction is location-specific or license-type-generic.
7. **Renewal boundary**: Violations dated AFTER the `release_boundary` must be excluded from the ranking calculation. Track these in `excluded_post_boundary_count`.
8. **Successor hints on renewal roster**: The `successor_hint` field indicates the licensee may be operating under a variant name; violations may be filed under either name.
