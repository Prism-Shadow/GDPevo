# Portfolio Category Classification

Classify each work item into exactly one of **NewFeature**, **TechDebt**,
**Reliability**, **Security** by resolving conflicting `work_type`, `labels`,
and `title` signals. **Ignore `mirror_status` and `legacy_category`** — they
are stale.

## Signal sets

- **Security signals**: `work_type ∈ {Security, Compliance}` OR a label in
  `{security, cve, auth, encryption}`.
- **Reliability signals**: `work_type ∈ {Reliability, Incident, Bug}` OR a
  label in `{reliability, incident, outage, latency, flaky}`.
- **TechDebt work_types**: `{Refactor, Chore, Dependency}`.
- **NewFeature work_types**: `{Feature, Enhancement}`.
- **Stale-security title markers** (the title explicitly says the security
  signal is stale/decorative): phrases such as `"stale security label"`,
  `"with auth title"`, `"stale auth"`. When present, ignore the security
  signal from labels for that item.

## Decision rule (in order)

1. **Security wins unless flagged stale.** If a security signal is present AND
   the title does NOT contain a stale-security marker → **Security**.
   Security overrides *every* work_type (including TechDebt and NewFeature
   work_types, and even Reliability work_types). This is the highest
   precedence.
2. Else, classify by **authoritative `work_type`**:
   - `Reliability`, `Incident`, `Bug` → **Reliability**.
   - `Refactor`, `Chore`, `Dependency` → **TechDebt**. (Reliability/other
     labels do **not** override TechDebt work_types.)
   - `Feature`, `Enhancement` → look at labels: if a reliability signal is
     present → **Reliability**; otherwise → **NewFeature**.
3. (Fallback, e.g. unknown work_type with no security signal): use labels —
   reliability signal → Reliability; otherwise NewFeature.

## Why the rule has this shape

- Security is treated as domain-elevating: a refactor, chore, dependency, or
  feature that touches `auth`/`encryption`/`cve`/`security` is security work.
  The only escape is an explicit stale marker in the title (otherwise the
  label would silently win and the marker would be pointless).
- Reliability labels elevate only NewFeature-type work (a `Feature`/`Enhancement`
  tagged with outage/reliability/flaky is really reliability work), but do
  **not** elevate TechDebt-type work (a `Chore`/`Refactor` cleanup that
  mentions reliability is still tech debt — the work is the cleanup).
- `work_type` is otherwise authoritative. `Bug` is reliability, `Dependency`
  is tech debt, `Compliance` is security.

## Quick map

| work_type          | no sec/rel labels       | + security label (not stale) | + reliability label only |
|--------------------|-------------------------|------------------------------|--------------------------|
| Security/Compliance| Security                | Security                     | Security                 |
| Reliability/Incident/Bug | Reliability       | Security                     | Reliability              |
| Refactor/Chore/Dependency | TechDebt         | Security                     | TechDebt                 |
| Feature/Enhancement| NewFeature              | Security                     | Reliability              |

## Notes

- The `stale-export` *label* appears on stale mirror/export records (usually
  duplicates) — it is not a classification signal; handle it via duplicate
  exclusion, not classification.
- When a title contains `"with auth title"` / `"stale security label"`, the
  item usually still classifies cleanly by its remaining (non-security)
  signals via step 2.
- For SLA tasks, only the **Reliability** and **Security** categories are
  SLA-relevant; items classifying as NewFeature/TechDebt are out of the SLA
  population.
