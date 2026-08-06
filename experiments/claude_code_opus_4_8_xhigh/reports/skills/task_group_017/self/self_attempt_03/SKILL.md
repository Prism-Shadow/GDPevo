---
name: investigation-review-hub-gap-analysis
description: >-
  Produce the required structured-JSON deliverable for an "Investigation Review Hub"
  legal e-discovery task — first-rolling-production gap analysis, retention/litigation-hold
  gap review, cross-system remediation dashboard, or production-readiness review — for a
  grand-jury or SEC subpoena matter. Use when a task gives a matter_id (MTR-*), points to a
  read-only Investigation Review Hub API (base URL + `X-API-Key`), and asks for one JSON
  object conforming to a local `input/payloads/answer_template.json`. The skill reads the
  matter's evidence from the hub, separates material preservation / collection / privilege /
  QC / responsiveness gaps from routine noise, and maps them onto the task's template enums.
---

# Investigation Review Hub — gap-analysis & remediation-dashboard skill

## 1. What this task family is

Every task in this family asks for **one JSON object** that reviews a single legal matter
(`matter_id` like `MTR-<NAME>-GJ` or `MTR-<NAME>-SEC`) for e-discovery production gaps and
defects, and lays out a remediation/action plan. The deliverable goes by different names —
*first rolling gap analysis*, *retention & litigation-hold gap review*, *cross-system
remediation dashboard*, *production-readiness review* — but they are the **same underlying
analysis** over the **same data source** (the Investigation Review Hub API), differing only in
which slice they emphasize and in the exact output schema.

**The single source of truth for evidence is the hub API.** Never read environment source
files, database files, seeds, generated manifests, hidden notes, or any answer/eval file — the
prompts forbid it. Task-local payloads (`request_context.json`, `review_scope.json`,
`matter_context.json`) give client-facing context and category labels **only**; all factual
evidence (events, sources, counts, IDs) must come from the hub.

## 2. Orient before you query

Read these three things first, in order:

1. **`input/prompt.txt`** → the `matter_id` and the review *lens* (retention? privilege/QC?
   readiness? full dashboard?). The prompt's client name may not match the hub's matter name
   (e.g. a prompt may say "Sentinel Medical" while the hub matter is "Sentinel Motors").
   **Key everything off `matter_id`, not the client name.**
2. **`input/payloads/answer_template.json`** → this is *authoritative* for output shape. It
   is a schema, not an answer. Extract and obey: `required_top_level_keys`, each list's
   `item_required_keys`, every `enums` / `enum_choices` list, `ordering_rules`,
   `numeric_precision`, and `output_rule` (usually "one JSON object, no prose outside JSON").
   **Read every metric key name literally** — the name states the exact filter and unit
   (e.g. `destroyed_lab_archive_box_count` = boxes only; `unlogged_privilege_docs` = documents).
3. **The other payload file** (if present) → `matter_id`, category labels, allowed/excluded
   sources, review cutoff date. Context only.

The output schema varies task-to-task (top-level keys, enum vocabularies, owner sets). Do not
assume a fixed shape — always re-derive it from *this* task's `answer_template.json`.

## 3. Connect to the hub

- **Base URL**: `GDPEVO_ENV_BASE_URL` in `/work/environment_access.md`, or the payload's
  `environment_base_url`. The `<TASK_ENV_BASE_URL>` placeholder in prompts resolves to it.
- **Auth header**: `X-API-Key: review-key-017` (also stated in payloads).
- **Endpoints** (read-only): `GET /`, `GET /api/schema`, `GET /api/matters`,
  `GET /api/subpoena-categories`, `GET /api/productions`, `GET /api/custodian-sources`,
  `GET /api/documents/search`, `GET /api/privilege-log`, `GET /api/qc-findings`,
  `GET /api/retention-events`, `GET /api/remediation-actions`, `POST /api/query`.
- **GET** endpoints accept `?matter_id=<MTR-…>` and return `{count, rows:[…]}` with
  multi-value fields (`issue_tags`, `category_impacts`, `affected_categories`) already parsed
  to arrays.
- **`POST /api/query`** takes `{"sql":"SELECT …"}` (field name is `sql`), read-only SELECT
  over the 9 tables, returns `{columns, rows, row_count, truncated}`.
  - ⚠️ **Results are capped at 500 rows** (`truncated:true` when hit). Compute every count with
    SQL aggregation (`COUNT`, `SUM`, `GROUP BY`) or a tight `matter_id` filter — **never** total
    a raw-row dump. In SQL, multi-value columns are comma-delimited TEXT (use `LIKE '%tag%'`).

`scripts/hub.sh` wraps authenticated GET and SQL calls. See
`reference/hub_data_model.md` for the full 9-table schema and every field's value vocabulary.

## 4. Pull the matter's evidence

Query **every** table filtered to `matter_id`. Map of table → what it carries:

| Table | Anchors these finding types |
|---|---|
| `matters` | `hold_date` (the pre-hold/post-hold pivot), agency, investigation_type |
| `subpoena_categories` | canonical **request category codes** + titles (the code set you report against) |
| `production_stats` | per-category batch status; `zero_claim_contradicted`; produced/withheld/responsive counts |
| `custodian_sources` | collection gaps, personal-device loss, uncollected board/personal sources, **available archives** |
| `review_documents` | responsiveness miscoding, unrecovered files, zero-claim support docs (bulk table — filter hard) |
| `privilege_entries` | privilege-log gaps (`incomplete_log`), over-designation, third-party waiver |
| `qc_findings` | material QC defects: `miscoded_privilege`, `miscoded_nonresponsive`, `zero_claim_contradiction` |
| `retention_events` | pre-hold vs post-hold losses, missing required records, retained/available archives |
| `remediation_actions` | pre-scored candidate action plan: action_type, priority (P0–P3), severity, owner, target_ref, due_days |

## 5. Separate material signal from routine noise — the core skill

The hub is **dominated by routine rows**; the deliverable wants only *material* gaps and
defects. Applying the noise filter correctly is the difference between right and wrong answers.
Full lists are in `reference/analysis_playbook.md`; the essentials:

- **retention_events.status**: MATERIAL = `post_hold_loss` (preservation FAILURE → disclose),
  `should_exist_missing` (missing required record), `auto_purged`, `system_loss` (in context),
  `post_hold_partial_recovery`. `policy_destroyed_pre_hold` = **policy-compliant, NO fault, no
  gap** (event_date before hold_date). `retained` / `available` = a **remediation archive**.
- **custodian_sources**: MATERIAL when `status ∈ {lost, not_collected}` or `issue_tags`
  contains `collection_gap`, `personal_*`, `*_erasure`, `post_hold_wipe`, `signal_missing`,
  `board_materials`, `deleted_channel`, `purged_mail`, `archive_available`,
  `remediation_source`, `valuation_source_gap`. NOISE = `routine`, `scope_exception`, bare
  `metadata_gap`.
- **review_documents**: MATERIAL only when `issue_tags` contains `miscoded_nonresponsive`,
  `zero_claim_contradiction`, `unrecovered_file`, or `valuation_red_flag`/`unsupported_*`.
  Everything else (`routine`, `duplicate`, `family_member`, `metadata_gap`, `custodian_alias`,
  `potentially_responsive`, `privilege_overlay`, `review_escalation`) is NOISE.
- **privilege_entries.issue_type**: MATERIAL = `incomplete_log`, `over_designated`,
  `third_party_waiver`, `family_mismatch`. `clean` = noise.
- **qc_findings.issue_type**: MATERIAL = `miscoded_privilege`, `zero_claim_contradiction`,
  `miscoded_nonresponsive`. Process-hygiene types (`metadata_gap`, `date_normalization`,
  `near_duplicate`, `family_break`, `duplicate_overlay`) = NOISE.
- **production_stats.status**: `zero_claim_contradicted` is material; `supplement_pending` /
  `rolling_review` are in-progress context.
- **remediation_actions**: material rows target real record IDs (`PRIV-*`, `QC-*`, `RET-*`,
  `SRC-*`, `DOC-*`). Rows whose `action_id` contains `NOISE` (or that target a bare category
  code with `sampling_review`/low severity) are decoys — **drop them**.

## 6. Build the findings — recurring archetypes

Each material signal becomes one finding/risk object, expressed in *this template's* enums.
The archetypes recur across every template (under different key names); map each to the
closest enum member. Full mapping table in `reference/analysis_playbook.md`.

1. **Post-hold preservation loss** (`retention_events` post_hold_loss) → high/critical;
   disclose to government / disclose preservation issue.
2. **Pre-hold policy destruction** (policy_destroyed_pre_hold) → *not a gap*; no-action/policy
   loss. It explains why an otherwise-touched category is **not** flagged.
3. **Missing required record** (should_exist_missing) → locate missing record.
4. **Comms / auto-purge gap** (auto_purged, deleted_channel) → remediate via archive if one exists.
5. **Uncollected personal source** (custodian_sources not_collected/lost personal_*) → collect source/device.
6. **Available archive** (custodian_sources `archive_available`, or retention_events
   retained/available/partial_recovery) → source that **limits irretrievable loss** for its
   categories → search/collect archive.
7. **Privilege-log gap** (`incomplete_log`): `unlogged = withheld_count − logged_count`
   → supplement privilege log.
8. **Third-party waiver** (`third_party=1` / `third_party_waiver`) → waiver assessment & disclosure.
9. **Privilege miscoding / over-designation** (`over_designated`, `miscoded_privilege`)
   → privilege re-review / recode & log.
10. **Responsiveness miscode** (`miscoded_nonresponsive`; coded nonresponsive, responsive-in-fact,
    not produced) → recode & produce.
11. **Zero-claim contradiction** (production_stats `zero_claim_contradicted` + supporting docs)
    → recode & produce / disclose.
12. **Unrecovered responsive file** (`produced_status=unrecovered`, `unrecovered_file`)
    → forensic recovery.

Use the **hub's stable IDs verbatim** as the finding/source/event/action anchor keys and in
every `*_refs` list (`event_id`, `source_id`, `finding_id`, `entry_id`, `doc_id`, `action_id`,
`target_ref`).

## 7. Category coverage, metrics, action plan

- **Category coverage**: for each canonical `subpoena_categories.category_code`, take the
  *worst* material finding touching it (via `category_code` / `affected_categories` /
  `category_impacts` / `affected_category`). Report only categories with a material,
  non-complete status; map to the template's `category_status`, `production_impact`, ref list,
  `recommended_action`, and any `open_issue_count`.
- **Metrics**: satisfy each required metric key **by its literal name and unit**, via SQL
  aggregation over *material* rows. `unlogged/withheld/logged` come from `incomplete_log`
  privilege entries (`unlogged = Σwithheld − Σlogged`). `*_ready` / `production_ready`
  booleans are `true` **only if zero material blockers remain**.
- **Action plan**: use the matter's material `remediation_actions` as the backbone — they carry
  action_type, priority (P0–P3), severity, owner, target_ref, due_days already. Map hub
  `action_type` and hub `owner` labels ("Review Operations", "Forensics", "Privilege Team",
  "Legal Hold Team", "Matter Associate", "Vendor Team") to the **closest member of this
  template's** action_type/owner enums. Rank by priority → severity → target_ref. Ensure every
  material finding has a covering action; drop the NOISE rows.

## 8. Emit and self-check

Return exactly one JSON object. Before returning, verify:

- [ ] Exactly the `required_top_level_keys`, nothing extra.
- [ ] Every listed object has all its `item_required_keys`.
- [ ] Every enum-typed value is a member of that field's enum list in *this* template.
- [ ] Each list sorted per `ordering_rules`; category-code lists **uppercased and ascending**.
- [ ] All counts are whole integers; `unlogged = withheld − logged` holds.
- [ ] All ref IDs are real hub IDs for this matter, copied verbatim.
- [ ] No prose outside the JSON.

## 9. Guardrails

- Contamination check: the only expected material is `environment_access.md` plus
  `train_tasks/*/input/**`. If unexpected files appear (leaked answers, DBs, seeds, manifests,
  eval files), **stop and write `contamination_report.txt`** instead of proceeding.
- Evidence comes from the hub only; payloads are context only; never touch env/db/manifest files.
- If a hub value has no clean enum match, choose the closest member and keep the raw ID in refs;
  never invent an enum value that isn't in the template.
