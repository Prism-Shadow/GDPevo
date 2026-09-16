# Portfolio Category Classification Reference

This reference details the work_type-to-category mapping with annotated examples drawn from the task environment. Use it when a portfolio-mix task requires classification decisions, especially for ambiguous cases.

## Category definitions

The four portfolio categories represent different kinds of engineering investment:

- **NewFeature**: Net-new functionality, product enhancements, feature rollouts.
- **TechDebt**: Refactoring, cleanup, chores, dependency upgrades without direct feature or security motivation.
- **Reliability**: Incident response, bug fixes, latency work, outage recovery, flaky-test repair.
- **Security**: CVE remediation, encryption work, auth hardening, compliance evidence.

## Base mapping table

Start every classification from this table. The `work_type` field provides the strongest initial signal.

| work_type | Category | Rationale |
|---|---|---|
| `Reliability` | Reliability | Direct reliability work. |
| `Incident` | Reliability | Incidents are reliability events. |
| `Bug` | Reliability | Bug fixes improve reliability. |
| `Dependency` | Reliability | Dependency upgrades in this dataset are reliability-motivated (migration/cleanup patterns). |
| `Security` | Security | Direct security work. |
| `Enhancement` | Security | Enhancements in this dataset pattern toward security tooling or compliance. |
| `Compliance` | Security | Compliance evidence is security-adjacent. |
| `Refactor` | TechDebt | Refactoring is tech-debt reduction. |
| `Chore` | TechDebt | Chores are cleanup/maintenance. |
| `Feature` | NewFeature | Default starting point; labels may override. |

## Override rules

Apply these in order. Once an override fires, stop.

### Rule 1: Feature with security label -> Security

When `work_type` is `Feature` and any label contains `"security"`, classify as Security.

Example: WI-24024-P001 has `work_type: "Feature"`, labels `["feature", "rollout", "security"]`. The `"security"` label overrides Feature's default NewFeature mapping. Classify as Security.

Even when the title mentions "stale security label", this confirms the item has a security association. The "stale" qualifier describes the label source, not the nature of the work.

### Rule 2: Feature with migration signal (no security) -> Reliability

When `work_type` is `Feature` and labels or title contain `"migration"`, but no `"security"` label is present, classify as Reliability.

Example: WI-24024-P004 has `work_type: "Feature"`, labels `["feature", "migration"]`, no security signal. The `"migration"` label pushes it toward Reliability.

### Rule 3: Feature with cleanup/refactor signal (no security, no migration) -> TechDebt

When `work_type` is `Feature` and labels or title contain tech-debt indicators (`"cleanup"`, `"refactor"`) without security or migration signals, classify as TechDebt.

Example: An item with `work_type: "Feature"`, labels `["cleanup", "feature"]` and no security or migration signals.

### Rule 4: Title tie-breaking

When labels and work_type conflict but none of the override rules match, examine the title. Look for these keywords:

- **Reliability indicators**: "outage", "incident", "latency", "flaky", "retry", "crash"
- **Security indicators**: "cve", "encryption", "auth", "compliance", "audit"
- **TechDebt indicators**: "cleanup", "refactor", "migrate", "deprecate"

### Rule 5: "stale-export" label

When the labels array contains the literal string `"stale-export"`, the entire label set is unreliable. Discard labels for classification and rely solely on `work_type` and `title`. The `"stale-export"` label itself is not a category signal.

Example: WI-24024-P011 has `work_type: "Security"`, labels `["security", "stale-export"]`. The `work_type` Security dominates. Also, it is a duplicate (status: "Closed", but has `duplicate_of` set), so it is excluded anyway.

## Annotated classification examples

These examples are based on real work items in the environment. Use them to calibrate your classification decisions.

### WI-24024-P001: Feature with security label

```
work_type: Feature
labels: ["feature", "rollout", "security"]
title: "Atlas backend feature rollout with stale security label"
legacy_category: security
```

Classification: **Security**. Rule 1 applies (`"security"` in labels). The title's "stale security label" phrase does not negate the security association; it confirms it.

### WI-24024-P002: Refactor

```
work_type: Refactor
labels: ["auth", "encryption", "cleanup", "refactor"]
title: "Identity auth encryption refactor cleanup"
legacy_category: tech-debt
```

Classification: **TechDebt**. Base mapping from `Refactor` is TechDebt. Labels and title mention auth/encryption but `work_type` Refactor maps directly to TechDebt and is not Feature (so override rules don't apply). The labels are descriptive, not overriding.

### WI-24024-P003: Incident

```
work_type: Incident
labels: ["incident", "latency", "feature", "reliability"]
title: "Atlas latency incident follow-up feature toggle"
legacy_category: new
```

Classification: **Reliability**. Base mapping from `Incident`. The `"feature"` label does not trigger an override because the base work_type is not Feature.

### WI-24024-P004: Feature with migration

```
work_type: Feature
labels: ["feature", "migration"]
title: "Identity consent screen feature migration"
legacy_category: maintenance
```

Classification: **Reliability**. Rule 2 applies: Feature with `"migration"` and no security signal.

### WI-24024-P005: Chore

```
work_type: Chore
labels: ["cleanup", "flaky", "reliability"]
title: "Atlas queue cleanup for flaky reliability alert"
legacy_category: quality
```

Classification: **TechDebt**. Base mapping from `Chore`. Labels mention reliability but Chore maps directly to TechDebt.

### WI-24024-P006: Security

```
work_type: Security
labels: ["security", "cve", "rollout"]
title: "Identity cve audit for rollout banner"
legacy_category: new
```

Classification: **Security**. Base mapping from `Security`. The `legacy_category "new"` is misleading.

### WI-24024-P007: Dependency (migration/cleanup)

```
work_type: Dependency
labels: ["migration", "cleanup", "auth"]
title: "Atlas migration cleanup with auth title"
legacy_category: security
```

Classification: **Reliability**. Base mapping from `Dependency` is Reliability. Despite `legacy_category: "security"` and "auth" mentions, Dependency maps directly to Reliability.

### WI-24024-P008: Enhancement (outage/reliability)

```
work_type: Enhancement
labels: ["outage", "reliability", "feature"]
title: "Identity outage recovery dashboard enhancement"
legacy_category: new
```

Classification: **Security**. Base mapping from `Enhancement` is Security. Labels mentioning outage/reliability do not override the Enhancement mapping.

### WI-24024-075: Security (feature label)

```
work_type: Security
labels: ["auth", "encryption", "feature", "security"]
title: "Rollout feature mobile telemetry batch"
legacy_category: quality
```

Classification: **Security**. Base mapping from `Security`. The `legacy_category: "quality"` is untrustworthy.

### WI-24024-098: Enhancement with feature/rollout labels

```
work_type: Enhancement
labels: ["feature", "rollout"]
title: "Cleanup rollout billing ledger writer"
legacy_category: security
```

Classification: **Security**. Base mapping from `Enhancement`. The title's "cleanup" does not override Enhancement -> Security.

### WI-24024-P022: Feature with rollout, auth labels

```
work_type: Feature
labels: ["feature", "rollout", "auth"]
title: "Growth checkout feature rollout with auth guard"
legacy_category: security
```

Classification: **NewFeature**. The `"auth"` label is not `"security"`, so Rule 1 does not fire. No migration or cleanup signals. Stays NewFeature.

### WI-24024-P023: Security with encryption, flaky labels

```
work_type: Security
labels: ["security", "encryption", "flaky"]
title: "Mobile encryption crash fix for checkout"
legacy_category: quality
```

Classification: **Security**. Base mapping from Security.

### WI-24024-P024: Refactor with migration, cleanup, feature labels

```
work_type: Refactor
labels: ["migration", "cleanup", "feature"]
title: "Growth checkout migration cleanup experiment"
legacy_category: new
```

Classification: **TechDebt**. Base mapping from `Refactor`.

### WI-24024-P025: Incident with outage, feature labels

```
work_type: Incident
labels: ["outage", "incident", "feature"]
title: "Mobile checkout outage follow-up banner"
legacy_category: new
```

Classification: **Reliability**. Base mapping from `Incident`.

### WI-24024-P026: Enhancement with feature, rollout labels

```
work_type: Enhancement
labels: ["feature", "rollout"]
title: "Growth payment sheet feature polish"
legacy_category: maintenance
```

Classification: **Security**. Base mapping from `Enhancement`. Despite the feature-like title and labels, Enhancement maps to Security.

### WI-24024-P027: Reliability

```
work_type: Reliability
labels: ["reliability", "latency", "flaky"]
title: "Mobile checkout flaky latency guardrail"
legacy_category: bug
```

Classification: **Reliability**. Base mapping.

### WI-24024-P028: Compliance (security, cve, feature labels)

```
work_type: Compliance
labels: ["security", "cve", "feature"]
title: "Growth checkout cve copy update"
legacy_category: new
```

Classification: **Security**. Base mapping from `Compliance`.

### WI-24024-007: Bug (flaky, reliability labels)

```
work_type: Bug
labels: ["flaky", "reliability"]
title: "Mobile client flaky checkout retry bug"
legacy_category: quality
```

Classification: **Reliability**. Base mapping from `Bug`.

## Distractor recognition

Some work items appear in the same scope but should not be included in the primary portfolio mix. Recognize these patterns:

1. **Duplicates**: `status == "Duplicate"` with non-null `duplicate_of`. Exclude from primary counts; report separately.

2. **Cancelled**: `status == "Cancelled"`. These were never completed. Exclude from primary counts.

3. **Not in quarter scope**: The `closed_at` date must fall within the quarter. Work items with `closed_at` outside the quarter are excluded.

4. **Wrong team/product_area**: Only items matching the given scope teams and product areas qualify.
