---
name: asteria-fleet-reconciliation
description: >-
  Solve Asteria Fleet "Data Quality Hub" reconciliation/certification tasks. Use when a
  task provides payloads/case_scope.json + payloads/answer_template.json and an
  environment_access.md pointing at a read-only Fleet Data Quality Hub, and asks for a
  reconciled/certified JSON audit of a contacts, fuel, freight, or maintenance collection
  (dedup overlapping source snapshots as of a cutoff, quarantine bad rows, normalize units
  & currency, resolve identities/categories, rank exceptions, assign opaque control codes,
  and decide a PASS/PASS_WITH_EXCEPTIONS/HOLD certification).
---

# Asteria Fleet Data Quality Hub — reconciliation & certification

## When this applies
The task gives you `payloads/case_scope.json`, `payloads/answer_template.json`, an
`environment_access.md`, and a prompt about the "Asteria Fleet Data Quality Hub". The
collection belongs to one of four families — **contacts, fuel, freight, maintenance** —
but the underlying job is always the same: reconcile overlapping snapshots of one
collection as of a business cutoff, flag data-quality defects, normalize, assign Asteria's
opaque control codes, and emit one JSON object that matches the answer template exactly.

## Supporting files (read the ones you need)
- `references/environment.md` — how to reach the hub: creds, endpoints/filters, the
  `POST /api/query` SQL interface, pagination.
- `references/data_model.md` — the 8 logical views and their fields, per family.
- `references/reconciliation.md` — the shared algorithm (dedup, quarantine, normalize,
  identity resolution, readiness, ranking, certification).
- `references/codebook.md` — **decoded meanings + assignment rules for every opaque code**
  (`SB/MS`, `RB`, `LD/HR`, `IC/OR/FP`). Their expansions are withheld from the task on
  purpose; this codebook is how you assign them by rule.
- `references/output_contract.md` — schema/ordering/rounding/JSON-only discipline.
- `scripts/hub_client.py` — dependency-free client. `HubClient()` auto-reads the base URL
  and bearer token from `environment_access.md`; `.query(sql)` / `.rows(sql)` /
  `.get(path)` / `.get_all(path)`. CLI: `python3 hub_client.py catalog|schema|snapshots <id>|sql "<SQL>"|get <path>`.

## Procedure
1. **Connect.** `from hub_client import HubClient; hc = HubClient()`. Never hard-code the
   URL/token — they rotate; read them from `environment_access.md`. `curl` is usually
   absent; use Python.
2. **Read the scope.** From `case_scope.json`: `collection_id`, the cutoff
   (`business_cutoff`/`cutoff_at`/`as_of`+`business_period`), focus clusters / anchors /
   watchlist / control cases, ranking limits, `status_thresholds`+`status_action_map` or
   `certification_gate`, and ordering rules. Every scoped ID you echo must exist in the
   scope or the public data.
3. **Find the authoritative snapshot.** `GET /api/source-snapshots?collection=<id>`; the
   authoritative one is `snapshot_status=CERTIFIED`, id `<collection_id>-certified`.
4. **Pull scoped rows** with `POST /api/query` (SQL over the views — one call gets the full
   set; check `truncated`). Aggregate server-side where you can.
5. **Reconcile** per `references/reconciliation.md`:
   dedup across snapshots (retain CERTIFIED) → detect quarantine defects → resolve
   categories/identities → normalize units (conversions) and money (CERTIFIED FX, incl.
   USD) → compute totals, rollups, readiness, and exception rankings.
6. **Assign control codes** strictly from `references/codebook.md`, re-deriving each from
   the record evidence for the exact IDs requested. Match the template's enum.
7. **Decide certification.** Map status→action: `PASS→RELEASE`,
   `PASS_WITH_EXCEPTIONS→REVIEW_EXCEPTIONS`, `HOLD→BLOCK_AND_REMEDIATE`, using the scope's
   thresholds/gate.
8. **Emit & self-check.** Build the object to match `answer_template.json` exactly
   (keys, enums, array lengths, ordering, rounding), validate it, then output **only** the
   JSON — no commentary, no Markdown.

## Gotchas that cost points
- **CERTIFIED wins.** Duplicates across snapshots are resolved to the certified copy; the
  retained snapshot also determines the `SB-*`/`MS-*` codes.
- **Alias applicability is as-of-cutoff.** Only ACTIVE + in-window aliases resolve a
  category; match on word boundaries, not substrings. Zero matches → unrecognized,
  multiple → ambiguous (both quarantine); a single match that differs from the expected
  class is a *valid* mismatch that still counts in totals.
- **USD is not 1.0.** Always apply the certified FX rate for the record's date, USD included.
- **Quarantined records never enter normalized totals**, but valid class mismatches do.
- **Contacts:** the master/survivor row is the one with a non-null `master_hint`; a shared
  value like `SHARED-HELPDESK` means *contested*, not master. Readiness-eligible = active +
  usable channel; consent gates readiness; the three code axes `IC`/`OR`/`FP` are independent.
- **Ordering & fixed-length arrays** are graded — sort exactly as the template says and emit
  one row per required group/ID even when a count is zero.
- **Output is JSON only.** No prose or code fences in the answer.
