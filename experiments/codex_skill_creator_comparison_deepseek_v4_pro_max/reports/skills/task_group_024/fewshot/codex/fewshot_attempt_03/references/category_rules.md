# Portfolio Category Classification

Classify every primary work item into exactly one of four categories:
**NewFeature**, **TechDebt**, **Reliability**, **Security**.

Never use `legacy_category`. Use authoritative fields: `work_type`, `labels`,
`title`, and `status` (for the `Verified`+`Incident` Security gate).

## Priority Resolution

Apply rules in order — the first match wins. Each rule checks signals from
labels and title text (case-insensitive substring).

### 1. Security (check first)

Classify as Security when any of these is true:

- Any label or title contains: `security`, `cve`, `encryption`, `auth`,
  `vulnerability`, `credentials`
- `work_type` is `Incident` AND the title contains `security` or `cve`

Security signals override everything, including `Refactor` work_type and
reliability/outage labels.

### 2. Reliability (check second)

Classify as Reliability when any of these is true:

- Any label or title contains: `outage`, `reliability`, `incident`,
  `resilience`, `stabilize`, `harden`, `latency`, `flaky`
- `work_type` is `Incident` (without Security signals above)

### 3. TechDebt (check third)

Classify as TechDebt when any of these is true:

- `work_type` is `Refactor`
- Any label or title contains: `refactor`, `cleanup`, `tech-debt`, `debt`,
  `migration`, `migrate`

### 4. NewFeature (check fourth)

Classify as NewFeature when:

- `work_type` is `Enhancement` or `Feature`
- Any label contains `feature` (without stronger signals above)

### Fallback

If still unclassified after the four rules above, use `work_type`:

- `Bug` → Reliability
- `Task` → TechDebt
- `Chore` → TechDebt
- `Dependency` → TechDebt
- `Compliance` → Security
- `Incident` → Reliability
- Everything else → TechDebt

## Examples

| Work Item | work_type | Key Signals | Category | Why |
|---|---|---|---|---|
| P002 | Refactor | auth, encryption, refactor | Security | Security signals override Refactor |
| P004 | Feature | migration | TechDebt | migration → TechDebt before NewFeature |
| P005 | Chore | cleanup, reliability | Reliability | reliability label wins before TechDebt |
| P007 | Dependency | auth | Security | auth → Security before TechDebt |
| P022 | Feature | auth | Security | auth → Security |
| P024 | Refactor | migration, cleanup | TechDebt | Refactor → TechDebt |
| P026 | Enhancement | feature, rollout | NewFeature | No stronger signal |
| 098 | Enhancement | "Cleanup" in title | TechDebt | Title "Cleanup" triggers TechDebt |

**Title signals count equally with label signals.** For example, a title
containing "Cleanup" triggers the TechDebt rule even if no cleanup label
is present.
