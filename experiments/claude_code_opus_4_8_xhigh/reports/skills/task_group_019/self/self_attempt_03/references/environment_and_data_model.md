# Environment & data model reference

Companion to `SKILL.md`. Describes how to reach the shared licensing data service
and the shape of every record family. Field lists reflect the environment as
observed; **always trust live data and the task's own `answer_template.json` over
this document** — schemas may drift and enum vocabularies differ per task.

## Reaching the environment

- The run ships an `environment_access.md`. It contains:
  - `GDPEVO_ENV_BASE_URL=<base>` — substitute this for every `<TASK_ENV_BASE_URL>`
    placeholder in the prompt.
  - The credential for SQL: `POST /api/sql requires header X-Task-Token: <token>`.
  - The list of allowed endpoints. **Call only endpoints the prompt/env file allow.**
- Never hardcode a base URL or token — read them from `environment_access.md` each run.
  `scripts/licensing_env.py` parses both for you.

## Two ways to read data

1. **GET `<endpoint>`** → returns a JSON **array** of all rows for that resource.
2. **POST `/api/sql`** → body `{"query": "SELECT ..."}`, header `X-Task-Token: <token>`,
   `Content-Type: application/json`. Response:
   `{"columns":[...], "rows":[...], "row_count":N, "limit":200, "truncated":bool}`.
   Read-only: only `SELECT` is allowed; `DELETE`/`UPDATE`/etc. are rejected, and
   some constructs (e.g. `sqlite_master`) are blocked. Table names are the endpoint
   paths with slashes→underscores and no `/api/` prefix, e.g.
   `/api/contractor/bonds` → table `contractor_bonds`,
   `/api/liquor/site-evidence` → `liquor_site_evidence`,
   `/api/alcohol/violations` → `alcohol_violations`.

### ⚠️ GET truncates at ~200 rows
GET responses are capped at 200 rows even when the table has more (observed:
`contractor_bonds`=222, `contractor_insurance`=222, `alcohol_violations`=273 all
return only 200 via GET). **A target's records can be silently missing from a raw
GET dump.** For the large tables (`contractor_bonds`, `contractor_insurance`,
`contractor_violations`, `contractor_correspondence`, `alcohol_violations`,
`liquor_incidents`, `liquor_settlements`) prefer `POST /api/sql` with a `WHERE`
clause narrowed to the target ids/locations so you get every relevant row. Keep
per-target filtered queries small (well under the 200-row SQL limit) and check the
`truncated` flag.

## Distractor rows
Every table mixes target rows with **distractors** you must ignore. Non-target id
prefixes seen include `-DIS-` (distractor), `-TE2-`/`-TEn-` (other test batches),
and other `-TRk-` batches. Filter strictly to the exact target ids/location the
prompt names; never let a near-miss row leak into the answer.

---

## Contractor family (applications & supporting files)

Join key is usually `application_id`; license history joins via `prior_license_id`
/ `license_id` and/or `applicant_name` (history notes say "matched by applicant name").

- **`contractor_applications`**: `application_id`, `applicant_name`, `trade`,
  `county`, `submitted_date`, `years_experience`, `endorsement_status`
  (`missing|pending|verified|...`), `prior_license_id`, `requested_class`,
  `self_disclosed_issue`.
- **`contractor_bonds`**: `bond_id`, `application_id`, `amount`, `status`
  (`active|cancelled|expired`), `effective_date`, `cancel_date`, `source_date`,
  `surety`. A target can have several bonds (old + current); evaluate the current one.
- **`contractor_insurance`**: `insurance_id`, `application_id`, `amount`, `status`
  (`active|expired|pending`), `expiration_date`, `verified_date`, `insurer`.
- **`contractor_license_history`**: `license_id`, `applicant_name`, `trade`,
  `status` (`active|expired|suspended|revoked`), `status_date`, `notes`.
  `suspended`/`revoked` are the hard-blocker signals.
- **`contractor_violations`**: `violation_id`, `license_id`, `related_application_id`,
  `severity` (`minor|medium|serious`), `status` (`open|resolved|dismissed`),
  `theme`, `violation_date`, `resolved_date`. Only `open` violations are live;
  `serious`+`open` is a policy hard block (see `serious_open_violation_blocks`).
- **`contractor_correspondence`**: `correspondence_id`, `related_application_id`,
  `assertion_type`, `assertion_value`, `subject`, `received_date`, `notes`,
  `verified_by_agency` (1=verified, 0=applicant copy only / unverified). Unverified
  or stale correspondence feeds `stale_or_unverified_correspondence_ids` and means
  you cannot treat the applicant's claim as satisfying a requirement.
- **`contractor_inspections`**: `inspection_id`, `related_application_id`,
  `result` (`pass|conditional|fail|no access`), `finding_code`
  (`NONE|DOC_GAP|SAFETY_RECHECK|UNVERIFIED_SITE|WRONG_TRADE`), `inspection_date`,
  `notes`. `DOC_GAP`→document gap; `SAFETY_RECHECK`→safety recheck required.

## Liquor family (restricted-premises staff package)

Join key is `location_id` (from the application) for settlements/incidents/
site-evidence, and `license_class` for privileges.

- **`liquor_applications`**: `application_id`, `applicant_name`, `dba`, `address`,
  `license_class` (`Tavern|Restaurant|BeerWine|Package`), `location_id`,
  `requested_posture` (`new|transfer|...`), `submitted_date`, `agency`.
- **`liquor_settlements`**: `settlement_id`, `location_id`, `basis_code`
  (`SAME_PREMISES|NOISE|PUBLIC_SAFETY|SALE_TO_MINOR|...`), `settlement_type`
  (`warning|restricted|conditional approval|historic refusal`), `effective_date`,
  `source_name`, `controls_json`. `controls_json` = `{"active":bool,
  "controls":[...], "expires":"YYYY-MM-DD", "review_required":bool}`. **Only
  settlements with `active:true` (and not expired) supply current
  location-specific controls.** `basis_code=SAME_PREMISES` supports the
  same-premises basis.
- **`liquor_privileges`**: `privilege_id`, `license_class`, `obligation_code`
  (`ID_CHECK|HOURS|SECURITY|FOOD_SERVICE|CCTV|PATIO|NOISE|DELIVERY`),
  `standard_required` (1/0), `description`. The **ordinary/standard obligations**
  for a class are those rows with `standard_required=1` for that `license_class`.
  (Observed: `ID_CHECK`, `HOURS`, and — for classes that serve food — `FOOD_SERVICE`
  are `standard_required=1`; the rest are 0.) These are *separate from* the
  location-specific controls (policy `standard_privileges_separate_from_controls`).
- **`liquor_incidents`**: `incident_id`, `location_id`, `risk_code`
  (`NOISE|AFTER_HOURS|ASSAULT|MINOR_SALE|TAX_HOLD|FOOD_SERVICE_GAP`), `severity`
  (`low|medium|high`), `status` (`open|referred|closed|dismissed`), `incident_date`,
  `source_name`. `open`/`referred` are live; `closed`/`dismissed` are not. `high`
  severity (esp. open/referred) triggers board review / escalation
  (`major_incidents_trigger_board_review`).
- **`liquor_site_evidence`**: `evidence_id`, `location_id`, `evidence_code`
  (`POLICE_MEMO|CONTROL_SIGNAGE|FLOOR_PLAN|SITE_PHOTO|NEIGHBOR_NOTICE|TAX_CLEARANCE`),
  `status` (`verified|missing|stale|conflicting`), `evidence_date`, `notes`.
  Anything not `verified` (missing/stale/conflicting) is a **verification gap**.

## Alcohol renewal family (manual-review queue)

- **`alcohol_licensees`**: `license_no`, `facility_name`, `address`, `location_id`,
  `channel_type`, `agency`, `active` (1/0), `successor_to` (prior license_no or null).
- **`alcohol_violations`**: `violation_id`, `license_no`, `facility_name`,
  `address`, `severity`, `disposition` (`open|...`), `fine_balance` (number),
  `alert_flag` (1/0), `theme`, `violation_date`, `source_name`.
- **`renewal_rules`**: `rule_id`, `title`, `release_boundary` (`YYYY-MM-DD`),
  `effective_date`, `details_json`. `details_json` keys observed:
  `use_violations_on_or_before` (= the boundary; violations **after** it are
  distractors to exclude), `alert_flag_requires_manual_review`,
  `unpaid_fines_require_hold`, `late_rows_are_distractors`. Pick the rule whose
  `release_boundary` matches the boundary the prompt states.

## Policy baseline (`/api/policies`)

Returns rows across families; each has `policy_id`, `family`
(`contractor|liquor|renewal`), `rule_code`, `title`, `citation`, `agency`,
`effective_date`, and a stringified `details_json`. **Always parse `details_json`
and read thresholds live** rather than hardcoding numbers. Key rows:

- Contractor class standards (`family:"contractor"`, one per class/trade, e.g.
  `CON-ELE-ClassA`, `CON-PLU-ClassB`, `CON-HVA-ClassB`, `CON-GEN-ClassA`,
  `CON-ROO-Limited`, `CON-SOL-Specialty`). `details_json`:
  `minimum_bond`, `minimum_insurance`, `minimum_years_experience`,
  `required_endorsement` (or null), `serious_open_violation_blocks`. Match an
  application to its policy by `requested_class`/`trade`.
- **`CON-LEGACY`** (`POL-CON-LEGACY`, "Prior contractor review baseline"):
  `endorsement_required_for_specialty:false`, `minimum_bond_reduction:10000`,
  `use_for_prior_rule_comparison:true`. This is the **prior baseline** used to
  decide `policy_impacted` — see the playbook.
- Liquor: `LIQ-SETTLEMENT-CONTROLS` (`current_site_evidence_required`,
  `same_premises_history_matters`, `standard_privileges_separate_from_controls`),
  `LIQ-RISK-MATRIX` (`major_incidents_trigger_board_review`).
- Renewal: `REN-BOUNDARY` (`exact_license_match_preferred`,
  `known_on_or_before_boundary_only`, `successor_match_mark_uncertain`).
