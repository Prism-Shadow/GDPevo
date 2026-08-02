# Data model & code-mapping reference

Supporting detail for `SKILL.md`. All schemas below were confirmed against a live
licensing environment, but **the authoritative enum vocabulary for any given task is
always the `allowed_values` inside that task's `answer_template.json`** — vocabularies
differ between task variants (e.g. `insurance_expired`/`insurance_not_current`,
`obtain_current_bond`/`file_active_bond`). Read the template first; use only its codes.

---

## 1. Environment / API

- Base URL and auth live in `environment_access.md` (the prompt shows it as
  `<TASK_ENV_BASE_URL>`). Read that file every task — do not hard-code a URL or token.
- **GET** endpoints return a full JSON array of records (no auth). Filter client-side.
- **POST `/api/sql`** requires header `X-Task-Token: <token from environment_access.md>`
  and JSON body `{"query": "<SELECT ...>"}` (key is `query`, not `sql`).
  - Table name = endpoint path with `/` → `_`:
    `contractor_applications`, `contractor_bonds`, `contractor_insurance`,
    `contractor_license_history`, `contractor_violations`, `contractor_correspondence`,
    `contractor_inspections`, `liquor_applications`, `liquor_settlements`,
    `liquor_privileges`, `liquor_incidents`, `liquor_site_evidence`,
    `alcohol_licensees`, `alcohol_violations`, `renewal_rules`, `policies`.
  - Result caps at **200 rows** (`"limit":200`, `"truncated":true/false`). Narrow with
    `WHERE ... LIKE 'C-TR1-%'` / `IN (...)`; aggregate with `GROUP BY` when counting.
  - Introspection / non-`SELECT` constructs are blocked (no `sqlite_master`, DDL, or
    stacked statements). Use it read-only for filtering and joins.

## 2. `policies` (family = contractor | liquor | renewal)

`details_json` is a JSON string — parse it. Key rows:

- **contractor** `POL-CON-001..006`, `rule_code` encodes trade + class
  (`CON-ELE-ClassA`=Electrical/Class A, `CON-PLU-ClassB`=Plumbing/Class B,
  `CON-HVA-ClassB`=HVAC/Class B, `CON-GEN-ClassA`=General Building/Class A,
  `CON-ROO-Limited`=Roofing/Limited, `CON-SOL-Specialty`=Solar/Specialty).
  Fields: `minimum_bond`, `minimum_insurance`, `minimum_years_experience`,
  `required_endorsement` (or null), `serious_open_violation_blocks`.
- **contractor legacy** `POL-CON-LEGACY` = prior baseline used for the `policy_impacted`
  comparison: `{endorsement_required_for_specialty:false, minimum_bond_reduction:10000,
  use_for_prior_rule_comparison:true}`.
- **liquor** `POL-LIQ-001` `{current_site_evidence_required, same_premises_history_matters,
  standard_privileges_separate_from_controls}`; `POL-LIQ-002`
  `{major_incidents_trigger_board_review}`.
- **renewal** `POL-REN-001` `{exact_license_match_preferred, known_on_or_before_boundary_only,
  successor_match_mark_uncertain}`.

## 3. Contractor family record shapes

- `contractor_applications`: `application_id, trade, requested_class, years_experience,
  endorsement_status` (`missing|pending|verified|not_required`), `prior_license_id`,
  `self_disclosed_issue`, `county`, `submitted_date`.
- `contractor_bonds` / `contractor_insurance`: **two rows per application** — a current
  `...-A` and a historical `...-OLD`. Bond: `amount, status`
  (`active|cancelled|expired`), `effective_date`, `cancel_date`. Insurance: `amount,
  status` (`active|pending|expired`), `expiration_date`, `verified_date`.
- `contractor_license_history`: keyed by `license_id` (= application's `prior_license_id`);
  `status` (`active|expired|suspended`), `notes` (suspension noted as
  "Active suspension pending board action").
- `contractor_violations`: `related_application_id`, `severity`
  (`minor|medium|serious`), `status` (`open|resolved`), `violation_date`, `theme`.
- `contractor_correspondence`: `related_application_id`, `correspondence_id`,
  `verified_by_agency` (0/1), `notes` (stale flagged as "Stale attachment predates
  application"), `assertion_type`, `assertion_value`.
- `contractor_inspections`: `related_application_id`, `finding_code`
  (`NONE|DOC_GAP|SAFETY_RECHECK|UNVERIFIED_SITE`), `result` (`pass|conditional|fail`).

### Deficiency → required-action pairing (map to the template's actual codes)

| condition | deficiency (example vocab) | required action (example vocab) |
|---|---|---|
| current bond amount < `minimum_bond` | `bond_shortfall` | `increase_bond_amount` / `increase_bond` |
| no active bond (all cancelled/expired) | `bond_cancelled` / `no_active_bond` | `obtain_current_bond` / `file_active_bond` |
| insurance expired / lapsed by review date | `insurance_expired` / `insurance_not_current` | `provide_current_insurance` / `renew_insurance` |
| insurance status `pending` | `insurance_pending` | `verify_insurance_binding` |
| insurance amount < `minimum_insurance` | `insurance_shortfall` | `increase_insurance_amount` / `increase_insurance` |
| `endorsement_status`=missing & endorsement required | `endorsement_missing` | `obtain_required_endorsement` |
| `endorsement_status`=pending | `endorsement_pending` | `verify_pending_endorsement` |
| endorsement unverified (variant vocab) | `endorsement_not_verified` | `verify_endorsement` |
| `years_experience` < `minimum_years_experience` | `experience_shortfall` | `submit_experience_evidence` / `document_experience` |
| license-history status `suspended` | `active_suspension` | `board_review_suspension` / `clear_suspension` |
| open serious violation | `open_serious_violation` / `unresolved_serious_complaint` | `resolve_serious_violation` / `resolve_complaint` / `board_review` |
| open minor/medium violation | `open_minor_violation` | `resolve_minor_violation_review` |
| inspection `DOC_GAP` | `inspection_doc_gap` | `clear_document_gap` |
| inspection `SAFETY_RECHECK` | `inspection_safety_recheck` | `complete_safety_recheck` |

`policy_impacted` = true when a deficiency/flag exists **only because of the current 2025
standard** and would not arise under `POL-CON-LEGACY` — the two canonical cases:
(a) a Specialty trade whose current standard requires an endorsement (legacy:
`endorsement_required_for_specialty=false`); (b) a bond that meets `minimum_bond − 10000`
but falls short of the current `minimum_bond`.

## 4. Liquor family record shapes

- `liquor_applications`: `application_id, license_class` (`Tavern|Restaurant|BeerWine|
  Package|...`), `location_id`, `requested_posture`, `address`, `dba`.
- `liquor_privileges`: per `license_class`, rows of `obligation_code`
  (`ID_CHECK|HOURS|SECURITY|FOOD_SERVICE|CCTV|PATIO|NOISE|DELIVERY`) with
  `standard_required` (1/0). **standard obligations = codes where `standard_required=1`.**
- `liquor_settlements`: per `location_id`; `basis_code`
  (`NOISE|SAME_PREMISES|PUBLIC_SAFETY|SALE_TO_MINOR|...`), `settlement_type`,
  `effective_date`, `controls_json` = `{active:bool, controls:[...], expires, review_required}`.
  **Only settlements with `controls_json.active=true` (and not expired) are current
  controls.** `location_specific_control_codes` = the `controls` arrays of the active
  settlements. `same_premises_basis_applies` = an active settlement has
  `basis_code=SAME_PREMISES`.
- `liquor_incidents`: per `location_id`; `risk_code`, `severity` (`low|medium|high`),
  `status` (`open|referred|closed|dismissed`). Open incidents → follow-up gap /
  escalation; high-severity/major → board review (`POL-LIQ-002`).
- `liquor_site_evidence`: per `location_id`; `evidence_code`
  (`CONTROL_SIGNAGE|FLOOR_PLAN|POLICE_MEMO|SITE_PHOTO|NEIGHBOR_NOTICE|TAX_CLEARANCE`),
  `status` (`verified|missing|stale|conflicting`), `notes` (current vs. legacy hints:
  "Current packet"/"Current evidence" vs "Old location name"/"Field import").

### Evidence/incident → verification-gap mapping (map to the template's actual codes)

`CONTROL_SIGNAGE`+conflicting → `CONTROL_SIGNAGE_CONFLICTING` / `control_signage_missing`;
`CONTROL_SIGNAGE`(current)+missing → `CONTROL_SIGNAGE_CURRENT_MISSING`;
`FLOOR_PLAN`+conflicting → `FLOOR_PLAN_CONFLICTING`/`floor_plan_conflicting`;
`FLOOR_PLAN`+stale → `FLOOR_PLAN_STALE`; `POLICE_MEMO`+conflicting →
`POLICE_MEMO_CONFLICTING`/`police_memo_identity_note`; `SITE_PHOTO`+missing →
`SITE_PHOTO_MISSING`; `NEIGHBOR_NOTICE`+missing → `NEIGHBOR_NOTICE_MISSING`;
`TAX_CLEARANCE`+missing / open TAX_HOLD incident → `TAX_CLEARANCE_MISSING`/`tax_hold_unresolved`;
open incident → `OPEN_INCIDENT_FOLLOW_UP`; camera/food-service evidence absent →
`camera_evidence_missing`/`food_service_evidence_missing`; late-night context →
`late_night_monitoring_needed`. `first_90_day_plan` check_codes and
`escalation_trigger_codes` come directly from the template's enum and pair with the gaps,
active controls, and covered risks identified.

## 5. Renewal family record shapes

- `renewal_rules`: `release_boundary` / `details_json.use_violations_on_or_before`
  (the boundary date), plus `alert_flag_requires_manual_review`,
  `late_rows_are_distractors`, `unpaid_fines_require_hold`. Pick the rule whose boundary
  matches the prompt's release boundary.
- `alcohol_licensees`: `license_no, facility_name, address, active` (1/0),
  `successor_to` (predecessor license_no or null), `location_id`.
- `alcohol_violations`: `license_no, violation_id, violation_date, severity, disposition,
  fine_balance, alert_flag, source_name, theme`. Post-boundary rows carry
  `source_name='post_boundary_feed'` and `-LATE` ids.

### Matching & labelling

- Count only violations with `violation_date <= boundary`. Post-boundary rows are
  distractors → `post_boundary_violation_ids_excluded`.
- `match_confidence`: `exact` when matched by `license_no` directly; `uncertain` when the
  licensee has `successor_to` set (history spans the predecessor permit); `close_address`
  when matched by shared/near address rather than exact license.
- `next_step_label`: `manual_fine_check` (unpaid `fine_balance>0`), `manual_ALERT_check`
  (`alert_flag=1`), `board_review` (serious/major or unpaid-fine hold),
  `additional_record_check` (close/uncertain match needing more records).
- Inactive predecessor permits (`active=0`, e.g. `...-OLD-...`) are **not** target queue
  rows; they only inform a successor's `uncertain` history.
