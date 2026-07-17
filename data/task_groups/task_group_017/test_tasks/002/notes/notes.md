# Test 002 Notes - M-BAY-144 Retention/Hold Remediation

## English Audit Notes

Task scope: test_002 asks the solver to review matter `M-BAY-144`, the Bay & Tidewater Emissions Data Matter, for retention, preservation, and hold-remediation issues. Solver-visible files are English-only and consist of `input/prompt.txt` and `input/payloads/answer_template.json`. The prompt does not include the answer path, scoring checklist, or train-anchor guidance.

Data/source lineage:
- Source scenario: `SCN_017_white_collar_investigation_production_review`.
- Source example family: mainly `E002` retention/subpoena/hold analysis, with transfer also from `E003` custodian/source issue review.
- Task design brief: `scratch/task_group_design.md` defines `test_002` as a retention/hold remediation task for `M-BAY-144` with the same family schema as `train_002`.
- Public environment data: `task_group/task_group_017/env/data/generated/*.json`, exposed through the shared API endpoints in `env/server.py`.
- Task-local payloads: only `input/payloads/answer_template.json`; there is no task-local factual memo for this test task.

Important evidence and answer basis:
- `matters`: `M-BAY-144` has subpoena date `2024-12-04`, hold date `2024-12-06`, production deadline `2025-04-15`, and regulator notice flag true.
- `subpoena_categories`: core current categories are `B-01` emissions lab data, `B-02` Teams/EHS discussions, `B-03` executive email/VaultSeven archive, `B-04` Tidewater audit reports, and `B-05` off-site vendor boxes and personal devices. Noise categories with `BA-N...` IDs should not drive this task's formal answer.
- `production_logs`: `PL-0023` through `PL-0027` provide the current batch status and notes for `B-01` through `B-05`.
- `retention_rules`: `RR-0011` through `RR-0014` provide the controlling retention facts for 2020 emissions lab data, Teams channel content, executive email, and the Tidewater audit report.
- `destruction_events`: `DE-0008` is the pre-hold 2020 lab-data destruction; `DE-0009` is the post-hold Teams channel purge.
- `collection_events`: `CE-0019` through `CE-0023` provide collection status, quantities, source names, and missing counts for the core issue set.

Standard-answer rationale:
- `RC-2020-LAB`: Six units of 2020 emissions lab data were destroyed on `2023-01-27` under the three-year retention rule before the `2024-12-06` hold. This is a policy gap affecting `B-01`, not post-hold spoliation. Summary exports are the only partial recovery source.
- `RC-TEAMS-PURGE`: Eleven Teams channels were purged on `2025-02-05`, after the hold date. This is the critical post-hold preservation issue affecting `B-02`, requiring regulator notice.
- `RC-EMAIL-VAULTSEVEN` and `RS-EMAIL-VAULTSEVEN`: VaultSeven retains executive email despite active purge. The collection event shows 9,220 collected archive items for `B-03`; the proper classification is recoverable archive, not lost data.
- `RC-TIDEWATER-AUDIT` and `RS-AUDIT-TIDEWATER`: The missing 2024 Tidewater audit report should exist under the five-year report rule and vendor-copy override, so it is a retained-missing source for `B-04` requiring vendor retrieval.
- `HD-OFFSITE-VENDOR` and `HD-PERSONAL-DEVICE`: The hold notice omitted off-site vendor boxes and personal devices for `B-05`. The split defects preserve the two different action enums: hold refresh for the off-site vendor omission and supplemental collection for the personal phone omission.

Evaluation basis:
- The evaluator has 9 exact-match scoring points totaling 18 raw points. Weights are in `{1,2,3}` and are normalized to a `score` from 0.0 to 1.0.
- Scored points cover complete issue/source sets; pre-hold 2020 lab destruction; post-hold Teams purge date, quantity, affected category, and action; VaultSeven archive availability and count; the missing 2024 Tidewater audit report within five-year retention/vendor copy; partial lab recovery source; off-site vendor and personal-device hold omissions; remediation action ranking; and overall disclosure/category status.
- String-like judgments are represented as enums in `answer_template.json`: timing class, severity, primary action, defect type, recovery status, and owner queue.
- The evaluator normalizes lists by sorting and trims scalar strings, but otherwise uses exact matches. Free-form `due_basis` text is required by the answer schema but not scored independently.
- Self-check using `output/answer.json` returns `score: 1.0`.

Transfer design:
- Train anchor `train_002` is the primary anchor. It teaches the retention/hold schema, the distinction between pre-hold policy destruction and post-hold preservation loss, the use of retention rules plus destruction/collection events, recoverable archive handling, vendor retrieval for retained-missing audit reports, and remediation action enums.
- Train anchor `train_005` is the secondary anchor. It reinforces source-readiness reasoning for archive sources, Teams gaps, personal-device hold omissions, and supplemental collection actions.
- Transfer-dependent difficulty: recognizing that the same legal timing rules from `train_002` apply to different Bayport record classes; mapping current production-log categories to retention/destruction/collection records despite noise rows; and assigning action enums without a solver-visible SOP checklist.
- Task-specific exploration difficulty: finding the correct Bayport event IDs and counts (`DE-0008`, `DE-0009`, `CE-0019` through `CE-0023`, `RR-0011` through `RR-0014`, `PL-0023` through `PL-0027`) and ignoring `BA-N...` noise categories.

Construction record:
- Author: OpenAI Codex task-builder subagent.
- Created: 2026-07-07.
- Updated: 2026-07-07.
- Major changes: initial formal `test_002` construction with prompt, answer template, standard answer, exact-match evaluator, and bilingual notes.

## 中文审计说明

任务范围：test_002 要求解题方审查 `M-BAY-144`，即 Bay & Tidewater Emissions Data Matter，判断留存、保全和补救问题。解题可见文件仅为英文，包括 `input/prompt.txt` 和 `input/payloads/answer_template.json`。提示词不包含答案路径、评分清单或训练任务锚点说明。

数据和来源：
- 来源场景：`SCN_017_white_collar_investigation_production_review`。
- 来源示例族：主要来自 `E002` 的传票、留存和保全分析，也使用 `E003` 的保管人和来源问题审查经验。
- 任务设计说明：`scratch/task_group_design.md` 将 `test_002` 定义为 `M-BAY-144` 的留存和保全补救任务，并要求与 `train_002` 使用同一任务族结构。
- 公共环境数据：`task_group/task_group_017/env/data/generated/*.json`，通过 `env/server.py` 中的共享 API 端点暴露。
- 本任务本地负载：只有 `input/payloads/answer_template.json`；该测试任务没有本地事实备忘录。

关键证据和答案依据：
- `matters`：`M-BAY-144` 的传票日期为 `2024-12-04`，保全日期为 `2024-12-06`，生产截止日为 `2025-04-15`，并标记监管通知为 true。
- `subpoena_categories`：当前核心类别是 `B-01` 排放实验室数据、`B-02` Teams/EHS 讨论、`B-03` 高管邮件和 VaultSeven 归档、`B-04` Tidewater 审计报告、`B-05` 场外供应商箱和个人设备。`BA-N...` 噪声类别不应进入正式答案。
- `production_logs`：`PL-0023` 到 `PL-0027` 给出 `B-01` 到 `B-05` 的当前批次状态和说明。
- `retention_rules`：`RR-0011` 到 `RR-0014` 分别对应 2020 排放实验室数据、Teams 频道内容、高管邮件和 Tidewater 审计报告的控制性留存事实。
- `destruction_events`：`DE-0008` 是保全前的 2020 实验室数据销毁；`DE-0009` 是保全后的 Teams 频道清除。
- `collection_events`：`CE-0019` 到 `CE-0023` 给出核心问题的收集状态、数量、来源名称和缺失数量。

标准答案理由：
- `RC-2020-LAB`：六个单位的 2020 排放实验室数据在 `2023-01-27` 根据三年留存规则销毁，早于 `2024-12-06` 的保全日期。这是影响 `B-01` 的政策缺口，不是保全后毁损。摘要导出是唯一的部分恢复来源。
- `RC-TEAMS-PURGE`：11 个 Teams 频道在保全后于 `2025-02-05` 被清除。这是影响 `B-02` 的关键保全后问题，需要监管通知。
- `RC-EMAIL-VAULTSEVEN` 和 `RS-EMAIL-VAULTSEVEN`：VaultSeven 保留高管邮件，尽管活动系统存在清除。收集事件显示 `B-03` 有 9,220 个归档项目已收集；正确分类是可恢复归档，而不是数据灭失。
- `RC-TIDEWATER-AUDIT` 和 `RS-AUDIT-TIDEWATER`：缺失的 2024 Tidewater 审计报告应根据五年规则和供应商副本要求仍然存在，因此是 `B-04` 的应留存但缺失来源，需要供应商取回。
- `HD-OFFSITE-VENDOR` 和 `HD-PERSONAL-DEVICE`：保全通知遗漏了 `B-05` 的场外供应商箱和个人设备。拆成两个缺陷是为了保留不同的动作枚举：场外供应商遗漏需要刷新保全通知，个人电话遗漏需要补充收集。

评估依据：
- 评估器包含 9 个精确匹配评分点，共 18 个原始分，权重均在 `{1,2,3}` 中，并归一化为 0.0 到 1.0 的 `score`。
- 评分点覆盖完整的问题和来源集合、保全前 2020 实验室数据销毁、保全后 Teams 清除的日期和数量及影响类别和动作、VaultSeven 归档可用性和数量、五年留存和供应商副本下缺失的 2024 Tidewater 审计报告、实验室摘要的部分恢复来源、场外供应商和个人设备保全遗漏、补救动作排序，以及整体披露和类别状态。
- 类似字符串的判断都在 `answer_template.json` 中转换为枚举：时间分类、严重程度、主要动作、缺陷类型、恢复状态和负责队列。
- 评估器会对列表排序并去除标量字符串首尾空格，除此之外使用精确匹配。`due_basis` 文本是答案结构要求，但不单独评分。
- 使用 `output/answer.json` 自检返回 `score: 1.0`。

迁移设计：
- 主要训练锚点是 `train_002`。它提供留存和保全结构、保全前政策销毁与保全后灭失的区分、留存规则与销毁/收集事件的联合使用、可恢复归档的处理、仍应保留审计报告的供应商取回，以及补救动作枚举。
- 次要训练锚点是 `train_005`。它加强归档来源、Teams 缺口、个人设备保全遗漏和补充收集动作的来源就绪性判断。
- 依赖迁移的难点：把 `train_002` 的法律时间判断规则迁移到不同的 Bayport 记录类别；在噪声行中把当前生产日志类别映射到留存、销毁和收集记录；在没有可见 SOP 清单的情况下选择动作枚举。
- 任务自身探索难点：找到正确的 Bayport 事件 ID 和数量（`DE-0008`、`DE-0009`、`CE-0019` 到 `CE-0023`、`RR-0011` 到 `RR-0014`、`PL-0023` 到 `PL-0027`），并忽略 `BA-N...` 噪声类别。

构造记录：
- 作者：OpenAI Codex task-builder subagent。
- 创建日期：2026-07-07。
- 更新日期：2026-07-07。
- 主要变更：首次构建正式 `test_002`，包括提示词、答案模板、标准答案、精确匹配评估器和双语 notes。
