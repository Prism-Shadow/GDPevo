---
name: portfolio-management
description: Analyze engineering portfolio data from a shared REST environment. Use when the user needs portfolio mix reviews, SLA aging audits, release readiness assessments, work item classification, blocker/dependency analysis, or any task that involves the portfolio management endpoints (work-items, mix-targets, sla-policy, releases, milestones, blockers, dependencies, query). Trigger on mentions of portfolio mix, SLA aging, release readiness, work item classification, engineering portfolio, quarterly review, blocker analysis, dependency chains, or tasks that reference a task environment base URL with these endpoints.
---

# Portfolio Management

Work with an engineering portfolio management REST environment. The environment exposes work items, mix targets, SLA policy, releases, milestones, blockers, dependencies, and an optional SQL query endpoint. Your job is to navigate these endpoints, classify and filter work items according to portfolio conventions, perform domain calculations (percentages, SLA aging, readiness scores), and produce structured JSON answers.

## Getting oriented

The user will provide a base URL, typically `<TASK_ENV_BASE_URL>`. The environment access file lists available endpoints. Read it first.

Available endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/work-items` | All work items in the environment (single JSON array under key `work_items`) |
| GET | `/api/work-items/{item_id}` | Single work item by ID |
| GET | `/api/mix-targets` | Portfolio mix targets by scope |
| GET | `/api/sla-policy` | SLA severity-to-days mapping |
| GET | `/api/releases` | Release definitions |
| GET | `/api/releases/{release_id}` | Single release by ID |
| GET | `/api/milestones` | All milestones across releases |
| GET | `/api/dependencies` | Dependency relationships between work items |
| GET | `/api/blockers` | Blocker records against work items |
| POST | `/api/query` | Restricted SQL queries (may require an `X-Env-Token` header) |

Always fetch the full dataset from the list endpoints rather than querying items one at a time. The `work-items` endpoint returns all items; filter and classify in memory.

## Work item record shape

Each work item has these fields:

| Field | Purpose |
|-------|---------|
| `id` | Unique identifier (e.g. `WI-24024-X000`) |
| `title` | Human-readable description |
| `status` | Authoritative current state (`In Progress`, `Review`, `Closed`, `Done`, `Verified`, `Deployed`, `Duplicate`, `Cancelled`, `Backlog`, `Reopened`, etc.) |
| `work_type` | Primary type (`Feature`, `Bug`, `Security`, `Reliability`, `Incident`, `Refactor`, `Dependency`, `Enhancement`, `Chore`, `Compliance`) |
| `labels` | Array of tag strings (`security`, `reliability`, `feature`, `cve`, `cleanup`, `refactor`, `migration`, `rollout`, `outage`, `flaky`, `latency`, `stale-export`, etc.) |
| `legacy_category` | Older classification field (`security`, `quality`, `new`, `tech-debt`, `maintenance`, `bug`, `feature`, `admin`) — useful as a hint but not authoritative |
| `product_area` | Business domain (`Atlas Backend`, `Identity`, `Checkout`, `Data Reliability`, `Security Operations`, `Core Runtime`, `Edge Routing`, `Revenue Systems`, `Release Train`, `API Connectivity`) |
| `team` | Owning team |
| `owner` | Person assigned (may be `null`) |
| `severity` | `S1`, `S2`, `S3`, `S4` |
| `priority` | Integer 1-5 |
| `created_at` | ISO date |
| `closed_at` | ISO date or `null` |
| `due_at` | ISO date |
| `duplicate_of` | ID of the canonical/primary work item this duplicates, or `null` |
| `mirror_status` | **Stale/inconsistent export field — never use this as the source of truth.** Always read `status` for the actual state. |
| `milestone_id` | Associated milestone or `null` |
| `release_id` | Associated release or `null` |
| `story_points` | Integer size estimate |

## Authoritative field rule

**`status` is authoritative; `mirror_status` is not.** The `mirror_status` field is a stale export artifact that may contradict the real `status`. Take all decisions (closed vs. open, complete vs. incomplete, duplicate detection) from `status`, `closed_at`, `duplicate_of`, and `work_type`/`labels`/`title`. Never gate logic on `mirror_status`.

Similarly, if a record carries the `stale-export` label, treat its metadata with extra suspicion — prefer the primary fields over any mirrored or legacy data.

## Portfolio category classification

Work items must be classified into exactly one of four portfolio categories: **NewFeature**, **TechDebt**, **Reliability**, **Security**. The category is not stored directly on a work item; derive it from the signals below.

### Signal sources and priority

Classify each work item by checking signals in this order. The first category with a **dominant, unambiguous signal** wins. When signals conflict, weigh the substance of the work (what the team actually did) over incidental labels or stale metadata.

**Security signals** (classify as `Security` if dominant):
- `work_type` is `Security` or `Compliance`
- Labels contain `security`, `cve`, `encryption` (and the work is not primarily a refactor/cleanup of security infrastructure — check the title)
- `legacy_category` is `security` — use this as corroboration, not as a standalone reason

**Reliability signals** (classify as `Reliability` if dominant):
- `work_type` is `Reliability` or `Incident`
- Labels contain `reliability`, `outage`, or `incident` (without stronger security signals)
- Bug work items that carry `reliability` or `outage` labels are Reliability, not NewFeature or TechDebt
- `legacy_category` of `bug` or `quality` combined with `reliability`/`outage` labels

**TechDebt signals** (classify as `TechDebt` if dominant):
- `work_type` is `Refactor`, `Dependency`, or `Chore`
- Labels contain `cleanup`, `refactor`, or `migration` — and the item lacks stronger reliability or security signals
- `legacy_category` is `tech-debt` or `maintenance` — corroboration, not standalone

**NewFeature** (default when no stronger signal applies):
- `work_type` is `Feature` or `Enhancement` and the item lacks dominant Security, Reliability, or TechDebt signals
- Only use NewFeature when the item is genuinely feature work, not when feature labels are incidental

### Resolving conflicts

When an item carries signals from multiple categories:

1. **Work type overrides labels.** A `Security` work type makes the item Security even if it has `feature` labels. A `Reliability` or `Incident` work type makes it Reliability.
2. **Security dominates Reliability.** An item with both security and reliability labels leans Security unless the work type clearly says Reliability/Incident.
3. **Labels of `cleanup`, `refactor`, `migration` make an item TechDebt** unless overridden by Security or Reliability work types. A Feature with `migration` labels and `maintenance` legacy is TechDebt, not NewFeature.
4. **When labels are evenly split**, use the title and `legacy_category` as tiebreakers. The title often reveals what was actually done.
5. **`stale-export` and `stale` labels** are warnings, not classification signals. They don't change the category.

### Exclusion rules

Before classifying, remove these from the primary population:

- **Duplicates** — Items with `status` of `"Duplicate"` or a non-null `duplicate_of` field. Track them separately as exclusion flags (they point to their canonical item). Do not count them in the primary category counts.
- **Cancelled items** — `status` of `"Cancelled"`. Track them as excluded. Do not count them.
- **Not-closed items for portfolio mix** — When the task asks for a "closed portfolio mix", only include items that have a non-null `closed_at` and a status indicating completion (`Closed`, `Done`, `Verified`, `Deployed`). Items that are `In Progress`, `Review`, `Backlog`, or `Reopened` without a `closed_at` are not yet closed.

For SLA audits, include items that are in progress but not yet closed, as long as they match the scope.

## Portfolio mix analysis

When building a portfolio mix:

1. Get the mix target for the given `scope_id` from `/api/mix-targets`. The target has `new_feature_pct`, `tech_debt_pct`, `reliability_pct`, `security_pct` in decimal form. Multiply by 100 to get percentage points.
2. Filter work items to the scope (teams, product areas, quarter, closed status).
3. Exclude duplicates and cancelled items, recording their IDs.
4. Classify each remaining item into one category.
5. Count items per category. Compute percentages: `(category_count / total_included) * 100`, rounded to 1 decimal place.
6. For each category, compute `gap_pct = actual_pct - target_pct`, also in percentage points rounded to 1 decimal.
7. Under-invested categories are those with negative `gap_pct`, ordered from most negative to least negative.

## SLA aging analysis

SLA policy is at `/api/sla-policy`:

| Severity | Days to due |
|----------|-------------|
| S1 | 3 |
| S2 | 10 |
| S3 | 21 |
| S4 | 45 |

An item is **overdue** on the as-of date if: `as_of_date > due_at` AND the item is not closed (no `closed_at`, or `closed_at > as_of_date`). Items closed before or on the as-of date are not overdue regardless of their due_at.

To compute aging: `aging_days = as_of_date - created_at` (in days). But note: for the aging bucket, use the time since creation, not since the due date. Confirm from the answer template exactly what aging represents — different tasks may ask for different windows.

The **breach rate** is: `overdue_primary_count / included_primary_count`, rounded to 3 decimal places.

For duplicate clusters: when an item has `duplicate_of` pointing to a primary ID, that primary ID and all its duplicates form a cluster. Duplicates are excluded from primary counts but reported as clusters.

For the escalation queue (when requested), order overdue items by severity (S1 first), then by due date (earliest first), then by ID.

## Release readiness

For a release readiness assessment:

1. Get the release from `/api/releases/{release_id}`.
2. Get all milestones from `/api/milestones`, filter to those with `release_id` matching.
3. Get all work items, filter by `release_id` and `milestone_id`. Separate primary items from duplicates (duplicates do not count toward primary completion).
4. For each milestone, compute: `completion_pct = (completed_primary / primary_total) * 100` rounded to 1 decimal. A primary item is "complete" when its `status` is `Closed`, `Done`, `Verified`, `Deployed`, or `Closed`.
5. **Ship decision**: consider incomplete work items, unresolved high-impact blockers (severity `High` or `Critical`, not `Resolved`), and critical dependencies.
   - `SHIP`: all milestones have high completion, no unresolved high/critical blockers, no gating dependencies.
   - `SHIP_WITH_WATCH`: acceptable completion but some low-risk open items or blockers.
   - `NO_SHIP`: significant incomplete work, unresolved high/critical blockers, or broken dependency chains.
6. Gating work item IDs are the non-complete release work items that block readiness — typically those in `In Progress`, `Review`, or `Backlog` status.
7. Unresolved high-impact blockers: filter blockers to those with `severity` of `High` or `Critical` and `status` not `Resolved`. Count by exact `cause` string.
8. Dependency chains: for each gating work item, trace `depends_on` relationships where `relation` is `blocks-release-readiness` or similar. Follow the chain until you reach a non-complete dependency or a leaf. Sort chains lexicographically by the full path.
9. Readiness score: `completed_primary / total_primary` across all release work, rounded to 3 decimal places.

## Ordering conventions

Apply these ordering rules consistently:

- Work item ID lists: sort **lexicographically** (standard string sort) unless the answer template explicitly asks for chronological order.
- Team names: sort **alphabetically**.
- Duplicate clusters: sort by `primary_id` lexicographically; within each cluster, sort `duplicate_ids` lexicographically.
- Gap table / mix table rows: list in fixed order: NewFeature, TechDebt, Reliability, Security.
- Milestone completion: sort by `milestone_id` ascending.
- Gating work item IDs: sorted ascending, no duplicates.

When a template demands `closed_at` ascending then `id` ascending, use that ordering instead.

## Precision

- Percentages (completion_pct, actual_pct, target_pct, gap_pct): **1 decimal place**.
- Rates (breach_rate, readiness_score): **3 decimal places**.
- All counts are integer item counts, not story points.

## Dealing with query endpoint

The `/api/query` endpoint accepts POST with `{"query": "<SQL>"}` and may require an `X-Env-Token` header. The token, if needed, is in the environment access file. Use this endpoint sparingly — only when the standard REST endpoints cannot answer a question efficiently. Never use it to bypass the classification rules described above.

## Answer format

The user will provide an answer template file (JSON Schema or example JSON). Follow the template exactly:
- Include every `required` field.
- Do not add extra fields beyond what the template defines.
- Match enum values precisely.
- Follow the ordering and precision rules stated in the prompt and template.

If the template uses `$schema` and `const` constraints, your output must satisfy them — the schema is part of the contract.

## Common pitfalls

1. **Using `mirror_status` instead of `status`.** This is the most frequent error. Check `status` for every decision. `mirror_status` is stale.
2. **Counting duplicates as primary work.** Items with `status: "Duplicate"` or non-null `duplicate_of` are not primary. Exclude them from counts and completion rates.
3. **Classifying by `work_type` alone.** An item with `work_type: "Feature"` might be TechDebt if its labels and title show migration/cleanup work. Always cross-check labels and title.
4. **Double-counting items in dependency chains.** Each work item ID should appear in exactly one role. If an item is a gating item, it's not also a "dependency of" unless the answer template explicitly calls for that.
5. **Forgetting to exclude closed items from overdue calculations.** If `closed_at <= as_of_date`, the item is not overdue even if `due_at < as_of_date`.
6. **Using story points for percentages.** All mix percentages are count-based, not effort-based, unless explicitly stated otherwise.

## Reference files

- [references/data-model.md](references/data-model.md) — detailed field reference and edge-case catalog from the training environment
