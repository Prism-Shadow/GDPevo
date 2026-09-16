# API Endpoints

The Cedar Ridge Intake Coordination Portal exposes these endpoints. The base URL is provided in the task prompt as a placeholder like <TASK_ENV_BASE_URL>.

## Endpoint Reference

| Endpoint | Method | Description |
|----------|--------|-------------|
| / | GET | Root, returns available endpoints |
| /patients | GET | All patients |
| /patients/{patient_id} | GET | Single patient record |
| /referrals | GET | All referrals |
| /referrals/{referral_id} | GET | Single referral record |
| /transfers | GET | All transfer requests |
| /transfers/{transfer_id} | GET | Single transfer record |
| /documents | GET | All documents |
| /chart/{patient_id} | GET | Patient chart/clinical record |
| /programs/{program_code}/candidates | GET | Candidates for a chronic-care program |
| /icd/{code} | GET | ICD-10 code metadata (chapter, description, etc.) |
| /pharmacies | GET | Pharmacy network directory |
| /query | POST | Read-only SQL endpoint for multi-table queries |

## Batch Processing Patterns

### Roster workflows (patient access / insurance)

Fetch in this order, parallelizing where possible:
1. Read the roster data from the task payload (target_roster.json or similar) to get the patient list, requested service date, and service line
2. Fetch each patient by ID: GET /patients/{patient_id}
3. Fetch each patient chart: GET /chart/{patient_id}
4. Fetch referral data if needed: GET /referrals and GET /referrals/{referral_id}
5. Look up pharmacy network status: GET /pharmacies, filtered by the patient pharmacy
6. Use POST /query for bulk cross-table lookups when many patients share the same data patterns

### Referral audit workflows

1. Fetch all referrals: GET /referrals
2. Filter to the target batch by batch ID, program code, or naming convention
3. For each referral in the batch, fetch referral detail, patient, chart, ICD codes, and documents
4. Use POST /query for duplicate detection and insurance anomaly scans

### Transfer review workflows

1. Fetch all transfers: GET /transfers
2. Filter to the target batch
3. For each transfer, fetch transfer detail, patient, and documents; cross-reference with required document checklist
4. Determine capacity from the transfer and facility data returned by the API

### Enrollment panel workflows

1. Fetch candidates: GET /programs/{program_code}/candidates
2. For each candidate, fetch chart and patient data
3. Use POST /query to reconcile clinical criteria across the candidate set

## Using POST /query

The /query endpoint accepts a JSON body with a query field containing a SQL SELECT statement. Use it for finding duplicates across referrals, detecting shared insurance IDs across patients, reconciling ICD chapters against service lines in bulk, and counting documents by type and patient.

The query language is standard read-only SQL. Only SELECT statements are allowed.
