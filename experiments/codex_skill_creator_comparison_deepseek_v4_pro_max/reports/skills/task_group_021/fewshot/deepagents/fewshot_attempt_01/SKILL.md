---
name: asteria-data-quality-hub
description: "Reconcile, audit, and certify data-quality records from the Asteria Fleet Data Quality Hub REST API (contacts, fuel, freight, maintenance, and roster collections). Use when the task mentions the Asteria Fleet Data Quality Hub, a task-environment base URL with endpoints such as /api/catalog/collections, /api/catalog/schema, /api/contacts, /api/transactions/fuel, /api/transactions/freight, /api/maintenance/events, /api/reference/aliases, /api/reference/conversions, /api/reference/fx, /api/source-snapshots, or /api/query, or any Asteria Fleet certification, audit, reconciliation, or readiness workflow."
license: MIT
compatibility: designed for deepagents-code
allowed-tools:
  - shell_command
---

# Asteria Fleet Data Quality Hub

Certify data-quality records served by a shared REST API. Tasks always supply
a runtime base URL in `environment_access.md`. Every certification follows the
same pipeline:

1. **Discover** the target collection and schema via
   `GET /api/catalog/collections` and `GET /api/catalog/schema`.
2. **Reconcile sources** via `GET /api/source-snapshots`. The `-certified`
   snapshot is always the authoritative source; `-provisional` snapshots are
   supplementary.
3. **Load records** via the domain endpoint and via `POST /api/query` for
   filtered or aggregated data.
4. **Classify** every logical record. Quarantined records are excluded from
   normalized totals; mismatches remain in totals but are flagged.
5. **Assign opaque control codes** (IC-*, FP-*, OR-*, RB-*, SB-*, LD-*, MS-*,
   HR-*) from the code families documented in
   [code_families.md](references/code_families.md).
6. **Apply certification gates** from the case scope. Common outcomes: `PASS`
   / `RELEASE`, `PASS_WITH_EXCEPTIONS` / `REVIEW_EXCEPTIONS`, `HOLD` /
   `BLOCK_AND_REMEDIATE`.
7. **Produce JSON** matching the supplied answer template. Follow every
   ordering rule. Use only stable IDs present in the API responses.

## Snapshot reconciliation

- The `-certified` snapshot is always authoritative; retain its copy when a
  record appears in both snapshots.
- Raw row count = sum across all snapshots. Logical count = after deduplication.
  Duplicate count = raw minus logical.
- Report the certified snapshot ID in every `authoritative_snapshot_id` field.

## Numeric precision

- Currency (USD), volume (L), weight (KG), distance (KM): 2 decimal places.
- Rates (quarantine_rate): 4 decimal places.
- Counts: exact integers. Phone: digits-only. Email: Unicode NFKC lowercase.

## References

- [api.md](references/api.md) — Endpoint reference, response shapes, query syntax.
- [code_families.md](references/code_families.md) — All opaque control codes.
- [workflow.md](references/workflow.md) — Domain-specific rules and gates.
