---
name: asteria-fleet-reconciliation
description: Use this skill for Asteria Fleet Data Quality Hub tasks that ask Codex to audit, reconcile, certify, normalize, or close fleet contact, fuel, freight, or maintenance collections and return a strict JSON answer from payloads/case_scope.json and payloads/answer_template.json. Use it whenever the prompt mentions Asteria, Fleet Data Quality Hub, source snapshots, aliases, unit or FX normalization, duplicate source records, compact control codes, readiness, quarantine, certification, or ledger close decisions.
---

# Asteria Fleet Reconciliation

This skill solves Asteria Fleet Data Quality Hub reconciliation tasks. Treat each task as a data audit, not a writing task: collect the full scoped data, apply the task's answer contract exactly, derive every count and code from the live records, and return only the requested JSON object.

## First Moves

1. Read the task prompt, `payloads/case_scope.json`, `payloads/answer_template.json`, and the task's `environment_access.md`.
2. Extract the collection id, cutoff or `as_of`, population scope, requested focus ids or decision panels, required top-level keys, allowed code enums, ordering rules, and numeric precision.
3. Identify the collection family from the prompt, catalog, or endpoint names:
   - contacts: partner onboarding, field service roster, dealer, warranty, or other contact master tasks
   - fuel: fuel purchases or charging transactions
   - freight: carrier invoice charges or accrual close tasks
   - maintenance: maintenance events, work orders, odometer history, or reliability history
4. Read the domain reference that applies before computing:
   - contacts: `references/contact_rules.md`
   - fuel or freight: `references/ledger_rules.md`
   - maintenance: `references/maintenance_rules.md`
   - compact codes: `references/codes.md`
   - final validation: `references/final_checks.md`

Do not reuse prior answer values or memorize specific ids from examples. The reusable pattern is the reconciliation method, the code semantics, and the contract discipline.

## Data Collection

Use the running hub described by `environment_access.md`. Direct GET endpoints are usually enough and are safer than ad hoc SQL:

```bash
python /path/to/skill/scripts/asteria_collect.py \
  --case-dir /path/to/task/input \
  --env-file /path/to/task/environment_access.md \
  --out /tmp/asteria-work
```

If the task layout differs, pass `--base-url`, `--collection`, and `--family` explicitly. The direct collection endpoints use `collection=<collection_id>` as the filter, not `collection_id=<collection_id>`. Page every endpoint until the returned `total` is satisfied; several collections are larger than one page.

Fetch at least:

- `/api/catalog/collections` and `/api/catalog/schema`
- `/api/source-snapshots?collection=...`
- the family data endpoint (`/api/contacts`, `/api/transactions/fuel`, `/api/transactions/freight`, or `/api/maintenance/events`)
- `/api/reference/aliases` for fuel/freight domains
- `/api/reference/conversions` for needed unit kinds
- `/api/reference/fx` when money must be normalized

Use `/api/query` only when the current task's access note gives a working credential. Even then, cross-check query results against direct endpoint totals for the scoped collection.

## Shared Reconciliation Rules

Use all raw rows in scope for raw-row counts. Build retained logical records separately:

- For contacts, logical entities are resolved people or partner contacts. Multi-source clusters are not the same as cross-snapshot duplicates.
- For fuel, the logical id is `transaction_id`.
- For freight, the logical id is `charge_id`.
- For maintenance, the logical id is `event_id` or the explicit logical event id named by the template.

For fuel, freight, and maintenance cross-snapshot duplicates, group rows by logical id. Retain the row from the highest-precedence snapshot status: `CERTIFIED` before `PROVISIONAL` before `STALE`. Break ties with later business update, then later ingestion, then stable id order. Report duplicate groups with sorted snapshot ids and the retained snapshot id. Duplicate raw count is raw rows minus logical ids unless the template defines a different duplicate measure.

Use source snapshot metadata to identify the authoritative snapshot. Prefer the certified snapshot for the collection and cutoff/as-of period. Authoritative row count comes from snapshot metadata when the contract asks for it; scoped raw row count comes from all fetched rows in the scoped collection.

## Work Style

Make the computation reproducible. For non-trivial counts, write small local scripts or notebooks in the task workspace that:

- load the fetched JSON files
- normalize strings, phone digits, units, and money deterministically
- produce intermediate tables for retained rows, quarantines, mismatches, focus panels, rankings, and totals
- validate required ordering and count reconciliations

Keep unrounded numeric work internally and round only at the final field precision. Use the answer template's names and no extra keys. If a template is descriptive rather than JSON Schema, still enforce its required keys, lengths, ordering, and enum values.

## Final Output

Return exactly one JSON object and no Markdown. Before finalizing, run the checks in `references/final_checks.md`.
