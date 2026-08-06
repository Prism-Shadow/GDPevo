---
name: portfolio-engineering-audit
description: Entry instructions for solving portfolio-engineering audit tasks (work-item portfolio-mix reviews, SLA-aging audits, and release-readiness assessments) against the shared work-items environment. Use when you must produce a single JSON answer for one of these audit task types and want the validated field conventions for scope, classification, duplicates, authoritative-vs-stale fields, ordering, and precision.
---

# Portfolio Engineering Audit Solver

This skill gives the **entry instructions** for three recurring portfolio-engineering audit
task families that share one work-items environment. Each task hands you `input/prompt.txt`
(business scope + what to return) and `input/payloads/answer_template.json` (the exact JSON
shape). Produce **one JSON object** matching the template, with **no prose outside the JSON**.

These instructions capture the conventions that were validated by scoring; they are generic and
contain no task-specific answers. Apply them to whichever family the prompt describes.

## 0. Universal conventions (apply to all three families)

### 0.1 Authoritative vs stale fields
The environment carries both authoritative fields and stale "mirror/export" fields. The prompts
explicitly tell you to use authoritative fields.

- `status`, `closed_at`, `created_at`, `due_at`, `owner`, `team`, `product_area`, `work_type`,
  `severity`, `priority`, `labels`, `title`, `duplicate_of` are **authoritative**. Use them.
- `mirror_status` is a STALE/legacy status — **ignore it**. It disagrees with `status` on most
  records and is a trap.
- `legacy_category` is a stale/legacy category — **ignore it** for classification.
- The `stale-export` label is not a category signal — ignore it.
- Title **disclaimers** ("stale security label", "with auth title", etc.) are RED HERRINGS. Do
  **not** demote/relax a classification because of them; classify on the actual signals.

### 0.2 The "complete / closed" status set
`CLOSED = {Closed, Done, Verified, Deployed}`. Anything else (Backlog, In Progress, Review,
Reopened, Duplicate, Cancelled, Blocked, …) is non-complete/open for ageing and readiness math.

### 0.3 Duplicates — `duplicate_of` is authoritative
A work item is a **duplicate** when `duplicate_of` is non-null — **regardless of its `status`**.
Some duplicates carry a non-`Duplicate` (stale/mirror) status (e.g. status `Closed` but
`duplicate_of` set). Filtering duplicates by `status == 'Duplicate'` only misses these hidden
duplicates. Use `duplicate_of` non-null **or** `status == 'Duplicate'` (the latter is a subset).
- Duplicates are **separated out**, never counted in a primary/included set.
- Group duplicates into clusters keyed by their canonical primary (`duplicate_of`).
- An **orphan duplicate** (`status == 'Duplicate'` but `duplicate_of == null`) has no canonical
  primary; exclude it from primary and emit no cluster for it.
- `Cancelled` is excluded from primary sets (it is cancelled work, not a duplicate).

### 0.4 Classification — pure risk precedence
Classify every included work item into exactly one of four categories using **pure risk
precedence**: `Security > Reliability > TechDebt > NewFeature`, computed over the **union** of
`work_type` + `labels` + `title` signals.

Keyword sets (match on whole words / labels, case-insensitive):
- **Security**: security, cve, auth, encryption, compliance, audit, harden, patch, rotate, remediation
- **Reliability**: reliability, latency, outage, flaky, incident, stabilize, repair, recover, rehearsal
- **TechDebt**: cleanup, refactor, migrate, migration, deprecate, tech-debt
- **NewFeature**: feature, rollout, launch, extend, enable, build

`work_type → category` mapping (one signal in the union):
- Feature, Enhancement → NewFeature
- Security, Compliance → Security
- Reliability, Incident, Bug → Reliability
- Refactor, Chore, Dependency → TechDebt

Take the **highest-precedence** category present across all three signal sources. Do **not**
reweight by how many sources agree, do **not** honor title disclaimers, do **not** consult
`legacy_category`/`mirror_status`. (`work_type = Bug` counts as a Reliability signal, so an item
with no reliability keyword in its title can still be Reliability via work_type.)

A ready-to-use implementation is in `skill/classify.py`.

### 0.5 As-of awareness (audit-time truth)
When a prompt gives an **as-of date**, that is the audit cutoff. An item whose `closed_at` is
**after** the as-of date was **open at audit time**, even if its `status` field now reads
`Closed`/`Done`/`Verified` (it transitioned post-audit). Compare `closed_at <= as_of`, not the
current status string, when deciding open-vs-closed-at-audit. (Symmetric trap: an item with
status `Closed` but `duplicate_of` set is a hidden duplicate, not primary.)

### 0.6 Ordering and precision (match the template)
- ID lists: sorted **lexicographically ascending** (string sort — `WI-...-S021` sorts among the
  `-0xx` ids by string order).
- Teams in scope: the template's `teams` array order (usually alphabetical, but follow the template).
- Duplicate clusters: sorted by `primary_id`, each cluster's `duplicate_ids` sorted ascending.
- Milestone lists: sorted by `milestone_id` ascending.
- Dependency-chain paths: sorted lexicographically by the full path.
- Percentages: 1 decimal place. Rates (`sla_breach_rate`, `readiness_score`): **3 decimal places**.
- Severity counts are plain integers keyed `S1..S4`.
- The **escalation queue** and any other "ordered" list are the only places order is meaningful;
  sort ID *sets* lexicographically, but keep the escalation queue in escalation order (see §2).

### 0.7 Read the encoded ground-truth titles
Some seeded items (often an `S###` id series) have **titles that literally state the intended
audit status**: "…overdue", "…not overdue", "…closed late", "…closed before due", "…due today",
"…owner gap", "duplicate …", etc. Treat these phrases as ground truth:
- "overdue" / "due today" → overdue (due == as-of counts as overdue; boundary is overdue).
- "not overdue" / "closed before due" → not overdue.
- "closed late" → closed after its due date → overdue.
- "owner gap" → no owner (goes in missing-owner).
- "duplicate …" → belongs in a duplicate cluster, not primary.
When your computed answer disagrees with these title phrases, trust the title and re-check your
rule — these items exist to calibrate the conventions.

## 1. Family A — Portfolio-mix review (e.g. "Q4 closed-work portfolio mix")

**Scope:** team **and** product_area match the prompt; quarter filter on `closed_at` (e.g. Q4 =
`closed_at` month in Oct/Nov/Dec); closed set = `status in CLOSED`.

**Included set** = in-scope items that are closed in-period, **primary** (not duplicate per §0.3)
and not Cancelled. Hidden duplicates (closed status but `duplicate_of` set) **must** be excluded.

**Answer fields** (per template):
- `included_work_item_ids`: the primary closed set, sorted.
- `category_counts`: count of included items per category {NewFeature, TechDebt, Reliability,
  Security} via §0.4.
- `actual_pct`: one-decimal share of each category in the included total.
- `target_pct`: from the `mix_targets` row matching the prompt's `scope_id` (pull that row).
- `gap_pct`: `actual_pct − target_pct`, one decimal (negative = under-invested).
- `largest_deficit_category`: the category with the most-negative gap (most under target).
- `recommended_action`: typically `{action: REBALANCE_CAPACITY, category: <largest deficit>,
  owner_team: <team that owns the most included items in that category>}`.
- `excluded_distractor_ids`: in-scope in-period items excluded from primary closed work —
  duplicates (including hidden ones via `duplicate_of`) and Cancelled.

**Key traps:** hidden duplicates with a closed status; Cancelled records that look closed; the
`mix_targets` row is keyed by `scope_id` from the prompt, not by team.

## 2. Family B — SLA-aging audit (e.g. "SLA aging / SLA audit for two teams")

**Scope:** teams from the prompt; `categories = [Security, Reliability]` (use §0.4 to decide
membership — an item is SLA-relevant iff it classifies as Security or Reliability); an **as-of**
date and a **recent-closed window** in days.

**Primary population** = SLA-relevant (Security/Reliability), non-duplicate (§0.3), non-Cancelled
items that are **open at audit** (`closed_at` null or `closed_at > as_of`) **or** closed-at-audit
within the recent-closed window (`as_of − window_days <= closed_at <= as_of`). Apply §0.5: an item
closed after as-of is open-at-audit and IS primary even if status now reads closed.

**Overdue** = primary item with `due_at <= as_of` (boundary due==as-of counts as overdue; applies
to open AND recently-closed items). **Do not** compute overdue from the SLA-policy
`days_to_due[severity]` window — the policy table is reference metadata only; `due_at` is the
overdue clock. (Verify against the S-title phrases in §0.7 before adopting any other clock.)

**Answer fields** (per template):
- `included_primary_ids`: primary set, sorted.
- `overdue_primary_ids`: overdue primary ids, sorted.
- `overdue_counts_by_severity`: `{S1,S2,S3,S4}` integer counts of the overdue set.
- `escalation_queue_ids`: the overdue primary ids **in escalation order** (the only ordered list).
  Default to **priority ascending** (the `priority` field, 1 = highest), tie-broken by oldest
  `due_at` first, then id — but be aware "priority order" is under-specified; if a flat-zero score
  persists across set changes, the escalation ordering is a prime suspect (see §0.8).
- `missing_owner_ids`: included primary items with no `owner`, sorted.
- `duplicate_clusters`: `[{primary_id, duplicate_ids[]}]`, sorted by primary_id; include only
  duplicates whose canonical primary is in this audit's scope (an out-of-scope canonical is not
  part of this audit's cluster set).
- `sla_breach_rate`: `len(overdue) / len(primary)`, 3 decimals.

**Key traps:** closed-after-as-of items that look closed; orphan duplicates; out-of-scope
canonical primaries in clusters; confusing the SLA-policy window with the overdue clock.

## 3. Family C — Release-readiness assessment (e.g. "release REL-… readiness")

**Scope:** all work items whose `release_id` matches the prompt's release. Use authoritative
release/milestone/status/blocker/dependency data — not mirror fields.

**Answer fields** (per template):
- `ship_decision`: one of `SHIP`, `SHIP_WITH_WATCH`, `NO_SHIP`. Rule of thumb: any unresolved
  **Critical** blocker, or readiness below threshold → `NO_SHIP`; high-impact unresolved blockers
  but no Critical and readiness above threshold → `SHIP_WITH_WATCH`; else `SHIP`.
- `milestone_completion`: for every milestone in this release, `{milestone_id, complete_primary,
  primary_total, completion_pct}` over **primary** release items (exclude duplicates), sorted by
  `milestone_id` ascending. complete = status in CLOSED; completion_pct 1 decimal.
- `gating_work_item_ids`: non-complete **primary** release items, sorted, deduped.
- `blocker_cause_counts`: counts keyed by **exact cause text**, over unresolved
  (`resolved_at` null) **high-impact** (severity `High` or `Critical`) blockers for this release.
  Low-severity unresolved blockers are excluded.
- `critical_dependency_chains`: ordered id paths following the `blocks-release-readiness` (or
  equivalent gating) relation from a release work item to a **non-complete** terminal dependency,
  single-hop unless longer chains exist; sorted lexicographically by full path.
- `readiness_score`: completed-primary / primary-total, 3 decimals.

**Key traps:** duplicates in the primary/milestone denominator ("primary" wording excludes them);
`high-impact` = `High`/`Critical` only; chains follow the gating relation to a non-complete
terminal dependency (a dependency that is itself complete does not produce a chain).

## 0.8 Working method under scalar-only feedback
The judge returns only a score (and a `correct` boolean) — **no per-field feedback, no correct
values**. Consequences for your process:

- You get a small, fixed number of feedback rounds per task. Treat each round as expensive.
- Make your first candidate your best single interpretation; on later rounds change the **most
  uncertain single assumption** per round so a score change localizes it.
- A **score that stays identical across rounds where you changed set-membership fields** means
  the blocker is on a field that did NOT change (typically the ordered escalation list, the scope
  object, or a convention applied identically each time). When stuck, re-examine the unchanged
  fields and the ordering/precision rules (§0.6), not the IDs.
- Some tasks plateau (a nonzero score you cannot fully localize). That is expected; record the
  best-scoring candidate and move on rather than burning rounds on undirected churn.
- Always cross-check computed overdue/breach/classification against the §0.7 title phrases before
  spending a feedback round — they are free, definitive signal.

## How to use this skill
1. Read the task's `prompt.txt` → identify the family (A mix / B SLA / C release).
2. Read `answer_template.json` → that is the exact field contract; match keys, types, ordering,
   and precision. If the template differs from this skill's field list in naming, **follow the
   template**.
3. Pull the environment's work items (and milestones/releases/dependencies/blockers/mix-targets
   as the family needs) and apply §0 conventions, then the family section.
4. Emit one JSON object, no prose.
5. If feedback is available, spend rounds as in §0.8.
