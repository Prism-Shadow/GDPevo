# Cedar Ridge Intake Coordination Portal — API Reference

Base URL: from `environment_access.md` → `base_url` field. All paths below are relative to that base.

---

## GET /

Health check. Returns portal status and available endpoint catalog.

---

## GET /patients

Returns the full patient registry as a JSON array.

### Response shape per patient

```json
{
  "patient_id": "string (e.g. P001)",
  "insurance_status": "valid | invalid | missing",
  "insurance_id": "string",
  "prescription_status": "valid | invalid | missing",
  "pharmacy_id": "string",
  "lifestyle_risk": "low | medium | high",
  "overall_risk": "low | medium | high",
  "preferred_contact_available": "boolean",
  "emergency_contact_on_file": "boolean",
  "address_on_file": "boolean",
  "service_line": "string",
  "demographics": { "...": "..." }
}
```

---

## GET /patients/{patient_id}

Returns a single patient record, same shape as the array entry above.

---

## GET /referrals

Returns all referrals. Filter client-side by batch_id or other fields as needed.

### Response shape per referral

```json
{
  "referral_id": "string (e.g. REF0001)",
  "patient_id": "string",
  "batch_id": "string",
  "icd10_codes": ["string (e.g. S83.512A)"],
  "narrative_text": "string (free-text clinical narrative)",
  "urgency": "urgent | routine | admin",
  "authorization_status": "approved | pending | denied | not_submitted",
  "documents_received": ["string (document type codes)"],
  "imaging_received": "boolean",
  "scheduled_appointment": "boolean",
  "scheduled_date": "date or null"
}
```

---

## GET /referrals/{referral_id}

Returns a single referral record, same shape as the array entry above.

---

## GET /transfers

Returns all transfer requests.

### Response shape per transfer

```json
{
  "transfer_id": "string (e.g. TR0001)",
  "patient_id": "string",
  "batch_id": "string",
  "requested_start_date": "string (YYYY-MM-DD)",
  "packet_documents": [
    {
      "doc_type": "string (e.g. hbsag, monthly_labs, history_physical)",
      "received_date": "string (YYYY-MM-DD)",
      "status": "received | missing"
    }
  ],
  "facility": "string"
}
```

---

## GET /transfers/{transfer_id}

Returns a single transfer record, same shape as the array entry above.

---

## GET /documents

Returns all document records.

### Response shape per document

```json
{
  "document_id": "string",
  "patient_id": "string",
  "referral_id": "string or null",
  "transfer_id": "string or null",
  "doc_type": "string",
  "received_date": "string (YYYY-MM-DD)",
  "status": "received | missing | stale"
}
```

---

## GET /chart/{patient_id}

Returns the active chart record for a patient.

### Response shape

```json
{
  "patient_id": "string",
  "chart_active": "boolean",
  "active_problems": { "last_updated": "string (YYYY-MM-DD)", "has_dmhtn_diagnosis": "boolean" },
  "vitals": { "last_updated": "string (YYYY-MM-DD)", "present": "boolean" },
  "labs": { "last_updated": "string (YYYY-MM-DD)", "present": "boolean" },
  "medications": { "last_updated": "string (YYYY-MM-DD)", "present": "boolean" },
  "allergies": { "last_updated": "string (YYYY-MM-DD)", "present": "boolean" },
  "consent": { "status": "signed | declined | missing", "signed_date": "string or null" },
  "demographics_on_file": "boolean"
}
```

---

## GET /programs/{program_code}/candidates

Returns the list of patient IDs currently qualifying as candidates for the given program.

### Response shape

```json
{
  "program_code": "string",
  "candidate_patient_ids": ["string (e.g. P026)"],
  "as_of_date": "string (YYYY-MM-DD)"
}
```

---

## GET /icd/{code}

Returns ICD-10 metadata for a single code.

### Response shape

```json
{
  "code": "string",
  "description": "string",
  "chapter": "string (e.g. S00-T88, M00-M99, J00-J99)",
  "laterality": "string or null (e.g. left, right, bilateral, null)",
  "category": "string"
}
```

---

## GET /pharmacies

Returns the pharmacy network directory.

### Response shape per pharmacy

```json
{
  "pharmacy_id": "string",
  "name": "string",
  "network_status": "in_network | out_of_network",
  "pbm_compatible": "boolean"
}
```

---

## POST /query

Read-only SQL endpoint. Send a JSON body:

```json
{"sql": "<SQL query string>"}
```

Returns a JSON array of result rows. The database schema maps to the REST resource shapes above — tables include `patients`, `referrals`, `transfers`, `documents`, `charts`, `pharmacies`, and `icd_codes`. Use this for bulk joins when REST round-trips would be excessive.

### Example queries

- Cross-reference referrals against patients and ICD chapters:
  `SELECT r.referral_id, r.patient_id, i.chapter, r.icd10_code FROM referrals r JOIN icd_codes i ON r.icd10_code = i.code WHERE r.batch_id = '<batch>'`

- Find insurance IDs shared across distinct patients:
  `SELECT p1.patient_id, p2.patient_id, p1.insurance_id FROM patients p1 JOIN patients p2 ON p1.insurance_id = p2.insurance_id AND p1.patient_id < p2.patient_id`

- Check document freshness:
  `SELECT d.doc_type, d.received_date, d.patient_id FROM documents d WHERE d.transfer_id IN (<transfer_id_list>)`
