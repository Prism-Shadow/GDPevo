# test_002 Notes - Portola Energy Subpoena Retention Coverage Matrix

## English

### Data and Source Lineage

This task belongs to `task_group_017`, scenario `SCN_017_white_collar_investigation_production_review`, with source-example lineage from `E001`, `E002`, and `E003`. It is the formal test task `test_002` described in `scratch/task_group_design.md`: a Portola Energy grand jury subpoena review focused on retention coverage for trading blotters, deal-chat exports, voicemail, archive exceptions, and surveillance reports.

The task-builder ownership scope is `task_group/task_group_017/test_tasks/002/`. Solver-visible materials are `input/prompt.txt`, `input/payloads/review_scope.json`, and `input/payloads/answer_template.json`. The substantive evidence is expected to come from the shared Investigation Review Hub at `<TASK_ENV_BASE_URL>`, especially the matter, subpoena-category, custodian-source, retention-event, remediation-action, and optional read-only SQL query endpoints. No solver-visible task-local payload contains the answer facts.

The stable matter is `MTR-PORTOLA-GJ`. The key generated environment records for this task are `RET-PORT-TRADE-2018`, `RET-PORT-CHAT-POST`, `RET-PORT-VOICE`, `RET-PORT-AUDIT-MISSING`, and `SRC-PORT-ENERGYCOMMS`.

### Task Definition and Scenario Fit

The business request asks for a structured retention coverage matrix for a DOJ Fraud Section grand jury matter involving Portola Energy trading records. The solver must classify retention events by timing against the hold date, identify communication-system gaps, recognize an available chat-attachment archive, treat a missing surveillance report as a record that should exist, compute normalized metrics, and rank remediation actions.

This fits the white-collar investigation production review scenario because it requires cross-system reconstruction of subpoena category impacts, retention policies, source availability, legal-risk classes, and operational remediation. It is not a tutorial: the prompt asks for a realistic legal-operations deliverable and does not expose scoring points, answer facts, or the transfer SOP.

### Material Map

`input/prompt.txt` gives the user-facing request, requires use of `<TASK_ENV_BASE_URL>`, and prohibits use of local environment source files, manifests, database files, answers, or evaluation files.

`input/payloads/review_scope.json` gives the matter identifier, endpoint inventory, API key information for the read-only SQL endpoint, and client-facing category labels for `PE-A` through `PE-I`. It does not identify which retention events or categories are affected.

`input/payloads/answer_template.json` defines the required output JSON shape, enum choices, list ordering, stable ID conventions, and integer precision for counts, retention months, purge-window days, and action ranks.

The shared hub should supply these decisive facts:

- `RET-PORT-TRADE-2018`: 12 monthly 2018 trade blotters destroyed on 2024-11-30, before the 2025-01-09 hold, under policy section `2.7` and a 72-month retention schedule, affecting `PE-B`.
- `RET-PORT-CHAT-POST`: 18 deal-chat exports deleted on 2025-02-04, after the 2025-01-09 hold, under policy section `6.2`, affecting `PE-D` and `PE-E`.
- `RET-PORT-VOICE`: trader voicemail auto-purge after 120 days, with event date 2025-03-11, hold date 2025-01-09, and affected category `PE-D`.
- `SRC-PORT-ENERGYCOMMS`: EnergyComms chat archive is available for chat attachments and affects `PE-D` and `PE-E`.
- `RET-PORT-AUDIT-MISSING`: the 2024 surveillance report should exist under a 60-month retention rule but is missing, affecting `PE-F` and `PE-I`.

### Solution and Evaluation Basis

The standard answer places all four retention events in `retention_events`, includes the deleted chat exports and voicemail auto-purge in `communication_gaps`, places EnergyComms in `available_archives`, and gives five prioritized actions.

The key legal distinction is timing. `RET-PORT-TRADE-2018` is `policy_destroyed_pre_hold` and low risk because the destruction date predates the hold and matches the 72-month retention schedule. `RET-PORT-CHAT-POST` is a high-risk `post_hold_loss` because the deletion happened after the hold and involved 18 chat exports. `RET-PORT-VOICE` is an `auto_purged` communication gap rather than a box or document destruction event. `RET-PORT-AUDIT-MISSING` is `should_exist_missing` because the 2024 surveillance report should remain under a 60-month rule. `SRC-PORT-ENERGYCOMMS` is an available archive exception for chat attachments, so the response should collect the archive while still treating the post-hold export deletion as a preservation issue.

The evaluator has eight whole-point scoring goals:

- `P01_matter_and_event_coverage`, weight 1: correct matter id and complete four-event retention set.
- `P02_trade_blotter_pre_hold_policy_classification`, weight 2: trade blotter status, risk, category, dates, policy section, 72-month period, and 12 monthly blotters.
- `P03_chat_export_post_hold_loss`, weight 3: deal-chat post-hold loss status, categories `PE-D` and `PE-E`, 18-export volume, communication-gap entry, archive exception reference, and disclosure action.
- `P04_voice_auto_purge_gap`, weight 2: voicemail auto-purge status, 120-day window, category `PE-D`, dates, and communication-gap entry.
- `P05_energycomms_archive_exception`, weight 2: EnergyComms archive availability, chat-attachment scope, category set, archive-limitation field, and collection owner.
- `P06_missing_surveillance_report`, weight 3: surveillance report missing-required-record status, 60-month retention period, category set, one-report count, and locate action.
- `P07_metrics`, weight 2: event counts, archive count, 12 blotters, 18 exports, 120-day purge window, missing report count, and affected-category sets.
- `P08_action_ranking`, weight 3: exact operational order for preservation disclosure, missing-report search, archive collection, voicemail documentation, and no-action policy-loss disposition.

These scoring points cover more than four distinct outcomes: retention timing classification, post-hold preservation loss, communication auto-purge, archive exception implications, missing required records, numeric aggregation, and remediation ranking. Each point is deterministic and all-or-nothing. The evaluator normalizes IDs, enum casing, integer-like values, and category sets; it does not score prose.

Likely model pitfalls include treating the pre-hold trade blotter destruction as spoliation, failing to connect the post-hold chat deletion to both `PE-D` and `PE-E`, omitting the EnergyComms archive because it is a source record rather than a retention event, treating the available archive as fully curing the post-hold deletion, forgetting the 120-day voicemail purge window, and ranking the low-risk pre-hold policy loss above higher-risk remediation work.

### Transfer Design

The intended train anchors are `train_002` and `train_005`. From `train_002`, a fewshot skill can infer the distinction between pre-hold policy destruction and post-hold preservation loss, the treatment of communication auto-purge, the handling of a missing report that should exist under a retention rule, and the use of separate `retention_events`, `communication_gaps`, `available_archives`, `metrics`, and action rows. From `train_005`, a skill can infer that archive availability changes the remediation path for deleted collaboration or communication data, and that action ranking should prioritize disclosure and recovery work over documentation or no-action dispositions.

The task-specific exploration remains nontrivial because Portola uses new category codes, new event IDs, a different business domain, chat attachment archive scope rather than email or Teams archive scope, and volumes measured as monthly blotters, exports, days, and reports rather than boxes. The solver-visible prompt does not restate the hidden SOP; transfer is expected to come from comparing train inputs and answers.

### Construction Record

Author: Task-builder 07 / Codex.

Created: 2026-07-18.

Updated: 2026-07-18.

Major changes: Created the complete formal `test_002` task folder with solver-visible prompt and payloads, hidden standard answer, bilingual notes, and deterministic evaluator.

## Chinese

### 数据来源与任务定位

本任务属于 `task_group_017`，场景为 `SCN_017_white_collar_investigation_production_review`，来源示例为 `E001`、`E002` 和 `E003`。它是 `scratch/task_group_design.md` 中规划的正式测试任务 `test_002`：围绕 Portola Energy 的大陪审团传票，审查交易 blotter、deal chat 导出、voicemail、归档例外以及 surveillance report 的留存覆盖情况。

本任务构建者只负责 `task_group/task_group_017/test_tasks/002/`。求解者可见材料包括 `input/prompt.txt`、`input/payloads/review_scope.json` 和 `input/payloads/answer_template.json`。实质证据应来自共享 Investigation Review Hub 的 `<TASK_ENV_BASE_URL>`，特别是 matter、subpoena category、custodian source、retention event、remediation action 以及可选只读 SQL 查询端点。任务本地可见 payload 不包含答案事实。

稳定 matter id 是 `MTR-PORTOLA-GJ`。本任务使用的关键环境记录是 `RET-PORT-TRADE-2018`、`RET-PORT-CHAT-POST`、`RET-PORT-VOICE`、`RET-PORT-AUDIT-MISSING` 和 `SRC-PORT-ENERGYCOMMS`。

### 任务定义与场景契合

业务请求是为 Portola Energy 能源交易记录相关的 DOJ Fraud Section 大陪审团事项生成结构化 retention coverage matrix。求解者需要根据 hold 日期对 retention events 做时间分类，识别通信系统缺口，认定可用的 chat attachment archive，判断 surveillance report 属于本应存在但缺失的记录，计算规范化指标，并排序补救动作。

该任务契合白领调查 production review 场景，因为它要求跨系统重建传票类别影响、保存政策、来源可用性、法律风险分类和运营补救动作。它不是教程；prompt 只提出真实的法律运营交付需求，不暴露评分点、答案事实或迁移 SOP。

### 材料地图

`input/prompt.txt` 提供面向求解者的业务请求，要求使用 `<TASK_ENV_BASE_URL>`，并禁止使用本地环境源码、manifest、数据库文件、答案或评估文件。

`input/payloads/review_scope.json` 提供 matter 标识、端点清单、只读 SQL 端点的 API key 信息，以及 `PE-A` 到 `PE-I` 的客户请求类别标签。它不说明哪些 retention events 或 categories 受到影响。

`input/payloads/answer_template.json` 定义所需 JSON 输出结构、枚举选项、列表排序、稳定 ID 约定，以及计数、保存月数、自动清除天数和动作排序的整数精度。

共享 hub 应提供以下关键事实：

- `RET-PORT-TRADE-2018`：12 个月度 2018 trade blotters 于 2024-11-30 销毁，早于 2025-01-09 hold，依据政策 `2.7` 和 72 个月保存计划，影响 `PE-B`。
- `RET-PORT-CHAT-POST`：18 个 deal-chat exports 于 2025-02-04 删除，晚于 2025-01-09 hold，依据政策 `6.2`，影响 `PE-D` 和 `PE-E`。
- `RET-PORT-VOICE`：trader voicemail 120 天自动清除，event date 为 2025-03-11，hold date 为 2025-01-09，影响 `PE-D`。
- `SRC-PORT-ENERGYCOMMS`：EnergyComms chat archive 对 chat attachments 可用，影响 `PE-D` 和 `PE-E`。
- `RET-PORT-AUDIT-MISSING`：2024 surveillance report 根据 60 个月保存规则应当存在但缺失，影响 `PE-F` 和 `PE-I`。

### 答案与评估依据

标准答案把四个 retention events 放入 `retention_events`，把已删除的 chat exports 和 voicemail auto-purge 放入 `communication_gaps`，把 EnergyComms 放入 `available_archives`，并给出五个按优先级排序的动作。

核心法律判断是时间点。`RET-PORT-TRADE-2018` 是 `policy_destroyed_pre_hold` 且风险低，因为销毁日期早于 hold，并符合 72 个月保存计划。`RET-PORT-CHAT-POST` 是高风险 `post_hold_loss`，因为删除发生在 hold 之后且涉及 18 个 chat exports。`RET-PORT-VOICE` 是 `auto_purged` 通信缺口，而不是纸箱或文档销毁事件。`RET-PORT-AUDIT-MISSING` 是 `should_exist_missing`，因为 2024 surveillance report 在 60 个月规则下应当保留。`SRC-PORT-ENERGYCOMMS` 是 chat attachments 的可用归档例外，因此响应中应收集归档，同时仍把 hold 后导出删除视为 preservation issue。

评估器包含八个整点评分目标：

- `P01_matter_and_event_coverage`，权重 1：正确 matter id 和完整四个 retention event 集合。
- `P02_trade_blotter_pre_hold_policy_classification`，权重 2：trade blotter 的状态、风险、类别、日期、政策条款、72 个月保存期和 12 个月度 blotters。
- `P03_chat_export_post_hold_loss`，权重 3：deal-chat hold 后损失状态、`PE-D` 和 `PE-E` 类别、18 个 exports、communication gap 条目、归档例外引用和披露动作。
- `P04_voice_auto_purge_gap`，权重 2：voicemail auto-purge 状态、120 天窗口、类别 `PE-D`、日期和 communication gap 条目。
- `P05_energycomms_archive_exception`，权重 2：EnergyComms archive 可用性、chat attachment 范围、类别集合、归档限制字段和收集责任人。
- `P06_missing_surveillance_report`，权重 3：surveillance report 为 missing required record、60 个月保存期、类别集合、1 份报告以及 locate action。
- `P07_metrics`，权重 2：事件计数、归档数量、12 个 blotters、18 个 exports、120 天自动清除窗口、缺失报告数量和受影响类别集合。
- `P08_action_ranking`，权重 3：preservation disclosure、missing-report search、archive collection、voicemail documentation 和 no-action policy-loss disposition 的准确运营顺序。

这些评分点覆盖超过四类不同业务结果：留存时间分类、hold 后保全损失、通信自动清除、归档例外影响、应存在记录缺失、数值汇总和补救排序。每个评分点都是确定性的全得或零分。评估器会规范化 ID、枚举大小写、整数值和类别集合，不评价自由文本。

常见错误包括把 hold 前的 trade blotter 销毁误认为 spoliation，未把 hold 后 chat 删除同时关联到 `PE-D` 和 `PE-E`，因为 EnergyComms 是 source record 而不是 retention event 就漏掉它，把可用归档误认为完全治愈 hold 后删除，忘记 120 天 voicemail 清除窗口，以及把低风险 hold 前政策损失排在更高风险补救工作之前。

### 迁移设计

本测试任务的主要训练锚点是 `train_002` 和 `train_005`。从 `train_002`，fewshot skill 可以推断 hold 前按政策销毁与 hold 后保全损失的区别、通信自动清除的处理方式、本应存在但缺失报告的留存判断，以及分别使用 `retention_events`、`communication_gaps`、`available_archives`、`metrics` 和动作行的输出约定。从 `train_005`，skill 可以推断可用归档会改变已删除协作或通信数据的补救路径，并且动作排序应优先处理披露和恢复工作，再处理记录化或 no-action 结论。

本任务仍然需要任务特定探索，因为 Portola 使用新的类别代码、新的事件 ID、不同业务领域、chat attachment archive 而非 email 或 Teams archive，并且数量单位包括 monthly blotters、exports、days 和 reports，而不是 boxes。求解者可见 prompt 不复述隐藏 SOP；迁移应来自对训练输入和标准答案的比较。

### 构建记录

作者：Task-builder 07 / Codex。

创建时间：2026-07-18。

更新时间：2026-07-18。

主要变更：创建完整正式 `test_002` 任务目录，包括求解者可见 prompt 和 payload、隐藏标准答案、双语 notes，以及确定性 evaluator。
