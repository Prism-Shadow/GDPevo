 # Advisory API Endpoints
 
 Base URL is supplied by the harness as `API_BASE` (e.g. `http://task-env:9008/`).
 All responses are JSON. No authentication headers are required.
 
 ## Endpoints
 
 ### GET /api/clients
 Returns the full client list. Each client object includes:
 - `client_id` (e.g. `CLT-0000`)
 - `name`
 - `dob` (ISO date)
 - `tax_filing_status`
 - `marginal_tax_rate`
 - Other profile fields that may differ across source documents
 
 Filter in code by `client_id` to find the target client.
 
 ### GET /api/clients/{client_id}
 Returns a single client record. May contain a `sources` array or similar structure
 listing the document sources for each field.
 
 ### GET /api/source-documents
 Returns all source documents. Each document has:
 - `source_type` enum: `SIGNED_PROFILE`, `ATTORNEY_MEMO`, `CUSTODIAN_EXPORT`, `CRM_NOTE`, `STALE_MARKETING_INTAKE`
 - `client_id` (may be null for global docs)
 - `fields` or content block with field-level values
 
 Filter by `client_id` to find documents relevant to the target client.
 
 ### GET /api/retirement-accounts
 Returns all retirement accounts across clients. Each account includes:
 - `account_id`
 - `client_id`
 - `account_type` (e.g. `traditional_ira`, `roth_ira`, `401k`)
 - `balance` (current USD)
 - `owner_dob` or `owner_age`
 - `source_type` for conflict resolution
 
 Filter by `client_id` to get the target client's accounts.
 
 ### GET /api/life-insurance
 Returns all life insurance policies. Each policy includes:
 - `policy_id`
 - `client_id` (or `owner_client_id`)
 - `death_benefit`
 - `annual_premium`
 - `issue_date`
 - `policy_type`
 - `beneficiaries` array (with names, relationships, counts)
 - `source_type`
 
 Filter by `client_id`.
 
 ### GET /api/trust-candidates
 Returns trust candidate records. Each includes:
 - `trust_type` (e.g. `GRAT`, `CRAT`, `ILIT`)
 - `client_id`
 - Funding or asset fields
 - Term fields
 - Beneficiary or charitable fields
 
 Filter by `client_id`.
 
 ### GET /api/policies/tax
 Returns tax policy constants as a flat object. Typical keys:
 - `estate_tax_rate` (e.g. 0.40)
 - `gift_tax_rate`
 - `income_tax_rate_top`
 - `capital_gains_rate`
 - `annual_gift_exclusion` (per-beneficiary amount)
 - `lifetime_exemption` (total lifetime gift/estate exemption)
 - `charitable_deduction_rate` (e.g. 0.35 for CRAT income tax deduction)
 - `section_7520_rate` (used for GRAT/CRAT present-value calculations)
 
 These are global constants; no client filtering is needed.
 
 ### GET /api/rmd-factors
 Returns RMD divisor factors keyed by age. A table mapping age to divisor.
 Used to compute required minimum distributions: `RMD = prior_year_balance / divisor`.
 
 ### GET /portal/client/{client_id}
 Returns a portal summary for the given client. May include aggregated views
 that help cross-check other endpoint data. Use as a secondary source.
