---
name: asteria-fleet-data-quality
description: >-
  Answer Asteria Fleet "Data Quality Hub" reconciliation tasks. Use whenever a
  task points at a running hub (via environment_access.md), gives a
  payloads/case_scope.json + payloads/answer_template.json, and asks you to
  reconcile overlapping source snapshots for a collection as of a business
  cutoff and return one JSON object — for any family: contacts / partner
  onboarding / field-service roster, fuel purchases, freight charges, or
  maintenance events. Covers auditing counts, de-duplication & survivorship,
  quarantine, normalized totals (unit + FX), focus/anchored cases, rollups,
  rankings, opaque internal control codes, and the certification decision.
---

# Asteria Fleet Data Quality Hub reconciliation

Every task in this family is one job: **reconcile a collection's overlapping
source snapshots as of a business cutoff and emit exactly the JSON object the
answer contract asks for.** The domain vocabulary changes (contacts / fuel /
freight / maintenance) but the method does not.

## Inputs you are given
- `prompt.txt` — the narrative: which family, what to report, and the precise
  definitions of any ranking/exposure/exception terms. Read term definitions
  literally.
- `payloads/case_scope.json` — the `collection_id`, business cutoff, focus
  clusters / anchored cases / decision-panel IDs, ranking limits & tie-breaks,
  thresholds and status→action map.
- `payloads/answer_template.json` — a JSON Schema. It is the contract: required
  keys, enums (including the **allowed control-code values**), patterns, array
  sizes, numeric precision, ordering notes. Obey it exactly
  (`additionalProperties:false`).
- `environment_access.md` — base URL + `Bearer` token + endpoint list for the
  live hub. Read connection details from here at runtime; never hard-code them.

## Tools
- `scripts/hub_client.py` — stdlib-only read-only client. Parses
  `environment_access.md`, exposes `hub.rows(sql)`, `hub.scalar(sql)`,
  `hub.query(sql)`, and a paginating `hub.get(path, **params)`. CLI:
  `python3 scripts/hub_client.py sql "SELECT ..."` and
  `python3 scripts/hub_client.py get /api/source-snapshots collection=<id>`.
- `references/api_and_query.md` — endpoints, the SQL `/api/query` interface, all
  logical-view schemas, and stable reference data (conversions, aliases, FX).
- `references/reconciliation.md` — the step-by-step pipeline (scope → dedup →
  validate/quarantine → normalize → canonicalize → rank → status → format).
- `references/control_codes.md` — how to derive every opaque control-code family
  (`IC/OR/FP` for contacts; `RB/SB/LD` for fuel & freight; `MS/HR` for
  maintenance) from observable reconciliation outcomes.

## Workflow
1. **Orient.** Read `prompt.txt`, `case_scope.json`, and `answer_template.json`.
   List the exact top-level keys the template requires and note every enum,
   pattern, ordering rule, and precision.
2. **Connect & map the data.** `GET /api/catalog/schema` for the family's view;
   `GET /api/source-snapshots?collection=<id>` for the snapshot set (which is
   CERTIFIED, which PROVISIONAL, their `source_system`s). Prefer the SQL endpoint
   for all counting/joining — it returns the full result set with no page cap.
3. **Reconcile** following `references/reconciliation.md`:
   dedup across snapshots (retain CERTIFIED; contacts cluster by normalized
   email/phone) → validate & quarantine per family rules → normalize valid rows
   to canonical units and USD (certified FX by business date) → canonicalize
   entities with field-level precedence (contacts) → compute rollups/rankings
   with the scope's sorts and tie-breaks.
4. **Derive control codes** with `references/control_codes.md`: classify each
   referenced row/alias by the observable dimension its family keys on, then
   pick the value from the template's enum. Codes are deterministic labels of
   reconciliation outcomes, never guesses.
5. **Decide status** using the scope's thresholds and action/routing map, with
   the scope's exact field names.
6. **Assemble & validate.** Produce one JSON object with every required key and
   no extras. Sort ID lists and ranked arrays as specified, dedupe sets, match
   types (e.g. phone digits stay a string) and precision. Re-check it against
   `answer_template.json`. **Return JSON only — no Markdown, no commentary.**

## Guardrails
- Always filter by the scoped `collection_id`; the hub holds many collections.
- Snapshot precedence is CERTIFIED > PROVISIONAL for retained records.
- Quarantined records never enter normalized totals; quarantine disposition
  dominates mismatch when both apply.
- Read the live reference tables (aliases, conversions, FX) each task — validity
  windows and the alias set are cutoff- and task-specific.
- Do not invent stable IDs; use only IDs present in the hub or the case scope.
- The specific numeric/ID values in any one task are outputs to compute, not
  constants to reuse — derive them fresh every time from the live hub.
