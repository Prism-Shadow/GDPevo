---
name: ehr-quality-governance-packets
description: Produce normalized JSON packets from a read-only EHR quality-governance HTTP API. Use when a task gives case-object IDs (patients, referrals, duplicate candidates, service requests, batch IDs) plus an input/payloads/answer_template.json schema and asks you to reconcile clinical evidence into one strict-schema JSON object. Covers duplicate-merge readiness packets, referral-coordination packets, care-transition handoff packets, duplicate+ServiceRequest quality review, and referral-batch audits. Reach the environment ONLY over the network via environment_access.md; the API is the sole source of truth for environment data.
---

# EHR Quality-Governance Packets

This skill solves a family of tasks that all share one shape: you are given a few
**case-object IDs** in a `prompt.txt`, a strict output **schema** in
`input/payloads/answer_template.json`, and a **read-only EHR HTTP API** described
in `environment_access.md`. You must fetch evidence over the network, reconcile it
against the clinical record, and emit **a single normalized JSON object** that
conforms exactly to the template.

The five packet types this skill covers:
1. **Duplicate-chart merge readiness packet** — pick canonical target/source, merge
   disposition, active clinical-key unions, identity match/conflict signals,
   document/audit evidence, specialist+PCP contact.
2. **Referral coordination packet** — reconcile a referral with the active chart:
   diagnosis/code set for the letter, allergy readiness, encounter + required-document
   evidence, receiving provider, authorization/readiness, medication highlights,
   referral-letter field choices.
3. **Care-transition handoff packet** — patient + recipient, active clinical keys,
   the N most relevant handoff encounters, latest immunization, applicable disclosure,
   risk flags + evidence, send readiness.
4. **Duplicate + ServiceRequest quality review** — validate the duplicate-review
   outcome and the ServiceRequest quality signals (code validity, reason-code
   validation, performer service line, SBAR coverage).
5. **Referral-batch audit** — invalid/out-of-range diagnosis codes, laterality/narrative
   mismatches, duplicate groups, insurance/patient anomalies, follow-up queues,
   Tier 1/2/3 action plan, summary counts.

## Inputs you are given

- `prompt.txt` — states the packet type and lists the **case-object IDs** to act on.
  It contains a `<TASK_ENV_BASE_URL>` placeholder. Extract every ID it names.
- `input/payloads/answer_template.json` — the **output contract**. It states required
  top-level keys, field types, `enum` allowed values, which arrays have `set_semantics`,
  and `ordering` rules. Treat it as law.
- (Some tasks add extra payloads, e.g. a request manifest listing `requested_outputs`.
  Read every file under `input/payloads/`.)
- `environment_access.md` — the **base URL** and the list of allowed `GET` endpoints.
  No authentication.

## Non-negotiable rules

- **The network API is the only source of truth for environment data.** Do not read
  local source files for environment data. Use `environment_access.md` solely to obtain
  the base URL needed to reach the API over the network.
- **`normalized_key` is provided by the API** on conditions, medications, and allergies.
  Read it directly; never invent or re-derive it.
- **Output is one JSON object only.** No prose, no markdown fences, no extra keys, no
  omitted required keys. Conform exactly to `answer_template.json`.
- **Honor every enum, set-semantics, and ordering rule in the template.** Arrays marked
  as sets → sorted ascending (alphabetically unless the template says otherwise). Dates
  → `YYYY-MM-DD`.
- **Active records only.** Filter clinical lists by `status == "active"`. Exclude stale,
  inactive, opposite-laterality, and unrelated-distractor records (see
  `references/normalization.md`).
- **The duplicate candidate's `merge_preview` is a hint, not authoritative.** Patient
  active-list endpoints are authoritative for clinical unions; the preview may omit
  active keys that the patient endpoints contain.
- **Do not copy specific values from any example.** Derive every value from the live API
  for the case objects in the current prompt.

## Workflow

1. **Parse the prompt.** Identify the packet type and extract every case-object ID.
2. **Internalize the template.** Read `answer_template.json` (and any extra payload).
   Note required top-level keys, field types, enums, set-semantics, and ordering. This
   is the contract you must satisfy.
3. **Resolve the base URL.** Read `environment_access.md`, substitute the value into
   `<TASK_ENV_BASE_URL>`.
4. **Fetch evidence.** Map each case object to its endpoints (see
   `references/api_endpoints.md`) and pull the records you need. List endpoints return
   the **full** set and ignore query parameters — filter client-side by `batch_id`,
   `patient_id`, `service_line`, etc.
5. **Reconcile.** Apply the reasoning for your packet type (see
   `references/reconciliation_playbook.md`). Use `scripts/ehr_client.py` for fetching
   and the shared normalization helpers.
6. **Normalize.** Apply the conventions in `references/normalization.md` (active filter,
   sorted sets, `YYYY-MM-DD` dates, distractor exclusion, enum compliance).
7. **Validate against the template.** Every required key present; every enum value legal;
   every set sorted; every date formatted; no extra keys.
8. **Emit one JSON object.** Nothing else.

## Case-object → endpoint map (compact)

| Case object | Endpoints |
|---|---|
| Patient `P-…` | `/api/patients/{id}` + `/conditions` `/medications` `/allergies` `/encounters` `/documents` `/immunizations` `/disclosures` `/service-requests` |
| Duplicate candidate `DUP-…` | `/api/duplicates/{id}` (has `merge_preview`, `match_signals`, `conflict_signals`) |
| Referral `REF-…` | `/api/referrals/{id}` ; batch via `/api/referrals` filtered by `batch_id` |
| Service request `SR-…` | `/api/patients/{patient_id}/service-requests` (carries `sbar`, `reason_codes`, `service_code`) |
| Provider `PRV-…` | `/api/providers/{id}` |
| ICD-10 code | `/api/icd10/{code}` (`chapter`, `expected_terms`, `requires_laterality`) |
| Service code | `/api/service-codes/{code}` (`active`, `service_line`) |
| Audit logs | `/api/audit-logs` filtered by `patient_id` |

ID formats you will see: patients `P-NNNNN`, providers `PRV-XXX-NNN`, referrals
`REF-…`, duplicate candidates `DUP-…`, service requests `SR-…`, batches
`MONYY-LINE-X`. Always use the exact IDs from the prompt.

## Normalization in one screen

- `normalized_key`: take it verbatim from the API record.
- Active filter: `status == "active"` (case-insensitive). Inactive → excluded distractor.
- Sets: unique, non-empty, sorted ascending (string order) unless the template overrides.
- Dates: pass through as `YYYY-MM-DD`.
- Distractors to exclude: inactive clinical records, opposite-laterality conditions for
  the joint in question, unrelated document types (e.g. `chart_summary`), unrelated audit
  logs, synthetic-looking encounter IDs outside the selection window.
- Derived (not stored) fields: `performer_service_line` (from provider lookup),
  `service_code_valid` (from service-code `active`), `reason_code_validation` (from
  ICD-10 lookup), `sbar_coverage` (from the `sbar` object).

## Output checklist (before emitting)

- [ ] One JSON object, no prose, no fences.
- [ ] All required top-level keys present; no extra keys.
- [ ] Every enum value is in the template's allowed list.
- [ ] Every set array sorted ascending; dates `YYYY-MM-DD`.
- [ ] Clinical unions use active records only; distractors excluded and (where the
      template asks) listed under `excluded_distractors`.
- [ ] Every cited evidence ID actually exists in the fetched records.
- [ ] No value copied from an example — all derived from the live API for this prompt.

## References

- `references/api_endpoints.md` — full endpoint catalog, response shapes, wrapper keys,
  the no-server-side-filter rule, and stored-vs-derived fields.
- `references/normalization.md` — normalization conventions and the
  duplicate-preview-vs-active-list reconciliation rule in detail.
- `references/reconciliation_playbook.md` — per-packet-type reasoning that turns
  evidence into the template's fields.
- `scripts/ehr_client.py` — generic, tested API client + normalization helpers
  (stdlib only). Run `python3 scripts/ehr_client.py` for a reachability smoke test.
