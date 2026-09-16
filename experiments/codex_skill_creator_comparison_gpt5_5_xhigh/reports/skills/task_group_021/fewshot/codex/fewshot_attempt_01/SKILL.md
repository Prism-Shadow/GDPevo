---
name: asteria-hub-reconciliation
description: Reconcile Asteria Fleet Data Quality Hub audit and certification tasks and return schema-valid JSON. Use when a task provides TASK_ENV_BASE_URL plus environment_access.md, payloads/case_scope.json, and payloads/answer_template.json for contact or roster readiness, fuel or freight transaction normalization, maintenance history integrity, source snapshots, aliases, conversions, FX, duplicate records, quarantines, rankings, status decisions, or opaque Asteria control-code panels.
---

# Asteria Hub Reconciliation

## Required Workflow

1. Read the task prompt, `payloads/case_scope.json`, `payloads/answer_template.json`, and `environment_access.md`. Use `environment_access.md` only for the base URL, credentials, and query-interface details needed to access the running hub.
2. Read the hub catalog, schema, source snapshots, and the domain records named by the prompt. Use `/api/query` when endpoint pages are large, when joins are needed, or when source rows must be filtered by collection and cutoff.
3. Build a local working table with every in-scope raw row. Keep public stable IDs, source system, snapshot ID, business time, update time, status, aliases, units, currency, and all evidence fields needed for the answer contract.
4. Select the authoritative snapshot as of the business cutoff, then collapse overlapping rows by their logical business ID or identity cluster. Retain the authoritative/certified occurrence when duplicates cross snapshots, and report all duplicate groups required by the contract.
5. Apply the domain rules in [references/reconciliation_playbook.md](references/reconciliation_playbook.md). Compute all counts from the retained logical records, excluding quarantined records only where the prompt says normalized totals must exclude them.
6. Fill every scoped focus, ranking, watchlist, and decision-panel entry from live hub evidence. Do not reuse example IDs, counts, names, or answer rows from prior tasks.
7. Emit exactly one JSON object matching the supplied answer contract. Sort arrays and round numbers exactly as the contract or case scope requires. Run `scripts/contract_lint.py` as a final shape check when possible.

## Helper Scripts

- `scripts/hub_dump.py`: fetch paginated hub endpoints or submit a read-only query with credentials supplied from `environment_access.md`.
- `scripts/contract_lint.py`: lightweight stdlib-only JSON contract checker for required keys, extra keys, enums, basic types, array bounds, uniqueness, and simple patterns.

Use the scripts as helpers, not as substitutes for reading the schema and reasoning from the records. If a script's generic pagination or contract checks do not match the live hub or custom template, inspect the response manually and adapt the solve in the workspace, not inside this skill.
