## Cedar Ridge Portal API Reference

All responses are JSON. Use `curl -s <BASE_URL>/<endpoint>` for GET and
`curl -s -X POST <BASE_URL>/query -H "Content-Type: application/json" -d '{"sql": "..."}'` for SQL.

### GET /patients

Returns a JSON array of patient objects.

```
[
  {
    "patient_id": "P001",
    "name_first": "string",
    "name_last": "string",
    "dob": "YYYY-MM-DD",
    "address": "string | null",
    "phone": "string | null",
    "email": "string | null",
    "emergency_contact_name": "string | null",
    "emergency_contact_phone": "string | null",
    "preferred_contact_method": "string | null",
    "insurance_plan_id": "string | null",
    "insurance_plan_name": "string | null",
    "insurance_start_date": "YYYY-MM-DD | null",
    "insurance_end_date": "YYYY-MM-DD | null",
    "covered_service_lines": ["string", ...] | null,
    "pbm_id": "string | null",
    "pbm_name": "string | null",
    "pbm_active": "boolean | null",
    "pbm_plan_match": "boolean | null",
    "preferred_pharmacy_id": "string | null",
    "preferred_pharmacy_name": "string | null",
    "pharmacy_network_status": "string | null",
    "lifestyle_risk": "string | null",
    "overall_risk": "string | null"
  }
]
```

### GET /patients/{patient_id}

Returns a single patient object with the same shape as above.

### GET /referrals

Returns a JSON array of referral objects.

```
[
  {
    "referral_id": "REF0001",
    "patient_id": "P042",
    "batch_id": "ORTHO-JUN-01 | PULM-JUN-02",
    "service_line": "string",
    "icd10_code": "string",
    "icd10_description": "string",
    "narrative": "string | null",
    "laterality": "string | null",
    "urgency": "urgent | routine | admin",
    "referring_provider": "string | null",
    "referral_date": "YYYY-MM-DD",
    "requested_appointment_date": "YYYY-MM-DD | null",
    "authorization_status": "approved | pending | denied | not_submitted | null",
    "has_records": "boolean",
    "has_imaging": "boolean",
    "insurance_policy_id": "string | null",
    "scheduled_appointment_date": "YYYY-MM-DD | null"
  }
]
```

### GET /referrals/{referral_id}

Returns a single referral object with the same shape as above.

### GET /transfers

Returns a JSON array of transfer objects.

```
[
  {
    "transfer_id": "TR0001",
    "patient_id": "P014",
    "batch_id": "DIAL-WINTER-01",
    "referring_facility": "string",
    "requested_start_date": "YYYY-MM-DD",
    "required_documents": ["string", ...],
    "received_documents": ["string", ...]
  }
]
```

### GET /transfers/{transfer_id}

Returns a single transfer object with the same shape as above.

### GET /documents

Returns a JSON array of document objects.

```
[
  {
    "document_id": "string",
    "transfer_id": "TR0001 | null",
    "referral_id": "REF0001 | null",
    "patient_id": "P014",
    "doc_type": "string",
    "received_date": "YYYY-MM-DD",
    "status": "string"
  }
]
```

### GET /chart/{patient_id}

Returns a patient chart object.

```
{
  "patient_id": "P026",
  "chart_active": "boolean",
  "active_problems": [{"code": "string", "description": "string", "date_noted": "YYYY-MM-DD"}],
  "vitals": [{"date": "YYYY-MM-DD", "bp_systolic": int, "bp_diastolic": int, ...}],
  "labs": [{"date": "YYYY-MM-DD", "a1c": float | null, "hdl": float | null, "ldl": float | null, "creatinine": float | null, "egfr": float | null}],
  "medications": [{"name": "string", "dose": "string", "frequency": "string"}],
  "allergies": [{"name": "string"}],
  "demographics": "object | null",
  "consent_status": "string | null",
  "recent_hospitalization": "boolean",
  "recent_ed_visit": "boolean",
  "medication_adherence": "string | null",
  "diagnoses": [{"code": "string", "description": "string", "status": "string"}]
}
```

### GET /programs/{program_code}/candidates

Returns a JSON array of patient IDs qualifying for the program.

```
["P026", "P027", "P028", ...]
```

### GET /icd/{code}

Returns ICD-10 metadata for a specific code.

```
{
  "code": "S83.512A",
  "description": "string",
  "chapter": "S00-T88",
  "chapter_description": "string",
  "category": "string"
}
```

### GET /pharmacies

Returns a JSON array of pharmacy objects.

```
[
  {
    "pharmacy_id": "string",
    "pharmacy_name": "string",
    "network_id": "string",
    "in_plan_network": "boolean"
  }
]
```

### POST /query

Accepts a JSON body with a `sql` key containing a read-only SELECT statement.
Returns a JSON array of result rows.

```bash
curl -s -X POST <BASE_URL>/query \
  -H "Content-Type: application/json" \
  -d '{"sql": "SELECT r.referral_id, p.patient_id FROM referrals r JOIN patients p ON ..."}'
```

Use SQL when individual GET calls would require manual cross-referencing:
finding all referrals for a batch not linked to a patient chart, identifying
patients sharing the same insurance policy, or counting documents per transfer.

### Common Cross-Reference Patterns

- Referral → Patient: `GET /referrals/{id}` has `patient_id`; follow with `GET /patients/{patient_id}`
- Referral → ICD: `GET /referrals/{id}` has `icd10_code`; follow with `GET /icd/{code}`
- Referral → Chart: get `patient_id` from referral, then `GET /chart/{patient_id}`
- Transfer → Documents: filter `GET /documents` by `transfer_id`
- Transfer → Patient / Chart: `GET /transfers/{id}` has `patient_id`
- Patient → Pharmacy: `GET /patients/{id}` has `preferred_pharmacy_id`; `GET /pharmacies` for network lookup
