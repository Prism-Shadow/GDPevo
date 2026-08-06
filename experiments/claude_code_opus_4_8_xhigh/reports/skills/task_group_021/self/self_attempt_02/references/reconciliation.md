# Reconciliation, normalization, and control codes

## Two deduplication modes — pick by sub-family

### A. Stable-ID reconciliation (transactions, charges, maintenance events)

Rows carry a stable business id (e.g. a transaction/charge/event id). The same
id can appear in multiple snapshots.

- One **logical record** = one distinct stable id.
- **Retain** the occurrence from the authoritative snapshot; if the id is absent
  there, retain from the next-highest-precedence snapshot that has it
  (`CERTIFIED` > `PROVISIONAL` > `STALE`, then most recent).
- `duplicate_raw_count = scoped_raw_rows − logical_records`.
- When the contract wants `duplicate_groups`: one entry per id with ≥2 raw
  occurrences — list the `snapshot_ids` it appears in (sorted, unique) and the
  `retained_snapshot_id` / `retained_event_id`.

### B. Entity resolution / clustering (contacts, people, partners)

There is no single pre-assigned entity id; you must cluster.

- Cluster rows that share **strong normalized identifiers** — normalized email,
  digits-only phone, and/or name plus a corroborating key. Follow any matching
  rule the prompt/schema states.
- A cluster with >1 member is a **merged duplicate cluster**.
- `canonical_entity_count` / `canonical_person_count` counts **all** resolved
  entities **including quarantined** ones.
- Pick a **survivor / master** row id (the contract says which id to use as the
  stable master — often a chosen public row id).
- **Focus / anchor / watchlist** items give a seed/anchor row id: resolve its
  cluster and report `member_row_ids` (deduplicated, lexicographically sorted),
  the survivor/master, canonical field values, and the per-field source system.
- **Contested clusters**: identifier cases that conflict and cannot be
  auto-merged are reported as contested (`CONTESTED_NO_AUTOMERGE`) and counted in
  `contested_identifier_cluster_count`, not silently merged.

### Field-level source precedence (mode B canonical values)

Each canonical field (name, email, phone, city, depot/region, consent, record
status) is chosen independently by a source-system precedence order (source
systems differ per task, e.g. `CRM | Compliance Master | Partner Portal` or
`HR Directory | Dispatch | Identity Registry`). Take the value from the
highest-precedence source that has a usable value for that field; fall through
when it is missing/unusable. Record which source each field came from
(`*_source_system`). Determine the precedence order from the prompt/schema/policy
— do not invent it. Typical `resolution_outcome` values:
`SINGLE_SOURCE`, `FIELD_LEVEL_PRECEDENCE_APPLIED`, `CONTESTED_NO_AUTOMERGE`,
`NO_USABLE_CONTACT`.

## Validity vs. mismatch vs. quarantine

Keep three buckets strictly distinct:

- **Valid**: passes all integrity checks and has a resolvable canonical
  category → enters normalized totals.
- **Mismatch**: expected category/class ≠ the recognized one, but the row is
  otherwise valid → **still valid, still in totals**; also listed in the
  mismatch id set and counted for exception rankings.
- **Quarantine**: unusable → **excluded from normalized totals**, listed in the
  quarantine id set. Quarantine reasons by sub-family:
  - Contacts/people: no usable canonical channel (no usable email **and** no
    usable phone).
  - Fuel/freight: description/alias resolves to **zero** categories
    (unrecognized) or **more than one** (ambiguous); nonpositive/invalid
    quantity, weight, or distance.
  - Maintenance: missing or unparsable timestamp; odometer out of valid range;
    labor negative or extreme (out of allowed range).

An **exception** (for merchant/carrier/asset rankings) is a distinct retained
logical record that is either a valid class mismatch **or** quarantined.

## Normalization

- **Category via aliases**: normalize the free-text description and match against
  `/api/reference/aliases`. Exactly one canonical match ⇒ recognized; zero ⇒
  `unrecognized`; more than one ⇒ `ambiguous`. Unrecognized and ambiguous are
  both quarantined and both belong in the "no unique recognized category" id set.
- **Units via conversions**: convert every quantity to the canonical unit
  (`L`, `KG`, `KM`, …) using `/api/reference/conversions`.
- **Currency via fx**: convert spend to the base currency (usually `USD`) using
  `/api/reference/fx`, applying the rate effective for each record's **business
  date** (rates are effective-dated — do not use a single flat rate unless the
  data has only one).
- **Contact fields**: email = trim + Unicode NFKC + lowercase; phone = digits
  only (kept as a string); name = Unicode-preserving canonical display.
- Carry full precision through all arithmetic; round **once**, at final
  aggregation, to the contract's decimals.

## Readiness / channel logic (contact sub-families)

- An entity is **readiness-eligible** only if it is **ACTIVE and retains ≥1
  usable email or phone**. Inactive entities and no-channel entities are not
  eligible.
- A channel is **ready** only when **consent is GRANTED**. A usable channel with
  non-granted consent is *blocked-consent*, not ready.
- Partition eligible entities into mutually exclusive `both / email_only /
  phone_only / not_ready` (they sum to the eligible count). For depot/region
  readiness, the disposition counts (`dispatchable`, `blocked_consent`,
  `blocked_no_contact`, `blocked_inactive`) partition the depot's total.

## Control-code inference (IC-/OR-/FP-/RB-/SB-/LD-/MS-/HR-)

The code expansions are deliberately withheld; the **allowed values live in the
current `answer_template.json` enum** — emit only those. Families observed:
identity (IC), outreach (OR), field-provenance (FP), reference-basis/policy (RB),
source-basis/retention (SB), ledger-disposition/routing (LD), maintenance-source
(MS), history-route (HR). Do not assume a prior task's value set carries over.

Procedure:

1. **Look for an authoritative dictionary first.** Check `/api/catalog/schema`,
   the reference tables, and `POST /api/query` for a table that maps codes to
   meanings or attaches a code to each record/reference. If present, use it
   directly.
2. **Otherwise infer from record state.** Each family partitions cases into as
   many buckets as it has allowed values. Determine, for each anchored/focus/
   quarantine/readiness case, the record's resolved state (its provenance, its
   identity-resolution outcome, its outreach/channel readiness, its
   retention/ledger disposition) and map like states to like codes.
3. **Use monotonic hints cautiously.** The numeric suffixes often order by
   severity/quality/confidence within a family; treat that as a hypothesis to
   verify against observed data, not a fact.
4. **Apply consistently.** Two cases in identical resolved states must receive
   the same code across the whole answer. Assign codes only from the enum, and
   only for the cases the contract asks about.
