# Opaque control-code panels

## Principle
- The hub exposes public stable IDs (transactions, charges, events, contact rows, reference aliases, focus clusters, control cases). The answer requires opaque internal control codes (compact codes such as `RB-17`, `IC-40`) for the IDs listed in the scope's decision panels.
- Code expansions are deliberately NOT supplied in the task materials. Infer each code from the underlying record's evidence in the hub.
- Allowed values come from THIS task's `answer_template.json` enum. Do not assume values from other tasks — always read the current template's enums.
- Emit one coded object per scoped ID, in the order/sort the template requires. Templates set `minItems`/`maxItems` equal to the scoped count — never skip an ID.

## Code families observed (illustrative — the template enum is authoritative)
- **Reference-policy** `RB-17 / RB-42 / RB-83` — fuel & freight reference rows (alias IDs `FUA-*`, `FRA-*`). Inferred from the alias row's `reference_status`/validity and the reconciled audit.
- **Source-basis** `SB-24 / SB-61 / SB-79` — fuel transactions & freight charges. Inferred from which source snapshot/system the retained occurrence came from (authoritative vs duplicate vs supplementary).
- **Ledger disposition / routing** `LD-14 / LD-31 / LD-53 / LD-72 / LD-88` — fuel transactions & freight charges. Inferred from the record's validity / mismatch / quarantine outcome and ledger routing rules.
- **Identity** `IC-25 / IC-40 / IC-70 / IC-90` — contacts. Inferred from cluster identity strength (single-source vs field-level-merged vs contested).
- **Outreach** `OR-15 / OR-35 / OR-60 / OR-80` — contacts. Inferred from channel readiness / consent / contactability outcome.
- **Field-provenance** `FP-20 / FP-55 / FP-75` — contacts. Inferred from which source system supplied the canonical field (field-level precedence).
- **Maintenance-source** `MS-12 / MS-47 / MS-86` — maintenance events. Inferred from the event's source system / snapshot.
- **History-route** `HR-19 / HR-33 / HR-74` — maintenance events. Inferred from the event's validity / regression / duplicate outcome.

## Inference method
1. For each scoped ID, fetch its full evidence from the hub: the retained raw row, its `snapshot_id` / `source_system`, and its classification outcome from Phase 3.
2. Identify the distinguishing attribute(s) the code encodes for that family (source system, snapshot status/basis, validity/mismatch/quarantine outcome, field-supplying system, readiness/consent outcome).
3. Map the attribute tuple to exactly one allowed code value from the template enum. The mapping is consistent: IDs with identical evidence receive identical codes; differing evidence may yield different codes.
4. If evidence is insufficient to decide, re-query the hub (e.g., the alias row, the snapshot row, the cluster's member rows). Do not guess and do not default to a single value.

## Do not
- Do not memorize a fixed ID→code table — codes are derived per task from current evidence.
- Do not emit a code outside the template's enum.
- Do not skip any scoped ID.
- Do not import code values from a different task's template; the enum can differ.
