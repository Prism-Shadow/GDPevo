# Hub API Endpoint Reference

All endpoints are read-only GET requests except `POST /api/query`. Base URL is resolved from `environment_access.md`.

## Endpoint Catalog

### `GET /`

Health check. Returns hub status and version. Always callable without authentication.

**Use in Phase 2** to confirm the hub is reachable before proceeding.

---

### `GET /api/schema`

Returns the data schema: available entities, their fields, field types, and relationships between entities. The authoritative map of what data lives where.

**Always call first** after confirming hub reachability. Do not assume endpoint structure from training tasks — the live schema may differ.

**Response includes**:
- Entity names and their fields
- Field types (string, integer, date, boolean, enum)
- Foreign-key relationships between entities
- Available query parameters for search endpoints

---

### `GET /api/matters`

Returns all matters in the hub.

**Response**: List of matter objects with:
- `matter_id` — stable identifier (e.g., `MTR-SENTINEL-GJ`, `MTR-HARBORSTONE-GJ`)
- `client` — client organization name
- `matter_type` — agency or investigation type (grand jury, SEC, DOJ, etc.)
- `status` — matter status
- `open_date` — matter open date
- `description` — matter description

**Use**: Confirm the matter ID from the prompt exists. Retrieve matter-level metadata for the answer's `matter_id` field.

---

### `GET /api/subpoena-categories`

Returns all request categories for subpoenas and document requests.

**Response**: List of category objects with:
- `category_code` — short code (e.g., `A`, `B`, `SEC-FIN`, `DOJ-ANTITRUST-1`)
- `title` — human-readable title
- `description` — scope of documents requested
- `matter_id` — which matter the category belongs to

**Use**: Retrieve all category codes for the matter. These codes populate `category_impacts`, `affected_categories`, and `category_code` fields throughout the answer.

---

### `GET /api/productions`

Returns production status information.

**Response**: List of production records with:
- Production dates and rolling production identifiers
- Produced document counts by category
- Production status (complete, partial, pending)
- Links to category codes

**Use**: Archetypes A and D. Determine which categories have been produced, what volumes, and what gaps exist.

---

### `GET /api/custodian-sources`

Returns custodian data sources, collection status, and source metadata.

**Response**: List of source objects with:
- `source_id` — stable identifier
- `custodian_name` — custodian name
- `source_type` — email, personal_phone, laptop, shared_drive, messaging, archives, etc.
- `collection_status` — collected, partial, not_collected, lost, pending
- `hold_date` — when the litigation hold was issued to this custodian
- `affected_categories` — which request categories this source covers
- `notes` — context about gaps or issues

**Use**: All archetypes. Identify collection gaps, lost sources, uncollected personal devices, and available archives.

---

### `GET /api/documents/search`

Search documents with query parameters.

**Query parameters** (varies — check `/api/schema` for the running instance):
- `category` — filter by category code
- `coding` — filter by coding status (responsive, nonresponsive, privileged)
- `produced` — filter by production status
- `custodian` — filter by custodian
- `q` — text search

**Response**: List of document objects with:
- `document_id` — stable identifier
- `category_code` — which category the document falls under
- `coding` — responsive/nonresponsive/privileged determination
- `produced_status` — produced, not_produced, withheld
- `privilege_basis` — if withheld, the privilege basis
- `custodian` — source custodian
- `review_date` — when reviewed

**Use**: All archetypes. Find miscoded documents, count documents by status, trace privilege assertions.

---

### `GET /api/privilege-log`

Returns privilege log entries: documents withheld from production on privilege grounds.

**Response**: List of privilege log entries with:
- `log_id` — stable identifier
- `document_id` — linked document
- `privilege_basis` — attorney-client, work product, etc.
- `logged` — whether the document appears on the privilege log (true) or is withheld but unlogged (false)
- `waived` — whether privilege has been waived
- `third_party` — third party involved in communication (relevant to waiver)
- `category_code` — affected category
- `date` — document date

**Use**: Archetypes A, C, D. Count withheld/logged/unlogged documents. Identify privilege log gaps (withheld but not logged). Identify potential waiver events (third-party communications). Identify over-designation patterns.

---

### `GET /api/qc-findings`

Returns quality-control findings: coding errors, responsiveness determinations, privilege miscoding.

**Response**: List of QC finding objects with:
- `finding_id` — stable identifier
- `document_id` — document with the issue
- `finding_type` — miscoded_responsive, miscoded_privilege, privilege_log_gap, etc.
- `severity` — critical, high, medium, low
- `status` — open, confirmed, cleared
- `current_coding` — what the document is currently coded as
- `recommended_coding` — what it should be coded as
- `category_code` — affected category

**Use**: Archetypes A, C, D. Identify miscoded responsive documents that need recoding and reproduction. Identify privilege coding errors. Count document-level issues.

---

### `GET /api/retention-events`

Returns retention and preservation events.

**Response**: List of retention event objects with:
- `event_id` — stable identifier
- `event_type` — policy_destroyed_pre_hold, post_hold_loss, auto_purged, active_system_loss, etc.
- `event_date` — when the retention event occurred
- `hold_date` — when the litigation hold was issued (for comparison)
- `policy_section` — retention policy section governing the records
- `retention_period_months` — standard retention period
- `record_type` — type of records affected
- `volume_count` — number of boxes/records affected
- `volume_unit` — boxes, records, days, months
- `affected_categories` — which request categories are impacted
- `system` — which system the records were in (for communication gaps)
- `archive_source_id` — if an archive exception exists, the source ID

**Use**: Archetypes B and C. Determine what was destroyed before vs. after the hold. Identify auto-purge events and policy-compliant destruction. Quantify lost volumes. Link to available archives.

---

### `GET /api/remediation-actions`

Returns existing remediation actions and their status.

**Response**: List of remediation action objects with:
- `action_id` — stable identifier
- `action_type` — type of remediation
- `owner` — responsible party
- `status` — pending, in_progress, complete
- `target_refs` — record IDs the action targets
- `category_impacts` — affected categories
- `priority` — P0, P1, P2, P3

**Use**: Archetypes A and C. Identify what remediation is already underway. Avoid duplicating existing actions. Inform priority — if an action is already in progress, new actions should account for it.

---

### `POST /api/query`

Read-only SQL query endpoint. Use for cross-cutting questions that require joins or aggregation across multiple entity types.

**Headers**: `X-API-Key: review-key-017` (from `environment_access.md` credentials)

**Request body**: `{ "query": "<SQL statement>" }`

**Response**: `{ "rows": [...], "row_count": N }`

**Use when**:
- You need counts by category across multiple filters
- You need to join documents with privilege log entries and QC findings
- You need distinct counts that span multiple GET endpoints
- The filtered search parameters on GET endpoints are insufficient

**Constraints**:
- SELECT only — no INSERT, UPDATE, DELETE, DROP, ALTER
- Single statement per request
- Query timeout may apply

## Data Relationship Map

```
matter ──┬── subpoena-categories (by matter_id)
         ├── custodian-sources (by matter_id)
         ├── productions (by matter_id)
         ├── documents (by matter_id, category_code)
         │      ├── privilege-log entries (by document_id)
         │      └── qc-findings (by document_id)
         ├── retention-events (by matter_id)
         └── remediation-actions (by matter_id)
```

When building findings, trace from the finding back to its supporting hub records. A retention loss finding references a `retention-events` record. A coding error finding references a `qc-findings` record and its linked `documents` record. A privilege gap finding references `privilege-log` entries and their linked `documents` records.
