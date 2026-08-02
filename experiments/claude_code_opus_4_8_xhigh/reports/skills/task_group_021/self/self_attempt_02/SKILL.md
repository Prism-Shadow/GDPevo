---
name: asteria-fleet-dq-certification
description: >-
  Use when a task asks you to audit, reconcile, or certify data from the
  "Asteria Fleet Data Quality Hub" (a read-only HTTP API given via
  environment_access.md) and return a single strict JSON object that matches a
  supplied answer_template.json for a population defined in a case_scope.json.
  Covers the whole Asteria family: partner/contact master certification,
  field-service contact-readiness, fuel/freight transaction normalization &
  accrual close, and maintenance-log integrity. Trigger cues: "Asteria Fleet
  Data Quality Hub", case_scope.json + answer_template.json payloads, a
  <TASK_ENV_BASE_URL> + Bearer token, "reconcile overlapping source records as
  of the business cutoff", authoritative source snapshot, quarantine, canonical
  entity, duplicate cluster, normalized totals, focus clusters / focus people /
  focus assets, opaque control codes (IC-/OR-/FP-/RB-/SB-/LD-/MS-/HR-),
  certification / reconciliation / close status + next action.
---

# Asteria Fleet Data-Quality Hub — reconciliation & certification

## What this family of task is

Every task in this family gives you the same three things and asks for one JSON
answer:

1. **`prompt.txt`** — the business framing and the narrative rules (which
   endpoints matter, what counts as an exception, tie-break wording, "do not
   include quarantined rows in totals", etc.). **Read it as normative** — it
   frequently states the decisive rule (e.g. "a channel is ready only when
   consent is granted", "quarantined charges do not enter normalized totals").
2. **`payloads/case_scope.json`** — the scope: `collection_id`, a business
   **cutoff / `as_of` / business_period**, the **focus / anchor / watchlist**
   items you must decide individually, ranking limits & sort/tie-break policy,
   and any **thresholds / gates** and **status→action map**.
3. **`payloads/answer_template.json`** — the **output contract**. It is either a
   JSON Schema (draft 2020-12) *or* a custom `field_contract` object. It is the
   single source of truth for the shape, required keys, `additionalProperties:
   false`, allowed **enum values** (including every allowed control-code value),
   array lengths, ordering, uniqueness, and numeric precision.

Runtime connection details (base URL, `AUTHORIZATION: Bearer …`, and the exact
list of permitted endpoints) come **only** from `environment_access.md`.

The job is always: **discover → select authoritative source → page all rows →
reconcile duplicates → classify validity / quarantine → normalize → compute
metrics, focus decisions, rollups & rankings → assign control codes → decide
status & action → emit one strict JSON object with no prose.**

The concrete numbers, IDs, and code values differ per task — **never carry a
value from one task into another**. Derive everything from the live hub for the
scope you were given.

## Operating rules (do these in order)

1. **Read all three inputs before calling anything.** Extract from
   `case_scope.json`: the collection id, the cutoff/`as_of`/period, every focus /
   anchor / watchlist / control-case id (with its seed/evidence row ids and the
   *exact* order they must be reported in), ranking limit + primary sort + tie
   breaks, thresholds, gate conditions, and the status→action map. Then read
   `answer_template.json` and list every required key, enum set, array
   length/`minItems`/`maxItems`, ordering rule, uniqueness rule, and rounding
   precision. Build your output skeleton from that list.

2. **Connect read-only.** Take the base URL and bearer token from
   `environment_access.md`; send the `AUTHORIZATION` header on every request.
   Use **only** the endpoints listed there. This hub is read-only — never
   attempt a write; `POST /api/query` is a read/query interface, not a mutation.
   See `references/hub-access.md`.

3. **Discover the model.** `GET /api/catalog/collections` (confirm the scoped
   collection) and `GET /api/catalog/schema` (learn field names, types, which
   field is the *business date*, which fields are stable IDs, how snapshots and
   the query interface are shaped, and whether a code/enum dictionary is
   exposed). Do not assume field names — read them.

4. **Select the authoritative snapshot.** `GET /api/source-snapshots`. Pick the
   authoritative snapshot for the collection as of the cutoff/`as_of`: prefer
   `CERTIFIED` over `PROVISIONAL` over `STALE`, and among those the latest
   snapshot effective **≤** the cutoff. Report its id (and status where the
   contract asks). Overlapping logical records are resolved in its favour
   (details in `references/reconciliation.md`).

5. **Fetch the full population, paginated.** The collection is larger than one
   page — loop until every page is retrieved (follow the cursor / page param;
   `POST /api/query` may aggregate or page more efficiently). Filter to the
   scoped collection and to rows whose **business date ≤ cutoff** (use `as_of` /
   `business_period` as the contract dictates). Also fetch the reference tables
   you need: `/api/reference/aliases`, `/api/reference/conversions`,
   `/api/reference/fx`. Confirm your row counts against a `POST /api/query`
   count when possible.

6. **Reconcile duplicates → logical entities.** Use the right mode:
   - *Stable-ID reconciliation* (transactions, maintenance events, charges): the
     same stable id appearing in multiple snapshots is one logical record; keep
     the occurrence from the authoritative snapshot. `duplicate_raw_count =
     raw_rows − logical_records`.
   - *Entity resolution / clustering* (contacts, people, partners): cluster rows
     that share strong normalized identifiers (email, phone digits, name+key),
     pick a survivor/master, and set each canonical field by **field-level
     source-system precedence**. `canonical_entity_count` **includes**
     quarantined entities.
   See `references/reconciliation.md`.

7. **Classify validity / quarantine.** Apply the quarantine conditions for the
   sub-family (no usable contact channel; unrecognized/ambiguous category;
   nonpositive/invalid quantity, weight, or distance; missing/invalid timestamp;
   invalid odometer; negative/extreme labor; …). **A category/class *mismatch*
   is still valid and stays in normalized totals; only *quarantined* rows are
   excluded.** Keep these two buckets strictly separate.

8. **Normalize.** Map free-text → canonical category via aliases (exactly one
   match required; 0 → unrecognized, >1 → ambiguous — both quarantine). Convert
   units to the canonical unit via conversions and currency to the base currency
   via fx, using the factor/rate applicable to each record's **business date**.
   Normalize contact fields (NFKC-trim-lowercase email, digits-only phone,
   Unicode-preserving name). Carry full precision; round **only** at final
   aggregation to the contract's decimals.

9. **Compute the reported artefacts** exactly as the contract names them:
   summary counts, per-focus/anchor decisions (membership, survivor/master,
   canonical values, source systems), quarantine/mismatch id sets, readiness /
   channel partitions, region/depot rollups (one row per represented value),
   and rankings (apply the primary sort, then the listed tie-breaks, then the
   limit).

10. **Assign control codes.** The opaque codes (IC-/OR-/FP-/RB-/SB-/LD-/MS-/HR-)
    have their expansions withheld — infer each family's meaning from the data
    and apply it **consistently** to every case in that family. Only ever emit
    values from the current template's enum. See the inference procedure in
    `references/reconciliation.md`.

11. **Decide status & action.** Compute `quarantine_rate = quarantine_count /
    canonical_entity_count`, rounded to the contract's decimals. Apply
    `status_thresholds` from the case scope (PASS ≤ pass_max; PASS_WITH_EXCEPTIONS
    ≤ pass_with_exceptions_max; else HOLD). **Hard gates override thresholds** —
    if a gate condition holds (e.g. odometer regression present), force the gate
    status/action. Map status→action via the case scope's map, or the standard
    PASS→RELEASE / PASS_WITH_EXCEPTIONS→REVIEW_EXCEPTIONS /
    HOLD→BLOCK_AND_REMEDIATE. See `references/output-contract.md`.

12. **Emit one JSON object, validate, stop.** Output *only* the JSON — no
    Markdown, no commentary. Run the pre-submit checklist in
    `references/output-contract.md` (keys, enums, lengths, ordering, uniqueness,
    rounding, `additionalProperties:false`) before you finish.

## Determinism

Everything must be reproducible from the hub state as of the cutoff. When a rule
is genuinely ambiguous, resolve it from `prompt.txt` first, then the schema, then
the most conservative reading — and apply the same choice everywhere. Do not
introduce randomness or wall-clock time into any decision.

## References

- `references/hub-access.md` — endpoints, auth, snapshots, pagination, the query
  interface.
- `references/reconciliation.md` — dedup modes, validity/quarantine per
  sub-family, normalization (aliases/conversions/fx), canonical-field precedence,
  readiness logic, and the control-code inference procedure.
- `references/output-contract.md` — count definitions, ordering/uniqueness,
  rounding, thresholds/gates → status/action, and the pre-submit checklist.
