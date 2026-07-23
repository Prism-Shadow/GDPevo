---
name: engineering-portfolio-review
description: Analyze an engineering work-item portfolio against the shared portfolio environment (HTTP API + SQL endpoint; base URL and token live in environment_access.md). Use for portfolio-mix gap reviews, SLA aging/breach audits, and release-readiness assessments. Encodes the authoritative-status-over-mirror, primary-vs-duplicate, cancelled/distractor exclusion, 4-category resolution, stable ordering, and exact rounding rules so the single JSON answer matches the provided answer_template.json schema.
---

# Engineering Portfolio Review

Reusable procedure for tasks that ask you to analyze an engineering work-item
portfolio against the shared "portfolio" environment and return one JSON object
matching a provided `answer_template.json`.

## When to use

Use this skill when a task points you at a shared environment reached via
`environment_access.md` and asks for a single JSON answer over work-item data.
Three review archetypes live here (a task is one of them):

- **Portfolio-mix review** — classify closed work into 4 categories, compare the
  actual count-based mix to a target mix, report gaps, under-invested categories,
  and a rebalance action.
- **SLA aging / breach audit** — over reliability & security work: find overdue
  primary items, aging buckets, owner/team hotspots, duplicate clusters, missing
  owners, and the breach rate.
- **Release-readiness assessment** — ship decision, milestone completion,
  gating work items, unresolved high-impact blocker causes, critical dependency
  chains, and a readiness score.

If the task gives you `input/payloads/answer_template.json` and says "return only
a JSON object" over this environment, you are in the right place.

## Environment access — read `environment_access.md` every time

`environment_access.md` (staged alongside the task input) contains
`GDPEVO_ENV_BASE_URL`, the `X-Env-Token` header value, and the allowed endpoint
list. Rules:

- Send the `X-Env-Token` header on **every** request.
- Do **not** hardcode the URL or token, and do not use any other access path —
  `environment_access.md` is the only authorized way to reach the environment.
- Typed GET endpoints: `/api/work-items`, `/api/work-items/{id}`,
  `/api/mix-targets`, `/api/sla-policy`, `/api/releases`, `/api/releases/{id}`,
  `/api/milestones`, `/api/dependencies`, `/api/blockers`.
- SQL endpoint: `POST /api/query` with JSON body `{"sql": "<read-only SELECT>"}`.
  Returns `{columns, row_count, rows (array of arrays), truncated}`. Use it for
  joins, filters, and aggregations across the 7 tables. If `truncated` is true,
  re-query with a tighter `WHERE`/`LIMIT`. `PRAGMA` is not supported — inspect a
  table's columns via `SELECT * FROM <t> LIMIT 1` or the matching GET endpoint.
- Full table/field schema and categorical value spaces: see
  `references/data_model.md`.

## Core correctness rules (apply to every archetype)

These rules are what separate a correct answer from a plausible one. They follow
directly from the data model.

1. **Authoritative fields only.** Use the `status` field as truth; ignore
   `mirror_status`. `mirror_status` is a stale mirror/export field that
   frequently disagrees with `status` (it may read `Done`/`Complete`/`Open` when
   the authoritative status is `Cancelled`/`Verified`/`In Progress`). When a
   prompt says "do not use stale mirror fields" or "use authoritative fields," it
   means this.

2. **Ignore `legacy_category`.** It is a deprecated free-text category
   (`bug`, `feature`, `security`, `tech-debt`, …) that conflicts with reality.
   Resolve the portfolio category yourself per rule 4. Several templates make
   this explicit with an `ignored_mirror_status_and_legacy_category: true` flag.

3. **Primary vs duplicate.** A record is a **duplicate** when
   `status == "Duplicate"` **OR** `duplicate_of` is non-null. `duplicate_of`
   holds the canonical primary id. Count **primaries only** in every count,
   total, denominator, and rate. Report duplicates (grouped by their
   `duplicate_of` primary) in the answer's duplicate-cluster / exclusion lists —
   never in the counts. A duplicate can still carry a terminal `status` (e.g.
   `status: "Closed"` with `duplicate_of` set); the `duplicate_of` field decides,
   not the status.

4. **Cancelled excluded.** Records with `status == "Cancelled"` are out of the
   primary population; report them in an exclusion list if the template has one.
   Their `mirror_status` may misleadingly read `Done`.

5. **Closed / complete status set.** Treat `{Closed, Done, Deployed, Verified}`
   as terminal (closed/complete). Non-terminal: `Backlog`, `In Progress`,
   `Review`, `Reopened`. (`Cancelled` and `Duplicate` are excluded per rules 3–4.)
   This is the observed terminal set; confirm it against the prompt's wording.

6. **Portfolio category resolution** (4 categories: `NewFeature`, `TechDebt`,
   `Reliability`, `Security`). Scan `work_type` + `labels` + `title`
   (case-insensitive) for keyword signals, then assign by **precedence
   Security > Reliability > TechDebt > NewFeature** (first match wins;
   `NewFeature` is the default when nothing matches).

   | Category | Keyword signals (in work_type / labels / title) |
   |---|---|
   | Security | `security`, `cve`, `encryption`, `auth` |
   | Reliability | `reliability`, `outage`, `latency`, `flaky`, `incident` |
   | TechDebt | `refactor`, `cleanup`, `migration`, `tech-debt` |
   | NewFeature | `feature`, `rollout`, `enhancement` (also the default) |

   Trust structured `labels`/`work_type` signals over a title's narrative — a
   title like "...with stale security label" does **not** nullify an actual
   `security` label. Do not use `legacy_category`.

7. **Stable ordering** (templates enforce these):
   - ID lists: ascending / lexicographic.
   - Teams: alphabetical (unless the template pins a specific order).
   - Category tables (`gap_table` / `mix_table`): rows in the order
     `NewFeature, TechDebt, Reliability, Security`.
   - Duplicate clusters: sorted by `primary_id`; each cluster's `duplicate_ids`
     sorted ascending.
   - Dependency chains: sorted lexicographically by the full path.
   - `milestone_completion`: sorted by `milestone_id` ascending.
   - `included_work_item_ids` (portfolio): ordered by `closed_at` ascending,
     then `id` ascending.

8. **Rounding.**
   - Percentages (`actual_pct`, `target_pct`, `gap_pct`, `completion_pct`):
     1 decimal place.
   - Rates (`breach_rate`, `sla_breach_rate`, `readiness_score`): exactly
     3 decimal places.
   - `gap_pct = actual_pct − target_pct`.
   - `target_pct` comes from `mix_targets` percentage **fractions × 100** (the
     table stores a fraction like `0.25`, not the percentage `25.0`).

9. **Output format.** Return exactly one JSON object matching
   `input/payloads/answer_template.json`. Respect `additionalProperties: false`
   and the `required` list. Use `const`/`enum` values verbatim. No prose outside
   the JSON. **Field sets differ between templates** — e.g. some portfolio
   templates split exclusions into separate `excluded_duplicate_ids` and
   `excluded_cancelled_ids` flags, while others merge them into one
   `excluded_distractor_ids` list. Follow the given template, not a remembered
   shape.

## General procedure

1. **Parse the prompt.** Identify the archetype and the scope: teams,
   product_area(s), quarter, `scope_id` / target `scope_id`, `as_of` date,
   `recent_closed_window_days`, categories, and/or `release_id`.
2. **Read `environment_access.md`** for the base URL, token, and endpoint list.
3. **Read `input/payloads/answer_template.json`** and lock the exact output
   schema before computing anything.
4. **Fetch the data** you need (GET endpoints or SQL). See
   `references/data_model.md` for table/field semantics.
5. **Apply scope filters + the core rules** (primary/duplicate, cancelled,
   closed/complete set, category resolution).
6. **Compute the archetype metrics** — see `references/archetypes.md` for the
   per-archetype playbook, including the verified formulas (overdue, aging,
   readiness, gating, escalation order).
7. **Assemble the JSON** per the template; verify ordering, rounding, and
   required fields; emit only the JSON.

## Archetype playbooks

Step-by-step per archetype live in `references/archetypes.md`:

- **A. Portfolio-mix review** — mix vs target, gaps, under-invested categories,
  rebalance action, exclusion flags.
- **B. SLA aging / breach audit** — `overdue = as_of > due_at`, aging buckets,
  owner/team hotspot, duplicate clusters, missing owners, breach rate,
  escalation queue.
- **C. Release-readiness assessment** — ship decision, milestone completion,
  gating items, blocker-cause counts, dependency chains, readiness score.

## Common pitfalls

- Using `mirror_status` instead of `status` → wrong population and wrong
  overdue/complete calls.
- Counting duplicates in totals/rates → inflated counts (duplicates point at a
  primary; the primary is already counted).
- Letting `legacy_category` or a title's "stale" wording override real
  `labels`/`work_type` signals → wrong category.
- Forgetting that `Cancelled` records are excluded.
- Mis-keying `mix_targets`: the target row is selected by `scope_id` (named in
  the prompt), and its `*_pct` fields are fractions (×100 for percentage points).
- Averaging milestone percentages for `readiness_score` — it is the **pooled**
  ratio `sum(complete_primary) / sum(primary_total)`, not a mean.
- Adding fields the template does not allow, or omitting required ones.
- Emitting prose alongside the JSON.
