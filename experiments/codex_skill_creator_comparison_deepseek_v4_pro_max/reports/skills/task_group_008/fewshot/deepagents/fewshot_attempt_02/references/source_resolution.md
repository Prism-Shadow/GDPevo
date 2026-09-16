 # Source Resolution Hierarchy
 
 Client records arrive from multiple advisory systems and may conflict.
 Use the fixed resolution hierarchy below. Resolve field-by-field, not
 document-by-document. When a controlling source is missing for a
 particular field, fall through to the next source in the hierarchy.
 
 ## Profile Source Hierarchy (for client identity, demographics, goals, beneficiaries)
 
 1. `SIGNED_PROFILE` — client-signed planning profile; highest authority
 2. `ATTORNEY_MEMO` — attorney-prepared memo; second authority
 3. `CUSTODIAN_EXPORT` — custodian data feed; third authority
 4. `CRM_NOTE` — advisor notes in CRM; fourth authority
 5. `STALE_MARKETING_INTAKE` — old marketing intake form; lowest authority, use only when nothing else exists
 
 ## Account Source Hierarchy (for retirement account balances, account types)
 
 1. `CUSTODIAN_EXPORT` — direct custodian feed; highest authority for account data
 2. `SIGNED_PROFILE` — client-stated values; second authority
 3. `CRM_NOTE` — advisor notes; lowest authority for account data
 
 ## Policy Source Hierarchy (for life insurance policies)
 
 1. `SIGNED_PROFILE` — client-signed document; highest authority
 2. `ATTORNEY_MEMO` — attorney document; second authority
 3. `CUSTODIAN_EXPORT` — custodian data; third authority
 4. `CRM_NOTE` — advisor notes; lowest authority
 
 ## Goal Source Hierarchy (for trust comparison, estate planning goals)
 
 1. `SIGNED_PROFILE` — client's stated goals
 2. `ATTORNEY_MEMO` — attorney guidance
 3. `CUSTODIAN_EXPORT` — limited relevance but may appear
 4. `CRM_NOTE` — advisor notes
 5. `STALE_MARKETING_INTAKE` — lowest
 
 ## Asset Source Hierarchy (for trust funding assets, liquid assets)
 
 1. `ATTORNEY_MEMO` — attorney-prepared asset schedule
 2. `SIGNED_PROFILE` — client-stated
 3. `CRM_NOTE` — advisor notes
 
 ## Procedure
 
 1. Fetch `/api/source-documents` and filter by the target `client_id`.
 2. For each field needed, check documents in hierarchy order until a value is found.
 3. Record which source controlled each category in `source_resolution`:
    - `controlling_profile_source` — the source that resolved client profile fields
    - `controlling_account_source` — the source that resolved account fields
    - `controlling_beneficiary_source` — the source that resolved beneficiary data
    - `controlling_policy_source` — the source that resolved insurance policy data
    - `controlling_goal_source` — the source that resolved estate planning goals
    - `controlling_asset_source` — the source that resolved asset/funding data
 4. Cross-validate against `/portal/client/{client_id}` when values seem inconsistent.
