# Per-family recipes

Read the task prompt and its `answer_template.json` first — the template's exact keys, enums,
`const` values, ordering, and rounding are the contract. These recipes are the reusable
procedure behind each family. Never hardcode a scope's target percentages or any computed
answer value; derive everything at runtime.

---

## A. Portfolio-mix review
*(count-based category mix of closed work vs. a target; gaps; rebalance; exclusion flags)*

1. Read scope from the prompt: `scope_id`, quarter, teams, product area(s).
2. Fetch the target: `mix_targets` row where `scope_id == <scope_id>`. Convert `*_pct`
   fractions to percentage points (×100), rounded to 1 decimal.
3. Candidate items: `team ∈ teams` AND `product_area ∈ product_areas` AND `closed_at` falls in
   the quarter.
4. Apply hygiene (see data-model.md): split out **duplicates** (`status=="Duplicate"` or
   `duplicate_of` set) and **cancelled** (`status=="Cancelled"`). Keep the rest that are in a
   **completed** state (`Closed/Done/Verified/Deployed`) as the **included primary** set.
   (Distractor tasks also drop `stale-export`/`papertrail`-flagged same-scope records.)
5. Classify each included item (classification.md) → `category_counts`.
6. `actual_pct` (1 dec) = 100·count/total. `gap_pct` (1 dec) = actual − target.
7. `under_invested` / `largest_deficit` = negative-gap categories, most negative first.
8. Follow-up / recommended action: negative gap present → `REBALANCE_CAPACITY` on the largest
   negative-gap category (`LARGEST_NEGATIVE_GAP`); none → `MAINTAIN_CURRENT_MIX` /
   `NO_NEGATIVE_GAPS`; contradictory data → `INVESTIGATE_DATA_QUALITY` / `DATA_CONFLICT`. Set
   `owner_team` / secondary fields per template.
9. Exclusion outputs: list excluded duplicate ids and cancelled ids (and distractor ids) as the
   template names them; set any `ignored_mirror_status_and_legacy_category`-style flag to `true`
   (having actually ignored those fields).
10. Order `included_work_item_ids` by `closed_at` asc then `id` asc (unless template says
    otherwise); order teams/areas as the template dictates.

---

## B. SLA-aging audit
*(primary vs. duplicate clusters; overdue/aging; breach rate; hotspots; escalation)*

1. Read scope: teams, categories (subset of `Reliability`/`Security`), `as_of` date, recent
   closed-window days.
2. Candidate items: `team ∈ teams` and category (classification.md) ∈ scope categories.
3. Hygiene: separate **duplicate clusters** — group duplicates by their `duplicate_of`
   (canonical) id; the cluster `primary_id` is that canonical item; `duplicate_ids` sorted
   lexicographically; clusters sorted by `primary_id`. Duplicates and cancelled are **not**
   counted as primary.
4. `included_primary_ids` = primary items in the SLA population (still-open items plus items
   closed within the recent window, per the template's definition), sorted as required.
5. **Overdue** primary = primary item unresolved as of `as_of` with `due_at` before `as_of`
   (breached its SLA). `overdue_primary_ids` ⊆ included.
6. Aging distribution: bucket overdue items by aging days = `as_of − due_at` into the
   template's boundaries (e.g. `0-3, 4-7, 8-14, 15-30, 31+`), or by severity when the template
   asks for severity buckets.
7. `team_overdue_counts` per team (alphabetical). `top_hotspot` = the `(team, owner)` pair with
   the most overdue primaries; `owner` null → `UNASSIGNED`.
8. `missing_owner_ids` = included primaries with null owner.
9. `breach_rate` = overdue_primary_count / included_primary_count, rounded to **3 decimals**.
10. Escalation/priority queue (when asked) = overdue primaries ordered by the template's
    priority (typically severity S1→S4, then due date / id) — read the template's wording.

---

## C. Release-readiness assessment
*(milestone completion; gating ids; blocker causes; dependency chains; readiness; ship)*

1. Identify the release id from the prompt; pull its `milestones` and its work items
   (`release_id == <release>`), plus `blockers` and `dependencies`.
2. Use authoritative status only (never `mirror_status`). Primary = non-duplicate,
   non-cancelled.
3. `milestone_completion` (sorted by `milestone_id` asc): for each milestone,
   `primary_total` = primary release items with that `milestone_id`; `complete_primary` = those
   in a completed state; `completion_pct` = 100·complete/total (1 dec).
4. `gating_work_item_ids` = non-complete primary release items (sorted ascending, unique).
5. `blocker_cause_counts` = count **unresolved** (`resolved_at` null) **high-impact**
   (`severity ∈ {High, Critical}`) blockers for the release, keyed by exact `cause` string.
6. `critical_dependency_chains` = ordered id paths following `dependencies`
   (`blocked_id → depends_on_id …`) from a blocked release work item to a **non-complete**
   dependency; sort lexicographically by the full path.
7. `readiness_score` = total complete primary / total primary denominator across the release
   (3 decimals).
8. `ship_decision` ∈ `{SHIP, SHIP_WITH_WATCH, NO_SHIP}`. Honor any thresholds the task states.
   Default heuristic when unspecified: `NO_SHIP` if unresolved high-impact blockers exist or
   readiness is low; `SHIP` if readiness is complete/near-complete with no unresolved
   high-impact blockers and no gating items; otherwise `SHIP_WITH_WATCH`.

---

## Output discipline (all families)
- Return exactly one JSON object; no prose, no code fences.
- Include precisely the template's required keys (`additionalProperties:false`).
- Round only at output (1 dec for percentages, 3 dec for rates/scores).
- Re-verify counts via both SQL and code; confirm percentages sum to ~100 and that
  excluded ids never appear in included lists.
