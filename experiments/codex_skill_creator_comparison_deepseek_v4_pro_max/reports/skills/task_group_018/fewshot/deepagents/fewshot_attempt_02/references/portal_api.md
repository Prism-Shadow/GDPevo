# Court Operations Portal API Reference

## Base URL

The portal base URL is provided in the task prompt as a TASK_ENV_BASE_URL placeholder.
No credentials are required. All endpoints are read-only GET.

## Endpoints

### GET /api/jurisdictions
Returns court jurisdiction records with codes, names, and metadata.
Query: ?jurisdiction_code=<code> to filter by jurisdiction.

### GET /api/cases
Returns case records: case_number, defendant_name, dob, counsel_type, attorney_name,
case_status, disposition_date, charge counts.
Query: ?case_number=<case_number> to filter by case.

### GET /api/charges
Returns charge records per case: count_no, offense_code, statute, plea,
charge_disposition, fine_amount, jail_days_imposed, jail_days_suspended,
probation_months, departure_status.
Query: ?case_number=<case_number> to filter by case.

### GET /api/docket-entries
Returns docket entry records: entry_date, docket_entry_type, summary_code,
financial_total.
Query: ?case_number=<case_number> to filter by case.

### GET /api/citations
Returns traffic citation records: citation_number, jurisdiction_code,
defendant_name, violation_code, fine_tier, fee_schedule_source, standard_fine,
county_surcharge.
Query: ?citation_number=<citation_number> to filter by citation.

### GET /api/fee-schedules
Returns current fee schedule records: fee_code, amount, effective_date,
jurisdiction_code.
Query: ?jurisdiction_code=<code> to filter by jurisdiction.
Key fee_codes include: fine, court_cost, drug_assessment, public_defender_user_fee,
crime_lab_fee.

### GET /api/payment-policies
Returns payment policy records: policy_id, jurisdiction_code, minimum_monthly,
maximum_monthly, interval, supported_fees, account_fee_treatment.
Query: ?jurisdiction_code=<code> or ?policy_id=<id>.

### GET /api/forms
Returns form metadata: form_id, form_label, revision_date, required_field_groups.
Query: ?form_id=<id> or ?jurisdiction_code=<code>.

### GET /api/financial-petitions
Returns financial petition records: petition_id, case_number, petitioner_name,
submitted_date, requested_monthly_amount, requested_down_payment, balances,
budget details.
Query: ?petition_id=<id> or ?case_number=<case_number>.

### GET /api/search
General search endpoint. Accepts ?q=<query> for free-text search and
?type=<record_type> to scope to a record type (e.g., cases, citations, charges).

## Querying Pattern

For each case or citation in the reconciliation batch, query the portal for:
1. The case/citation record (identity, counsel, status)
2. Charges (plea, disposition, sentence components)
3. Docket entries (existing entries, financials)
4. Fee schedules (current amounts by jurisdiction)
5. Payment policies (installment bands, fee treatments)
6. Forms (required fields, labels, account references)
7. Financial petitions (if present in the task materials)

Combine portal records with local payloads:
- Local materials control courtroom-level events: what the judge said, what plea
  was entered, whether an order was signed, corrections the defense table made
  on the record.
- Portal controls current administrative data: the most recent fee schedule
  amounts, form revisions, policy bands, and CMS identity records.

When a portal record and local material conflict on an administrative value
(fee amount, policy parameter), prefer the portal. When they conflict on a
courtroom event (departure finding, counsel classification, plea), prefer the
local material.
