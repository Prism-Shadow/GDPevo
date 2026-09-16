# Portfolio Category Classification

## Priority Chain

Classify every work item into exactly one of **Security**, **Reliability**,
**TechDebt**, or **NewFeature**. Use this priority chain:

1. **Labels** (primary signal)
2. **work_type** (secondary)
3. **legacy_category** (tiebreaker only)
4. **title** keywords (last resort)

## Label Mapping

| Label | Category |
|-------|----------|
| `security`, `cve`, `auth`, `encryption` | Security |
| `reliability`, `outage`, `incident`, `latency`, `flaky` | Reliability |
| `cleanup`, `refactor`, `migration`, `dependency` | TechDebt |
| `feature`, `rollout`, `customer-request` | NewFeature |

Noise labels (ignore entirely for classification): `stale-export`, `papertrail`,
`release`, `follow-up`, `compliance`.

## Priority Within Labels

When multiple label categories are present, choose the highest priority:
**Security > Reliability > TechDebt > NewFeature**.

NewFeature label keywords (`feature`, `rollout`, `customer-request`) are the
weakest signals. When the only label category is NewFeature and `work_type` or
`legacy_category` provides a different signal, the non-NewFeature signal wins.

## Work Type Mapping

| work_type | Category |
|-----------|----------|
| Security | Security |
| Reliability, Incident | Reliability |
| Refactor, Chore, Migration, Dependency | TechDebt |
| Feature | NewFeature |
| Enhancement, Compliance | ambiguous — defer to labels/legacy |
| Bug | ambiguous — defer to labels/legacy |

## Legacy Category Tiebreaking

| legacy_category | Category |
|-----------------|----------|
| `security` | Security |
| `bug`, `incident`, `quality` | Reliability |
| `tech-debt`, `maintenance` | TechDebt |
| `new`, `feature` | NewFeature |
| `admin`, `release` | ambiguous — fall through to title |

## Title Scanning

Scan the title (case-insensitive) for these substrings:

| Substring | Category |
|-----------|----------|
| `cve`, `auth`, `encrypt`, `security`, `compliance` | Security |
| `outage`, `incident`, `latency`, `flaky`, `reliability`, `rehearsal` | Reliability |
| `cleanup`, `refactor`, `migrat`, `deprecat` | TechDebt |
| `feature`, `rollout`, `enhancement` | NewFeature |

## Stale Signal Handling

- **`mirror_status`**: Always ignore. Never use for classification or status
  determination. Use `status` as the authoritative field.
- **`legacy_category`**: Never use as the primary classification signal. It
  is a tiebreaker only.
- **`stale-export` label**: Pure noise. Skip it.
- **Title stale hints**: When a title contains "stale" adjacent to a category
  keyword (e.g. "stale security label"), this warns that the referenced field
  may be stale, but the underlying label signal on the item itself may still
  be valid. Evaluate holistically.

## Algorithm Pseudocode

```
def classify(item):
    cat_signals = set()
    for label in item.labels:
        if label in NOISE_LABELS: continue
        c = LABEL_MAP[label]
        if c: cat_signals.add(c)

    # Resolve labels with priority
    if cat_signals:
        for c in PRIORITY_ORDER:  # Security > Reliability > TechDebt > NewFeature
            if c in cat_signals:
                # NewFeature is weak: if only NewFeature and another field disagrees, override
                if c == "NewFeature" and cat_signals == {"NewFeature"}:
                    break  # fall through to work_type check
                return c

    # Work type
    c = WORK_TYPE_MAP.get(item.work_type)
    if c: return c

    # Legacy tiebreaker
    c = LEGACY_MAP.get(item.legacy_category)
    if c: return c

    # Title scan
    for kw, c in TITLE_KEYWORDS:
        if kw in item.title.lower():
            return c

    return "NewFeature"  # default
```
