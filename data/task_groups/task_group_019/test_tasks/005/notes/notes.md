# test_005 Notes

## English

### Data/source lineage

This task belongs to `SCN_019_regulatory_licensing_eligibility_and_compliance_review`, using the renewal-queue pattern from source example `E003` and the shared generated environment for `task_group_019`. The target construction metadata comes from `task_group/task_group_019/env/data/manifest.json`: hidden task group `test_005`, release boundary `2025-05-20`, target queue size `8`, current license numbers `AL-TE5-001` through `AL-TE5-008`, and a non-exact close successor case from `AL-TE5-OLD-003` to current license `AL-TE5-003`.

The standard answer was refreshed after the environment rework from the generated SQLite data in `env/data/licensing.db`, specifically the `alcohol_licensees`, `alcohol_violations`, and `renewal_rules` tables. Solver-visible access is through the public API endpoints named in `input/prompt.txt`; the manifest, database file, generator, notes, gold answer, and evaluator are hidden construction materials.

### Task definition and scenario fit

The solver acts as a licensing analyst preparing a resort-area alcohol renewal manual-review queue before release. The visible request identifies the eight current target license numbers, the release boundary, the target queue size, and the relevant API endpoints. The prompt intentionally does not expose the construction group tag. The expected output is a normalized JSON queue matching `input/payloads/answer_template.json`.

This fits the regulatory licensing scenario because it requires the same record reconciliation as the Montgomery renewal source task: current licensee identity, violation history, release-date boundary discipline, close/successor match handling, risk tiering, and controlled next-step labels. The test variation is a date-sensitive resort roster with repeated serious records, one close-address successor match, and post-boundary distractors.

### Material map

- `GET /api/alcohol/licensees`: current licensee roster, facility names, addresses, active flags, channel types, and successor indicators.
- `GET /api/alcohol/violations`: violation records, dates, severity, dispositions, fine balances, alert flags, source names, and post-boundary distractors.
- `GET /api/renewal/rules`: release-boundary rules, including that violations after the relevant release boundary are distractors and fine/alert flags require manual attention.
- `POST /api/sql`: optional read-only query path when the solver environment supplies SQL credentials.
- `input/payloads/answer_template.json`: output schema, closed enums, date format, list ordering, and summary fields.

### Solution and evaluation basis

The target current licensees are `AL-TE5-001` through `AL-TE5-008`. For scoring, only violations with `violation_date <= 2025-05-20` are counted. The eight current-license `*-LATE` rows dated after the boundary are listed in `summary.post_boundary_violation_ids_excluded` and are not used for counts, most recent dates, risk tiering, next-step labels, or rank.

The important reworked case is `AL-TE5-003`. Its current licensee row has `successor_to = AL-TE5-OLD-003`, the current address is `233 Lincoln Ave`, and the inactive old-license row uses `233 Lincoln Avenue`. The accepted matched violations are the current exact row `AV-AL-TE5-003-1` plus old-license rows `AV-AL-TE5-OLD-003-S1` and `AV-AL-TE5-OLD-003-S2`. This gives `violation_count = 3`, `most_recent_violation_date = 2025-05-16`, `match_confidence = close_address`, `risk_tier = high`, and `next_step_label = board_review`.

Gold queue order:

1. `AL-TE5-003`
2. `AL-TE5-008`
3. `AL-TE5-005`
4. `AL-TE5-007`
5. `AL-TE5-002`
6. `AL-TE5-001`
7. `AL-TE5-004`
8. `AL-TE5-006`

The first four licenses receive `board_review`: `AL-TE5-003`, `AL-TE5-008`, `AL-TE5-005`, and `AL-TE5-007`. They each have two or more serious matched pre-boundary violations after applying the current-license or accepted successor match. They are ranked by most recent matched pre-boundary date within the board-review group. The remaining four licenses receive `manual_fine_check`: `AL-TE5-002`, `AL-TE5-001`, `AL-TE5-004`, and `AL-TE5-006`, ranked by most recent matched pre-boundary date within the fine-check group. All eight target entries are `high` risk. `summary.close_or_uncertain_match_license_numbers` contains only `AL-TE5-003`; `summary.board_review_license_numbers` is sorted as `AL-TE5-003`, `AL-TE5-005`, `AL-TE5-007`, `AL-TE5-008`.

The evaluator has seven deterministic whole-point checks with raw weights:

- `SP001`, weight 3: exact queue membership and rank order.
- `SP002`, weight 2: per-license pre-boundary violation counts and most recent used dates.
- `SP003`, weight 2: match-confidence fields and the close/uncertain summary set.
- `SP004`, weight 2: controlled next-step labels.
- `SP005`, weight 2: exclusion of the eight post-boundary violation IDs and no late date used.
- `SP006`, weight 2: risk tiers and board-review summary set.
- `SP007`, weight 1: queue size, boundary date, and facility identity fields.

Each point is all-or-nothing. The evaluator accepts a candidate path as `$1` and defaults to the task gold answer when no path is supplied.

Likely model pitfalls are naming or relying on the hidden construction group tag from earlier task versions, counting only the exact current row for `AL-TE5-003`, copying the generator's internal `close_successor` label even though it is not an allowed output enum, using post-boundary `post_boundary_feed` rows, pulling unrelated same-address records from other renewal groups, and ranking solely by violation count while ignoring the next-step priority buckets.

### Transfer design

The primary train anchor is `train_003`. It transfers renewal boundary discipline, successor and close-address reconciliation, same-address distractor rejection, controlled match-confidence enums, queue summary conventions, and the ranked queue schema. The limited monitoring-label transfer from `train_002` and `train_005` applies only to escalation judgment: repeated serious risks should be escalated to `board_review`, while fine and alert issues stay in narrower manual-check labels. This test still requires task-specific exploration because the target license numbers, close successor pair, dates, counts, fine balances, and board-review set are all new.

### Construction record

- Author: Codex main agent
- Created: 2026-07-18
- Updated: 2026-07-18
- Major changes: refreshed prompt, standard answer, bilingual notes, and deterministic evaluator after environment rework; made `AL-TE5-003` a real close-address successor match using `AL-TE5-OLD-003` rows.

## Chinese

### 数据来源与谱系

本任务属于 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，沿用来源样例 `E003` 的 renewal queue 工作模式，并使用 `task_group_019` 的共享生成环境。目标构造信息来自 `task_group/task_group_019/env/data/manifest.json`：隐藏任务组为 `test_005`，release boundary 为 `2025-05-20`，目标队列大小为 `8`，当前许可证号为 `AL-TE5-001` 到 `AL-TE5-008`，并包含从旧许可证 `AL-TE5-OLD-003` 到当前许可证 `AL-TE5-003` 的非精确 close successor 匹配。

标准答案是在环境重构后根据生成的 SQLite 数据 `env/data/licensing.db` 重新推导的，主要使用 `alcohol_licensees`、`alcohol_violations` 和 `renewal_rules` 表。求解器只能通过 `input/prompt.txt` 中列出的公开 API 访问数据；manifest、数据库文件、生成脚本、notes、标准答案和 evaluator 都是隐藏构造材料。

### 任务定义与场景匹配

求解器扮演 licensing analyst，在 release 前为 resort-area alcohol renewal 构建 manual-review queue。可见请求给出了八个当前目标许可证号、release boundary、目标队列大小和相关 API。prompt 故意不暴露构造用的 group tag。预期输出是符合 `input/payloads/answer_template.json` 的规范化 JSON。

该任务符合监管许可审查场景，因为它要求把当前 licensee 身份、violation history、release-date 边界、close/successor match、risk tier 和封闭 next-step label 统一成可执行队列。这个 test 变体是一个日期边界敏感的 resort 名册，包含重复 serious 记录、一个 close-address successor 匹配和边界之后的 distractor。

### 材料地图

- `GET /api/alcohol/licensees`：当前许可证名册、facility name、address、active 状态、channel type 和 successor 信息。
- `GET /api/alcohol/violations`：violation 日期、severity、disposition、fine balance、alert flag、source name 和边界之后的 distractor。
- `GET /api/renewal/rules`：release-boundary 规则，包括相关边界之后的记录是 distractor，以及 fine/alert flag 需要人工关注。
- `POST /api/sql`：当环境提供 SQL 凭据时可用的只读查询入口。
- `input/payloads/answer_template.json`：输出结构、封闭枚举、日期格式、列表排序和 summary 字段。

### 解法与评估依据

目标当前许可证是 `AL-TE5-001` 到 `AL-TE5-008`。评分时只统计 `violation_date <= 2025-05-20` 的记录。八条当前许可证的 `*-LATE` 边界后记录列入 `summary.post_boundary_violation_ids_excluded`，不得用于 count、most recent date、risk tier、next-step label 或 rank。

关键重构案例是 `AL-TE5-003`。它的当前 licensee 行有 `successor_to = AL-TE5-OLD-003`，当前地址为 `233 Lincoln Ave`，失效旧许可证地址为 `233 Lincoln Avenue`。被接受的 matched violations 是当前精确行 `AV-AL-TE5-003-1`，加上旧许可证行 `AV-AL-TE5-OLD-003-S1` 和 `AV-AL-TE5-OLD-003-S2`。因此 `violation_count = 3`，`most_recent_violation_date = 2025-05-16`，`match_confidence = close_address`，`risk_tier = high`，`next_step_label = board_review`。

标准队列顺序为：

1. `AL-TE5-003`
2. `AL-TE5-008`
3. `AL-TE5-005`
4. `AL-TE5-007`
5. `AL-TE5-002`
6. `AL-TE5-001`
7. `AL-TE5-004`
8. `AL-TE5-006`

前四个许可证进入 `board_review`：`AL-TE5-003`、`AL-TE5-008`、`AL-TE5-005` 和 `AL-TE5-007`。在应用当前许可证或被接受的 successor 匹配后，它们各有至少两条边界前 serious violation，并在 board-review 组内按最新 matched pre-boundary 日期排序。其余四个许可证进入 `manual_fine_check`：`AL-TE5-002`、`AL-TE5-001`、`AL-TE5-004` 和 `AL-TE5-006`，并在 fine-check 组内按最新 matched pre-boundary 日期排序。八个目标的 risk tier 均为 `high`。`summary.close_or_uncertain_match_license_numbers` 只包含 `AL-TE5-003`；`summary.board_review_license_numbers` 按许可证号排序为 `AL-TE5-003`、`AL-TE5-005`、`AL-TE5-007`、`AL-TE5-008`。

Evaluator 有七个确定性整点评分项，原始权重如下：

- `SP001`，权重 3：队列 membership 与 rank order 完全正确。
- `SP002`，权重 2：每个许可证的边界前 violation count 和 most recent used date 正确。
- `SP003`，权重 2：match confidence 与 close/uncertain summary set 正确。
- `SP004`，权重 2：封闭 next-step label 正确。
- `SP005`，权重 2：正确排除八条边界之后 violation ID，且未使用 late date。
- `SP006`，权重 2：risk tier 与 board-review summary set 正确。
- `SP007`，权重 1：queue size、boundary date 和 facility identity 字段正确。

每个评分项都是 all-or-nothing。Evaluator 接受 `$1` 作为候选答案路径；如果未提供路径，则默认评分本任务的 gold answer。

常见错误包括在新版 prompt 中继续命名或依赖隐藏的 construction group tag、只统计 `AL-TE5-003` 的当前精确行、照抄生成器内部的 `close_successor` 标签而不是允许的输出枚举、使用 `post_boundary_feed` 的边界后记录、把其他 renewal group 中相似地址的记录错误并入、以及只按 violation count 排序而忽略 next-step priority bucket。

### 迁移设计

主要 train anchor 是 `train_003`。它迁移 renewal boundary discipline、successor 与 close-address reconciliation、相同地址 distractor 的排除、封闭 match-confidence enum、queue summary 惯例和 ranked queue schema。来自 `train_002` 与 `train_005` 的 monitoring-label transfer 只限于升级判断：重复 serious risk 应升级为 `board_review`，而 fine 与 alert 问题保留在更窄的 manual-check label 中。本 test 仍需要任务特定探索，因为目标许可证号、close successor pair、日期、count、fine balance 和 board-review set 都是新的。

### 构造记录

- 作者：Codex main agent
- 创建日期：2026-07-18
- 更新日期：2026-07-18
- 主要变更：环境重构后刷新 prompt、standard answer、双语 notes 和确定性 evaluator；将 `AL-TE5-003` 改为使用 `AL-TE5-OLD-003` 记录的真实 close-address successor 匹配。
