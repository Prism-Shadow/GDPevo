# train_003 Notes

## English

### Data/source lineage

This task belongs to `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, using the renewal-queue pattern from source example `E003` and the shared generated environment for `task_group_019`. The target construction metadata comes from `task_group/task_group_019/env/data/manifest.json`: construction tag `train_003`, release boundary `2025-04-10`, target queue size `10`, and current license numbers `AL-TR3-001` through `AL-TR3-010`.

The standard answer was reworked after the environment regeneration and is derived from `env/data/licensing.db`, specifically the `alcohol_licensees`, `alcohol_violations`, `renewal_rules`, and renewal policy rows. Solver-visible access remains through the public API endpoints in `input/prompt.txt`; the manifest, database file, generator, notes, gold answer, and evaluator are hidden construction materials. The prompt no longer names the construction group tag, but it still names the target license numbers, boundary date, and queue size.

### Task definition and scenario fit

The solver acts as a licensing analyst preparing a pre-release alcohol renewal manual-review queue. The visible request identifies the ten current license numbers, the release boundary, the target queue size, the data-service endpoints, and the answer template. The expected output is a normalized JSON object with ranked queue entries, matched violation evidence IDs, matched counts, latest matched dates, match confidence, risk tier, controlled next-step labels, and summary sets.

This fits the regulatory licensing scenario because it requires the same record-reconciliation workflow as the Montgomery renewal source task: current licensee identity, pre-boundary violation history, successor/close-match handling, release-date boundary discipline, risk tiering, and operational queue labels. The task is a formal train sample, not a tutorial; its solved output is meant to reveal conventions through comparison after solving.

### Material map

- `GET /api/alcohol/licensees`: current and inactive licensee roster, facility names, addresses, active flags, target groups, and `successor_to` links.
- `GET /api/alcohol/violations`: violation IDs, license numbers, dates, severity, disposition, fine balances, alert flags, and source names.
- `GET /api/renewal/rules`: release-boundary rules, including that post-boundary rows are distractors.
- `GET /api/policies` if exposed through environment instructions: renewal policy row `POL-REN-001`, which confirms boundary discipline and successor-match caution.
- `POST /api/sql`: optional read-only query path when SQL access is available.
- `input/payloads/answer_template.json`: output schema, closed enums, date format, matched evidence IDs, list ordering, and summary fields.

### Solution and evaluation basis

The target current licensees are exactly `AL-TR3-001` through `AL-TR3-010`. Only violations with `violation_date <= 2025-04-10` are counted. The ten `*-LATE` rows after the boundary are reported in `summary.post_boundary_violation_ids_excluded` and are not used for counts, latest dates, risk tiers, ranks, or evidence ID sets.

The key regenerated-data edge case is `AL-TR3-006`. The current licensee is active at `266 Seventh Ave` and has `successor_to = AL-TR3-OLD-006`; the inactive former permit has the same address. The matched pre-boundary evidence set for the current renewal queue entry is:

- `AV-AL-TR3-006-1`, current license exact row dated `2025-01-14`.
- `AV-AL-TR3-OLD-006-S2`, old-license successor row dated `2025-03-13`.
- `AV-AL-TR3-OLD-006-S1`, old-license successor row dated `2025-03-30`.

Therefore `AL-TR3-006` has `violation_count = 3`, `most_recent_violation_date = 2025-03-30`, `match_confidence = close_address`, `risk_tier = high`, and `next_step_label = board_review`. The template keeps the existing allowed non-exact confidence enum, so this same-address successor case is encoded as `close_address` rather than adding a new `successor` value.

Gold queue order:

1. `AL-TR3-007`
2. `AL-TR3-006`
3. `AL-TR3-008`
4. `AL-TR3-002`
5. `AL-TR3-005`
6. `AL-TR3-009`
7. `AL-TR3-004`
8. `AL-TR3-010`
9. `AL-TR3-003`
10. `AL-TR3-001`

The ranking groups `board_review` cases first, then `manual_fine_check`, then `manual_ALERT_check`; entries within a label are ordered by most recent matched pre-boundary violation date descending. `AL-TR3-006`, `AL-TR3-007`, and `AL-TR3-008` are the board-review set. `AL-TR3-006` is the only non-exact match in the summary set `close_or_uncertain_match_license_numbers`.

The evaluator has eight deterministic whole-point checks with raw weights:

- `SP001`, weight 3: exact queue membership and rank order.
- `SP002`, weight 3: matched violation evidence ID sets, including the `AL-TR3-006` successor evidence.
- `SP003`, weight 2: per-license pre-boundary violation counts and most recent used dates.
- `SP004`, weight 2: match-confidence fields and close/uncertain summary.
- `SP005`, weight 2: controlled next-step labels.
- `SP006`, weight 2: exclusion of the ten post-boundary violation IDs and no late date used.
- `SP007`, weight 2: risk tiers and board-review summary set.
- `SP008`, weight 1: queue size, boundary date, and facility identity fields.

Each point is all-or-nothing. The evaluator accepts a candidate path as `$1` and defaults to the task gold answer when no path is supplied. Likely model pitfalls are using post-boundary `post_boundary_feed` rows, failing to carry the `AL-TR3-OLD-006` successor history into `AL-TR3-006`, labeling the successor case as exact, omitting matched evidence IDs, ranking only by count rather than queue label and latest matched date, or using free-text next steps instead of the closed enum values.

### Transfer design

As a train task, `train_003` anchors the renewal-queue conventions that should transfer to `test_002` and `test_005`: enforce the release boundary, reconcile current licenses to true successor histories when the licensee record supports it, record non-exact confidence with an allowed enum, preserve matched evidence IDs separately from post-boundary exclusions, use controlled next-step labels, and treat violation history as manual-review risk rather than proof of an active hold. The solved output also shows the expected schema conventions for ranked queues and summary sets.

### Construction record

- Author: Codex main agent
- Created: 2026-07-18
- Updated: 2026-07-18
- Major changes: reworked `train_003` after environment regeneration; removed the construction tag from the solver-visible prompt; added matched violation IDs to the answer template; updated the gold answer and evaluator for the `AL-TR3-006` successor match using `AV-AL-TR3-006-1`, `AV-AL-TR3-OLD-006-S2`, and `AV-AL-TR3-OLD-006-S1`.

## 中文

### 数据来源与谱系

本任务属于 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，沿用来源样例 `E003` 的 renewal queue 工作模式，并使用 `task_group_019` 的共享生成环境。目标构造信息来自 `task_group/task_group_019/env/data/manifest.json`：构造标签为 `train_003`，release boundary 为 `2025-04-10`，目标队列大小为 `10`，当前许可证号为 `AL-TR3-001` 到 `AL-TR3-010`。

标准答案在环境重新生成后重新整理，依据 `env/data/licensing.db` 中的 `alcohol_licensees`、`alcohol_violations`、`renewal_rules` 和 renewal policy 记录。求解器只能通过 `input/prompt.txt` 中的公开 API 访问数据；manifest、数据库文件、生成脚本、notes、标准答案和 evaluator 都是隐藏构造材料。prompt 已不再暴露构造标签，但仍给出目标许可证号、边界日期和队列大小。

### 任务定义与场景匹配

求解器扮演 licensing analyst，在 renewal release 前构建 alcohol renewal manual-review queue。可见请求给出十个当前许可证号、release boundary、目标队列大小、数据服务端点和 answer template。预期输出是规范化 JSON，包含排名、匹配到的 violation evidence ID、匹配计数、最新匹配日期、match confidence、risk tier、封闭 next-step label 和 summary set。

该任务符合监管许可审查场景，因为它要求把 current licensee identity、边界前 violation history、successor/close match、release-date boundary、risk tier 和 operational queue label 统一起来。这是正式 train 样本，不是教程；它通过标准答案让后续 fewshot skill 推断可迁移规则。

### 材料地图

- `GET /api/alcohol/licensees`：当前与非活动许可证名册、facility name、address、active flag、target group 和 `successor_to` 链接。
- `GET /api/alcohol/violations`：violation ID、license number、日期、severity、disposition、fine balance、alert flag 和 source name。
- `GET /api/renewal/rules`：release boundary 规则，包括边界之后记录是 distractor。
- `GET /api/policies`（如果环境说明暴露）：renewal policy `POL-REN-001`，说明边界纪律和 successor match 需要谨慎处理。
- `POST /api/sql`：当环境提供 SQL 凭据时可用的只读查询入口。
- `input/payloads/answer_template.json`：输出结构、封闭枚举、日期格式、匹配 evidence ID、列表排序和 summary 字段。

### 解法与评估依据

目标当前许可证正是 `AL-TR3-001` 到 `AL-TR3-010`。只统计 `violation_date <= 2025-04-10` 的记录。十条边界之后的 `*-LATE` 记录列入 `summary.post_boundary_violation_ids_excluded`，不得用于 count、latest date、risk tier、rank 或 evidence ID set。

重新生成数据后的关键边界案例是 `AL-TR3-006`。当前许可证在 `266 Seventh Ave` 处于 active 状态，且 `successor_to = AL-TR3-OLD-006`；非活动旧许可证也在同一地址。该 current renewal queue entry 的边界前匹配 evidence set 为：

- `AV-AL-TR3-006-1`，当前许可证 exact row，日期 `2025-01-14`。
- `AV-AL-TR3-OLD-006-S2`，旧许可证 successor row，日期 `2025-03-13`。
- `AV-AL-TR3-OLD-006-S1`，旧许可证 successor row，日期 `2025-03-30`。

因此 `AL-TR3-006` 的 `violation_count = 3`，`most_recent_violation_date = 2025-03-30`，`match_confidence = close_address`，`risk_tier = high`，`next_step_label = board_review`。template 沿用已有的非 exact 置信度枚举，因此这个同地址 successor case 使用 `close_address`，没有新增 `successor` 枚举。

标准队列顺序为：

1. `AL-TR3-007`
2. `AL-TR3-006`
3. `AL-TR3-008`
4. `AL-TR3-002`
5. `AL-TR3-005`
6. `AL-TR3-009`
7. `AL-TR3-004`
8. `AL-TR3-010`
9. `AL-TR3-003`
10. `AL-TR3-001`

排序先放 `board_review`，再放 `manual_fine_check`，再放 `manual_ALERT_check`；同一 label 内按最新的边界前匹配 violation 日期降序排列。`AL-TR3-006`、`AL-TR3-007` 和 `AL-TR3-008` 是 board-review set。`AL-TR3-006` 是 `close_or_uncertain_match_license_numbers` summary set 中唯一的非 exact match。

Evaluator 有八个确定性整点评分项，原始权重如下：

- `SP001`，权重 3：队列 membership 与 rank order 完全正确。
- `SP002`，权重 3：匹配 violation evidence ID set 正确，包括 `AL-TR3-006` 的 successor evidence。
- `SP003`，权重 2：每个许可证的边界前 violation count 和 most recent used date 正确。
- `SP004`，权重 2：match confidence 与 close/uncertain summary 正确。
- `SP005`，权重 2：封闭 next-step label 正确。
- `SP006`，权重 2：正确排除十条边界之后 violation ID，且未使用 late date。
- `SP007`，权重 2：risk tier 与 board-review summary set 正确。
- `SP008`，权重 1：queue size、boundary date 和 facility identity 字段正确。

每个评分项都是 all-or-nothing。Evaluator 接受 `$1` 作为候选答案路径；如果未提供路径，则默认评分本任务的 gold answer。常见错误包括使用 `post_boundary_feed` 的边界后记录、没有把 `AL-TR3-OLD-006` 的 successor history 并入 `AL-TR3-006`、把 successor case 标成 exact、遗漏匹配 evidence ID、只按 count 排名而忽略 queue label 和最新匹配日期，以及使用自由文本 next step 而不是封闭枚举。

### 迁移设计

作为 train task，`train_003` 为 `test_002` 和 `test_005` 锚定 renewal-queue 的可迁移规则：严格执行 release boundary，在 licensee record 支持时把 current license 与真实 successor history 对齐，用允许的枚举记录 non-exact confidence，把匹配 evidence ID 与边界后排除项分开，使用封闭 next-step label，并把 violation history 表述为 manual-review risk 而不是 confirmed active hold。标准答案也展示了 ranked queue 与 summary set 的结构惯例。

### 构造记录

- 作者：Codex main agent
- 创建日期：2026-07-18
- 更新日期：2026-07-18
- 主要变更：环境重新生成后重做 `train_003`；从 solver-visible prompt 移除构造标签；在 answer template 中加入 matched violation IDs；更新 gold answer 和 evaluator，使 `AL-TR3-006` 使用 `AV-AL-TR3-006-1`、`AV-AL-TR3-OLD-006-S2` 和 `AV-AL-TR3-OLD-006-S1` 的 successor match。
