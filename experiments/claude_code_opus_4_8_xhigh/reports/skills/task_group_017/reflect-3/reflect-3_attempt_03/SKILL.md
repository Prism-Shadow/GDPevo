---
name: investigation-review-hub-gap-analysis
description: >-
  Produce a structured JSON gap/remediation analysis for a litigation or investigation
  matter from an "Investigation Review Hub" style data source (matters, subpoena
  categories, productions, custodian sources, review documents, privilege entries,
  QC findings, retention events, remediation actions). Use when a task asks for a
  first-rolling-production gap analysis, retention/litigation-hold gap review,
  production-readiness review, or cross-system remediation dashboard, and the answer
  must conform to a provided answer_template.json. The core skill is separating the
  handful of MATERIAL escalated records from the surrounding realistic NOISE, then
  mapping them faithfully into the template's objects, metrics, enums, and ordering.
---

# Investigation Review Hub — structured gap / remediation analysis

## What these tasks look like

You are given, in the task's `input/` directory:

- A `prompt.txt` naming a client, a `matter_id` (e.g. a stable `MTR-…` identifier), and the deliverable (gap analysis / retention review / readiness review / remediation dashboard).
- A payload file (`request_context.json`, `review_scope.json`, `matter_context.json`, …) that gives client-facing context and sometimes category labels. **Treat payloads as context only — the authoritative evidence lives in the hub.**
- An `answer_template.json` that fully specifies the output contract: `required_top_level_keys`, the object schemas, `enums`/`enum_choices`, `ordering_rules`, and numeric precision. **This file does not contain the answer; it defines the shape.**

The hub itself is a read-only data service reachable through the run's environment access file (a base URL + credential header it provides). It exposes one read endpoint per record type and a read-only SQL `POST` query endpoint. **Read connection details (base URL, credential, exact paths) from the run's environment access file at solve time — do not assume them.** Return **exactly one JSON object** conforming to the template and nothing else.

## The hub data model (verify at runtime with the schema endpoint)

All rows are keyed by `matter_id`; always filter to the task's matter. The read-only SQL endpoint makes filtering/aggregation easy (`SELECT * FROM <table> WHERE matter_id='…'`). Tables and their roles:

| Table | Key | Role in the analysis |
|---|---|---|
| `matters` | `matter_id` | Matter metadata; note `hold_date` (the litigation-hold date — the pivot for pre/post-hold classification). |
| `subpoena_categories` | `category_code` | The request categories for this matter. **Category code schemes differ per matter** (e.g. `R01…`, `A…`, `SEC-1…`, `SEC-A…`) — read them, never assume. |
| `production_stats` | `batch_id` | Per-category production batches; surfaces zero-production claims (`status`/`zero_claim_reason`, `produced_count=0`). |
| `custodian_sources` | `source_id` | Collection sources; lost/wiped/not-collected devices, personal messaging, board/SharePoint sites, available archives. |
| `review_documents` | `doc_id` | Individual docs (large, mostly noise); holds the specific escalated documents behind QC findings. |
| `privilege_entries` | `entry_id` | Privilege log entries: `withheld_count`, `logged_count`, `issue_type` (`incomplete_log`, `over_designated`, `third_party_waiver`, `family_mismatch`, `clean`). |
| `qc_findings` | `finding_id` | Quality-control findings incl. `miscoded_privilege`, `miscoded_nonresponsive`, `zero_claim_contradiction`, plus its own `severity`. |
| `retention_events` | `event_id` | Retention/destruction events: `policy_destroyed_pre_hold`, `post_hold_loss`, `should_exist_missing`, `system_loss`, `auto_purged`, `retained`, `available`; `volume_count`/`volume_unit`. |
| `remediation_actions` | `action_id` | **The backbone.** Each non-noise row's `target_ref` names one material record, with `priority`, `severity`, `owner`, `due_days`. |

## The one idea that matters: material records vs. noise

Each matter's tables are seeded with a small set of **material (escalated)** records and a larger set of **realistic noise/distractor** records. Getting the material set exactly right is the whole game.

**Material records** — include these:
- **Descriptive, human-readable stable IDs** that embed the matter and a descriptor, e.g. `SRC-<MATTER>-<CUSTODIAN>-<DEVICE>`, `RET-<MATTER>-<DESC>`, `PRIV-<MATTER>-<DESC>`, `QC-<MATTER>-<DESC>`, `DOC-<MATTER>-<DESC>`.
- **Notes stating a concrete, specific defect**, e.g. a personal device erased/wiped after the subpoena, "only N of M withheld docs are logged", "K boxes destroyed after the hold", a zero-production claim contradicted by responsive emails, an archive available for a deleted channel.
- **`issue_tags` naming a real problem**: `post_subpoena_erasure`, `post_hold_wipe`, `personal_device`, `personal_email`, `signal`/`sms`, `collection_gap`, `board_materials`, `deleted_channel`, `archive_available`, `valuation_source_gap`.

**Noise records** — exclude these:
- **Sequential/numbered IDs** like `SRC-<MATTER>NN`, `PRIV-<MATTER>NNN`, `QC-<MATTER>NNN`, `RET-<MATTER>-0NN`, and `ACT-<MATTER>-NOISE-NN`.
- **Boilerplate, non-escalation notes**: "realistic operational noise", "ordinary review variance", "similar labels across matters", "requires category-level context before escalation", "no production-impacting issue has been escalated yet", "marked for follow-up but not immediate remediation", "remediated by archive collection", "slightly different record labels", "minor metadata normalization issues".
- A `remediation_actions` row whose `action_id` contains `NOISE` (its `target_ref` is usually a bare category code, not a record ID).

**Authoritative anchor:** the material findings are exactly the set of `target_ref` values from `remediation_actions` rows whose `action_id` does **not** contain `NOISE`. Pull those first, then look each `target_ref` up in its table to get the details. Cross-check: every such target has a descriptive ID and a concrete note; every descriptive-ID record in the other tables should trace back to one of these targets. Do not invent findings that no material record supports, and do not promote noise.

## Workflow

1. **Read** `prompt.txt`, the context payload, and `answer_template.json`. Extract the `matter_id` and memorize the required keys, enums, and ordering rules.
2. **Confirm the schema** (schema endpoint) and read the matter's `subpoena_categories` to learn this matter's category codes and `hold_date`.
3. **Pull the backbone**: `remediation_actions` for the matter. Split into material rows and `NOISE` rows. The material `target_ref`s are your finding set and drive priority/severity/owner/due_days.
4. **Fetch each material record** from its table (custodian_sources / privilege_entries / qc_findings / retention_events / review_documents). Also scan those tables for descriptive-ID records and check `production_stats` for zero-production claims — reconcile against the backbone.
5. **Build the output objects** the template asks for (findings / risks / issues / category statuses / retained-or-available sources / privilege corrections / action plan). One object per material record (or per affected category, per the schema's description). Map each record's nature to the template enums (see below).
6. **Compute the metrics** from the material set (see below).
7. **Conform** to the contract: required keys, valid enum values only, ordering rules, integer precision, one JSON object, no prose.

## Mapping records to enum fields

Read the record; pick the closest enum the template offers. Consistent, defensible rules:

- **issue / risk / finding type**: lost or wiped device → preservation failure / post-hold loss; uncollected personal source (phone, personal email, Signal/SMS) → collection / personal-source gap; not-collected site/share → collection gap; retention destruction → pre-hold policy loss vs. post-hold loss vs. should-exist-missing vs. auto-purge/active-system-loss by the event `status`; incomplete privilege log → privilege-log gap; over-designated privilege → privilege miscoding / over-designation; privileged docs coded non-privileged → privilege miscoding; docs forwarded outside the privilege group → third-party waiver; responsive docs miscoded/withheld or a zero-claim contradicted by responsive docs → responsiveness miscode.
- **source_status / production_impact**: lost/wiped → lost / source-lost; not collected → not-collected / source-missing (or not-produced); available archive → available / source-available; privilege issues → not-applicable source with withheld-unlogged / privilege-exposure / underproduced impact.
- **severity**: take a record's **own** severity when it has one (a QC finding's `severity`), otherwise use the matching `remediation_actions.severity`. Note a finding's severity may differ from the action's priority tier.
- **priority / priority_rank**: use `remediation_actions.priority` and order by it. If an `ordering_rules` entry has a **secondary tiebreak** (e.g. "then target_id ascending"), the primary rank has **ties** → assign tiered ranks (all top-priority items share rank 1, next tier rank 2, …). If there is **no** tiebreak, assign **distinct** sequential ranks 1..N.
- **action_type**: preservation loss / spoliation → disclose; lost/wiped device → forensic recovery (or disclose); uncollected personal source → collect; not-collected site → collect source; incomplete log → supplement privilege log; over-designation/miscode → recode / privilege re-review; waiver → waiver assessment/disclosure; missing required record → locate; available archive → search/collect archive; zero-claim contradiction → recode-and-produce.
- **owner**: take `remediation_actions.owner` and map to the closest template owner enum; when the template lacks the literal role name, choose the nearest functional owner (privilege work → privilege team/counsel; QC/recode → review/QC; forensic collection → forensics/ediscovery vendor; disclosure → outside counsel; records destruction → records management).
- Use `not_applicable` / `no_action` / `unknown` / `null` deliberately where a field genuinely does not apply; use `0` (not null) for counts that the template says are "0 when not applicable".

## Deriving the metrics

Metrics are matter-scoped and computed **from the material set only** (noise records are excluded). They are the most reliably-correct part of the answer, so double-check every count — some schemas score the whole metrics block as a single unit, so one wrong number forfeits all of it.

- **Box / volume counts**: sum `volume_count` over material retention events whose `volume_unit` is boxes; split pre- vs. post-hold by comparing `event_date` to the matter `hold_date` (equivalently `policy_destroyed_pre_hold` vs. `post_hold_loss`). "Destroyed box count for the source named in the task" = the boxes of that matter's destroyed records source, or 0 when it isn't measured in boxes.
- **Privilege counts**: for an `incomplete_log` blocker, `unlogged = withheld_count − logged_count`; `waived` = withheld docs of `third_party_waiver` entries; over-designated and miscoded-privilege counts come from their own records. Watch whether a metric means "all withheld privileged docs" vs. "the selected incomplete-log blocker only" — the template's field description says which.
- **Responsiveness miscodes**: `doc_count` of the material `miscoded_nonresponsive` / `zero_claim_contradiction` QC finding(s).
- **Personal-source counts**: material `custodian_sources` with a personal `source_type` (personal phone/email/messaging) in a not-collected/partial/lost `status`.
- **Event counts by status**: count material events per status (post-hold loss, should-exist-missing, communication gaps = auto-purge + active-system loss, pre-hold policy destroyed, available archives). A top-level "total event count" often spans **all** material events (record + communication), even when the output splits them into separate typed lists — reconcile the count against the template's decomposition and the sub-counts.
- **Category rollups**: `affected_category_count` = size of the union of affected category codes across material records; the category list = that union, **sorted ascending and upper-cased**. A "ready"/"production_ready" boolean is `false` whenever any open material gap remains.

## Schema-conformance checklist

- Output is exactly one JSON object; include every `required_top_level_keys` entry; no prose or extra keys.
- Every enum value is copied verbatim from the template's enum lists.
- Every list obeys its `ordering_rules` (sort by id / code / rank ascending); category-code lists are sorted ascending and upper-cased.
- Integers are whole numbers; use `0` where the template says "0 when not applicable"; use `null` only where the template allows it.
- List membership matches the material set exactly — no noise, no invented items, correct counts.
- Cross-field consistency: `unlogged = withheld − logged`; a metric count equals the length/derivation of the list it summarizes; `affected_category_count` equals the length of the affected-category list.

## Pitfalls

- Category schemes and hold dates differ per matter — always read them; never carry numbers between matters.
- Do not treat numbered/boilerplate records as findings, and do not drop a descriptive-ID record that the backbone anchors.
- Payload files give labels/context only; when they disagree with the hub, the hub wins.
- The deterministic outputs (matter id, record IDs, counts, metrics) are where correctness is most attainable — compute them rigorously. Qualitative enum classifications are inherently judgment calls; apply the consistent rules above rather than guessing case by case.
