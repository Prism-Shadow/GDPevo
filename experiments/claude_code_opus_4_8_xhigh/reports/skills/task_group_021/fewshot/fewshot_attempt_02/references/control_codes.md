# Internal control codes — derivation rules

Tasks ask for opaque "control codes" whose plain-language expansions are
deliberately withheld. **Each code is a deterministic label for an observable
reconciliation outcome.** You never guess: you classify the referenced rows /
reference entries with the pipeline in `reconciliation.md`, then map the
resulting scenario to the code. The exact allowed values for a given task are
enumerated in that task's `answer_template.json` — always intersect your
derivation with that enum.

The mappings below are the code *families* and the scenario each value denotes.
Code numbers are arbitrary tags (not ordered/scored). Confirm the family's value
set against the answer template; if a template exposes a value not covered here,
derive it by analogy from the same observable dimension.

## Contacts

Codes are computed **per requested case** from that case's evidence rows (a
"case" is a focus cluster, an anchored control case, a quarantine result, a
readiness partition, or an inactive exclusion). The controlling dimension
differs by code family.

### Identity code `IC-*` — identity-resolution outcome of the evidence set
| Code | Scenario |
|---|---|
| `IC-70` | Evidence rows are a genuine duplicate cluster sharing a strong identifier (normalized email/phone) that resolves to **one** entity → merged. |
| `IC-25` | Rows **share a contact identifier** (same phone/email) but are **distinct** entities (different people/names) → kept separate (shared-identifier collision). |
| `IC-90` | Multiple rows match only weakly (**same name, no corroborating shared identifier**) → cannot merge confidently; ambiguous/contested cluster. |
| `IC-40` | A **single / isolated** row with no cluster to resolve against (includes a lone quarantined row). |

Note the set-dependence: the *same* row scored alone → `IC-40`, but grouped with
same-name siblings → `IC-90`. Classify the evidence **set** you were given.

### Outreach code `OR-*` — reachability of the (canonical) entity
| Code | Scenario |
|---|---|
| `OR-35` | **Ready**: active record, has a usable email or phone, consent GRANTED. |
| `OR-80` | **Consent-blocked**: active with usable contact, but consent not GRANTED (PENDING/DENIED). This is the "not_ready" state for readiness-eligible entities. |
| `OR-60` | **No usable contact**: active but no usable email and no usable phone (a contact-quarantine row). |
| `OR-15` | **Inactive**: record excluded because its status is not active. |

Readiness rule (used for `channel_readiness` counts and the readiness
partition): an entity is *readiness-eligible* only when active **and** retaining
at least one usable email or phone. A channel counts as "ready" only when
consent is GRANTED. Partition eligible entities into both / email_only /
phone_only / not_ready (usable channels present but no consent).

### Field-provenance code `FP-*` — how the canonical field values were sourced
| Code | Scenario |
|---|---|
| `FP-55` | Canonical fields drawn from **multiple** source systems via field-level precedence (a real cross-source merge). |
| `FP-20` | Canonical fields come from a **single** source record (no cross-source blending). |
| `FP-75` | Row is **quarantined** — no usable canonical values / no provenance to assign. |

## Fuel & Freight

### Reference-row / reference-policy code `RB-*` — status of a reference alias
| Code | Scenario |
|---|---|
| `RB-42` | `ACTIVE` alias whose `alias_text` is **unambiguous** (maps to exactly one canonical value; validity window covers the cutoff). |
| `RB-17` | Alias whose `alias_text` **collides** — the same text maps to two different canonical values (ambiguous). Both the active and the superseded/inactive colliding rows get this. |
| `RB-83` | `PROVISIONAL` reference alias (not yet authoritative). |

### Source-basis / source-retention code `SB-*` — snapshot provenance of the retained record
| Code | Scenario |
|---|---|
| `SB-24` | The logical record exists in the **CERTIFIED snapshot only**. |
| `SB-61` | The record appears in **both** snapshots (a de-duplicated pair; the certified copy is retained). |
| `SB-79` | The record exists in the **PROVISIONAL snapshot only**. |

### Ledger disposition / routing code `LD-*` — how a transaction/charge is dispositioned
| Code | Scenario |
|---|---|
| `LD-72` | Valid, recognized class **matches** the expected class (clean accept). |
| `LD-31` | Valid but recognized class **differs** from expected (accepted mismatch). |
| `LD-53` | Quarantined for an **invalid physical measure** (non-positive/absent quantity, weight, or distance). |
| `LD-14` | Quarantined because the description/alias is **unrecognized**. |
| `LD-88` | Quarantined because the description/alias is **ambiguous**. |

Quarantine dispositions dominate: a row that is both a class mismatch **and**
has an invalid measure is `LD-53`, not `LD-31`.

## Maintenance

### Maintenance-source code `MS-*` — snapshot provenance (parallels `SB-*`)
| Code | Scenario |
|---|---|
| `MS-12` | Event in the **CERTIFIED snapshot only**. |
| `MS-47` | Event present in **both** snapshots (duplicate; certified retained). |
| `MS-86` | Event in the **PROVISIONAL snapshot only**. |

### History-route code `HR-*` — the event's route through the reconstructed history
| Code | Scenario |
|---|---|
| `HR-33` | Valid event, accepted into the corrected history. |
| `HR-74` | Invalid/rejected event (fails an integrity check: missing/invalid timestamp, invalid odometer, negative/extreme labor). |
| `HR-19` | An **odometer-regression** event (its odometer reading goes backwards vs the asset's prior reliable reading). |

## Method summary
1. Reconcile the collection (dedup across snapshots, retain certified, classify
   each logical record: valid / mismatch / quarantine-reason; for contacts:
   cluster + resolve + assess reachability).
2. For each requested code, read the referenced rows/aliases and identify the
   **observable dimension** the family keys on (snapshot membership for SB/MS;
   reference status+collision for RB; disposition for LD; identity relationship
   for IC; reachability for OR; provenance breadth for FP; integrity route for
   HR).
3. Emit the matching code, constrained to the `answer_template` enum.
