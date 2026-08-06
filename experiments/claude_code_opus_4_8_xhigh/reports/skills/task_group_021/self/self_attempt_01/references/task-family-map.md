# Task-family map

Five recurring variants of the Asteria Fleet Data Quality Hub pipeline. Each is
scoped by its own `case_scope.json` and shaped by its own `answer_template.json`;
the values below are **archetypes, not answers** — always derive from the live
hub. Use this to recognize which subset of the pipeline (SKILL.md §2) a task
needs and which endpoints it touches.

## Common spine (all variants)

Intake scope → discover catalog/schema → pick authoritative snapshot →
paginate all rows → cutoff filter → dedup to logical entities → normalize →
classify valid/mismatch/quarantine → resolve canonical entities / survivors →
rollups + rankings + readiness → assign opaque control codes →
threshold+gate → status→action map → emit one JSON object.

## Variant A — Contact-master certification

- Endpoints: catalog, schema, `/api/contacts`, `/api/source-snapshots`,
  `/api/reference/{aliases,conversions,fx}`, `/api/query`.
- Scope: focus clusters (cluster_id + seed row), anchored control cases (case id
  + seed rows), `status_thresholds` (pass_max / pass_with_exceptions_max on
  quarantine rate), `status_action_map`.
- Core work: identity resolution into clusters; survivor selection; canonical
  email/phone/city + `city_source_system`; quarantine = no usable channel;
  channel readiness (eligible = active + usable channel; ready = consent
  granted); region rollup; certification via quarantine-rate thresholds.
- Control codes: `focus_decisions` (identity + field-provenance),
  `anchored_cases` (identity + outreach + field-provenance),
  `quarantine_result`, `readiness_partition` (an OR code per readiness bucket —
  a calibration lever), `inactive_exclusion` (outreach).

## Variant B — Contact-readiness roster (dispatch)

- Endpoints: catalog, schema, `/api/contacts`, `/api/source-snapshots`,
  `/api/query`.
- Scope: `population_scope`, `depot_key_field`, focus people
  (focus_person_id + source_row_anchor), identifier watchlist (contested cases),
  `policy_control_cases` grouped by `control_family`
  (IDENTITY / OUTREACH / FIELD_PROVENANCE) with pinned `evidence_row_ids`.
- Core work: reconcile HR Directory / Dispatch / Identity Registry with
  field-level precedence; per-focus resolution_outcome
  (FIELD_LEVEL_PRECEDENCE_APPLIED / SINGLE_SOURCE / CONTESTED_NO_AUTOMERGE /
  NO_USABLE_CONTACT); dispatchable = active + usable channel + consent granted;
  per-depot disposition partition (dispatchable / blocked_consent /
  blocked_no_contact / blocked_inactive summing to total); watchlist →
  contested clusters; release decision.
- Control codes: one `control_code` per policy control case, chosen from the
  family-appropriate enum (FP-*/IC-*/OR-*).

## Variant C — Fuel-purchase normalization audit

- Endpoints: catalog, schema, `/api/transactions/fuel`,
  `/api/reference/{aliases,conversions,fx}`, `/api/source-snapshots`,
  `/api/query`.
- Scope: base currency, canonical volume unit, focus asset ids, merchant ranking
  limit, reference-decision ids, transaction-decision ids.
- Core work: dedup to logical transactions; alias→fuel category (unrecognized /
  ambiguous → quarantine); invalid quantity → quarantine; expected-vs-actual
  category mismatch (valid); normalize liters + USD spend (exclude quarantined);
  per-fuel_type totals; focus-asset rollups; top-N merchants by exception count
  (then merchant_id asc).
- Control codes: `reference_policy_code` (RB-*), `source_basis_code` (SB-*),
  `ledger_disposition_code` (LD-*).

## Variant D — Freight-charge accrual reconciliation

- Endpoints: catalog, schema, `/api/transactions/freight`,
  `/api/reference/{aliases,conversions,fx}`, `/api/source-snapshots`,
  `/api/query`.
- Scope: base currency, canonical weight + distance units, carrier ranking
  limit, reference alias ids, source-decision charge ids, ledger-decision charge
  ids.
- Core work: dedup to logical charges (report duplicate groups with snapshot_ids
  + retained_snapshot_id); alias→service class (unrecognized/ambiguous →
  quarantine); non-positive weight/distance → quarantine; class mismatch
  (valid); normalized weight/distance/USD by service class; carrier ranking by
  mismatch USD exposure descending then carrier_id ascending;
  `quarantine_reason_counts`.
- Control codes: `reference_rows` (RB-*), `source_retention` (SB-*),
  `ledger_routing` (LD-*).

## Variant E — Maintenance-log integrity certification

- Endpoints: catalog, schema, `/api/maintenance/events`,
  `/api/source-snapshots`, `/api/reference/conversions`, `/api/query`
  (collection spans multiple pages).
- Scope: as_of, business period (start/end), event decision panel (event ids),
  corrected-distance definition + precision, asset risk ranking (limit +
  primary sort `rejected_event_count DESC` + tie-breaks), certification gate
  (odometer regression → HOLD / BLOCK_AND_REMEDIATE).
- Core work: authoritative snapshot + `snapshot_status`; cross-snapshot
  duplicate groups (retained event/snapshot); issue counts (missing/invalid
  timestamp, invalid odometer, negative/extreme labor, odometer regression);
  invalid vs regression split (regressions reported in corrected_metrics, not
  invalid_event_ids); corrected total distance (sum over assets of last minus
  first reliable odometer); asset risk ranking; certification with the hard
  regression gate.
- Control codes: `maintenance_source_code` (MS-*), `history_route_code` (HR-*).

## Reading a new/held-out variant

If a task doesn't match A–E exactly, it is still the same spine. Map its prompt
onto §2 stages: identify the collection + cutoff, the quarantine reasons it
names, the canonical/normalization rules, the rollups/rankings and their sort
keys, any code families and their enums, and the threshold/gate + action map —
then satisfy its `answer_template.json` literally.
