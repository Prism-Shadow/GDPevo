# Engineering Portfolio Rules

## Authoritative Fields

Use current work item fields, not stale mirrors:

- Status truth: `status`, `closed_at`.
- Scope truth: `team`, `product_area`, `release_id`, `milestone_id`.
- Category evidence: `work_type`, `labels`, `title`.
- Duplicate truth: `duplicate_of` and `status == "Duplicate"`.
- Do not use `mirror_status` or `legacy_category` for decisions.

## Primary Records

Exclude a work item from primary counts when:

- `duplicate_of` is non-null,
- `status` is `Duplicate`,
- `status` is `Cancelled`.

Duplicate records should still be reported when the template asks for duplicate clusters or exclusion flags. Group duplicate clusters by `duplicate_of` and sort duplicate IDs lexicographically unless the template specifies another order.

## Completion

Treat these statuses as complete for portfolio and release calculations:

- `Closed`
- `Done`
- `Deployed`
- `Verified`

Treat other non-cancelled, non-duplicate statuses as non-complete.

## Portfolio Category Classification

Classify with this precedence. Stop at the first matching category.

1. `Security`
   - `work_type` is `Security` or `Compliance`.
   - Labels or title contain strong security cues such as `security`, `cve`, `encryption`, `vulnerability`, or `audit evidence`.
   - Labels contain `consent`, or title contains `consent` and the product area is Identity.
   - Labels contain `auth` and the item does not otherwise have a clear tech-debt shape. Do not let weak title-only `auth` override clearer dependency, cleanup, migration, or refactor evidence.
2. `Reliability`
   - `work_type` is `Reliability`, `Incident`, or `Bug`.
   - Any category evidence contains `reliability`, `incident`, `outage`, `latency`, `flaky`, `rehearsal`, or `crash`.
3. `TechDebt`
   - `work_type` is `Refactor`, `Chore`, or `Dependency`.
   - Any category evidence contains `tech debt`, `tech-debt`, `refactor`, `cleanup`, `migration`, `dependency`, `deprecate`, or `stabilize`.
4. `NewFeature`
   - `work_type` is `Feature` or `Enhancement`.
   - Any category evidence contains `feature`, `enhancement`, `rollout`, `experiment`, `polish`, or `dashboard`.
   - Use this as the fallback when a template requires exactly one of the four categories.

This precedence deliberately lets security cues beat feature or tech-debt cues, reliability cues beat cleanup/refactor cues, and tech-debt cues beat generic feature cues.

## SLA Time Rules

For historical as-of calculations, exclude records created after the as-of date. Include primary records that were open as of the as-of date or closed inside the prompt's recent closed window. If a record closes after the as-of date, treat it as open as of that date.

Use `due_at` when present; otherwise derive a due date from `created_at` plus the matching `sla_policy.days_to_due` for the item's severity. An item is overdue only when the due date is strictly before its effective date. The effective date is `closed_at` for records closed on or before the as-of date, and the as-of date otherwise.

## Sorting And Rounding

Follow the answer template first. Common defaults:

- Work IDs for accounting lists: `closed_at` ascending, then ID ascending for closed-work portfolio lists; lexicographic ascending for SLA ID sets.
- Category rows: `NewFeature`, `TechDebt`, `Reliability`, `Security`.
- Teams: alphabetic unless the template gives a fixed order.
- Percentages from counts: `count / total * 100`, rounded to one decimal.
- Target mix values in `mix_targets` are fractions; multiply by 100 before comparing.
- Gap: `actual_pct - target_pct`, rounded to one decimal.
- Breach/readiness rates: numerator divided by denominator, rounded to three decimals.
