# Endpoint Guide

`environment_access.md` is the runtime authority for the **base URL** and the
**allowed `GET` paths**. This file describes *which endpoint family serves which
evidence need* and *how to cross-reference* them — it does not redefine the
paths. Always re-read `environment_access.md` for the exact paths and do not
hardcode them; if it and this guide ever disagree, `environment_access.md`
wins.

## Endpoint families and what they give you

| Need | Family | Use it for |
|---|---|---|
| Patient identity | patient detail | demographics, MRN, DOB, PCP linkage |
| Active clinical lists | conditions / medications / allergies | `normalized_key` values for active-list unions and reconciliation |
| Visit history | encounters | handoff-encounter selection, recent-encounter evidence, encounter diagnoses |
| Clinical documents | documents | required-document evidence (imaging, clinical notes), identity/continuity docs for merge packets |
| Immunizations | immunizations | latest-immunization block |
| Disclosures | disclosures | disclosure-permitted status for handoff readiness |
| Service requests | service-requests | ServiceRequest quality fields (status, intent, priority, codes, performers) |
| Audit trail | audit-logs | audit evidence IDs for merge packets |
| Duplicate review | duplicate candidates + detail | match/conflict signals, candidate status, target/source |
| Referrals | referrals (list + detail) | referral batch rows, referral-letter reconciliation, audit rows |
| Code directories | icd10 / service-codes | code validation (chapter, expected terms, laterality; service-code validity) |
| Provider directory | providers | contact blocks (name, role, facility, phone, fax, service_line) |

## Cross-referencing strategy

- **Resolve every ID in the prompt.** Each case object (patient, referral,
  candidate, service-request, provider) has a detail endpoint — fetch it.
- **Follow links outward.** A referral points at a patient and a provider; a
  duplicate candidate points at two patients; a service-request points at a
  requester and a performer. Fetch each linked record.
- **Gather the full active chart for every patient involved**, including
  patients that turn out to be distractors. You need the complete active list
  to (a) build correct unions and (b) recognize which records are stale or
  unrelated and must be excluded.
- **For audit tasks, fetch the whole batch** (referral list scoped to the
  batch), then per-referral patient and ICD-10 records. Every summary count in
  the output must match the rows you actually audited.
- **Use list endpoints to discover, detail endpoints to confirm.** E.g. list
  duplicate candidates to find the one named in the prompt, then fetch its
  detail; list referrals to enumerate a batch; list documents to find the one
  of the required type, then confirm its status.

## What is NOT environment data
`prompt.txt`, `answer_template.json`, and any extra `input/payloads/` files are
**task inputs** — read them locally. Everything that describes a real patient,
referral, provider, or code is **environment data** and must come from the API
over the network.
