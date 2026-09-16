---
name: asteria-dq-hub
description: "Audit, reconcile, and certify domain data collections against the Asteria Fleet Data Quality Hub REST API. Use when a task references the Asteria Fleet Data Quality Hub at the TASK_ENV_BASE_URL placeholder, involves reconciling overlapping source snapshots, detecting data-quality issues (mismatches, unrecognized entries, ambiguities, invalid measures), or assigning opaque internal control codes (IC-*, OR-*, FP-*, RB-*, SB-*, LD-*, MS-*, HR-*). Use when a task requires producing a structured certification or reconciliation JSON answer conforming to a supplied answer_template.json."
license: MIT
compatibility: designed for deepagents-code
---

# Asteria Fleet Data Quality Hub Audit and Certification

## Overview

This skill covers auditing and certifying domain data collections served by the Asteria Fleet Data Quality Hub, a read-only REST API that exposes contact records, financial transactions, maintenance events, reference tables, and snapshot metadata. Every task follows a shared pipeline: connect to the hub, survey the collection catalog and schema, resolve authoritative snapshots, reconcile overlapping records, detect and classify quality issues, normalize measures and currencies, derive opaque control codes from reference data, and produce a structured certification JSON.

## Connection

The hub base URL is always injected as the TASK_ENV_BASE_URL placeholder. Substitute with the value from environment_access.md. All endpoints are unauthenticated GET except /api/query, which requires a credential from environment_access.md. Use the credential as a Bearer token in the Authorization header for POST requests to /api/query.

## Available Endpoints

| Endpoint | Method | Purpose |
|---|---|---|
| /api/catalog/collections | GET | List all collections with family, source systems, time bounds, approximate record counts |
| /api/catalog/schema | GET | Field definitions for every logical view |
| /api/contacts | GET | Raw contact rows for a collection. Params: collection_id, limit, offset |
| /api/transactions/fuel | GET | Raw fuel transaction rows. Params: collection_id, limit, offset |
| /api/transactions/freight | GET | Raw freight charge rows. Params: collection_id, limit, offset |
| /api/maintenance/events | GET | Raw maintenance event rows. Params: collection_id, limit, offset |
| /api/reference/aliases | GET | Text-to-canonical-value mappings. Param: domain |
| /api/reference/conversions | GET | Unit conversion factors. Param: kind (volume, distance, weight) |
| /api/reference/fx | GET | Daily FX rates with rate_status |
| /api/source-snapshots | GET | Snapshot metadata. Param: collection_id |
| /api/query | POST | Run arbitrary SQL. Bearer auth. Body: {"collection_id":"...","sql":"...","limit":N} |

Paginate large collections with limit and offset on parameterized endpoints, or use /api/query SQL for filtering, joins, and grouping.

## General Audit Pipeline

Every audit task follows this sequence:

1. **Read the case scope** (case_scope.json): extract collection_id, business_cutoff/cutoff_at/as_of, focus IDs, decision-panel IDs, and certification thresholds.
2. **Query the catalog**: GET /api/catalog/collections to confirm the collection exists and identify its source systems.
3. **Load the schema**: GET /api/catalog/schema to understand field meanings for the relevant logical view.
4. **Resolve snapshots**: Query /api/source-snapshots filtered to the collection. Pick the authoritative snapshot: prefer snapshot_status=CERTIFIED whose business_cutoff is on or after the task cutoff. Fall back to the newest PROVISIONAL snapshot. Record authoritative snapshot_id, snapshot_status, and row_count.
5. **Fetch all data**: Retrieve all rows from the relevant domain endpoint across all snapshots for the collection. When a logical key appears in multiple snapshots, retain the row from the authoritative snapshot and count the others as duplicates.
6. **Detect quality issues**: See [references/data-quality-rules.md](references/data-quality-rules.md) for domain-specific rules.
7. **Normalize measures**: Convert volumes, distances, weights to canonical units using /api/reference/conversions. Convert non-USD amounts to USD using /api/reference/fx with rate_status=CERTIFIED rates for the relevant date. Round to the precision declared in the case scope (typically 2 decimal places).
8. **Derive control codes**: For every public stable ID in the case scope decision panels, cross-reference the hub reference tables and snapshot metadata. Map to the allowed code enumerations in the answer template. See [references/control-codes.md](references/control-codes.md).
9. **Apply thresholds and produce answer**: Compare quality rates to case-scope thresholds, map to status/action enumerations, and write one JSON object matching the answer template exactly. All ID lists must be sorted lexicographically unless the template specifies a different ordering.

## Reference Data Loading

Always load reference tables relevant to the task domain before processing data:

- **Aliases**: Filter by domain (fuel, service_class, event_type). Use rows with reference_status=ACTIVE for canonical matching. Retain all statuses when deriving codes for policy decision panels.
- **Conversions**: Filter by kind (volume, distance, weight). Use the factor from from_unit to to_unit.
- **FX rates**: Filter to rate_status=CERTIFIED and match rate_date to the transaction date.

## Resources

- [references/data-quality-rules.md](references/data-quality-rules.md) -- Detailed quality detection rules per domain
- [references/control-codes.md](references/control-codes.md) -- Code derivation methodology for all code families
