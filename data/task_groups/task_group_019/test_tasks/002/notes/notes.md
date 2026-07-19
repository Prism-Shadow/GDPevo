# test_002 Notes

## English

### Data/source lineage

This task belongs to `SCN_019_regulatory_licensing_eligibility_and_compliance_review` and uses the renewal manual-review queue family derived from source example `E003`. It is the formal `test_002` task for `task_group_019`, anchored to the transfer conventions exposed by `train_003`.

The regenerated environment manifest identifies the renewal boundary `2025-06-15`, target queue size `12`, and current target license numbers `AL-TE2-001` through `AL-TE2-012`. The standard answer was recalculated from `task_group/task_group_019/env/data/licensing.db`, using `alcohol_licensees`, `alcohol_violations`, and `renewal_rules`. Solver-visible access remains limited to the public endpoints named in `input/prompt.txt`; the manifest, database, generator, notes, answer, and evaluator are hidden construction materials.

### Task definition and scenario fit

The solver acts as a licensing analyst preparing a summer pre-release alcohol renewal manual-review queue. The prompt now identifies only the target license-number range, release boundary, target queue size, and environment endpoints; it no longer names the construction group tag. The expected output is a normalized JSON object matching `input/payloads/answer_template.json`.

This fits the regulatory licensing scenario because it requires current-licensee matching, date-bound violation filtering, successor or close-address handling, risk tiering, controlled next-step labels, and a memo-ready queue summary. The task cannot be solved from the prompt alone; it requires environment exploration and transfer of renewal-queue conventions from `train_003`.

### Material map

- `GET /api/alcohol/licensees`: current licensee roster, facility names, addresses, active flags, location ids, and successor markers.
- `GET /api/alcohol/violations`: violation history, dates, themes, severity, disposition, fine balances, alert flags, and source names.
- `GET /api/renewal/rules`: release-boundary policy records, including the `2025-06-15` summer release rule.
- `POST /api/sql`: optional read-only query path if the solver environment supplies SQL credentials.
- `input/payloads/answer_template.json`: required output shape, enum values, date format, queue length, rank ordering, and summary fields.

### Solution and evaluation basis

The gold answer uses the current target licenses `AL-TE2-001` through `AL-TE2-012`. Matched violations must have `violation_date <= 2025-06-15`. The twelve `AV-AL-TE2-*-LATE` rows are after the boundary and are excluded from counts, most recent dates, rank, risk tier, and labels.

The key regenerated edge case is `AL-TE2-012`. Its current license row has `successor_to = AL-TE2-OLD-012` at the same address, `332 River Ave`. The matched pre-boundary set is the current exact row `AV-AL-TE2-012-1` plus legacy successor rows `AV-AL-TE2-OLD-012-S1` and `AV-AL-TE2-OLD-012-S2`. This gives `violation_count = 3`, `most_recent_violation_date = 2025-06-10`, `match_confidence = close_address`, `risk_tier = high`, and `next_step_label = board_review`. The template already allows `close_address`, so no solver-visible schema change is needed for this non-exact successor match.

Gold queue order:

1. `AL-TE2-012`
2. `AL-TE2-010`
3. `AL-TE2-005`
4. `AL-TE2-008`
5. `AL-TE2-002`
6. `AL-TE2-007`
7. `AL-TE2-009`
8. `AL-TE2-001`
9. `AL-TE2-004`
10. `AL-TE2-011`
11. `AL-TE2-006`
12. `AL-TE2-003`

The answer ranks by next-step priority, then most recent matched violation date descending, then matched count descending, then license number ascending. `board_review` applies to licenses with repeated serious matched pre-boundary violations, including successor rows. `AL-TE2-012` and `AL-TE2-010` are therefore board-review cases. `manual_fine_check` applies to material fine-balance or unpaid-fine exposure without the board trigger. `AL-TE2-003` is the remaining alert-driven lower-risk entry and uses `manual_ALERT_check`. Risk is high for board-review and material fine-exposure entries, and medium for `AL-TE2-003`.

The evaluator has seven deterministic whole-point checks with raw weights:

- `SP001`, weight 3: exact queue membership and rank order.
- `SP002`, weight 2: per-license pre-boundary matched violation counts and most recent used dates, including the successor-expanded count for `AL-TE2-012`.
- `SP003`, weight 2: match-confidence fields and the close/uncertain summary containing `AL-TE2-012`.
- `SP004`, weight 3: controlled next-step labels.
- `SP005`, weight 2: exclusion of the twelve post-boundary violation IDs and no late date used.
- `SP006`, weight 2: risk tiers and board-review summary set `AL-TE2-010`, `AL-TE2-012`.
- `SP007`, weight 1: queue size, boundary date, and facility identity fields.

Each point is all-or-nothing. Raw weights are converted to `weight / 15`. The evaluator accepts a candidate answer path as `$1` and defaults to this task's `output/answer.json` when no path is passed.

Likely model pitfalls are naming or filtering by the hidden construction group tag, counting post-boundary `post_boundary_feed` rows, missing the `AL-TE2-012` successor link, treating successor rows as exact matches, leaving `AL-TE2-012` at the current-only count of one, ranking solely by most recent violation date without next-step priority, and using free-text next steps instead of the closed enum labels.

### Transfer design

`test_002` is anchored to `train_003`. The transferable knowledge is the renewal-queue discipline: enforce the release boundary, prefer exact current-license matches when adequate, use successor or close-address matching when a current target license links to legacy rows, mark non-exact matches with the allowed non-exact enum, use the closed next-step label set, preserve the ranked queue schema, and summarize excluded late records plus board-review licenses. The high-value transfer-dependent scoring points are `SP001`, `SP003`, `SP004`, `SP005`, and `SP006`. Task-specific exploration remains necessary because the boundary is later, the queue is larger, the target licensees are new, and the regenerated data makes `AL-TE2-012` a real successor-match case.

### Construction record

- Author: task-builder-test-002; reworked by Codex main agent
- Created: 2026-07-18
- Updated: 2026-07-18
- Major changes: reworked prompt to remove the construction group tag, recalculated the standard answer and evaluator against the regenerated database, and documented the `AL-TE2-012` successor match using `AV-AL-TE2-012-1`, `AV-AL-TE2-OLD-012-S1`, and `AV-AL-TE2-OLD-012-S2`.

## 中文

### 数据来源与谱系

本任务属于 `SCN_019_regulatory_licensing_eligibility_and_compliance_review`，使用来源样例 `E003` 抽象出的 renewal manual-review queue 工作族。它是 `task_group_019` 的正式 `test_002`，迁移锚点是 `train_003` 中体现的 renewal queue 规则与输出惯例。

重新生成后的环境 manifest 给出了边界日期 `2025-06-15`、目标队列大小 `12`，以及当前目标许可证 `AL-TE2-001` 到 `AL-TE2-012`。标准答案根据 `task_group/task_group_019/env/data/licensing.db` 重新计算，使用 `alcohol_licensees`、`alcohol_violations` 和 `renewal_rules` 表。求解器只能通过 `input/prompt.txt` 中列出的公开端点访问数据；manifest、数据库、生成脚本、notes、answer 和 evaluator 都是隐藏构造材料。

### 任务定义与场景匹配

求解器扮演 licensing analyst，在夏季 renewal release 前准备 alcohol renewal manual-review queue。当前提示只给出目标许可证范围、release boundary、队列大小和环境入口；它不再暴露构造用的 group tag。预期输出是符合 `input/payloads/answer_template.json` 的规范化 JSON。

该任务符合监管许可审查场景，因为它要求识别当前 licensee、按日期边界筛选 violation、处理 successor 或 close-address 关系、确定 risk tier、选择封闭 next-step label，并生成可供工作人员复核的 summary。提示本身不能直接给出答案；求解器必须探索环境数据，并迁移 `train_003` 中体现的 renewal queue 规则。

### 材料地图

- `GET /api/alcohol/licensees`：当前许可证名册、facility name、address、active 状态、location id 和 successor 标记。
- `GET /api/alcohol/violations`：violation history、日期、theme、severity、disposition、fine balance、alert flag 和 source name。
- `GET /api/renewal/rules`：release-boundary 政策记录，包括 `2025-06-15` summer release rule。
- `POST /api/sql`：当求解环境提供 SQL 凭据时可用的只读查询入口。
- `input/payloads/answer_template.json`：输出结构、枚举值、日期格式、队列长度、rank 排序和 summary 字段。

### 解法与评估依据

标准答案使用当前目标许可证 `AL-TE2-001` 到 `AL-TE2-012`。纳入匹配的 violation 必须满足 `violation_date <= 2025-06-15`。十二条 `AV-AL-TE2-*-LATE` 记录位于边界之后，因此不得用于 count、most recent date、rank、risk tier 或 label。

重新生成后的关键边界案例是 `AL-TE2-012`。它的当前许可证记录在同一地址 `332 River Ave` 上有 `successor_to = AL-TE2-OLD-012`。边界前匹配集合由当前 exact 记录 `AV-AL-TE2-012-1` 加上 legacy successor 记录 `AV-AL-TE2-OLD-012-S1` 和 `AV-AL-TE2-OLD-012-S2` 组成。因此 `violation_count = 3`，`most_recent_violation_date = 2025-06-10`，`match_confidence = close_address`，`risk_tier = high`，`next_step_label = board_review`。模板已经允许 `close_address`，因此这个非 exact successor match 不需要修改求解器可见 schema。

标准队列顺序为：

1. `AL-TE2-012`
2. `AL-TE2-010`
3. `AL-TE2-005`
4. `AL-TE2-008`
5. `AL-TE2-002`
6. `AL-TE2-007`
7. `AL-TE2-009`
8. `AL-TE2-001`
9. `AL-TE2-004`
10. `AL-TE2-011`
11. `AL-TE2-006`
12. `AL-TE2-003`

排序先看 next-step priority，再按最新匹配 violation 日期降序、匹配数量降序、许可证号升序。`board_review` 用于存在重复 serious 边界前匹配记录的许可证，包括 successor rows。因此 `AL-TE2-012` 和 `AL-TE2-010` 是 board-review case。`manual_fine_check` 用于没有 board trigger 但存在明显 fine-balance 或 unpaid-fine 风险的条目。`AL-TE2-003` 是剩余的 alert-driven 低风险条目，因此使用 `manual_ALERT_check`。board-review 和明显 fine-exposure 条目为 high risk，`AL-TE2-003` 为 medium。

Evaluator 有七个确定性整点评分项，原始权重如下：

- `SP001`，权重 3：队列 membership 与 rank order 完全正确。
- `SP002`，权重 2：每个许可证的边界前 matched violation count 和 most recent used date 正确，包括 `AL-TE2-012` 的 successor-expanded count。
- `SP003`，权重 2：match confidence 与包含 `AL-TE2-012` 的 close/uncertain summary 正确。
- `SP004`，权重 3：封闭 next-step label 正确。
- `SP005`，权重 2：正确排除十二条边界之后 violation ID，且没有使用 late date。
- `SP006`，权重 2：risk tier 与 board-review summary set `AL-TE2-010`、`AL-TE2-012` 正确。
- `SP007`，权重 1：queue size、boundary date 和 facility identity 字段正确。

每个评分项都是 all-or-nothing。原始权重按 `weight / 15` 转换为分值。Evaluator 接受 `$1` 作为候选答案路径；如果未传入路径，则默认评分本任务的 `output/answer.json`。

常见错误包括按隐藏 construction group tag 命名或过滤、使用 `post_boundary_feed` 的边界后记录、漏掉 `AL-TE2-012` 的 successor link、把 successor rows 误标为 exact、只把 `AL-TE2-012` 算作当前许可证的一条记录、只按最新 violation 日期排序而忽略 next-step priority、以及使用自由文本 next step 而不是封闭枚举。

### 迁移设计

`test_002` 锚定 `train_003`。需要迁移的知识包括：严格执行 release boundary；在当前许可证记录足够时优先 exact match；当当前目标许可证链接到 legacy rows 时使用 successor 或 close-address matching；用允许的非 exact enum 标记非 exact match；使用封闭 next-step label；保持 ranked queue schema；并在 summary 中列出 late exclusion 和 board-review license。高价值迁移相关评分项为 `SP001`、`SP003`、`SP004`、`SP005` 和 `SP006`。任务本身仍需要数据探索，因为边界日期更晚、队列更大、目标 licensee 全部更新，并且重新生成的数据使 `AL-TE2-012` 成为真实 successor-match case。

### 构造记录

- 作者：task-builder-test-002；由 Codex main agent 返工
- 创建日期：2026-07-18
- 更新日期：2026-07-18
- 主要变更：修改 prompt 以移除 construction group tag；根据重新生成的数据库重新计算 standard answer 和 evaluator；记录 `AL-TE2-012` 使用 `AV-AL-TE2-012-1`、`AV-AL-TE2-OLD-012-S1`、`AV-AL-TE2-OLD-012-S2` 的 successor match。
