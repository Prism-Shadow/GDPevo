# Test 001 Notes - M-ALD-507 First Production Gap Review

## English Audit Notes

Lineage:
- Scenario source: `SCN_017_white_collar_investigation_production_review`.
- Task group: `task_group_017`, operation family "Production/category gap review".
- Source-example influence: `E001` is the closest first-production gap review pattern; `E003` contributes custodian, QC, and privilege issue structure; `E002` contributes source-availability and retention/portal thinking.
- Matter fixture: `M-ALD-507`, Alderline Revenue Recognition Inquiry.
- Task-local payloads: `input/payloads/answer_template.json` and `input/payloads/partner_request.json`.

Task definition:
- The solver acts for a white-collar production team preparing for an SEC status call.
- The visible input asks for a structured first-production gap review for `M-ALD-507`.
- The expected answer is JSON with `matter_id`, `production_phase`, `category_findings`, `priority_issues`, `disclosure_required`, and `next_actions`.
- The solver must use the shared API and not rely on a task-specific evidence packet. The prompt and payloads are English-only and avoid answer facts, scoring weights, or SOP checklists.

Scenario fit:
- This test belongs to the same workflow as `train_001`: compare subpoena categories against production logs, collection events, privilege logs, QC events, custodians, documents, and retention/source records.
- It also tests transfer from privilege and source-gap conventions in later train tasks: privilege-log completeness is numerical, all-withheld counsel logistics can be over-designation, and uncollected personal chat/device sources are material category gaps.
- The task preserves long-horizon difficulty through noisy generated records for the same matter, including non-scored `AL-N...` categories and stale/noisy production, collection, privilege, and document rows.

Material map:
- `matters`: `M-ALD-507` shows SEC Financial Reporting and Audit Group, subpoena date `2024-08-12`, hold date `2024-08-14`, deadline `2024-12-18`, production protocol true, and regulator notice flag true.
- `subpoena_categories`: scored categories are `A-01`, `A-02`, `A-04`, `A-08`, and `A-09`; noisy categories such as `AL-N001` through `AL-N005` are not in the standard answer.
- `production_logs`: `PL-0018` records the blocked personal-message category; `PL-0019` records the miscoded D. Ibarra complaint for `A-09`; `PL-0020` records the missing Q2 2022 board package for `A-02`; `PL-0021` records 980 withheld and zero produced for prior counsel logistics `A-08`; `PL-0022` records 3,640 privileged-coded records, 2,275 logged, and 1,365 unlogged for `A-01`.
- `collection_events`: `CE-0016` records C-TP-090's encrypted phone not collected after subpoena and Signal/Telegram unavailable; `CE-0017` records D. Ibarra mailbox collection with the non-responsive miscoding; `CE-0018` records the separate board portal source for the missing Q2 2022 board package.
- `privilege_logs`: `PV-0008` supports the A-01 privilege-log gap; `PV-0009` supports the A-08 prior counsel logistics over-designation risk.
- `qc_events`: `QC-0007` identifies one miscoded D. Ibarra revenue-recognition override complaint; `QC-0008` identifies the missing Q2 2022 board package in the separate board portal.
- `custodians`: `C-TP-090` is T. Price, Revenue Controller, with the encrypted phone and Signal/Telegram gap; `C-DI-091` is D. Ibarra, Senior Revenue Accountant, with the complaint miscoding.
- `documents`: `DOC-ALD-IBARRA-001` is the miscoded non-responsive complaint email; `DOC-ALD-BOARD-Q2-2022` is the missing board package in the board portal.
- `retention_rules`: `RR-0015` confirms board packages have a board-portal copy and seven-year retention, supporting the recoverable source-gap classification.

Solution and evaluation basis:
- The affected category set is exactly `A-01`, `A-02`, `A-04`, `A-08`, and `A-09`.
- `PI-ALD-PERSONAL-MESSAGES`: `A-04` is blocked because C-TP-090's personal phone is encrypted and not collected after subpoena; Signal and Telegram are unavailable. It is critical, `post_hold_spoliation`, notice-required, and uses regulator notice plus supplemental collection, forensic recovery, hold refresh, and custodian declaration actions.
- `PI-ALD-IBARRA-MISCODE`: `A-09` needs supplemental production because `DOC-ALD-IBARRA-001`, a D. Ibarra revenue-recognition override complaint, was collected but coded non-responsive. It is a high-severity `coding_error`, with QC reprocessing and supplemental production.
- `PI-ALD-PRIV-UNLOGGED`: `A-01` has a privilege protocol defect. The controlling counts are withheld/privileged-coded `3640`, logged `2275`, and unlogged `1365`.
- `PI-ALD-COUNSEL-OVERBROAD`: `A-08` has 980 withheld and zero produced for prior counsel logistics, creating over-designation risk and requiring privilege review and production of non-privileged material.
- `PI-ALD-BOARD-PORTAL`: `A-02` has a recoverable source gap because the Q2 2022 board package exists in a separate board portal but was not produced.
- `disclosure_required` is true because of the personal-message post-hold collection failure and the privilege-log protocol defect. The ranked action plan puts regulator notice first, then personal-source collection, board-portal collection, QC reprocessing, privilege-log supplement, and counsel over-designation review.
- The evaluator has 9 exact-match scoring points with raw weights: SP001 identity and complete sets weight 1; SP002 personal-message gap weight 3; SP003 Ibarra miscoding weight 2; SP004 privilege-log counts weight 3; SP005 counsel logistics over-designation weight 2; SP006 board-portal gap weight 2; SP007 category mapping weight 2; SP008 ranked remediation/disclosure actions weight 3; SP009 exclusion of noisy issues weight 1.
- The evaluator normalizes list ordering and requires exact scalar, enum, boolean, and integer values. It outputs JSON with `score` and `points`; self-check against `output/answer.json` must return `score: 1.0`.

Transfer design:
- Train anchor `train_001`: teaches the same first-production schema, category-finding pattern, personal-channel disclosure treatment, miscoded complaint treatment, privilege-log gap calculation, overbroad all-withheld counsel risk, and ranked remediation style.
- Train anchor `train_004`: reinforces privilege-log arithmetic, zero-produced counsel category over-designation risk, and complaint/document miscoding despite narrower review labels.
- Train anchor `train_005`: reinforces missing personal-device/cloud/text source treatment, hold-refresh and supplemental-collection actions, and source-readiness distinctions.
- Transfer-dependent scoring goals are SP002, SP003, SP004, SP005, SP007, and SP008. These require applying train-derived conventions to new category IDs, custodian IDs, counts, and noisy records.
- Task-specific exploration difficulty is concentrated in SP006 and SP009: the solver must find the board-portal row, retention rule, and correct material category set among noisy `AL-N...` records without being given answer facts in the prompt.

Construction record:
- Author: task-builder subagent for `task_group_017/test_001`.
- Created date: 2026-07-07.
- Updated date: 2026-07-07.
- Files created only under `task_group/task_group_017/test_tasks/001/`.
- No seed scenario files, environment files, other tasks, `task_group.yaml`, or unrelated scratch files were modified.

## 中文审计说明

血缘来源：
- 场景来源：`SCN_017_white_collar_investigation_production_review`。
- 任务组：`task_group_017`，操作族为“生产/类别缺口审查”。
- 源示例影响：`E001` 是最接近的第一轮生产缺口审查模式；`E003` 提供保管人、QC 和特权问题结构；`E002` 提供来源可用性、保留和门户来源判断。
- 事项夹具：`M-ALD-507`，Alderline Revenue Recognition Inquiry。
- 本任务本地负载：`input/payloads/answer_template.json` 和 `input/payloads/partner_request.json`。

任务定义：
- 解题方扮演准备 SEC 状态会的白领调查生产团队成员。
- 可见输入要求对 `M-ALD-507` 做结构化第一轮生产缺口审查。
- 预期答案是 JSON，字段包括 `matter_id`、`production_phase`、`category_findings`、`priority_issues`、`disclosure_required` 和 `next_actions`。
- 解题方必须使用共享 API，而不是依赖任务专属证据包。prompt 和 payload 只使用英文，不包含答案事实、评分权重或 SOP 清单。

场景契合：
- 本测试与 `train_001` 属于同一工作流：将传票类别与生产日志、收集事件、特权日志、QC 事件、保管人、文档和保留/来源记录进行比对。
- 它还测试后续训练任务中的特权和来源缺口惯例迁移：特权日志完整性需要数值计算，律师后勤类别全部扣留可能是过度指定，未收集的个人聊天/设备来源是实质类别缺口。
- 任务通过同一事项中的噪声生成记录保持长链路难度，包括非评分的 `AL-N...` 类别以及陈旧/噪声生产、收集、特权和文档记录。

材料映射：
- `matters`：`M-ALD-507` 显示 SEC Financial Reporting and Audit Group，传票日期 `2024-08-12`，保全日期 `2024-08-14`，截止日期 `2024-12-18`，生产协议标记为 true，监管通知标记为 true。
- `subpoena_categories`：评分类别是 `A-01`、`A-02`、`A-04`、`A-08` 和 `A-09`；`AL-N001` 到 `AL-N005` 等噪声类别不在标准答案中。
- `production_logs`：`PL-0018` 记录个人消息类别被阻塞；`PL-0019` 记录 `A-09` 的 D. Ibarra 投诉被误编码；`PL-0020` 记录 `A-02` 缺少 Q2 2022 董事会材料；`PL-0021` 记录 `A-08` 先前律师后勤有 980 条扣留且零生产；`PL-0022` 记录 `A-01` 有 3,640 条特权编码记录、2,275 条已登录、1,365 条未登录。
- `collection_events`：`CE-0016` 记录 C-TP-090 的加密手机在传票后未收集，Signal 和 Telegram 不可用；`CE-0017` 记录 D. Ibarra 邮箱已收集但被编码为 non-responsive；`CE-0018` 记录缺失的 Q2 2022 董事会材料位于单独董事会门户。
- `privilege_logs`：`PV-0008` 支撑 A-01 特权日志缺口；`PV-0009` 支撑 A-08 先前律师后勤过度指定风险。
- `qc_events`：`QC-0007` 指出一条 D. Ibarra 收入确认 override 投诉被误编码；`QC-0008` 指出单独董事会门户中存在缺失的 Q2 2022 董事会材料。
- `custodians`：`C-TP-090` 是 Revenue Controller T. Price，存在加密手机和 Signal/Telegram 缺口；`C-DI-091` 是 Senior Revenue Accountant D. Ibarra，存在投诉误编码。
- `documents`：`DOC-ALD-IBARRA-001` 是被误编码为 non-responsive 的投诉邮件；`DOC-ALD-BOARD-Q2-2022` 是董事会门户中缺失的董事会材料。
- `retention_rules`：`RR-0015` 确认董事会材料有董事会门户副本且保留七年，支撑可恢复来源缺口分类。

解答与评估依据：
- 受影响类别集合精确为 `A-01`、`A-02`、`A-04`、`A-08` 和 `A-09`。
- `PI-ALD-PERSONAL-MESSAGES`：`A-04` 被阻塞，因为 C-TP-090 的个人手机在传票后加密且未收集，Signal 和 Telegram 不可用。它是 critical、`post_hold_spoliation`、需要通知，并需要监管通知、补充收集、取证恢复、保全刷新和保管人声明。
- `PI-ALD-IBARRA-MISCODE`：`A-09` 需要补充生产，因为 `DOC-ALD-IBARRA-001` 是 D. Ibarra 关于收入确认 override 的投诉，已经收集但被编码为 non-responsive。它是 high 级 `coding_error`，需要 QC 重处理和补充生产。
- `PI-ALD-PRIV-UNLOGGED`：`A-01` 是特权协议缺陷。控制性计数为扣留/特权编码 `3640`、已登录 `2275`、未登录 `1365`。
- `PI-ALD-COUNSEL-OVERBROAD`：`A-08` 的先前律师后勤类别有 980 条扣留且零生产，形成过度指定风险，需要特权审查并生产非特权材料。
- `PI-ALD-BOARD-PORTAL`：`A-02` 是可恢复来源缺口，因为 Q2 2022 董事会材料存在于单独董事会门户但未生产。
- `disclosure_required` 为 true，原因是个人消息保全后收集失败和特权日志协议缺陷。补救动作排序为监管通知、个人来源收集、董事会门户收集、QC 重处理、特权日志补充、律师后勤过度指定审查。
- 评估器有 9 个精确匹配评分点，原始权重为：SP001 身份和完整集合权重 1；SP002 个人消息缺口权重 3；SP003 Ibarra 误编码权重 2；SP004 特权日志计数权重 3；SP005 律师后勤过度指定权重 2；SP006 董事会门户缺口权重 2；SP007 类别映射权重 2；SP008 补救/披露动作排序权重 3；SP009 排除噪声问题权重 1。
- 评估器会归一化列表顺序，但标量、枚举、布尔和整数值必须精确匹配。输出 JSON 包含 `score` 和 `points`；使用 `output/answer.json` 自检必须返回 `score: 1.0`。

迁移设计：
- 训练锚点 `train_001`：教授相同第一轮生产 schema、类别发现模式、个人渠道披露处理、误编码投诉处理、特权日志缺口计算、全部扣留的律师类别过度指定风险，以及补救动作排序。
- 训练锚点 `train_004`：强化特权日志算术、零生产律师类别过度指定风险，以及较窄审查标签下的投诉/文档误编码。
- 训练锚点 `train_005`：强化缺失个人设备、云端和文本来源处理，保全刷新与补充收集动作，以及来源就绪状态区分。
- 依赖迁移的评分目标是 SP002、SP003、SP004、SP005、SP007 和 SP008。这些点要求把训练中学到的惯例应用到新的类别 ID、保管人 ID、计数和噪声记录上。
- 任务特定探索难度集中在 SP006 和 SP009：解题方必须在没有 prompt 答案事实的情况下找到董事会门户记录、保留规则以及正确的实质类别集合，并排除噪声 `AL-N...` 记录。

构建记录：
- 作者：`task_group_017/test_001` task-builder subagent。
- 创建日期：2026-07-07。
- 更新日期：2026-07-07。
- 文件仅创建在 `task_group/task_group_017/test_tasks/001/` 下。
- 未修改 seed scenario、环境文件、其他任务、`task_group.yaml` 或无关 scratch 文件。
