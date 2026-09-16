# Northstar Business Records

## Record Types and Relationships

### Cases
Identifier format: `CASE-*`, `P2P-*`, `APPEAL-*`, `CLAIM-*`, `QUEUE-*`.
Cases link to policies, documents, authorizations, claims, appeals, and service margins.
Query via `/api/cases/{case_id}` or SQL `SELECT * FROM cases WHERE case_id = ?`.

### Policies
Contain clinical/coverage criteria. Criteria IDs like `PT-ACTIVE`, `PT-DEFICIT`, `PT-DX`, `PT-POC`, `PT-UNITS` for physical therapy; `PET-IND`, `PET-FACTOR` for PET imaging; `DRUG-AUTH`, `DRUG-DENIAL`, `DRUG-RATIONALE`, `DRUG-FAILURES` for pharmacy.
Query via `/api/policies/{policy_id}` or SQL.

### Documents
Clinical evidence documents attached to cases. Identifiers like `DOC-*`. Each has a content type, date, and relation to a case.
Key distinction: active current clinical documents vs. stale/excluded documents.
Query via `/api/documents/{document_id}` or SQL `SELECT * FROM documents WHERE case_id = ? ORDER BY document_id`.

### Appeals
Pharmacy and medical appeals. Identifiers like `APL-*`. Contain routing (standard, expedited), deadlines, and attached evidence.
Query via `/api/appeals` or SQL `SELECT * FROM appeals WHERE appeal_id = ?`.

### Drug Trials / Medication Evidence
Records for formulary failure evidence: `TRIAL-*` formatted IDs. Each documents a medication trial with outcome (success/failure/insufficient).
Query via SQL: `SELECT * FROM drug_trials WHERE case_id = ?`.

### Claims and Claim Lines
Claim identifiers like `CLAIM-*`. Claim lines like `CL-*`. Each line has CPT code, modifier, units, and paid amount.
Query via SQL: `SELECT * FROM claims WHERE claim_id = ?` and `SELECT * FROM claim_lines WHERE claim_id = ? ORDER BY line_id`.

### Rate Schedules / Benchmarks
Benchmark identifiers like `BM-*`. Contain allowed amounts by CPT, modifier, plan type, and effective date.
Stale benchmarks (e.g., `BM-OLD-*`) must be rejected in favor of current effective benchmarks.
Query via `/api/rate-schedules` or SQL `SELECT * FROM benchmarks WHERE cpt_code = ? AND modifier = ? ORDER BY effective_date DESC`.

### Authorizations
Authorization numbers like `NPA-*`. Contain approved units, date ranges, CPT codes, modifiers.
Query via SQL: `SELECT * FROM authorizations WHERE case_id = ?` or `SELECT * FROM authorizations WHERE auth_number = ?`.

### Service Margins
Margin records like `SM-*`. Contain payer segment, service domain, CPT, costs, revenue, and ratios.
Query via SQL: `SELECT * FROM service_margin WHERE month_id IN (...)`.

### P2P Events
Peer-to-peer discussion records like `P2P-*`. Contain the outcome, new information flag, and discussion notes.
Query via SQL: `SELECT * FROM p2p_events WHERE case_id = ?`.

## General Query Strategy

1. Start with REST endpoints for list-level discovery: `/api/cases`, `/api/policies`, `/api/tables`.
2. Drill into specific records with `/api/cases/{case_id}`, `/api/policies/{policy_id}`, `/api/documents/{document_id}`.
3. Use SQL for cross-entity joins, filtering by criteria codes, ordering by dates, and aggregation.
