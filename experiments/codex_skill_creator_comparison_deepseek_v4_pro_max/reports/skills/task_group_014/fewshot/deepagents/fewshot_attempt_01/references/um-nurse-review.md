# UM Nurse Prior Authorization Review

## Overview

Review a prior authorization case for physical therapy (PT) services and produce a structured determination summary. The output matches the UM nurse determination answer template with required fields: `case_id`, `recommendation`, `final_status`, `route`, `authorization`, `criteria_results`, `evidence_documents`, `excluded_documents`, `determination_letter`, `next_action`, `basis_audit`.

## Workflow

### 1. Gather case context

Pull the case record from the environment. Identify:
- The case ID (e.g., `CASE-TR-001`)
- The service domain (physical therapy)
- The requesting provider and member context
- The requested CPT codes, units, and date range

Use REST `GET /api/cases/{case_id}` or SQL to retrieve case facts.

### 2. Review policy criteria

Pull the applicable PT policy. Map each requested CPT to its criteria. The five required criteria keys are:

| Criterion ID | What It Checks |
|-------------|----------------|
| `PT-ACTIVE` | Active treatment need (member has ongoing functional deficit) |
| `PT-DEFICIT` | Documented functional deficit |
| `PT-DX` | Qualifying diagnosis on file |
| `PT-POC` | Valid plan of care with frequency, duration, goals |
| `PT-UNITS` | Requested units within policy limits |

For each criterion, set the result to one of: `met`, `not_met`, `unclear`, `not_applicable`.

### 3. Review clinical documents

Retrieve all clinical documents attached to the case. Every document has a document ID and content. Classify documents:

- **Evidence documents** (`evidence_documents`): Current, relevant clinical records that support the determination. Listed in ascending document_id order.
- **Excluded documents** (`excluded_documents`): Stale, irrelevant, or superseded records. Listed in ascending document_id order.

The source precedence rule is `current_clinical_records_over_stale_export`. Current evaluations and plans of care take priority over stale exports or outdated records.

### 4. Make the recommendation

Map the criteria results to a recommendation:

| Criteria Pattern | Recommendation | Final Status | Route | Letter | Next Action |
|-----------------|---------------|-------------|-------|--------|-------------|
| All criteria met | `approve` | `approved` | `nurse_approval` | `approval` | `issue_approval` |
| Any criterion not met | `deny` | `denied` | `medical_director_review` | `adverse_determination` | `route_md_review` |
| Missing information | `pend_for_information` | `pended` | `pending_information` | `information_request` | `request_more_information` |
| Complex clinical judgment needed | `escalate_to_md` | `md_review_required` | `medical_director_review` | `adverse_determination` | `route_md_review` |

### 5. Build the authorization block

When approving, populate the `authorization` object:

- `auth_number`: from the case or generate in format `NPA-{digits}`
- `approved_units`: total approved service units (integer)
- `approved_start` / `approved_end`: date range in YYYY-MM-DD
- `approved_cpt`: list of approved CPT codes, ascending order
- `modifier`: the billing modifier (e.g., `GP` for PT)

### 6. Construct the basis_audit

Use `current_clinical_records_over_stale_export`:

- `controlling_record_ids`: current clinical docs that directly support the result
- `exception_record_ids`: stale documents excluded from the determination
- `precedence_record_order`: controlling records first, then exception records

## Key Patterns from Training

- When all five PT criteria are met and the only issue is a stale document, the recommendation is `approve` with the stale doc excluded.
- Criteria results must be exhaustive -- every required criterion key must have a value.
- Evidence document lists are ordered ascending by document ID.
- The authorization CPT list is ordered ascending by CPT code.
