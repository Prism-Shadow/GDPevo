# Court Operations Portal API Endpoints

The portal is at a base URL given as <TASK_ENV_BASE> or similar. All endpoints
are GET and return JSON. The response format is `{"count": N, "results": [...]}`.

## Endpoints

### GET /api/jurisdictions
Returns all active jurisdictions. Use to confirm the jurisdiction_code for
the target court. Fields: jurisdiction_code, court_name, county, state,
clerk_office, policy_ref, active, timezone.

### GET /api/cases
Query by case_number. Returns case-level records: defendant_first,
defendant_last, defendant_dob, counsel_type, attorney_name, status,
disposition_date, jurisdiction_code, case_type, judge, prosecutor.

### GET /api/charges
Query by case_number. Returns charge records: charge_id, count_no, offense_code,
statute, description, severity, plea, disposition, verdict, fine_amount,
jail_days_imposed, jail_days_suspended, probation_months,
license_suspension_months, departure_type, departure_reason.

### GET /api/docket-entries
Query by case_number. Returns docket entries: entry_id, entry_type, entry_date,
text, entered_by, source.

### GET /api/citations
Query by citation_number. Returns citation records for traffic cases.

### GET /api/fee-schedules
Returns all fee schedule entries across jurisdictions. Each entry has: fee_id,
fee_type, jurisdiction_code, label, amount, effective_date, end_date,
mandatory (boolean), priority, statute, violation_code.

**Critical**: Check effective_date and end_date. A record with end_date in the
past is archival. Use only records where end_date is null (current) or
end_date is on/after the disposition date.

When filtering for a specific jurisdiction, match by jurisdiction_code.

### GET /api/payment-policies
Query by jurisdiction_code. Returns payment policy records: policy_id,
policy_name, min_monthly, max_monthly, down_payment_required, first_due_days,
account_fee, restitution_priority, return_to_court_offset_days.

### GET /api/forms
Query by form_family or jurisdiction_code. Returns form metadata: form_id,
form_name, jurisdiction_code, label, required_fields, placeholder_instruction,
revision_date.

### GET /api/financial-petitions
Query by petition_id or case_number. Returns petition records with financial
counter data.

### GET /api/search
Query with a case number, citation number, or defendant name. Returns
multi-type results with result_type indicating whether each result is a
case, charge, docket_entry, citation, or petition.

## Query Patterns

**Quick lookup**: `/api/search?q=<case_number>`
**Full case detail**: `/api/cases?case_number=<case_number>`
**Charges on a case**: `/api/charges?case_number=<case_number>`
**Docket history**: `/api/docket-entries?case_number=<case_number>`
**Jurisdiction policies**: `/api/payment-policies?jurisdiction_code=<code>`
**Form metadata**: `/api/forms?form_family=<family>` or
`/api/forms?jurisdiction_code=<code>`
**Fee schedule for jurisdiction**: `/api/fee-schedules` then filter by
jurisdiction_code and effective date.
**Petition lookup**: `/api/financial-petitions?petition_id=<id>` or
`/api/financial-petitions?case_number=<case_number>`

## Response Patterns

All list endpoints return `{"count": N, "results": [...]}`. Single-record
endpoints may collapse to one result. An empty response or count:0 means no
records matched the query.

When using /api/search, each result has a result_type field:
- "cases" — case record
- "docket_entries" — docket entry
- "charges" — charge record
- "citations" — citation record

For /api/search results, use the type-specific endpoints to get full detail
when needed.
