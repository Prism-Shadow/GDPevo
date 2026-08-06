---
name: asteria-fleet-dq-certification
description: Audit and certify an Asteria Fleet Data Quality Hub collection — reconcile overlapping source snapshots as of a business cutoff, normalize units/currency, quarantine invalid records, classify expected-vs-actual mismatches, infer opaque internal control codes, and emit one JSON object conforming exactly to the run's answer contract.
---

# Asteria Fleet Data Quality Hub — collection audit & certification

## When to use

Use this skill when a task asks you to audit / reconcile / certify a business
collection served by the **Asteria Fleet Data Quality Hub** (a read-only HTTP
API) and return a single JSON object matching an `answer_template.json` /
answer contract. The run always stages four inputs alongside this skill:

- `prompt.txt` — the brief and which interfaces are relevant.
- `payloads/case_scope.json` — collection id, business cutoff, focus /
  ranking / decision-panel ID lists, certification thresholds, status→action map.
- `payloads/answer_template.json` — the exact output contract (required keys,
  types, enums, array lengths, ordering rules, numeric precision). Authoritative.
- `environment_access.md` — the live base URL, the `Authorization` bearer token,
  and the allowed-endpoint allowlist. The **only** source for network access.

Collection families seen: **fuel purchases**, **freight charges**,
**maintenance events**, and **contact populations** (partner-onboarding
certification, field-service roster readiness). Per-family outputs and
distinguishing logic live in `references/playbooks.md`.

## Core principle

The hub holds **overlapping source snapshots** per collection. Your job is to
pick the authoritative snapshot, deduplicate raw rows into logical records as of
the business cutoff, separate **quarantined** (unusable) records from **valid**
ones, flag **mismatch** records (valid but expected-vs-actual category differs),
normalize units and currency, infer the opaque control codes the contract
demands, and certify. **Never copy specific answer values from training
material** — derive every count, ID, code, total, and ranking from the live hub
records plus the run's `case_scope.json`.

## Step 0 — read the inputs

1. `prompt.txt` — note the family and which interfaces it names.
2. `payloads/case_scope.json` — every parameter you must obey (collection id,
   cutoff, focus IDs, ranking limits, decision-panel ID lists, thresholds,
   status→action map, fixed gates).
3. `payloads/answer_template.json` — the contract. Note required top-level keys,
   per-field enums, `minItems`/`maxItems`, `pattern`s, `multipleOf`, and any
   `x-ordering_rules` / field `description`s that state ordering or precision.
   Two shapes occur: a JSON-Schema object (most runs) or a `field_contract`
   object with `required_top_level_keys` + `field_contract` (contact-roster
   style). Enforce both equivalently.
4. `environment_access.md` — extract base URL, `Authorization` header value, and
   the allowed-endpoint allowlist. Use **only** these to reach the hub.

## Step 1 — connect to the hub

Resolve the prompt's `<TASK_ENV_BASE_URL>` placeholder to the base URL from
`environment_access.md`. Send `Authorization: Bearer <token>` on every request.
Stay inside the allowed-endpoint allowlist.

| Endpoint | Purpose |
|---|---|
| `GET /api/catalog/collections` | List collections; confirm the target by `collection_id`; read `family`, `source_systems`, time span. |
| `GET /api/catalog/schema` | Logical `views` and their fields/meanings. |
| `GET /api/source-snapshots?collection=<id>` | Snapshot metadata: `snapshot_id`, `snapshot_status` (CERTIFIED/PROVISIONAL/STALE), `row_count`, `business_cutoff`. |
| `GET /api/transactions/fuel?collection=<id>&limit=&offset=` | Fuel rows (paginated). |
| `GET /api/transactions/freight?collection=<id>&limit=&offset=` | Freight charge rows (paginated). |
| `GET /api/maintenance/events?collection=<id>&limit=&offset=` | Maintenance event rows (paginated). |
| `GET /api/contacts?collection=<id>&limit=&offset=` | Contact rows (paginated). |
| `GET /api/reference/aliases` | Alias → canonical category/class maps. |
| `GET /api/reference/conversions` | Unit conversion factors. |
| `GET /api/reference/fx` | FX rates to base currency. |
| `POST /api/query` | Authenticated ad-hoc query layer over the views. The GET endpoints above already support full paging; probe `/api/query`'s body contract at runtime only if you need server-side filtered joins. |

**Pagination:** every list endpoint accepts `limit` and `offset` and returns
`total`. Loop `offset += limit` until you have collected `total` items.
Collections are larger than one page — never assume a single response is
complete. Full detail, auth notes, and the view→field map are in
`references/hub_api.md`.

## Step 2 — end-to-end procedure

1. **Resolve collection & snapshots.** Confirm the `collection_id` exists in
   `/api/catalog/collections` and note its `family`. From
   `/api/source-snapshots?collection=<id>`, the **authoritative snapshot** is the
   one with `snapshot_status` CERTIFIED (and `business_cutoff` matching the
   case-scope cutoff). Record its `snapshot_id` as `authoritative_snapshot_id`.
   Other snapshots (PROVISIONAL/STALE) are overlap sources to deduplicate
   against. Do **not** assume a `-certified` suffix — snapshot-id naming varies
   by family (transactional families use `-certified`/`-provisional`; some
   contact families use `-s01`/`-s02`). The `snapshot_status` field is
   authoritative.
2. **Load schema** (`/api/catalog/schema`) for the relevant view's field names.
3. **Page all raw rows** for the collection from the family's data endpoint,
   each tagged with its `snapshot_id`.
4. **Apply the cutoff.** Keep only rows whose business date is `<=` the
   case-scope cutoff (family's business-date field — see playbooks).
5. **Deduplicate across snapshots.** Group by logical key (`transaction_id` /
   `charge_id` / `event_id` / contact identity). When the same logical record
   appears in multiple snapshots, **retain the authoritative-snapshot
   occurrence**, drop the rest. `raw_row_count` = all in-scope raw rows;
   `duplicate_raw_count` = dropped duplicates; logical count = raw − duplicates.
   Report duplicate groups with the retained snapshot id.
6. **Classify each logical record** into one disposition:
   - **Quarantine** — unusable (family-specific conditions in playbooks).
     Excluded from normalized totals **and** from mismatch exposure; still
     counted as an exception.
   - **Mismatch** — valid but recognized category/class (from alias resolution)
     differs from the expected category/class on the record. **Included** in
     normalized totals **and** in mismatch exposure.
   - **Valid (clean)** — otherwise; included in normalized totals.
   - `exception` = distinct logical records that are a mismatch **or**
     quarantined.
7. **Normalize units & currency.** Convert quantity/weight/distance to the
   canonical unit from `case_scope` (`L`, `KG`, `KM`) using
   `/api/reference/conversions`; convert amount to base currency (`USD`) using
   `/api/reference/fx`. Apply to valid + mismatch records only, never
   quarantined.
8. **Compute outputs** — exactly the sections the contract requires (audit
   summary counts, mismatch/unrecognized ID lists, normalized totals overall +
   per category/class, focus rollups, ranked arrays, duplicate groups,
   quarantine ID sets, region/depot rollups, readiness partitions, control-code
   panels, certification status). Apply the contract's **ordering** and
   **precision** (see `references/reconciliation.md`).
9. **Infer opaque control codes** for every decision-panel ID in `case_scope`
   (focus clusters, anchored/identifier/control cases, reference IDs,
   transaction/charge IDs, event IDs). Codes are family-prefixed vocabularies;
   infer each from the reconciled evidence — never copy a specific code from
   training answers. See `references/code_inference.md`.
10. **Certify.** Apply case-scope thresholds (e.g.
    `pass_max_quarantine_rate`, `pass_with_exceptions_max_quarantine_rate`) and
    any fixed gate to derive `status` (PASS / PASS_WITH_EXCEPTIONS / HOLD), then
    map via the case-scope `status_action_map` to the action (RELEASE /
    REVIEW_EXCEPTIONS / BLOCK_AND_REMEDIATE). Fixed gates (e.g. an odometer
    regression gate forced to HOLD) override computed thresholds.
11. **Emit exactly one JSON object** conforming to `answer_template.json`:
    only required top-level keys, correct nesting, enums, array lengths,
    ordering, precision. No extra keys, no commentary, no Markdown. Validate
    against the template before returning.

## Critical rules (do not violate)

- **One JSON object, exact contract.** No extra or missing keys, no prose.
  Validate against the template.
- **Derive everything from live records + case_scope.** Never reuse training
  answer values (no counts, no ID lists, no code assignments, no canonical
  values, no rankings).
- **Quarantined records never enter normalized totals or mismatch exposure**;
  valid mismatches enter both. `exception` = mismatch ∪ quarantine (distinct).
- **Authoritative snapshot wins** for duplicate retention; `authoritative_snapshot_id`
  comes from `snapshot_status` CERTIFIED, not a hardcoded id suffix.
- **Page until `total`.** Never assume one response is complete.
- **Stable IDs only** — IDs present in the public data or case_scope; preserve
  the contract's ordering.
- **Precision** — round monetary/quantity totals to 2 decimals (rates to 4);
  counts are exact integers. Round at the final aggregation step, not mid-sum.

## References

- `references/hub_api.md` — endpoint catalog, auth, pagination, snapshot model, view→field map.
- `references/reconciliation.md` — dedup, cutoff, quarantine/mismatch, normalization, ordering, precision, certification.
- `references/code_inference.md` — opaque code families, prefixes, evidence dimensions.
- `references/playbooks.md` — per-collection-family playbooks (fuel, freight, maintenance, contacts).
