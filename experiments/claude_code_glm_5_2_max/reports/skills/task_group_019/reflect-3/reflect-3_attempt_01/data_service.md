# SQL Data-Service Reference

The task prompt advertises `GET /api/<family>/<resource>` REST endpoints. **The REST feeds
are incomplete**: they omit rows for the target IDs of the train/test set (notably the
financial-coverage rows for several contractor applications). Treat a REST absence for an
otherwise-active target as "the feed dropped it," not "no record exists."

`POST /api/sql` is the authoritative source. It serves the same logical tables with the
full row set.

## SQL constraints

- **Only `SELECT`** statements are accepted.
- `SELECT *`, `sqlite_master`, `information_schema.*`, and `PRAGMA …` are blocked.
- Reference columns by name. Bind target ids with `WHERE col IN ('…','…')`.
- Authorization for `/api/sql` is set by the request header required for SQL access (see
  the environment access notes provided with the run).

## Table → content map

| Table | Family | Key columns | Notes |
|---|---|---|---|
| `policies` | all | `policy_id, family, rule_code, effective_date, details_json` | thresholds/flags as JSON in `details_json` |
| `contractor_applications` | contractor | `application_id, trade, requested_class, years_experience, endorsement_status, prior_license_id, submitted_date` | one row per application |
| `contractor_bonds` | contractor | `bond_id, application_id, amount, status, effective_date, cancel_date, source_date` | multiple rows per app (-A active, -OLD historical) |
| `contractor_insurance` | contractor | `insurance_id, application_id, amount, status, expiration_date, verified_date` | multiple rows per app |
| `contractor_license_history` | contractor | `license_id, applicant_name, status, status_date, notes` | match by `prior_license_id`; `status` ∈ active/expired/suspended/revoked |
| `contractor_violations` | contractor | `violation_id, related_application_id, license_id, violation_date, severity, theme, status, resolved_date` | match by related_application_id or license_id; severity ∈ minor/medium/serious; status ∈ open/resolved/dismissed |
| `contractor_correspondence` | contractor | `correspondence_id, related_application_id, received_date, subject, assertion_type, assertion_value, verified_by_agency, notes` | `verified_by_agency` 0/1 |
| `contractor_inspections` | contractor | `inspection_id, related_application_id, inspection_date, result, finding_code, notes` | result ∈ pass/conditional/fail/no_access; finding_code ∈ NONE/DOC_GAP/SAFETY_RECHECK/UNVERIFIED_SITE/WRONG_TRADE |
| `liquor_applications` | liquor | `application_id, license_class, location_id, requested_posture, submitted_date` | |
| `liquor_settlements` | liquor | `settlement_id, location_id, effective_date, settlement_type, basis_code, controls_json, source_name` | `controls_json` has `{active, controls[], expires, review_required}` |
| `liquor_privileges` | liquor | `privilege_id, license_class, obligation_code, description, standard_required` | standard_required 1 → ordinary license obligation |
| `liquor_incidents` | liquor | `incident_id, location_id, incident_date, risk_code, severity, status, source_name` | status ∈ open/referred/closed/dismissed |
| `liquor_site_evidence` | liquor | `evidence_id, location_id, evidence_date, evidence_code, status, notes` | status ∈ verified/missing/conflicting/stale |
| `alcohol_licensees` | renewal | `license_no, facility_name, address, channel_type, active, location_id, successor_to` | `successor_to` links an old license number |
| `alcohol_violations` | renewal | `violation_id, license_no, facility_name, address, violation_date, theme, severity, disposition, fine_balance, alert_flag, source_name` | disposition ∈ open/pending/warning/settled/paid; `fine_balance>0` ⇒ unpaid; `alert_flag` 1 ⇒ manual review |
| `renewal_rules` | renewal | `rule_id, release_boundary, title, details_json` | pick the rule whose `release_boundary` matches the prompt's boundary date |

## Completeness cross-check

After fetching a target's rows, sanity-check coverage. A contractor application should
have ≥1 bond and ≥1 insurance row; a liquor location should have ≥1 active settlement;
every renewal target should have ≥1 pre-boundary violation. If a REST fetch returns zero
rows for an active target, re-fetch via SQL before treating the record as missing.
