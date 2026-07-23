# Opaque control-code inference

Several contracts require **opaque internal control codes** for the public
stable IDs listed in the case scope (focus clusters, anchored/control cases,
reference IDs, transaction/charge IDs, event IDs). These codes are intentionally
not expanded in the task materials — you infer each from the reconciled evidence
and the audit, selecting from the **allowed values enumerated in the run's
`answer_template.json`**.

**Do not copy specific code assignments from training answers.** The mapping
below describes only the *evidence dimensions* to read; the actual code value
for a given ID must be derived from that run's live records.

## Code families & prefixes

| Prefix | Family | Used for | Evidence dimensions |
|---|---|---|---|
| `IC-*` | identity | contact focus clusters, anchored/identifier cases, IDENTITY control cases | identity strength: number & agreement of source systems, `verified_flag`, cluster merge outcome (multi-row merged / single-source / contested) |
| `OR-*` | outreach | OUTREACH control cases, readiness partitions, inactive exclusion | consent state, channel usability (usable email/phone), readiness outcome, active-vs-inactive |
| `FP-*` | field provenance | FIELD_PROVENANCE control cases, focus-cluster field provenance | which source system supplied the surviving canonical field; field-level-precedence outcome |
| `RB-*` | reference policy | fuel & freight reference (alias) rows | alias resolution outcome (single recognized / ambiguous / unrecognized / mapped) |
| `SB-*` | source basis | fuel transactions & freight charges (source-decision panel) | snapshot-retention basis: authoritative retained vs duplicate dropped, source system |
| `LD-*` | ledger disposition / routing | fuel transactions & freight charges (ledger-decision panel) | reconciliation disposition: valid-clean / valid-mismatch / quarantined-unrecognized / quarantined-invalid-measure, and category outcome |
| `MS-*` | maintenance source | maintenance events (event-decision panel) | snapshot status / source system of the retained occurrence |
| `HR-*` | history route | maintenance events (event-decision panel) | validity / regression outcome: valid, rejected (bad time/odometer/labor), sequence-only regression, duplicate-retained |

## Method

For each decision-panel ID in the case scope:

1. **Gather evidence.** Pull the public row(s) behind the ID (the seed/focus
   row, the evidence_row_ids, or the transaction/charge/event/reference row).
   Apply the same reconciliation you used for the audit (authoritative
   snapshot, dedup, classification).
2. **Read the evidence signals** for that code's family (table above).
3. **Select the single allowed code** (from the contract enum) whose semantic
   meaning matches the evidence. The family prefix tells you which code set
   applies; the allowed values come from `answer_template.json`.
4. If a panel requires multiple codes per ID (e.g. an anchored case needs
   identity + outreach + field-provenance), evaluate each family independently
   against the same evidence.

## Notes

- The exact allowed code values differ per run and are listed in the contract's
  enums; do not assume a fixed vocabulary beyond the prefix families above.
- Codes are assigned **per evidence row/cluster**, not globally — two clusters
  with different identity strength take different `IC-*` codes.
- When evidence is ambiguous, prefer the code implied by the **reconciled**
  state (post-dedup, post-classification), not the raw row.
