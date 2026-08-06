# Control-code inference & certification status

## Control / decision code panels
Several output panels require an opaque internal code per scoped public ID. The **allowed values** and field names are declared in `answer_template.json` (as `enum`s). The human-readable meaning of each code is intentionally NOT supplied in the task materials — you infer which code applies from the ID's evidence.

### How to infer
1. For each scoped ID (reference alias, transaction/charge, event, focus cluster, control case, focus person), fetch its evidence via `POST /api/query` and the reference/contacts data.
2. Determine the ID's audit outcome:
   - which snapshot / source system it came from,
   - whether it is valid / a mismatch / quarantined, and the specific reason,
   - for contacts: identity strength, channel readiness, consent status, record status, field provenance.
3. Map that outcome onto the code enum for the panel. The mapping is consistent within a task: identical outcomes yield identical codes. Re-derive per ID; never transplant a code from another task's answer.

### Code families (allowed values live in the template)
| Family | Prefix | Typical panel |
|---|---|---|
| Reference policy | `RB-` | reference_decisions / reference_rows |
| Source basis / retention | `SB-` | transaction source_basis / freight source_retention |
| Ledger disposition / routing | `LD-` | transaction ledger_disposition / freight ledger_routing |
| Maintenance source | `MS-` | event maintenance_source_code |
| History route | `HR-` | event history_route_code |
| Identity | `IC-` | focus/anchored identity_code |
| Outreach | `OR-` | outreach_code / readiness_partition |
| Field provenance | `FP-` | field_provenance_code |

Emit one row per scoped ID, sorted by ID ascending (or by the contract's declared order). The exact allowed enum members differ per task — always read them from `answer_template.json`.

## Certification / close status
Read the certification rules from `case_scope.json`:

### Threshold + action-map style (e.g., partner onboarding)
- Compute the gate metric declared in the contract (e.g., `quarantine_rate = quarantined_rows / canonical_entities`, rounded to the declared decimals).
- Classify against `status_thresholds`:
  - metric ≤ `pass_max_*` → `PASS`
  - metric ≤ `pass_with_exceptions_max_*` → `PASS_WITH_EXCEPTIONS`
  - else → `HOLD`
- Map status → action via `status_action_map` (PASS→RELEASE, PASS_WITH_EXCEPTIONS→REVIEW_EXCEPTIONS, HOLD→BLOCK_AND_REMEDIATE).

### Gate style (e.g., maintenance odometer regression)
- A `certification_gate` declares a condition and its status/action. A triggered gate (e.g., any odometer regression) ⇒ that status/action directly.

### Default (no explicit rules)
Infer conservatively from the audit: any quarantine / invalid / regression ⇒ `HOLD` / `BLOCK_AND_REMEDIATE`; a fully clean audit ⇒ `PASS` / `RELEASE`.

The status/action pair must be one of the template's allowed enum pairs.
