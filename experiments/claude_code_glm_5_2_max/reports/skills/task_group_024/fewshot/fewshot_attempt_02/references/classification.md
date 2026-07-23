# Portfolio Category Classification

Each **primary** work item is classified into exactly one of:

`NewFeature`, `TechDebt`, `Reliability`, `Security`

## Signals

Gather signals from three sources on the work item:

1. `work_type` — exact value match.
2. `labels` — array; any element that matches a signal keyword.
3. `title` — case-insensitive substring match for a signal keyword.

The stale `legacy_category` field is **never** a signal — ignore it.

## Priority order (first match wins)

Evaluate in this order. The first category with any matching signal (from any of
the three sources) wins. If nothing matches, the item falls through to
NewFeature.

### 1. Security
- Labels / title keywords: `security`, `cve`, `encryption`, `auth`
- `work_type` in: `Security`, `Compliance`

### 2. Reliability
- Labels / title keywords: `reliability`, `outage`, `incident`, `latency`,
  `flaky`
- `work_type` in: `Reliability`, `Incident`

### 3. TechDebt
- Labels / title keywords: `cleanup`, `refactor`, `migration`, `tech-debt`
- `work_type` in: `Refactor`, `Chore`, `Bug`, `Dependency`

### 4. NewFeature (residual)
- Labels / title keywords: `feature`, `new`, `polish`, `rollout`
- `work_type` in: `Feature`, `Enhancement`
- Default when no higher-priority signal is present.

## Why all three sources matter

A single item can carry conflicting signals. The priority order resolves them
deterministically:

- A `Feature`/`Enhancement` work item with a `security`/`auth`/`encryption`/
  `cve` signal (label or title) is **Security**, not NewFeature.
- A `Feature`/`Enhancement` with `cleanup`/`migration`/`refactor` (label or
  title) is **TechDebt**, not NewFeature.
- A `Chore`/`Refactor` with `reliability`/`outage`/`flaky` is **Reliability**,
  not TechDebt.
- `Security` beats `Reliability` beats `TechDebt` beats `NewFeature` whenever
  more than one is present.

The `title` is often the deciding signal when `work_type` and `labels` alone
would be ambiguous — always include it in the match.

## Important: classify primary records only

Duplicates and cancelled records are never classified into the mix. Apply
classification only to the included primary set (see SKILL.md record-handling
rules), after scope filtering and duplicate/cancelled exclusion.

## Validation note

This priority order and signal vocabulary were validated against multiple
portfolio-mix tasks in this environment (title-aware label resolution). If a
future task's data introduces labels or work_types not covered above, extend the
signal sets by analogy (security-related → Security; availability/incident →
Reliability; cleanup/refactor/migration → TechDebt; net-new capability →
NewFeature) and keep the priority order unchanged.
