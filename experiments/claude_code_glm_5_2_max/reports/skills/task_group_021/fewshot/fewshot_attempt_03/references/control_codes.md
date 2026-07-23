# Internal control codes

Asteria attaches opaque compact control codes to focus decisions, anchored
control cases, and decision panels. These codes are **internal identifiers
whose expansions are intentionally not supplied** in any task material.

## Families

| Family | Prefix | Domain |
|---|---|---|
| Identity | `IC-*` | Contact / partner master identity decisions. |
| Outreach | `OR-*` | Contact channel / outreach readiness. |
| Field provenance | `FP-*` | Which source system supplies a canonical field. |
| Reference policy | `RB-*` | Reference-row (alias) policy decision. |
| Source basis | `SB-*` | Source retention / basis for a transaction or charge. |
| Ledger disposition | `LD-*` | Ledger routing / disposition for a transaction or charge. |
| Maintenance source | `MS-*` | Maintenance-log source decision. |
| History route | `HR-*` | Maintenance history routing. |

The exact allowed values per family are enumerated in each task's
`answer_template.json`. Always use a value from that enum; never invent one.

## How to infer a code

For each scoped id (focus cluster, control case, decision-panel row):

1. Gather the evidence from the reconciled audit and the hub's reference data:
   the record's source system(s), alias-resolution outcome, quarantine reason,
   mismatch type, snapshot basis, consent/record status, etc.
2. Use `/api/query` and the reference endpoints to find how the hub ties each
   evidence condition to a code. The mapping is deterministic in the data —
   discover it, do not guess.
3. Select the code from the contract enum that corresponds to that evidence.
4. For control cases grouped by `control_family`, restrict the code to that
   family's prefix (e.g. `IDENTITY` → `IC-*`, `OUTREACH` → `OR-*`,
   `FIELD_PROVENANCE` → `FP-*`).

## What not to do

- Do not copy a code→id mapping from training examples or memory. Each task's
  records carry their own evidence; re-derive every code.
- Do not emit a code outside the answer_template enum for its panel.
- Do not invent expansions or human-readable meanings for the codes.
- Do not assume a family's enum is fixed across tasks — read the current
  answer_template for the allowed values.
