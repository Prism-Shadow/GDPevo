 # Investigation Review Hub Analysis Skill

 ## Purpose
 Use this skill when a task requires producing structured JSON deliverables from an Investigation Review Hub—a read-only API providing matter metadata, subpoena categories, production statistics, custodian sources, review documents, privilege logs, QC findings, retention events, and remediation actions.

 ## Core Workflow

 ### 1. Discover the Environment
 Read any task-provided `environment_access.md` or equivalent. Note the base URL, allowed GET/POST endpoints, and any required API-key headers. If no environment file is present, use `<TASK_ENV_BASE_URL>` as the base.

 Confirm connectivity and retrieve the schema:
 - `GET /` — returns service status and available business endpoints.
 - `GET /api/schema` — returns table names, column names, and column types for every table in the hub.

 ### 2. Understand the Deliverable Contract
 Every task provides an `answer_template.json` (or equivalent schema file). Read it completely before querying data. It defines:
 - **Required top-level keys** — the sections your JSON must contain.
 - **Enum choices** for every categorical field. Use only values from these enums; never invent new ones.
 - **Field types and descriptions** — including which fields accept `null` and which require `0` as a default.
 - **Ordering rules** — sort arrays by the specified key (e.g., `finding_id` ascending, `category_code` ascending, `priority_rank` ascending).
 - **Numeric precision** — all counts are whole integers.

 Pay attention to subtleties like `"third_party": "string or null"` versus fields that are always strings. Map every field you output to its exact template definition.

 ### 3. Gather All Hub Data for the Matter
 Query every relevant endpoint for the specific `matter_id` named in the task prompt. Use GET endpoints for direct lookups and `POST /api/query` with SQL for flexible access. Always include the `X-API-Key` header when required.

 Recommended query order:
 1. `GET /api/matters` — confirm the matter exists and note its metadata.
 2. `GET /api/subpoena-categories?matter_id=<id>` — list all request categories and their descriptions.
 3. `POST /api/query` with `SELECT * FROM production_stats WHERE matter_id = ?` — understand production status per category.
 4. `POST /api/query` with `SELECT * FROM custodian_sources WHERE matter_id = ?` — identify source gaps, lost devices, personal sources, and available archives.
 5. `POST /api/query` with `SELECT * FROM qc_findings WHERE matter_id = ?` — find miscoded documents, privilege miscodes, and other quality issues.
 6. `POST /api/query` with `SELECT * FROM privilege_entries WHERE matter_id = ?` — quantify privilege log gaps, over-designations, and third-party waivers.
 7. `POST /api/query` with `SELECT * FROM retention_events WHERE matter_id = ?` — identify pre-hold destruction, post-hold loss, auto-purges, system losses, and missing records.
 8. `POST /api/query` with `SELECT * FROM remediation_actions WHERE matter_id = ?` — see which records the hub itself flags as requiring remediation (this reveals the truly material issues).
 9. `POST /api/query` with `SELECT * FROM review_documents WHERE matter_id = ?` — spot-check individual documents referenced by QC findings or source exceptions.

 ### 4. Separate Material Issues from Operational Noise
 The hub contains both actionable findings and routine/noise records. Use these heuristics to filter:

 **Material (include in answer):**
 - Records with specific, detailed `notes` describing a concrete problem (e.g., "Four boxes … destroyed after hold", "One complaint email miscoded nonresponsive", "Personal iPhone erased … after subpoena issuance").
 - Records whose IDs appear as `target_ref` in non-noise `remediation_actions` (exclude actions with `action_type` of `sampling_review`, `load_file_cleanup`, or `custodian_followup` with `"description": "Routine action included as realistic operational noise"`).
 - Sources with `status` of `lost`, or with `issue_tags` containing `post_subpoena_erasure`, `collection_gap`, or `personal_device`.
 - QC findings where the `notes` field describes a specific miscoding (e.g., "miscoded_nonresponsive", "miscoded_privilege", "zero_claim_contradiction").
 - Privilege entries with `issue_type` of `incomplete_log` or `third_party_waiver` where the gap is material (large unlogged count, or explicit note about missing logs).

 **Noise (exclude from answer):**
 - Records with notes like "Routine action included as realistic operational noise", "Entry included to create similar labels across matters", "Entry creates a similar label but has no unresolved production impact", "Potential issue was remediated by archive collection", "Vendor tracker and legal hold tracker use slightly different record labels", "Privilege sample has ordinary review variance".
 - QC findings with notes like "Review manager requested re-sampling before escalation", "Finding is similar to escalated records in another matter", "Quality-control sample is noisy but not dispositive without source comparison".
 - Sources with `issue_tags` of `routine`, `scope_exception`, or `metadata_gap` where the notes indicate no production impact.
 - Actions in `remediation_actions` whose descriptions explicitly state they are routine/noise.

 ### 5. Derive Metrics Precisely from Hub Data
 Calculate every numeric metric directly from the hub records you identified as material:

 - **Count fields**: Sum `doc_count`, `volume_count`, `withheld_count`, `logged_count` across the material records only.
 - **Unlogged documents**: Compute `withheld_count - logged_count` for each material incomplete-log privilege entry, then sum.
 - **Source/event counts**: Count distinct source IDs or event IDs that are material (not total rows).
 - **Category counts**: Derive from the union of `affected_categories` or `category_impacts` across all material records.
 - **Boolean fields**: Derive from the aggregate state (e.g., `production_ready` is `false` if any category has an open gap).

 Always use whole integers. Never estimate or round.

 ### 6. Build the Answer JSON
 Assemble the answer strictly following the template:

 1. Set `matter_id` to the exact identifier from the hub.
 2. Populate each top-level array using only material records, sorted as specified.
 3. Use stable hub record IDs (`source_id`, `event_id`, `finding_id`, `entry_id`, `doc_id`, `action_id`) as keys wherever the template calls for a stable identifier.
 4. Map every categorical value to exactly one of the template's allowed enum strings.
 5. For nullable fields, use JSON `null` (not the string `"null"` and not an empty string) when no value applies.
 6. When a field is not applicable, use `0` for counts, `[]` for lists, and `null` for optional strings.
 7. For action/priority items, derive `priority_rank` from the materiality ordering: post-hold losses and privilege log gaps rank highest, followed by personal source gaps and miscodes, then archive searches and monitoring.

 ### 7. Validate Before Submitting
 - Confirm every top-level key from `required_top_level_keys` is present.
 - Confirm every item in every array has all `item_required_keys`.
 - Confirm all array elements are sorted according to `ordering_rules`.
 - Confirm every string value appears in the corresponding `enums` list.
 - Confirm all counts are non-negative integers.
 - Check that no noise records leaked into the answer.

 ## Anti-Patterns to Avoid
 - Do not inspect local files, database files, seeds, or manifests as data sources—use only the running hub API.
 - Do not use the prompt's narrative description of the client or matter when the hub provides different metadata; always prefer the hub's own `matter_id`, `name`, and `agency` values.
 - Do not include every record from the hub; filter noise aggressively.
 - Do not invent IDs, enum values, or metric counts—derive everything from hub data.
 - Do not write prose or narrative outside the JSON answer.
