---
name: portfolio-work-item-analysis
description: Analyze the shared portfolio work-item environment to produce portfolio-mix reviews, SLA-aging audits, and release-readiness assessments. Use whenever a task points at the portfolio environment (work items, mix targets, SLA policy, releases, milestones, dependencies, blockers) and asks for a single JSON answer. Read this before fetching any data.
---

# Portfolio Work-Item Analysis

This skill handles a family of analysis tasks against one shared environment of
work items. Every task gives you a `prompt.txt` and an `answer_template.json`
(the JSON Schema contract) and asks for **a single JSON object, no prose**.

Three archetypes recur:

- **Portfolio mix review** — closed-work category mix vs. a target mix.
- **SLA aging audit** — overdue / aging analysis of reliability & security work.
- **Release-readiness assessment** — ship decision for one release.

The hard parts are never the math. They are (a) selecting the *right* records and
excluding duplicates / cancelled / distractors, and (b) using **authoritative**
fields while ignoring stale mirror/export fields. Get those right and the rest
follows.

## Always-on workflow

Run these steps for every task, in order.

1. **Read the contract.** Open `prompt.txt` and `input/payloads/answer_template.json`.
   The template is the spec: its `required` list, `enum` values,
   `additionalProperties: false`, `const` fields, ordering notes, and precision
   notes are mandatory. Match it exactly — no extra keys, no missing keys.
2. **Extract scope.** Pull teams, quarter or as-of date, product area(s),
   categories, window length, release id, and `scope_id` from the prompt. The
   `scope_id` selects the target-mix row; do not invent one.
3. **Get access.** Read `environment_access.md` for the base URL, the
   `X-Env-Token` value, and the allowed endpoint list. Use **only** that file for
   network access — do not hardcode URLs or tokens. See
   `references/access_and_query.md` for HTTP and SQL-query mechanics.
4. **Fetch what you need.** Pull the endpoints / tables the archetype requires
   (see `references/data_model.md` for the schema). Prefer the REST endpoints for
   whole-collection reads; use `POST /api/query` only for filtered/aggregated SQL.
5. **Apply universal data hygiene** (below) to separate primary work from
   duplicates, cancelled, and distractors.
6. **Compute** per the archetype rules below.
7. **Emit one JSON object** matching the template. No prose. Respect ordering and
   precision. Validate mentally against the schema before finishing.

## Universal data-hygiene rules (apply to every archetype)

These rules are the substance of the skill. They are derived from the actual
environment schema — see `references/data_model.md` for field vocabularies.

### Use authoritative fields; ignore stale ones
- **Authoritative** (use these): `status`, `work_type`, `owner`, `team`,
  `product_area`, `created_at`, `due_at`, `closed_at`, `severity`, `priority`,
  `labels`, `release_id`, `milestone_id`, `duplicate_of`.
- **Stale — never use as truth**:
  - `mirror_status` — a stale export of status. Ignore for any status/closed
    decision. (The prompt calls this out as "stale mirror fields"; some templates
    require `ignored_mirror_status_... = true`.)
  - `legacy_category` — a stale category tag. Ignore for portfolio category;
    classify from `work_type` / `labels` / `title` using the conventions below.

### Status → class
Map `status` (authoritative) as follows. `closed_at` is populated exactly for the
resolved states, so it is a reliable secondary signal.

| status                         | closed_at | class                              |
|--------------------------------|-----------|------------------------------------|
| `Closed`, `Done`, `Deployed`, `Verified` | set       | **completed / terminal** (closed work) |
| `Cancelled`                    | set       | **excluded** — cancelled           |
| `Duplicate`                    | set       | **excluded** — duplicate           |
| `Backlog`, `In Progress`, `Review`, `Reopened` | null      | **open / active**                  |

### Primary vs duplicate
- A record is a **duplicate (non-primary)** when `duplicate_of IS NOT NULL`
  (it points at its canonical primary) — primary signal — **or** `status = "Duplicate"`
  (corroborating signal). Treat either as a duplicate.
- **Primary records** (the ones you count) are: not a duplicate **and** not
  cancelled (`status` not in `Duplicate`/`Cancelled` and `duplicate_of` is null).
  Note the orphan edge case: `status = "Duplicate"` with `duplicate_of` null has
  no primary to cluster under — exclude it from primary counts; it cannot appear
  in a cluster.
- **Duplicate clusters**: for every record that has `duplicate_of` set,
  `primary_id = duplicate_of` (the canonical work item it points at) and the
  record's own `id` goes into that cluster's `duplicate_ids`. Duplicates are
  **reported** in `duplicate_clusters` but **never counted** as primary work.

### Distractors
Some records match the scope superficially (same team / area / quarter) but are
not primary closed portfolio work — they are open, duplicates, or cancelled.
Exclude them from the primary set and, where the template asks
(`excluded_distractor_ids`, exclusion flags), list them.

### Id discipline
- Use each included id **exactly once** across the answer.
- Sort id lists as the template specifies (usually lexicographically / ascending).
- Sort team / product-area lists alphabetically unless the template fixes an order.

### Precision
- Percentages / percentage points: **1 decimal place**.
- Rates (breach rate, readiness score): **3 decimal places**.
- `gap_pct = actual_pct − target_pct` (percentage points).

## Portfolio category classification

Four categories: `NewFeature`, `TechDebt`, `Reliability`, `Security`. Each
included item maps to **exactly one**. Resolve conflicting `work_type` / `labels`
/ `title` signals with this priority (a higher-priority signal wins):

1. **Security** — `work_type = Security` or `Compliance`; labels/title contain
   `security`, `cve`, `auth`, `encryption`.
2. **Reliability** — `work_type = Reliability` or `Incident`; labels/title contain
   `reliability`, `incident`, `outage`, `latency`, `flaky`.
3. **TechDebt** — `work_type = Refactor`, `Bug`, or `Chore`; labels/title contain
   `cleanup`, `refactor`, `tech-debt`, `deprecate`, `migrate`.
4. **NewFeature** — `work_type = Feature` or `Enhancement`; labels/title contain
   `feature`, `rollout`.

When signals conflict, prefer an explicit portfolio-category **label** over
`work_type`, and `work_type` over title keywords. Apply the rule consistently
across all items. (Never use `legacy_category`.)

## Archetype A — Portfolio mix review

*Examples: closed-work mix readout for a quarter, scope, and set of teams.*

1. **Select in-scope closed primary work**: `closed_at` within the stated quarter,
   `team` in the scope teams, `product_area` in the scope areas, status is a
   completed terminal (`Closed`/`Done`/`Deployed`/`Verified`), and the record is
   primary (not duplicate, not cancelled).
2. **Exclude & report**: duplicates and cancelled in-scope records go to the
   exclusion flags / distractor list the template defines.
3. **Classify** each included item into one portfolio category.
4. **Counts are item counts, not story points.** `total_included = sum(counts)`.
5. **actual_pct** = `count / total_included × 100`, 1 decimal.
6. **Target**: read the `mix_targets` row whose `scope_id` matches the prompt's
   `scope_id`. Target fractions are 0–1; multiply by 100 for percentage points.
7. **gap_pct** = actual − target, 1 decimal. Build the gap/mix table in the fixed
   order `NewFeature, TechDebt, Reliability, Security`.
8. **Under-invested / largest deficit** = category with the most negative
   `gap_pct`. List under-invested categories ordered most-negative → least-negative.
9. **Follow-up action**:
   - `REBALANCE_CAPACITY` when there is a negative gap (point at the largest
     deficit category; `owner_team` = the scope team that owns that category's
     work).
   - `MAINTAIN_CURRENT_MIX` when no gap is negative (`rationale_code = NO_NEGATIVE_GAPS`).
   - `INVESTIGATE_DATA_QUALITY` when the data conflicts (`rationale_code = DATA_CONFLICT`).
   - Otherwise `rationale_code = LARGEST_NEGATIVE_GAP`.
10. **Ordering**: `included_work_item_ids` by `closed_at` ascending, then `id`
    ascending. Teams / product areas alphabetical (or the order the template fixes).

## Archetype B — SLA aging audit

*Examples: reliability & security SLA aging for given teams, as-of date, window.*

1. **Primary SLA population** (`included_primary_ids`): primary work (not
   duplicate, not cancelled) for the scope teams whose portfolio category is in
   the SLA categories (typically `Security` and `Reliability`). Sort ascending.
2. **SLA due date** = `created_at + sla_policy.days_to_due` for the item's
   `severity` (S1=3, S2=10, S3=21, S4=45 days — read `sla_policy` to confirm).
3. **Overdue** (`overdue_primary_ids`): an item is overdue when its SLA due date
   has passed relative to the reference date — `as_of` for still-open items
   (`closed_at` null), `closed_at` for items that have closed. Reference date >
   SLA due date ⇒ overdue. Subset of included primary ids; sort ascending.
4. **Aging buckets** `0-3`, `4-7`, `8-14`, `15-30`, `31+` (days). Age = elapsed
   days from `created_at` to the reference date (as_of for open, closed_at for
   closed). Bucket each primary item; confirm the exact population (included
   primary vs. overdue) from the prompt + template.
5. **breach_rate / sla_breach_rate** = `overdue_primary_count /
   included_primary_count`, 3 decimals.
6. **By-severity** (`overdue_counts_by_severity`): count overdue primary items per
   `S1/S2/S3/S4`.
7. **Team / owner hotspot**: count overdue primary items per team, and per
   (team, owner) pair. `top_hotspot` = the pair with the most overdue; `owner` =
   `"UNASSIGNED"` when `owner` is null. Teams listed alphabetically.
8. **Escalation queue** (`escalation_queue_ids`): overdue primary ids in priority
   order for follow-up — sort by `priority` ascending (1 = highest), then
   `severity` (S1 > S2 > S3 > S4), then `due_at` ascending, then `id` ascending.
9. **missing_owner_ids**: included primary ids with `owner` null, sorted ascending.
10. **duplicate_clusters**: grouped by `primary_id = duplicate_of`,
    `duplicate_ids` sorted ascending, clusters sorted by `primary_id`.

## Archetype C — Release-readiness assessment

*Example: ship decision for a single release id.*

1. **Release work items** = `work_items` with `release_id` = the release under
   review. Restrict to **primary** (non-duplicate). Use authoritative `status`
   only — never `mirror_status` — as release truth.
2. **Milestone completion**: for each milestone in the release (from
   `milestones` where `release_id` matches), `primary_total` = primary release
   work items assigned to that `milestone_id`; `complete_primary` = those whose
   status is a completed terminal (`Closed`/`Done`/`Deployed`/`Verified`);
   `completion_pct` = complete/total × 100, 1 decimal. Sort by `milestone_id`
   ascending.
3. **Gating work item ids** = non-complete primary release work items (status not
   a completed terminal), sorted ascending, de-duplicated.
4. **Blocker cause counts**: from `blockers` for this release, count only
   **unresolved** (`resolved_at` null) **high-impact** (`severity` High or
   Critical) blockers, keyed by the **exact** `cause` string.
5. **Critical dependency chains**: from `dependencies`, follow `depends_on_id`
   edges starting from blocked release work items. A chain is an ordered path of
   work-item ids from a blocked release work item to a dependency that is
   non-complete (status not a completed terminal). `relation` values such as
   `blocks-release-readiness`, `validation-required`, `security-review-required`,
   `audit-evidence-required`, `implementation-dependency`, `depends-on` describe
   the edge; include edges that gate readiness. Sort chains lexicographically by
   the full id path.
6. **readiness_score** = `completed_primary_release_work / primary_release_denominator`,
   3 decimals.
7. **ship_decision**:
   - `SHIP` — readiness is complete, no gating items, no unresolved high-impact
     blockers, no non-complete critical dependencies.
   - `SHIP_WITH_WATCH` — broadly ready but with watchable risk (e.g., minor
     blockers or a small number of non-critical non-complete items).
   - `NO_SHIP` — open gating work, unresolved high-impact blockers, or broken
     critical dependency chains.

## Output discipline (all archetypes)

- Return **one JSON object** matching `answer_template.json` exactly: every
  `required` field present, values within `enum`, no keys beyond the schema
  (`additionalProperties: false`), `const` fields equal to their fixed value.
- **No prose outside the JSON.**
- Apply the ordering the template specifies; where it does not, sort ids
  ascending and names alphabetically.
- Round as specified (percentages 1 decimal, rates 3 decimals).
- Use each included id exactly once; de-duplicate id lists unless told otherwise.

## Final checks before submitting

- Did I use `status` (not `mirror_status`) for every closed/overdue decision?
- Did I classify from `work_type`/`labels`/`title` (not `legacy_category`)?
- Are duplicates excluded from counts and only reported in clusters?
- Are cancelled and distractor records excluded and listed where required?
- Does every list match the template's required ordering?
- Are all percentages 1 decimal and all rates 3 decimals?
- Does the object validate against the schema (required, enums, no extra keys)?
