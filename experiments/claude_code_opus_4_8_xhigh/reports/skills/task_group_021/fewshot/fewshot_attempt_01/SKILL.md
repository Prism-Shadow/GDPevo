---
name: asteria-fleet-dq-certification
description: >-
  Produce the certification/audit JSON answer for an Asteria Fleet Data Quality Hub
  task. Use when a prompt points at the shared "Fleet Data Quality Hub" at
  <TASK_ENV_BASE_URL> with an `environment_access.md`, a `payloads/case_scope.json`,
  and a `payloads/answer_template.json`, and asks you to reconcile overlapping source
  snapshots for a collection as of a cutoff and return one JSON object. Covers all
  families: contacts (partner / field-service / dealer / warranty contact
  readiness & certification), fuel-purchase normalization, freight-charge accrual
  reconciliation, and maintenance-log integrity — including the opaque identity /
  outreach / provenance / source-basis / ledger / history control codes.
---

# Asteria Fleet Data Quality Hub — certification/audit tasks

A task in this family hands you three payloads plus network access and asks for one
JSON object that certifies a data collection. The collection lives in a shared hub as
several overlapping **snapshots**; your job is to reconcile them as of a cutoff and
report reconciled counts, canonical entities, exceptions, rollups, opaque control
codes, and a certification decision — matching `payloads/answer_template.json` exactly.

The specifics (which collection, cutoff, focus ids, thresholds, answer shape) vary per
task and always come from the task's own files — read them every time. The methodology,
the hub's data model, and the control-code system are constant; those are captured in
the reference files here.

## 0. Read the task's own files first (never assume)
- `prompt.txt` — the narrative ask and which endpoints are in play.
- `payloads/case_scope.json` — the collection id, cutoff/`as_of`, focus/anchor/watchlist
  ids, ranking limits, and any thresholds/gate. Everything task-specific is here.
- `payloads/answer_template.json` — **the contract.** It may be a JSON Schema
  (`$schema`, `properties`, `required`, `enum`, `pattern`) or a prose `field_contract`.
  Compute exactly its fields; obey every ordering, rounding, `enum`, and `description`.
- `environment_access.md` — runtime base URL + bearer token. Read them from here; never
  hard-code. It is the *only* thing you use the network for.

## 1. Connect
Use `scripts/hub_client.py` (reads `environment_access.md`, wraps `POST /api/query`
and the REST endpoints, and guards the 2000-row SQL cap):

```python
import sys; sys.path.insert(0, "skill/scripts")
from hub_client import Hub
hub = Hub.from_env_file("environment_access.md")           # adjust paths to the run
hub.sql("SELECT snapshot_id, snapshot_status, source_system, business_cutoff, row_count "
        "FROM v_source_snapshots WHERE collection_id='<id>' ORDER BY snapshot_id")
```

`reference/environment_api.md` documents every view, column, endpoint, and the SQL
quirks (2000-row output cap → aggregate server-side or page with LIMIT/OFFSET;
`?collection=` on REST; ignore `STALE` snapshots).

## 2. Run the reconciliation pipeline
Determine the collection's `family` from `/api/catalog/collections`
(`contacts` / `fuel` / `freight` / `maintenance`) → that picks the view and the answer
shape. Then follow the spine in `reference/reconciliation_pipeline.md`:

**snapshots → cutoff scope → dedup to logical entities → validate & quarantine →
normalize (units via `v_unit_conversions`, USD via `v_fx_rates`) → recognize categories
(via `v_reference_aliases`) → survivorship / field-level precedence → aggregate rollups
& rankings → certification decision.**

Key invariants that recur in the answer:
- `raw_row_count` counts every raw occurrence across snapshots; `logical_*_count`
  counts distinct ids; `duplicate_raw_count = raw − logical`.
- The authoritative snapshot is `"{collection_id}-certified"`; retain its occurrence
  when a logical id spans snapshots.
- Quarantined entities are excluded from normalized totals but still counted as
  canonical.
- Category recognition: exactly one effective canonical match = recognized; zero =
  unrecognized; >1 = ambiguous. A recognized category ≠ expected = mismatch.

## 3. Assign the opaque control codes
Pick the family from the field's `enum`, then map from the reconciled data using
`reference/control_codes.md`. In short:
- `SB-*` (fuel/freight) & `MS-*` (maintenance) = **snapshot membership** of the retained
  id (certified-only / provisional-only / both).
- `LD-*` = fuel/freight **ledger disposition** (clean / mismatch / unrecognized /
  ambiguous / invalid-measure). `HR-*` = maintenance **history route** (valid /
  rejected / regression). `RB-*` = **alias** state at cutoff (effective / out-of-window
  / provisional).
- `IC-*` / `OR-*` / `FP-*` = contacts **identity / outreach-readiness / field-provenance**
  disposition of each scoped case's evidence set.

Derive, never copy an id→code pair from another task; verify against one obvious case.

## 4. Assemble and emit the answer
- Build one JSON object with exactly the template's top-level keys — no extras
  (`additionalProperties:false` / `additional_top_level_keys_allowed:false`).
- Apply every ordering rule (lexicographic id sorts, `rank` ascending, rollups sorted by
  key, ranked arrays by the scope's sort + id tiebreak) and every rounding rule
  (e.g. 2-dp money/volume; keep phone/id patterns as strings).
- Certification `status`→`action`: `PASS→RELEASE`, `PASS_WITH_EXCEPTIONS→REVIEW_EXCEPTIONS`,
  `HOLD→BLOCK_AND_REMEDIATE`, with `status` from the scope's thresholds/gate (see the
  pipeline file).
- Use only stable ids from the hub or the scope.
- **Output is the JSON object only** — no Markdown, no commentary, no trailing prose.

## 5. Verify before finishing
- Validate against `answer_template.json`: every `required` key present, every value in
  its `enum`/`pattern`, array `minItems`/`maxItems` and length rules met, no extra keys.
- Cross-check internal arithmetic: `duplicate_raw_count = raw − logical`; partition
  counts sum to their totals; per-category counts sum to the overall valid count;
  `quarantine_rate` recomputed from your own quarantine set.
- Re-derive one control code and one focus/anchor record end-to-end from the hub to
  confirm the pipeline and the decode tables agree.
- Confirm scoped lists cover exactly the ids the scope asked for, in the required order.

## Files
- `scripts/hub_client.py` — read-only hub client (SQL + REST + pagination).
- `reference/environment_api.md` — endpoints, SQL views/columns, snapshot & normalization model.
- `reference/reconciliation_pipeline.md` — per-family reconciliation, validation, decision rules.
- `reference/control_codes.md` — decoded control-code tables and runtime derivation recipe.
