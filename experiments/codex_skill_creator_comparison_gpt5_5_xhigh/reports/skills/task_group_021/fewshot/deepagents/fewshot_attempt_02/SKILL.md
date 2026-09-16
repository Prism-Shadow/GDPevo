---
name: asteria-dq-auditor
description: Reconcile Asteria Fleet Data Quality Hub collections and produce JSON audit or certification answers for contact master, dispatch roster, fuel ledger, freight accrual, and maintenance history tasks using case_scope and answer_template payloads, hub endpoints, source snapshots, alias references, unit and FX normalization, survivor selection, compact control codes, and release decisions.
---

# Asteria DQ Auditor

## Overview

Use this skill to solve Asteria Fleet Data Quality Hub reconciliation tasks. The goal is to derive the requested JSON answer from the task prompt, `payloads/case_scope.json`, `payloads/answer_template.json`, `environment_access.md`, and the hub's public read-only data.

## Workflow

1. Read the task prompt, `case_scope.json`, `answer_template.json`, and `environment_access.md`.
2. Identify the collection family from the prompt/catalog: contacts, fuel, freight, or maintenance.
3. Fetch all records for the scoped collection with pagination. Use `collection=<collection_id>` for collection endpoints.
4. Fetch source snapshots and all needed reference tables before computing metrics.
5. Apply the rules in [references/reconciliation.md](references/reconciliation.md).
6. Fill only the fields required by the answer template, preserving every ordering rule.
7. Validate the final response as strict JSON with no commentary.

## Helper Script

Use [scripts/asteria_audit.py](scripts/asteria_audit.py) to fetch and classify reusable intermediate data. Run it from the task workspace so it can read `environment_access.md` by default:

```bash
python skill/scripts/asteria_audit.py classify-ledger --family fuel --collection "$COLLECTION_ID" > fuel_classified.json
python skill/scripts/asteria_audit.py classify-ledger --family freight --collection "$COLLECTION_ID" > freight_classified.json
python skill/scripts/asteria_audit.py classify-maintenance --collection "$COLLECTION_ID" > maintenance_classified.json
python skill/scripts/asteria_audit.py classify-contacts --collection "$COLLECTION_ID" > contacts_classified.json
```

Use `fetch` when you need raw records for manual checks:

```bash
python skill/scripts/asteria_audit.py fetch --family contacts --collection "$COLLECTION_ID" > raw_contacts.json
```

The script emits classified intermediate records, not final answers. Map its output into the current answer template and recompute any task-specific ranking, focus panel, threshold, or status field required by `case_scope.json`.

## Decision Rules

- Use source snapshots to determine raw counts, authoritative snapshot IDs, duplicate occurrences, and retained records.
- For fuel and freight, recognize categories/classes from active, date-effective aliases using longest non-overlapping phrase matches. Quarantine only unresolved aliases or invalid physical measures; valid mismatches still enter normalized totals.
- For contacts, merge by strong contact identifiers, select canonical fields by field-level source precedence, and keep no-contact rows as quarantine singletons.
- For maintenance, reject malformed retained events first, then detect odometer regressions within each asset's retained chronological history.
- Use the compact code mappings in the reference file. Do not invent code meanings beyond the observed condition-to-code mappings.

## Final JSON

Return one JSON object conforming exactly to `payloads/answer_template.json`. Sort every list by the contract's ordering rule, use stable public IDs, round numeric fields only as specified, and omit all Markdown or explanatory text.
