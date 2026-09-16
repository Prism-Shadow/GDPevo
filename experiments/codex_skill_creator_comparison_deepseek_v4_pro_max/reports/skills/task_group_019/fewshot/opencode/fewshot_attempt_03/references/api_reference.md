# API Reference

## Base URL

The base URL is discovered from `environment_access.md` in the workspace root. The prompt uses `<TASK_ENV_BASE_URL>` as a placeholder — read the actual URL from that file. The credential for SQL access is also in that file.

## Common Endpoint

### GET /api/policies

Returns an array of policy objects. Every task across all three families begins here.

**Response shape:**

```json
{
  "agency": "State Contractors Licensing Board",
  "citation": "SCLB POLICY-CITE",
  "details_json": "{\"minimum_bond\": 50000, \"minimum_insurance\": 1000000, ...}",
  "effective_date": "YYYY-MM-DD",
  "family": "contractor",
  "policy_id": "POL-CON-NNN",
  "rule_code": "CON-TRADE-ClassN",
  "title": "Trade Class N application standards"
}
```

**`details_json`** is a JSON string. Parse it with a JSON parser — do not substring-match it. Fields inside vary by policy family:

**Contractor policy fields:**
- `minimum_bond` (number) — required bond amount in dollars
- `minimum_insurance` (number) — required insurance coverage in dollars
- `minimum_years_experience` (number) — required years
- `required_endorsement` (string or null) — endorsement code, null when not required
- `serious_open_violation_blocks` (boolean)
- For the legacy baseline: `endorsement_required_for_specialty` (boolean), `minimum_bond_reduction` (number), `use_for_prior_rule_comparison` (boolean)

**Liquor policy fields:**
- `current_site_evidence_required` (boolean)
- `same_premises_history_matters` (boolean)
- Settlement/privilege standard references

**Renewal policy fields (inside `/api/renewal/rules`):**
- `alert_flag_requires_manual_review` (boolean)
- `late_rows_are_distractors` (boolean)
- `unpaid_fines_require_hold` (boolean)
- `use_violations_on_or_before` (string, date)

**Policy impact:** A legacy policy's `rule_code` typically mentions "LEGACY" and its `details_json` contains `"use_for_prior_rule_comparison": true`. When a current 2025 policy has stricter requirements than the legacy baseline, any deficiency caused solely by the new requirement creates a policy impact (`policy_impacted: true`).

## Contractor Endpoints

### GET /api/contractor/applications

Returns all contractor applications. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `application_id` | string | Unique identifier, e.g. "C-APP-001" |
| `applicant_name` | string | |
| `trade` | string | Determines which policy rule applies |
| `requested_class` | string | "Class A", "Class B", "Limited", "Specialty" |
| `endorsement_status` | string | "verified", "pending", "missing", "not_required" |
| `years_experience` | number | |
| `prior_license_id` | string or null | |
| `self_disclosed_issue` | string or null | |
| `submitted_date` | string | YYYY-MM-DD |
| `county` | string | |

**SQL table name:** `contractor_applications`

### GET /api/contractor/bonds

Returns bond records. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `bond_id` | string | |
| `application_id` | string | Links to application |
| `bond_amount` | number | |
| `status` | string | "active", "cancelled", "expired" |
| `effective_date` | string | |
| `expiry_date` | string | |

**SQL table name:** `contractor_bonds`

### GET /api/contractor/insurance

Returns insurance records. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `insurance_id` | string | |
| `application_id` | string | Links to application |
| `coverage_amount` | number | |
| `status` | string | "current", "expired", "pending" |
| `effective_date` | string | |
| `expiry_date` | string | |

**SQL table name:** `contractor_insurance`

### GET /api/contractor/license-history

Returns prior license and suspension records. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `license_id` | string | |
| `application_id` | string | Links to application |
| `status` | string | "active", "suspended", "revoked", "expired" |
| `suspension_type` | string or null | |
| `effective_date` | string | |

**SQL table name:** `contractor_license_history`

### GET /api/contractor/violations

Returns violation records. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `violation_id` | string | |
| `application_id` | string | Links to application |
| `violation_type` | string | "minor", "serious" |
| `status` | string | "open", "closed", "resolved" |
| `violation_date` | string | |

**SQL table name:** `contractor_violations`

### GET /api/contractor/correspondence

Returns correspondence logs. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `correspondence_id` | string | |
| `application_id` | string | Links to application |
| `status` | string | "verified", "unverified", "stale" |
| `date` | string | |

**SQL table name:** `contractor_correspondence`

### GET /api/contractor/inspections

Returns inspection records. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `inspection_id` | string | |
| `application_id` | string | Links to application |
| `result` | string | "pass", "safety_recheck", "document_gap" |
| `status` | string | "resolved", "unresolved" |
| `inspection_date` | string | |

**SQL table name:** `contractor_inspections`

## Liquor Endpoints

### GET /api/liquor/applications

Returns liquor license applications. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `application_id` | string | e.g. "L-APP-001" |
| `location_id` | string | e.g. "LOC-APP" |
| `applicant_name` | string | |
| `license_type` | string | "restricted", "hotel_lounge", etc. |
| `same_premises_history` | boolean | |
| `submitted_date` | string | |

**SQL table name:** `liquor_applications`

### GET /api/liquor/settlements

Returns settlement/board-order records. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `settlement_id` | string | |
| `application_id` | string | |
| `risk_code` | string | e.g. "AFTER_HOURS", "ASSAULT" |
| `status` | string | |

**SQL table name:** `liquor_settlements`

### GET /api/liquor/privileges

Returns license privilege records. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `privilege_id` | string | |
| `application_id` | string | |
| `privilege_type` | string | |
| `status` | string | |

**SQL table name:** `liquor_privileges`

### GET /api/liquor/incidents

Returns incident reports. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `incident_id` | string | |
| `application_id` | string | |
| `incident_type` | string | e.g. "AFTER_HOURS", "ASSAULT", "MINOR_SALE" |
| `status` | string | "open", "closed" |
| `incident_date` | string | |

**SQL table name:** `liquor_incidents`

### GET /api/liquor/site-evidence

Returns site evidence records. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `evidence_id` | string | |
| `application_id` | string | |
| `evidence_type` | string | "floor_plan", "site_photo", "control_signage", "police_memo", "tax_clearance", "camera_evidence", "food_service_evidence" |
| `status` | string | "current", "missing", "conflicting", "stale" |
| `evidence_date` | string | |

**SQL table name:** `liquor_site_evidence`

## Alcohol Renewal Endpoints

### GET /api/alcohol/licensees

Returns alcohol licensee records. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `license_no` | string | e.g. "AL-LIC-001" |
| `facility_name` | string | |
| `address` | string | |
| `license_type` | string | |
| `status` | string | |

**SQL table name:** `alcohol_licensees`

### GET /api/alcohol/violations

Returns alcohol violation records. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `violation_id` | string | e.g. "AV-AL-LIC-001-1" |
| `license_no` | string | Matches to licensee |
| `violation_type` | string | |
| `violation_date` | string | YYYY-MM-DD |
| `fine_status` | string | "paid", "unpaid" |
| `alert_flag` | string or null | |

**SQL table name:** `alcohol_violations`

**Matching to licensees:** A violation matches a licensee when `violation.license_no === licensee.license_no` (exact), or when the violation's license_no pattern resembles a target licensee but differs (close_address). Pay attention to the `license_no` field — violations with IDs like "AV-AL-OLD-006-S1" suggest a close-address match where the violation references an older or slightly different license number for the same facility.

**Post-boundary violations:** Violations with dates after the renewal boundary date must be excluded from the queue ranking. They are recorded in `summary.post_boundary_violation_ids_excluded`.

### GET /api/renewal/rules

Returns renewal rules. Key fields:

| Field | Type | Notes |
|-------|------|-------|
| `rule_id` | string | |
| `title` | string | |
| `release_boundary` | string | YYYY-MM-DD; the cutoff date |
| `details_json` | string | JSON string with rule parameters |

**SQL table name:** `renewal_rules`

**Rule selection:** Match the prompt's boundary date to `release_boundary`. Use the matching rule.

## SQL Endpoint

### POST /api/sql

**Header required:** `X-Task-Token: licensing-review-019`

**Request body:**

```json
{"query": "SELECT * FROM contractor_applications WHERE application_id IN ('C-APP-001', 'C-APP-002')"}
```

**Response:** An array of row objects.

**Table names:** The table name is typically the plural form of the endpoint resource. REST endpoint `/api/contractor/applications` → SQL table `contractor_applications`. REST endpoint `/api/alcohol/violations` → SQL table `alcohol_violations`. When in doubt, try the REST endpoint resource name pluralized with underscores.

**Writing queries:**

1. Always use explicit `WHERE ... IN (...)` clauses with the target IDs from the prompt.
2. Use single quotes for string literals.
3. Column names use underscores and match the REST response field names.
4. The endpoint returns all matching rows — order them with `ORDER BY` if needed, or sort client-side.

**Example query patterns:**

```sql
-- Filter to target applications
SELECT * FROM contractor_applications WHERE application_id IN ('C-APP-001', 'C-APP-002', ...)

-- Get bonds for target applications
SELECT * FROM contractor_bonds WHERE application_id IN ('C-APP-001', 'C-APP-002', ...)

-- Get insurance for target applications
SELECT * FROM contractor_insurance WHERE application_id IN ('C-APP-001', 'C-APP-002', ...)

-- Get violations matching target licensees (renewal)
SELECT * FROM alcohol_violations WHERE license_no IN ('AL-LIC-001', 'AL-LIC-002', ...)

-- Get correspondence by pattern
SELECT * FROM contractor_correspondence WHERE correspondence_id LIKE 'COR-C-APP-%'
```
