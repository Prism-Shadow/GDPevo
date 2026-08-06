# Opaque control codes — decode table

Tasks ask you to attach compact "control codes" to scoped ids. Their expansions are
deliberately withheld from the task materials, but they are **not random**: each code
family encodes one structural dimension of the reconciled record, and the mapping is
**stable across every task in this family**. The tables below were reverse-engineered
from the hub's own records (join a coded id back to its reconciled attributes and the
code falls out). Derive each code from the reconciled data — do not invent, and do not
carry values between tasks by id. When unsure, corroborate against a scoped case whose
classification is unambiguous (a clean cross-source merge, a known quarantine row).

The answer_template's `enum` for each field tells you which family applies.

## Source-basis / snapshot-membership — where the retained occurrence lives

Same semantics, family-specific labels. Determine which snapshot(s) a logical id
appears in:

| meaning | fuel/freight (`SB`) | maintenance (`MS`) |
|---|---|---|
| present only in the **certified/authoritative** snapshot | `SB-24` | `MS-12` |
| present only in the **provisional** (non-authoritative) snapshot | `SB-79` | `MS-86` |
| present in **both** snapshots (cross-snapshot duplicate; retained = certified) | `SB-61` | `MS-47` |

## Disposition / routing — the record's audit outcome

### Ledger disposition `LD-*` (fuel/freight, per transaction/charge)

| record outcome | code |
|---|---|
| valid, recognized category **matches** expected (clean) | `LD-72` |
| valid but recognized category **mismatches** expected | `LD-31` |
| quarantined — **unrecognized** (zero recognized category) | `LD-14` |
| quarantined — **ambiguous** (multiple recognized categories) | `LD-88` |
| quarantined — **invalid physical measure** (non-positive quantity/weight/distance) | `LD-53` |

### History route `HR-*` (maintenance, per event)

| event outcome | code |
|---|---|
| valid / clean (retained into corrected history) | `HR-33` |
| rejected — in `invalid_event_ids` (bad time / odometer / labor) | `HR-74` |
| odometer regression (in `regression_event_ids`) | `HR-19` |

### Reference-alias decision `RB-*` (fuel/freight, per scoped alias id)

Judged on `v_reference_aliases` for that alias at the cutoff:

| alias state at cutoff | code |
|---|---|
| `ACTIVE` and effective (`valid_from <= cutoff <= valid_to`) | `RB-42` |
| out of window / not currently usable — `INACTIVE`, expired, or `valid_from` after cutoff | `RB-17` |
| `PROVISIONAL` status | `RB-83` |

## Contacts control families — identity / outreach / field-provenance

`control_family` (when the scope states it) selects the family. The code reflects the
character of the **evidence set** supplied for that case, evaluated against the
reconciled clusters.

### Identity `IC-*` — how the evidence resolves as an identity

| evidence character | code |
|---|---|
| clean cross-source duplicate set → **merged** into one canonical person | `IC-70` |
| same-name / same-entity rows that are duplicates but **conflict → not auto-merged** (e.g. same name, differing contact; same-source repeats) | `IC-90` |
| rows tied by a **shared contact identifier across different people** (helpdesk/shared-line collision) | `IC-25` |
| a single **unresolved / quarantined** row (no usable contact, no cluster, no collision) | `IC-40` |

### Outreach `OR-*` — dispatch/outreach readiness of the entity

| entity state | code |
|---|---|
| ACTIVE, has a usable channel, consent **GRANTED** → reachable/dispatchable | `OR-35` |
| ACTIVE, has a usable channel, consent **not granted** → blocked-consent | `OR-80` |
| **INACTIVE** entity (readiness exclusion) | `OR-15` |
| **no usable contact channel** (quarantine) | `OR-60` |

For a readiness partition: both / email_only / phone_only all map to `OR-35`
(reachable); not_ready maps to `OR-80`.

### Field provenance `FP-*` — how the canonical fields were assembled

| provenance | code |
|---|---|
| canonical built by **cross-source field-level precedence** (a real merge of the same entity across ≥2 systems) | `FP-55` |
| **no field-level merge** applied — single-source record, or an evidence set not merged into one entity | `FP-20` |
| **quarantined** (no usable field provenance / no usable contact) | `FP-75` |

## Runtime derivation recipe

1. Read the field's `enum` to pick the family/dimension.
2. For SB/MS: query the snapshots a logical id appears in.
3. For LD/HR/RB: compute the record's disposition through the pipeline, then map.
4. For IC/OR/FP: for each scoped case, take its `evidence_row_ids` (or seed rows),
   reconcile them, and classify the resulting cluster/entity per the tables above.
5. Sanity-check: pick one scoped case whose outcome is obvious and confirm the code it
   should get matches the table before trusting the rest.
