# Court Operations Portal — Endpoint Reference

Base URL: `http://task-env:9018/`
Authentication: none required (open within network)

| Method | Path | Key query params | Returns |
|--------|------|------------------|---------|
| GET | /api/jurisdictions | (none) | List of courts with jurisdiction_code, county, state, policy_ref |
| GET | /api/cases | case_number | Case identity, counsel, status, disposition_date, jurisdiction_code |
| GET | /api/charges | case_number | Charge details: offense, statute, plea, disposition, fine, jail, probation, departure, assessment_code |
| GET | /api/docket-entries | case_number | Entry date, type, source, text for each docket entry |
| GET | /api/citations | citation_number | Traffic citation: defendant, speed, zone, violation_code, plea, plan status |
| GET | /api/fee-schedules | jurisdiction_code | Fee rows: amount, effective_date, end_date, fee_type, mandatory flag, violation_code. **Use plural path** |
| GET | /api/payment-policies | jurisdiction_code | Policy: min/max monthly, account_fee, first_due_days, return_to_court_offset_days, restitution_priority |
| GET | /api/forms | jurisdiction_code | Form metadata: form_id, label, required_fields, placeholder_instruction |
| GET | /api/financial-petitions | petition_id | Petition: balances, income/obligations, default status, license_suspension_months |
| GET | /api/search | q | Full-text search across portal records. Useful for finding policy references |

## Key gotchas

- `/api/fee-schedule` (singular) returns 404. Use `/api/fee-schedules` (plural).
- `/api/citation` (singular) returns 404. Use `/api/citations` (plural).
- Fee schedule rows with a non-null `end_date` are archived/stale. Only use rows where `end_date` is null and `effective_date` <= disposition date.
- The payment-policies endpoint returns all policies if no jurisdiction_code filter is given.
