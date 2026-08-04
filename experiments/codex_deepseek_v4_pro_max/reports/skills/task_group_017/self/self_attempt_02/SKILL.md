## Investigation Review Hub Skill

This skill covers legal-operations review tasks powered by the **Investigation Review Hub** — a shared API environment that serves as the single source of record for matters, subpoena categories, productions, custodians, documents, privilege logs, QC findings, retention events, and remediation actions.

### When to use this skill

Activate this skill whenever the task involves:

- A gap analysis, retention/preservation review, remediation dashboard, production-readiness review, or privilege-QC review
- A `prompt.txt` that references an Investigation Review Hub at `<TASK_ENV_BASE_URL>`
- Payload files that include an answer template JSON schema
- A requirement to return a structured JSON object conforming to a provided template

### API reference

The Investigation Review Hub is consistently available at the base URL given by the task (often `<TASK_ENV_BASE_URL>`). All endpoints are read-only except `/api/query`.

**GET endpoints (all read-only):**

- `GET /` — root
- `GET /api/schema` — database schema (tables, columns, types)
- `GET /api/matters` — matter metadata
- `GET /api/subpoena-categories` — request/subpoena categories per matter
- `GET /api/productions` — production status
- `GET /api/custodian-sources` — custodian and data-source records
- `GET /api/documents/search` — document-level review/search
- `GET /api/privilege-log` — privilege-log entries
- `GET /api/qc-findings` — QC finding records
- `GET /api/retention-events` — retention-event records
- `GET /api/remediation-actions` — remediation-action records

**POST endpoint (read-only SQL):**

- `POST /api/query`
- Content-Type: `application/json`
- Required header: `X-API-Key: review-key-017`
- Body: `{"sql": "<SELECT statement>", "params": ["<value>", ...]}`
- Only `SELECT` statements are allowed. Use `?` placeholders with the `params` array.

### Input processing rules

1. **Read `prompt.txt` first.** It contains the task objective, the matter/client, the deliverable type, and source constraints.
2. **Read all payload files** in the `input/payloads/` directory:
   - Context payloads (e.g., `request_context.json`, `review_scope.json`, `matter_context.json`) provide client-facing metadata and category labels. Treat them as background reference only — the *evidence* must come from the hub.
   - The **answer template** (e.g., `answer_template.json`) defines the exact JSON output schema. It is a schema file, not a pre-filled answer. It specifies:
     - Required top-level keys
     - Field names, types, and descriptions
     - Enum value sets for every controlled vocabulary
     - Ordering rules (which lists to sort, by which key, in which direction)
     - Numeric precision (always whole integers)
3. **Extract the matter ID** from the context payload (or prompt) and use it as the primary filter when querying the hub.

### Source constraints (strict)

**Allowed sources:**
- All Investigation Review Hub API endpoints listed above
- Task-local payload files in the `input/` directory (context JSONs and the answer template)

**Prohibited sources — never access or inspect:**
- Local environment files or configuration files
- Database files (`.db`, `.sqlite`, etc.)
- Source code or seed files
- Generated manifests, setup scripts, or hidden notes
- Task answer files, evaluation files, or expected-output files
- Any file outside the `input/` directory that is not `environment_access.md`

If `environment_access.md` is present, use it only for the base URL and endpoint discovery. Do not treat it as a primary evidence source.

### Workflow pattern

Follow this general sequence for every task:

1. **Orient**: Read `prompt.txt`, the context payload, and the answer template schema. Identify the matter ID, the deliverable type, required top-level keys, and all enum sets.
2. **Explore schema**: Call `GET /api/schema` to understand the available tables, their columns, and relationships. This helps formulate precise SQL for the query endpoint.
3. **Confirm matter**: Call `GET /api/matters` (filtered to the target matter ID) to verify the matter exists and collect its metadata.
4. **Gather evidence**: Query the relevant GET endpoints based on the task type. When the task needs cross-table joins, aggregations, or custom filters beyond what the GET endpoints provide, use `POST /api/query` with parameterized SELECT statements. Always filter by `matter_id`.
5. **Build the answer**: Populate the JSON object field by field, strictly following the template schema:
   - Use **stable hub record IDs** (matter IDs, source IDs, event IDs, QC finding IDs, document IDs, action IDs, category codes) exactly as they appear in hub responses.
   - Apply the **enum values** from the template — never invent new statuses, types, or labels.
   - Respect all **required keys** per object and per top-level section.
   - Apply **ordering rules** as specified in the template (typically ascending by a sort key, or by priority rank with 1 as highest).
   - All numeric counts must be **whole integers**. Use `0` (not `null`) when a count field is not applicable.
   - Boolean fields use JSON `true`/`false`.
   - Date fields use `YYYY-MM-DD` format or `null`.
6. **Validate**: Before finalizing, compare the answer against the template's `required_top_level_keys` and each section's `item_required_keys`. Verify sort order and enum compliance.

### Output rules

- **Return exactly one JSON object.** No prose, commentary, markdown fences, or preamble outside the JSON.
- The JSON object must conform to the answer template provided in the task payloads.
- Follow template `ordering_rules` precisely.
- Use template `enum_choices` or `enums` for all controlled vocabulary fields.
- All counts are whole integers per `numeric_precision`.
- Stable identifiers from the hub must be used verbatim — do not generate synthetic IDs.

### Common task archetypes and evidence mapping

Based on the deliverable type in the prompt, prioritize these endpoints:

| Deliverable | Primary evidence endpoints |
|---|---|
| Gap analysis / rolling production review | `/api/subpoena-categories`, `/api/productions`, `/api/custodian-sources`, `/api/documents/search`, `/api/privilege-log`, `/api/qc-findings` |
| Retention / hold gap review | `/api/retention-events`, `/api/subpoena-categories`, `/api/custodian-sources`, `/api/documents/search` |
| Cross-system remediation dashboard | `/api/subpoena-categories`, `/api/productions`, `/api/custodian-sources`, `/api/privilege-log`, `/api/qc-findings`, `/api/retention-events`, `/api/remediation-actions` |
| Production-readiness / privilege-QC review | `/api/productions`, `/api/documents/search`, `/api/privilege-log`, `/api/qc-findings`, `/api/custodian-sources` |

For any archetype, use `POST /api/query` when you need to join tables, aggregate counts, or filter on conditions not directly exposed by a single GET endpoint.

### SQL query tips

- Always parameterize values using `?` placeholders and the `params` array. Never interpolate values directly into the SQL string.
- Filter by `matter_id` on every query to scope results to the target matter.
- When counting, use `COUNT(*)` or `COUNT(DISTINCT ...)` as appropriate, and ensure results are whole integers.
- For date-based filtering, the hub may use ISO-8601 date strings. Use `?` placeholders for date parameter values.
- If a query returns no rows, treat the result as an empty set, not an error — populate counts as `0` accordingly.
