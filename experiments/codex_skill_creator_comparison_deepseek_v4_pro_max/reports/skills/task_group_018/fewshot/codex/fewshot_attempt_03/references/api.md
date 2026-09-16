# Court Operations Portal API Reference

Base URL: `<TASK_ENV_BASE_URL>`. No credentials required. Query parameters are passed as URL query strings (e.g., `?case_number=XX-00-0000` or `?jurisdiction_code=AR-RC`).

## Table of Contents
1. GET /api/jurisdictions
2. GET /api/cases
3. GET /api/charges
4. GET /api/docket-entries
5. GET /api/citations
6. GET /api/fee-schedules
7. GET /api/payment-policies
8. GET /api/forms
9. GET /api/financial-petitions
10. GET /api/search

---

## 1. GET /api/jurisdictions

Returns court jurisdiction records. Filter with `?jurisdiction_code=` or `?state=`.

### Response fields

| Field | Type | Description |
|---|---|---|
| jurisdiction_code | string | Unique code (e.g., AR-RC, OR22-JEFF, VA-GLO) |
| court_name | string | Full court name |
| court_level | string | e.g., Circuit |
| state | string | Two-letter state code |
| county | string | County name |
| clerk_office | string | Office division |
| phone | string | Court phone |
| active | boolean | Whether active |
| policy_ref | string | Reference to sentencing/payment policy |
| timezone | string | IANA timezone |

---

## 2. GET /api/cases

Returns criminal and traffic case records. Filter with `?case_number=`, `?jurisdiction_code=`, or both.

### Response fields

| Field | Type | Description |
|---|---|---|
| case_number | string | Unique case identifier |
| case_type | string | e.g., criminal |
| jurisdiction_code | string | Court jurisdiction |
| defendant_first | string | First name |
| defendant_last | string | Last name |
| defendant_dob | string | Date of birth (YYYY-MM-DD) |
| counsel_type | string | retained, public_defender, appointed_private |
| attorney_name | string or null | Counsel name |
| attorney_label_raw | string | Raw label from source system |
| status | string | disposed, deferred, pending, continued |
| disposition_date | string or null | ISO date |
| filed_date | string | Filing date |
| judge | string | Judge name |
| prosecutor | string | Prosecutor name |
| external_party_id | string | Cross-reference ID |
| source_system | string | System of record |
| source_updated_at | string | ISO datetime |

---

## 3. GET /api/charges

Returns charge records. Filter with `?case_number=`.

### Response fields

| Field | Type | Description |
|---|---|---|
| charge_id | string | Unique charge identifier |
| case_number | string | Parent case |
| count_no | integer | Charge count number |
| offense_code | string | Abbreviated code (e.g., FLEEING, POSS-CS, DWI-1, THEFT-CLASS-D) |
| description | string | Text description |
| statute | string | Statute reference |
| severity | string | e.g., Class D felony, Class 1 misdemeanor |
| plea | string | guilty, no contest, not guilty, not entered |
| disposition | string | guilty, dismissed, deferred, pending, nolle_prosequi |
| verdict | string or null | Verdict text |
| fine_amount | number | Fine in dollars |
| jail_days_imposed | integer | Days imposed |
| jail_days_suspended | integer | Days suspended |
| probation_months | integer | Months probation |
| license_suspension_months | integer | Months license suspension |
| departure_type | string | dispositional, durational, or empty |
| departure_reason | string | Reason text |
| assessment_code | string or null | Assessment linkage |
| presumptive_min_months | integer | Minimum presumptive range |
| presumptive_max_months | integer | Maximum presumptive range |
| offense_date | string | Date of offense |

---

## 4. GET /api/docket-entries

Returns docket entries. Filter with `?case_number=`.

### Response fields

| Field | Type | Description |
|---|---|---|
| entry_id | string | Unique entry identifier |
| case_number | string | Parent case |
| entry_date | string | ISO date |
| entry_type | string | filing, hearing, disposition, financial, clerk_note |
| source | string | Source system |
| text | string | Entry text (may be redacted) |
| entered_by | string | Clerk or import-job |

---

## 5. GET /api/citations

Returns traffic citation records. Filter with `?citation_number=`, `?jurisdiction_code=`, or both.

### Response fields

| Field | Type | Description |
|---|---|---|
| citation_number | string | Unique citation identifier |
| jurisdiction_code | string | Court jurisdiction |
| defendant_name | string | Full name |
| defendant_dob | string | Date of birth |
| statute | string | Statute (e.g., ORS 811.109) |
| violation_code | string | Enum code (e.g., ORS_811_109_100PLUS) |
| violation_desc | string | Description |
| speed_mph | integer | Recorded speed |
| zone_mph | integer | Speed limit |
| event_date | string | Date of violation |
| hearing_date | string | Hearing date |
| officer | string | Officer name |
| status | string | disposed, pending |
| plea | string | guilty, no contest, not guilty |
| disposition | string | violation found, dismissed |
| plan_approved | boolean | Payment plan approved |
| monthly_payment | number or null | Monthly payment amount |
| first_due_date | string or null | First payment due date |

---

## 6. GET /api/fee-schedules

Returns fee schedule entries. Filter with `?jurisdiction_code=`.

### Response fields

| Field | Type | Description |
|---|---|---|
| fee_id | string | Unique fee identifier |
| jurisdiction_code | string | Court jurisdiction |
| fee_type | string | court_cost, fine, assessment, user_fee, county_surcharge, standard_fine |
| label | string | Human-readable label |
| amount | number | Fee amount in dollars |
| mandatory | boolean | Whether mandatory |
| effective_date | string | Start of effectivity |
| end_date | string or null | End of effectivity (null = current) |
| priority | integer | Sorting/application priority |
| statute | string or null | Governing statute |
| violation_code | string or null | Linked violation code |
| notes | string | Usage notes |

**Key rule:** Use fees where `effective_date <= disposition_date` and `end_date` is null or >= `disposition_date`. A fee with a non-null `end_date` before the disposition date is stale.

---

## 7. GET /api/payment-policies

Returns payment/installment policy records. Filter with `?jurisdiction_code=`.

### Response fields

| Field | Type | Description |
|---|---|---|
| policy_id | string | Unique policy identifier |
| policy_name | string | Human-readable name |
| jurisdiction_code | string | Court jurisdiction |
| min_monthly | number | Minimum monthly installment |
| max_monthly | number | Maximum monthly installment |
| down_payment_required | number | Required down payment (0 = none) |
| first_due_days | integer | Days from petition/order to first due date |
| account_fee | number | Account management fee (0 = not charged) |
| restitution_priority | string | Payment application order description |
| return_to_court_offset_days | integer | Days after final payment for return-to-court |
| subsequent_petition_rule | string | Rules for subsequent petitions |
| notes | string | Usage notes |

---

## 8. GET /api/forms

Returns court form metadata. Filter with `?jurisdiction_code=`.

### Response fields

| Field | Type | Description |
|---|---|---|
| form_id | string | Unique form identifier |
| form_name | string | Administrative form name |
| label | string | Human-readable label |
| jurisdiction_code | string | Court jurisdiction |
| required_fields | array of strings | Required field names |
| placeholder_instruction | string | Instruction for unavailable fields |
| revision_date | string | Form revision date |
| source_url | string | Internal URL |

---

## 9. GET /api/financial-petitions

Returns financial petition records. Filter with `?petition_id=` or `?case_number=`.

### Response fields

| Field | Type | Description |
|---|---|---|
| petition_id | string | Unique petition identifier |
| case_number | string | Parent case |
| jurisdiction_code | string | Court jurisdiction |
| petitioner_name | string | Petitioner name |
| petition_sequence | string | first, second |
| submitted_date | string | Date submitted |
| default_status | string | current, default review |
| employment_status | string | employed, part-time, seasonal |
| income_monthly | number | Monthly income |
| obligations_monthly | number | Monthly obligations |
| household_size | integer | Household members |
| public_assistance | boolean | Receiving assistance |
| fines_costs_balance | number | Fines and costs balance |
| restitution_balance | number | Restitution owed |
| license_suspension_months | integer | License suspension |
| requested_monthly | number | Requested monthly payment |
| probation_report_datetime | string or null | Probation report datetime |

---

## 10. GET /api/search

Cross-entity search. Filter with `?q=` (search string). Returns mixed results with a `result_type` field indicating entity type (cases, docket_entries, charges, citations). Result fields vary by type.

Useful when a single query should return everything known about a case number.
