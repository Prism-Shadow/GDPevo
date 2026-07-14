# CLRP — Cascadia Licensing Review Portal Skill

## Overview

Operates the Cascadia Licensing Review Portal (CLRP) read-only API to perform
three review workflows: Harbor State contractor eligibility, restricted alcohol
license review, and renewal manual-review queue generation.

## Environment

- Base URL: replace `<TASK_ENV_BASE_URL>` from the task prompt with the remote
  URL from `environment_access.md` if that file exists; otherwise use as given.
- All endpoints are read-only JSON. CSV exports are snapshots (use JSON for
  decisions, CSV only for cross-check).
- Verify: `GET <BASE>/health`

## Source Precedence

1. **API JSON endpoints** — authoritative per-record data
2. **CSV exports** — batch snapshots; may be stale
3. **Bulletins / standard obligations** — global rule definitions
4. **`GET /api/search/address`** — cross-domain materialized lookup

Never infer missing data. `"count": 0` or empty list means that data does not
exist — treat absence as `NONE`, `0`, or `[]` as the field type demands.

## Universal Workflow Rules

### 1. Read the Answer Template First

Every task directory has `input/payloads/answer_template.json`. Read it before
collecting data. It defines:
- Required top-level keys and their exact names
- Allowed enum values (use only these — case-sensitive, exact strings)
- List ordering rules (usually ascending by ID or by enum definition order)
- Which fields are required vs optional
- Number precision (counts are always integers)

### 2. Collect All Data Before Deciding

Gather every endpoint the task domain covers. Query per-application endpoints
(bonds, insurance, violations, complaints, field-notes) for every application
in the batch. Query batch-level endpoints once. Never decide from partial data.

### 3. Apply Rules in a Fixed Order

For each application, walk the checks in the documented order below. The first
deficiency found doesn't end the check — collect ALL deficiency codes for each
application. Only then derive the determination.

### 4. Output JSON Only

No markdown fences, no narrative, no trailing text. One JSON object. All dates
`YYYY-MM-DD`, months `YYYY-MM`, all counts integers.

---

## Workflow 1: Contractor Eligibility (Harbor State)

**Triggers**: batch ID like `HS-2026-XXX`, "contractor eligibility," "Harbor State."

### Endpoints

| Endpoint | Param | Scope |
|---|---|---|
| `/api/contractors/applications` | `batch_id=<B>` | Batch |
| `/api/contractors/bonds` | `name=<legal_name>` | Per app |
| `/api/contractors/insurance` | `name=<legal_name>` | Per app |
| `/api/contractors/violations` | `name=<legal_name>` | Per app |
| `/api/contractors/complaints` | `name=<legal_name>` | Per app |
| `/api/contractors/field-notes` | `name=<legal_name>` | Per app |
| `/api/contractors/correspondence` | `batch_id=<B>` | Batch → filter by `affects_application_id` |
| `/api/contractors/bulletins` | `effective_on=<CUTOFF>` | Global |
| `/exports/contractor_batch_<B>.csv` | — | Snapshot |

**Name matching caveat**: Bond, insurance, violation, complaint, and field-note
endpoints do partial/fuzzy name matching. Always verify the returned record's
`legal_name` matches the application's `legal_name` before using it.

### Decision Walk (apply in order, collect all deficiencies)

**1. Background / Conduct**
- `background_status == "adverse"` → `ADVERSE_PRIOR_REGISTRATION`
- `prior_registration_id` is non-empty AND `background_status != "clear"` → `ADVERSE_PRIOR_REGISTRATION`
- Violation with `status == "unresolved"` AND (`severity == "high"` OR `ag_referral == 1`) → `UNRESOLVED_PENALTY`
- Violation with type containing "fraudulent" → `DISQUALIFYING_CONDUCT`
- Complaint with `status == "open"` AND `severity == "high"` → `DISQUALIFYING_CONDUCT`
- Field note with `recommended_action != "no action"` OR `finding_type` containing "hold" → `FIELD_NOTE_HOLD`

**2. Correspondence**
- Item for this app with `document_status` IN `("needs_review", "new")` AND `item_type == "material notice"` → `CORRESPONDENCE_HOLD`

**3. Bond**
- No bond record found → `BOND_SHORTFALL` (treat as zero coverage)
- Bond `status == "cancelled"` → `BOND_CANCELLED`
- Compare BOTH `declared_bond_amount` (from application) AND the bond record's `amount` against the bulletin `threshold_value` for the application's `trade`. If EITHER is below threshold → `BOND_SHORTFALL`

**4. Insurance**
- No insurance record → `INSURANCE_VERIFY`
- `verification_status != "verified"` → `INSURANCE_VERIFY`
- `coverage_amount` < bulletin `INSURANCE_MINIMUM` threshold for trade → `INSURANCE_VERIFY`

**5. Exam Score**
- Below bulletin `EXAM_MINIMUM` threshold → `EXAM_SCORE_SHORTFALL`

**6. Experience**
- Below bulletin `EXPERIENCE_MINIMUM` threshold → `EXPERIENCE_VERIFY`

**7. Financial Statement**
- `financial_statement_filed == 0` → `FINANCIAL_STATEMENT_MISSING`

### Determination

- Any DENY-class reason (`DISQUALIFYING_CONDUCT`, `BOND_CANCELLED`) → `DENY`
- Any HOLD-class reason (all others except NO_DEFICIENCY) → `HOLD`
- No issues → `APPROVE` with `reason_codes: ["NO_DEFICIENCY"]`

### Bulletin Impact Calculation

Compare each application's determination with and without active bulletins:
- "Without" means applying only pre-2026/pre-bulletin thresholds
- An application is "changed by bulletins" if its determination OR its reason
  codes would differ absent the bulletins
- `deficiency_count_by_rule_type`: count how many deficiencies across all apps
  are attributable to each rule type's bulletin threshold

### Template Variants

**`train_004` pattern** (HS-2026-Q1B style):
- Adds `manual_followup_required: boolean` per application decision
- Adds separate `manual_followup` list with `followup_reason_codes` for apps
  needing staff action. Map deficiency reasons to followup codes:
  - `ADVERSE_PRIOR_REGISTRATION` → `PRIOR_REGISTRATION_FILE_REVIEW`
  - `BOND_CANCELLED` → `BOND_REPLACEMENT_REQUIRED`
  - `BOND_SHORTFALL` → `BOND_INCREASE_REQUIRED`
  - `INSURANCE_VERIFY` (carrier mismatch) → `CARRIER_VERIFICATION_REQUIRED`
  - `INSURANCE_VERIFY` (replacement) → `INSURANCE_REPLACEMENT_REQUIRED`
  - `UNRESOLVED_PENALTY` → `PENALTY_LEDGER_REVIEW`
  - `EXPERIENCE_VERIFY` → `EXPERIENCE_DOCUMENTATION_REQUIRED`
  - `FINANCIAL_STATEMENT_MISSING` → `FINANCIAL_STATEMENT_REQUIRED`
  - `CORRESPONDENCE_HOLD` → `MATERIAL_CORRESPONDENCE_REVIEW`
  - `FIELD_NOTE_HOLD` → `INSPECTOR_CLEARANCE_REQUIRED`
- Uses `rule_change_summary` instead of `bulletin_impacts`

---

## Workflow 2: Alcohol License Review

**Triggers**: application ID `AA-2026-XXXX`, premises ID `PM-2026-XXX`, review month.

### Endpoints

| Endpoint | Param |
|---|---|
| `/api/alcohol/applications` | `review_month=YYYY-MM` |
| `/api/alcohol/premises` | `premises_id=<ID>` |
| `/api/alcohol/incidents` | `premises_id=<ID>` |
| `/api/alcohol/settlements` | `premises_id=<ID>` |
| `/api/alcohol/restrictions` | `premises_id=<ID>` |
| `/api/alcohol/standard-obligations` | `license_type=<TYPE>` |
| `/api/search/address` | `address=<ADDR>` |

Always query standard obligations for BOTH the specific `license_type` AND the
`ALL` type (obligations scoped to `ALL` apply universally).

### Risk Assessment

**Same-premises basis**: Read `premises.same_premises_basis`:
- Contains "same address" or "overlapping" → `SAME_ADDRESS_OVERLAP`
- `prior_licensee` non-empty, no same-address language → `PRIOR_SETTLEMENT_AT_ADDRESS`
- `prior_licensee` empty → `NONE`

**Incident counts** (from `GET /api/alcohol/incidents`):
- `incident_count`: total records returned
- `unresolved_incident_count`: count where `disposition` is `"pending"` OR `""` (empty string)
- `high_severity_incident_count`: count where `severity == "high"`

**Prior incident level**: `0→NONE, 1-2→LOW, 3-4→MODERATE, 5+→HIGH`

**Settlement posture** (from `GET /api/alcohol/settlements`):
- No settlements → `NONE`
- `prior_or_current == "current"` → `CURRENT_SETTLEMENT`
- `original_posture` contains "restricted" or "denial" → `PRIOR_RESTRICTED_OR_DENIAL`
- `original_posture == "warning"` → `PRIOR_WARNING_WITH_CONTROLS`

**Control coverage** (from `GET /api/alcohol/restrictions`):
- Has any entry with `category == "premises-specific"` → `ADEQUATE_LOCATION_SPECIFIC`
- Only `category == "standard-obligation"` entries → `STANDARD_ONLY`
- No restrictions → `NO_CONTROLS`

**Overall risk**: Synthesize — HIGH incident level + unresolved + CURRENT_SETTLEMENT → `SEVERE`;
MODERATE incidents + any settlement → `ELEVATED`; LOW + standard controls → `MODERATE`;
clean → `LOW`.

### Verification Gaps (train_002 pattern — string list)

Identify missing or incomplete controls:
- No `AGE_CHECK` restriction → `AGE_VERIFICATION_CONTROL_NOT_IN_CURRENT_RESTRICTIONS`
- No `SECURITY_LOG` or `SECURITY_PLAN_LAPSE` related restriction with late-night incidents → `LATE_NIGHT_SECURITY_CONTROL_NOT_IN_CURRENT_RESTRICTIONS`
- Any incident `disposition == "pending"` → `PENDING_POLICE_CALL_DISPOSITIONS`
- Security plan lapse incident with empty disposition → `SECURITY_PLAN_LAPSE_DISPOSITION_MISSING`
- Prior settlement with no matching restrictions → `SETTLEMENT_TERMS_NOT_FOUND`
- None of the above → `NO_VERIFICATION_GAPS`

### Verification Gaps (train_005 pattern — object list with source_ids)

Each gap is an object with `gap_code`, `source_ids` (list of incident/settlement IDs supporting the gap), and `status`:
- `CONTROL_EVIDENCE_NOT_VERIFIED` → `MONITOR_IN_FIRST_90_DAYS`
- `PENDING_INCIDENT_DISPOSITIONS` → `REQUEST_BEFORE_FINAL`
- `POST_REVIEW_SETTLEMENT_TIMING` (settlement dated after review month) → `MONITOR_IN_FIRST_90_DAYS`
- `STANDARD_CONTROL_OVERLAP` (standard obligation also appears as premises-specific) → `SEPARATE_FROM_PREMISES_CONTROLS`
- `SUCCESSOR_CONTROL_SEPARATION` (prior licensee at same address) → `SEPARATE_FROM_PREMISES_CONTROLS`

### Inspection / Monitoring Controls

**Standard obligations**: From `GET /api/alcohol/standard-obligations` for the
license type + ALL. Map to the template's `control_code` / `obligation_code`
enum. Use `obligation_id` as `source_obligation_id`.

**Premises-specific controls**: From `GET /api/alcohol/restrictions` where
`category == "premises-specific"`. Include `control_code`, `source_ids`
(referencing restriction_id and settlement_id), check type, and whether it
requires first-90-day focus.

### Successor Risk (train_005)

- Same-premises basis + prior licensee non-empty + prior incidents → `HIGH`
- Same-premises basis + prior licensee non-empty + no prior incidents → `MODERATE`
- No prior licensee → `LOW`

### Records Requests & Escalation Triggers (train_005)

Derive from verification gaps and risk. Each gets a `request_code`/`trigger_code`
and `source_ids` referencing the underlying records (incident IDs, settlement IDs,
restriction IDs).

### Recommendation

Varies by template — always use the template's enum:
- `train_002`: `ISSUE_RESTRICTED`, `REQUEST_FOLLOWUP`, `DENY`
- `train_005`: `ISSUE_STANDARD`, `ISSUE_RESTRICTED_WITH_MONITORING`, `REQUEST_RECORDS_BEFORE_ISSUE`, `DENY`

### Review Month Comparison (train_002)

From `GET /api/alcohol/applications?review_month=<MONTH>`:
- `review_month_application_count`: total applications in the month
- For each application, check if its premises has location-specific restrictions → count as `restricted_reviews_with_location_specific_controls_count`
- `application_ids_with_location_specific_controls`: list their application IDs

---

## Workflow 3: Renewal Manual-Review Queue

**Triggers**: release batch `RV-2026-XXX`, release boundary date.

### Endpoints

| Endpoint | Param |
|---|---|
| `/api/renewals/licensees` | `release_batch=<B>` |
| `/exports/renewal_roster_<B>.csv` | — |
| `/api/renewals/violations` | `city=<CITY>` |
| `/api/search/address` | `address=<ADDR>` |

### Procedure

1. **Fetch all licensees** from the API and CSV export (CSV for cross-reference).
2. **Collect all unique cities** from licensees, then fetch violations for each city.
3. **Match violations to licensees** using three tiers:

   | Confidence | Rule |
   |---|---|
   | `exact` | `historical_name` == `facility_name` AND address matches |
   | `close` | Significant substring overlap between names, OR `successor_hint` matches `historical_name` |
   | `shared_address_manual` | Same address, different names |

4. **Apply boundary exclusion**: Drop violations where `violation_date > release_boundary`. Count these as `excluded_post_boundary_count`.

5. **Compute per-licensee metrics**:
   - `violation_count_used`: number of matched violations within boundary
   - `most_recent_date_used`: max violation_date among matched violations
   - `match_confidence`: use the highest confidence tier that produced a match (exact > close > shared_address_manual)

6. **Rank**: Sort by `violation_count_used` descending, then `most_recent_date_used` descending. Take top 10. Assign rank 1 through 10.

7. **Assign next_step_label** per licensee (use the worst case):
   - Any matched violation with `alert_related == 1` → `"manual ALERT check"`
   - Any with `fine_cents > 0` AND `disposition == "pending"` → `"manual fine check"`
   - Any with `severity == "high"` → `"board review"`
   - Otherwise → `"additional record check"`

8. **Method flags**:
   - `post_boundary_exclusion_applied`: `true` if any violations were excluded
   - `shared_address_records_not_spread`: `true` (shared addresses aren't artificially spread)
   - `queue_size`: `10`

---

## Cross-Domain Lookups

`GET /api/search/address?address=<URL-encoded address>` returns a consolidated
object with `alcohol_applications`, `alcohol_premises`, `renewal_licensees`, and
`renewal_violations` arrays. Use this when you need to connect records across
domains (e.g., checking if a contractor address is also a licensed premises).

---

## Pitfalls

1. **Name matching is partial**: Bond/insurance/violation/complaint/field-note endpoints use fuzzy name matching. Always verify `legal_name` in the response matches the application's `legal_name`.

2. **Bulletin applicability**: A bulletin with `effective_date` AFTER the application's `application_date` but ON OR BEFORE the review cutoff date still applies. Bulletins effective after the cutoff do not apply.

3. **Empty string ≠ missing**: `disposition: ""` counts as unresolved; `prior_registration_id: ""` means no prior — don't treat it as a valid ID.

4. **Bond amounts differ**: The application's `declared_bond_amount` and the bond record's `amount` can differ. Check BOTH against bulletin thresholds.

5. **Standard obligations are license-type-specific + ALL**: Always query both the application's `license_type` AND the `ALL` type. Merge the results. Every license has at least `INCIDENT_REPORT` and `PUBLIC_RECORDS`.

6. **Renewal name matching is fuzzy**: Violation `historical_name` rarely matches licensee `facility_name` exactly. Use substring matching: strip trailing numbers, match on shared words, check `successor_hint`.

7. **Settlement dates can post-date the review**: A settlement dated after the review month still informs `prior_or_current` and risk classification.

8. **Correspondence is batch-scoped**: Always filter correspondence by `affects_application_id`. Don't attribute batch-level correspondence to the wrong application.

9. **CSV may be stale**: The CSV export is a materialized snapshot. API JSON endpoints reflect current state. Use API data for decisions.

10. **Enum ordering matters**: When the template says "use the enum order listed here," sort reason codes by the order they appear in the template's `allowed_values` array, not alphabetically.

11. **Determination drives next_action**: In the contractor workflow, if multiple reasons exist, pick the most severe next action (deny > combined hold > specific fix). Multiple HOLD reasons without deny → `COMBINED_HOLD_REVIEW`.

12. **Review month applications are the comparison set**: For alcohol reviews, count ALL applications in the same review month, not just restricted-issuance ones.
