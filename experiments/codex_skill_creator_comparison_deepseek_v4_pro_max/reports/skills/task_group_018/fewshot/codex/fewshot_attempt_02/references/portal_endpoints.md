# Court Operations Portal — Endpoint Field Reference

Field-by-field descriptions of every endpoint in the Court Operations Portal.

## GET /api/jurisdictions

Returns a list of court jurisdictions with metadata.

| Field | Type | Description |
|---|---|---|
| `jurisdiction_code` | string | Unique jurisdiction identifier, e.g. `AR-RC`, `OR22-JEFF`, `VA-GLO` |
| `court_name` | string | Full court name |
| `county` | string | County name |
| `state` | string | Two-letter state code |
| `court_level` | string | Court level, e.g. `Circuit` |
| `clerk_office` | string | Office designation, e.g. `Criminal`, `Criminal/Finance`, `Traffic Violations` |
| `active` | boolean | Whether this jurisdiction is currently active |
| `phone` | string | Court phone number |
| `timezone` | string | IANA timezone |
| `policy_ref` | string | Reference to fee/policy bundle for this jurisdiction |

---

## GET /api/cases

Returns case records. Paginated — the response object has `count` and `results`.

| Field | Type | Description |
|---|---|---|
| `case_number` | string | Case identifier, e.g. `RC-25-0412` |
| `case_type` | string | Always `criminal` in this system |
| `jurisdiction_code` | string | Links to a jurisdiction in `/api/jurisdictions` |
| `defendant_first` | string | Defendant first name |
| `defendant_last` | string | Defendant last name |
| `defendant_dob` | string or null | Defendant date of birth, `YYYY-MM-DD` |
| `counsel_type` | string | `public_defender`, `appointed_private`, `retained`, `unknown` |
| `attorney_label_raw` | string | Raw intake label — can be misleading (e.g. `"APD"` may mean appointed private) |
| `attorney_name` | string or null | Attorney name |
| `status` | string | `disposed`, `deferred`, `pending`, `closed`, `continued` |
| `disposition_date` | string or null | Date of final disposition, `YYYY-MM-DD` |
| `filed_date` | string | Date case was filed, `YYYY-MM-DD` |
| `judge` | string | Presiding judge name |
| `prosecutor` | string | Prosecutor name |
| `external_party_id` | string | External party identifier |
| `source_system` | string | `AOC-CMS`, `VACMS`, `Legacy-CMS`, `Intake queue` — use CMS records as authoritative |
| `source_updated_at` | string | Last update timestamp |

---

## GET /api/charges

Returns charge records linked to cases by `case_number`.

| Field | Type | Description |
|---|---|---|
| `charge_id` | string | Unique charge identifier |
| `case_number` | string | Parent case number |
| `count_no` | integer | Count number within the case |
| `offense_code` | string | Code for the offense (e.g. `THEFT-CLASS-D`, `POSS-CS`, `DWI-1`) |
| `description` | string | Offense description |
| `statute` | string | Statute citation |
| `severity` | string | Severity classification |
| `offense_date` | string | Date of offense |
| `plea` | string | `guilty`, `no contest`, `not guilty` |
| `disposition` | string | `dismissed`, `deferred`, charge disposition |
| `verdict` | string or null | Verdict if applicable |
| `fine_amount` | number | Fine imposed in dollars |
| `jail_days_imposed` | integer | Jail days imposed |
| `jail_days_suspended` | integer | Jail days suspended |
| `probation_months` | integer | Probation term in months |
| `license_suspension_months` | integer | License suspension months |
| `departure_type` | string | `durational`, `dispositional`, or empty |
| `departure_reason` | string | Reason text |
| `presumptive_min_months` | integer | Minimum presumptive sentence |
| `presumptive_max_months` | integer | Maximum presumptive sentence |
| `assessment_code` | string or null | Assessment code if applicable |

---

## GET /api/docket-entries

Returns docket entry records linked to cases.

| Field | Type | Description |
|---|---|---|
| `entry_id` | string | Unique entry identifier |
| `case_number` | string | Parent case number |
| `entry_date` | string | Date of entry, `YYYY-MM-DD` |
| `entry_type` | string | `filing`, `hearing`, `disposition`, `financial`, `clerk_note` |
| `entered_by` | string | `clerk-a`, `clerk-b`, `supervisor`, `import-job` |
| `source` | string | `courtroom notes`, `financial module`, `case-management system` |
| `text` | string | Entry text |

---

## GET /api/citations

Returns traffic citation records.

| Field | Type | Description |
|---|---|---|
| `citation_number` | string | Citation identifier, e.g. `OR26-TR-1188` |
| `jurisdiction_code` | string | Links to jurisdiction |
| `defendant_name` | string | Defendant full name |
| `defendant_dob` | string | Defendant date of birth |
| `event_date` | string | Date of the traffic stop |
| `hearing_date` | string | Hearing date |
| `officer` | string | Issuing officer |
| `statute` | string | Statute code |
| `violation_code` | string | `ORS_811_109_100PLUS`, `ORS_811_109_31_40`, `ORS_811_109_21_30` |
| `violation_desc` | string | Description |
| `speed_mph` | integer | Measured speed |
| `zone_mph` | integer | Speed zone |
| `plea` | string | `guilty`, `no contest`, `not guilty` |
| `disposition` | string | `violation found`, `dismissed` |
| `status` | string | `disposed`, `pending` |
| `monthly_payment` | number or null | Approved monthly payment |
| `plan_approved` | boolean | Whether a payment plan was approved |
| `first_due_date` | string or null | First payment due date |

---

## GET /api/fee-schedules

Returns fee schedule entries. Filter by `jurisdiction_code` and `effective_date`.

| Field | Type | Description |
|---|---|---|
| `fee_id` | string | Unique fee identifier |
| `fee_type` | string | `court_cost`, `assessment`, `user_fee` |
| `jurisdiction_code` | string | Jurisdiction this fee applies to |
| `label` | string | Human-readable fee label |
| `amount` | number | Fee amount in dollars |
| `effective_date` | string | Date fee became effective |
| `end_date` | string or null | Date fee expired; null means still current |
| `mandatory` | boolean | Whether the fee is mandatory |
| `priority` | integer | Priority for application order |
| `statute` | string or null | Authorizing statute |
| `violation_code` | string or null | Specific violation this fee applies to |
| `notes` | string | Applicability notes |

**Fee types:**

- `court_cost`: Mandatory filing/processing fee for criminal cases. Every disposed criminal case gets this.
- `assessment`: Special-purpose fee like drug crime assessment or crime lab fee. Mandatory when the conviction charge triggers it.
- `user_fee`: Discretionary fee like Public Defender User Fee. Apply only when conditions are met (counsel is public defender, case is disposed).

---

## GET /api/payment-policies

Returns payment/installment plan policy rules.

| Field | Type | Description |
|---|---|---|
| `policy_id` | string | Unique policy identifier |
| `policy_name` | string | Policy name |
| `jurisdiction_code` | string | Jurisdiction this policy applies to |
| `min_monthly` | number | Minimum allowed monthly payment |
| `max_monthly` | number | Maximum allowed monthly payment |
| `first_due_days` | integer | Days from disposition to first payment due date |
| `down_payment_required` | number | Required down payment (usually 0) |
| `account_fee` | number | Account maintenance fee; 0 means excluded |
| `restitution_priority` | string | Priority order for applying payments |
| `return_to_court_offset_days` | integer | Days after final payment for return-to-court date |
| `subsequent_petition_rule` | string | Rule for subsequent petitions |
| `notes` | string | Additional policy notes |

---

## GET /api/forms

Returns court form metadata.

| Field | Type | Description |
|---|---|---|
| `form_id` | string | Unique form identifier |
| `form_name` | string | Full form name |
| `label` | string | Short label |
| `jurisdiction_code` | string | Jurisdiction this form belongs to |
| `revision_date` | string | Form revision date |
| `required_fields` | array of strings | Fields required on the form |
| `placeholder_instruction` | string | Instructions for handling missing fields |
| `source_url` | string | Internal form reference |

---

## GET /api/financial-petitions

Returns payment petition records.

| Field | Type | Description |
|---|---|---|
| `petition_id` | string | Unique petition identifier |
| `case_number` | string | Parent case number |
| `jurisdiction_code` | string | Jurisdiction |
| `petitioner_name` | string | Petitioner name |
| `petition_sequence` | string | `first`, `second` |
| `submitted_date` | string | Date petition was submitted |
| `requested_monthly` | number | Requested monthly payment |
| `income_monthly` | number | Monthly income |
| `obligations_monthly` | number | Total monthly obligations |
| `household_size` | integer | Household size |
| `employment_status` | string | Employment status |
| `public_assistance` | boolean | Whether receiving public assistance |
| `fines_costs_balance` | number | Fines and costs balance |
| `restitution_balance` | number | Restitution balance |
| `license_suspension_months` | integer | License suspension months from case |
| `probation_report_datetime` | string or null | Probation report date-time |
| `default_status` | string | `current`, `default review` |

---

## GET /api/search

Multi-entity search. Returns results spanning cases, charges, docket entries, and citations.

| Field | Type | Description |
|---|---|---|
| `result_type` | string | `cases`, `docket_entries`, `charges`, `citations` |
| `result_id` | string | Entity-specific identifier |
| Other fields | varies | Depends on `result_type` — mirrors the individual endpoint fields |
