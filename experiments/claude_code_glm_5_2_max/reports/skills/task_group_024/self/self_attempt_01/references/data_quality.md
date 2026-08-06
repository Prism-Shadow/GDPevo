# Data-quality rules

Apply **before any counting**. These traps recur across every task family.

## Authoritative vs stale fields
- `status` is authoritative. `mirror_status` is a stale mirror that frequently disagrees
  (e.g. `mirror_status` "Open" on a record whose `status` is "Duplicate" or "Closed"). Never
  use `mirror_status` as truth — not for closure, not for SLA, not for release readiness.
- `legacy_category` is legacy and must be **ignored entirely**. Do not classify from it.
- Release truth: use the `releases` / `milestones` / `blockers` / `dependencies` records,
  not mirror or export fields on work items.

## Primary vs non-primary work
Count only **primary, closed, in-scope** items. Separate the rest into reportable buckets —
never drop a record silently.

- **Duplicate** — `status == "Duplicate"` OR `duplicate_of` is set. Exclude from primary
  counts. Report in `duplicate_clusters` keyed by `primary_id = duplicate_of` (the canonical
  item the duplicate points at), with `duplicate_ids` sorted ascending. Where the template has
  it (e.g. portfolio-mix), also surface these in `exclusion_flags.excluded_duplicate_ids`.
- **Cancelled** — `status == "Cancelled"`. Exclude; report in
  `exclusion_flags.excluded_cancelled_ids` where the template has it.
- **Distractor** — same-scope records that look related but are not primary closed portfolio
  work (e.g. not closed, mirror-only status, wrong category, outside the closed window,
  belongs to a different scope_id). Exclude; report in `excluded_distractor_ids` where the
  template has it.
- **Closed** — authoritative `status` is a terminal completion status
  (Closed / Done / Verified / Deployed). In Progress / Review / Backlog / Reopened are **not**
  closed. Confirm the closed set against the task's window (quarter, or recent-closed-days
  relative to the as-of date).

## Portfolio category classification
Classify each included item into **exactly one** of NewFeature, TechDebt, Reliability,
Security. Resolve conflicting signals among `work_type`, `labels`, and `title` using the
default mapping + precedence below; **never** use `legacy_category`.

Default `work_type` → category mapping:
| work_type                       | category   |
|---------------------------------|------------|
| Security, Compliance            | Security   |
| Reliability, Incident           | Reliability |
| Refactor, Chore                 | TechDebt   |
| Feature, Enhancement            | NewFeature |

When signals conflict (e.g. `work_type` says one thing but `labels`/`title` say another), or
`work_type` is ambiguous (e.g. `Bug`, `Dependency`), apply this **precedence — first match
wins** — scanning `labels` and `title`:

1. **Security** — labels/title indicate security, cve, auth, vuln, encryption, compliance.
2. **Reliability** — labels/title indicate incident, outage, reliability, sre, latency.
3. **TechDebt** — labels/title indicate tech-debt, cleanup, maintenance, refactor, migration.
4. **NewFeature** — labels/title indicate feature, enhancement, launch, capability.

If still ambiguous after scanning, default to **TechDebt** unless a Security or Reliability
signal is present. Apply the rule **deterministically** so a re-run yields the same category
for the same item.

> This convention is distilled from observed `work_type`/`label` vocabulary. If a task
> supplies its own explicit category mapping, follow the task's mapping instead.
