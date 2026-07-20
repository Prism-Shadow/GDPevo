# train_002 Notes - HarborStone Chemicals Retention and Litigation-Hold Gap Review

## English

### Data and Source Lineage

This task belongs to `SCN_017_white_collar_investigation_production_review`, using the stage 1 example family `E001`, `E002`, and `E003`. It primarily anchors the retention-policy and litigation-hold timing workflow described in `E002`, while retaining the category-impact and remediation-action style from `E001` and `E003`.

The task-builder ownership scope is `task_group/task_group_017/train_tasks/002/`. Solver-visible local materials are `input/prompt.txt`, `input/payloads/review_scope.json`, and `input/payloads/answer_template.json`. The actual evidence is designed to live in the shared Investigation Review Hub at `<TASK_ENV_BASE_URL>`, especially the matter, subpoena-category, retention-event, custodian-source, remediation-action, and optional read-only query endpoints. The prompt explicitly instructs solvers not to inspect env files, generated manifests, database files, or setup scripts.

The stable matter is `MTR-HARBORSTONE-GJ`. The key generated environment records used by this task are `RET-HARB-LAB-2019`, `RET-HARB-EHS-POST`, `RET-HARB-VOICE`, `RET-HARB-TEAMS`, `RET-HARB-AUDIT`, and `SRC-HARB-IRONVAULT`.

### Task Definition and Scenario Fit

The business request is a realistic legal-operations review for HarborStone Chemicals in an environmental grand jury matter. The solver must identify retention and preservation gaps, distinguish pre-hold policy destruction from post-hold preservation loss, separate communications-platform gaps from physical-record loss, recognize a missing audit report that should still exist, and account for an available archive exception.

This fits the task group because it requires cross-system reconstruction of investigation response facts: category codes from the subpoena scope, retention event IDs, hold dates, record volumes, communication-source status, archive availability, and action ownership. It is a formal train task, not a tutorial. Fewshot skill generators can infer conventions from the solved answer, but the prompt does not expose the SOP or scoring logic.

### Material Map

`input/prompt.txt` gives the user-facing request and required use of `<TASK_ENV_BASE_URL>`. It avoids step lists, scoring weights, and answer facts.

`input/payloads/review_scope.json` gives only matter context and category labels. It does not state which categories are affected by any loss.

`input/payloads/answer_template.json` defines the expected normalized JSON shape, list ordering, numeric precision, and enum choices for `status`, `risk_level`, `action_type`, and `owner`.

The environment retention events supply the decisive business facts:

- `RET-HARB-LAB-2019`: 4 boxes of 2019 lab test data destroyed on 2023-01-18, before the 2024-11-14 hold, under policy section 3.1, affecting category `B`.
- `RET-HARB-EHS-POST`: 2 boxes of EHS correspondence destroyed on 2025-01-06, after the 2024-11-14 hold, affecting `C`, `D`, and `H`.
- `RET-HARB-VOICE`: voicemail auto-delete after 90 days, affecting `D`.
- `RET-HARB-TEAMS`: Teams messages before 2022-02-01 lost from the active system, affecting `D` and `E`.
- `RET-HARB-AUDIT`: October 2023 Calverley audit missing even though retention requires 60 months, affecting `E`, `F`, and `I`.
- `SRC-HARB-IRONVAULT`: email archive retains 7 years and is available, affecting `D` and `E`.

### Solution and Evaluation Basis

The standard answer places all five retention events in `retention_events`, the voicemail and Teams events in `communication_gaps`, IronVault in `available_archives`, and six prioritized remediation rows in `recommended_actions`.

The key legal distinction is timing. `RET-HARB-LAB-2019` is not a post-hold preservation failure because the destruction date predates the hold and the event is classified as `policy_destroyed_pre_hold`. `RET-HARB-EHS-POST` is a post-hold loss because it occurred on 2025-01-06 after the 2024-11-14 hold. `RET-HARB-AUDIT` should exist because the October 2023 audit falls within a 60-month retention requirement. IronVault is an available archive exception that prevents categories `D` and `E` from being treated as fully irretrievable for email archive content.

The evaluator has eight whole-point scoring goals with raw weights:

1. `P01_matter_and_event_coverage`, weight 1: matter id and complete five-event retention set.
2. `P02_pre_hold_policy_destruction`, weight 2: lab data status, low risk, category `B`, 4 boxes, 2023-01-18, hold date, and policy section 3.1.
3. `P03_post_hold_loss`, weight 3: EHS correspondence status, high risk, categories `C`, `D`, `H`, 2 boxes, destruction date, and hold date.
4. `P04_communication_gaps`, weight 2: separate voicemail auto-purge and Teams active-system loss with correct category sets and timing fields.
5. `P05_missing_audit_retention`, weight 3: Calverley audit should-exist-missing status, high risk, 60-month retention, categories `E`, `F`, `I`, and locate-missing-record action owned by compliance audit.
6. `P06_archive_exception`, weight 2: IronVault availability, 7-year retention, categories `D`, `E`, archive-limitation fields, and archive collection owner.
7. `P07_metrics`, weight 2: event counts, box counts, archive count, communication-gap count, and affected category set.
8. `P08_recommended_actions`, weight 2: target-specific action and owner set for the post-hold loss, missing audit, archive, Teams, voicemail, and pre-hold policy destruction.

The scoring points cover at least four distinct outcomes: retention timing classification, preservation-loss risk, communication-system gaps, missing-required-record analysis, archive exception implications, numeric aggregation, and remediation planning. Each point is all-or-nothing and deterministic. The evaluator normalizes IDs, enum casing, integer-like values, and category sets; it does not score prose quality.

Likely model pitfalls include treating all destroyed records as spoliation, missing the pre-hold distinction for the 2019 lab boxes, omitting category `H` from the post-hold EHS loss, treating the IronVault archive as another loss rather than an available source, merging voicemail and Teams into one generic communications issue, and forgetting that the Calverley audit should exist under the 60-month rule.

### Transfer Design

As a train task, this example is meant to teach transferable legal-operations habits through the solved answer rather than through solver-visible instructions. A fewshot skill can infer that retention records must be classified by comparing destruction dates to the legal hold date, that pre-hold policy destruction receives different treatment from post-hold loss, that active-system purge does not always equal total unavailability when an archive exists, and that category-impact arrays must be carried through to metrics and recommended actions.

This task also transfers output conventions. It shows that stable environment IDs should be preserved, affected categories should be sorted uppercase sets, communication gaps can be represented separately from physical-record events, available archives should be isolated in `available_archives`, and remediation actions should use controlled action and owner enums. These conventions anchor later test tasks such as Portola Energy and Vireo Labs without making those tasks copies of HarborStone.

### Construction Record

Author: Task-builder 02. Created: 2026-07-18. Updated: 2026-07-18. Major changes: created the complete formal task folder, solver-visible prompt and payloads, standard answer, deterministic evaluator, and bilingual notes for `train_002`.

## 中文

### 数据和来源

本任务属于 `SCN_017_white_collar_investigation_production_review`，来源示例族为 `E001`、`E002` 和 `E003`。任务主要承接 `E002` 中的保存政策和 litigation hold 时间判断，同时沿用 `E001`、`E003` 中按请求类别、证据来源和补救动作输出结构化结论的风格。

本任务构建者只负责 `task_group/task_group_017/train_tasks/002/`。求解者可见的本地材料是 `input/prompt.txt`、`input/payloads/review_scope.json` 和 `input/payloads/answer_template.json`。关键证据应来自共享 Investigation Review Hub，即 `<TASK_ENV_BASE_URL>`，尤其是 matter、subpoena category、retention event、custodian source、remediation action 以及可选只读 SQL 查询端点。提示中明确要求求解者不得查看 env 文件、生成清单、数据库文件或启动脚本。

稳定 matter id 是 `MTR-HARBORSTONE-GJ`。本任务使用的关键环境记录包括 `RET-HARB-LAB-2019`、`RET-HARB-EHS-POST`、`RET-HARB-VOICE`、`RET-HARB-TEAMS`、`RET-HARB-AUDIT` 和 `SRC-HARB-IRONVAULT`。

### 任务定义和场景适配

业务请求是 HarborStone Chemicals 环境类大陪审团传票事项中的保存和保全缺口审查。求解者需要识别保存和保全缺口，区分 hold 前按政策销毁和 hold 后保存失败，把通信平台缺口与纸质或实物记录损失分开，识别本应仍然存在的审计报告，并考虑可用归档源对缺口结论的影响。

该任务适合本任务组，因为它要求跨系统重建调查响应事实：传票类别代码、retention event id、hold 日期、记录数量、通信来源状态、归档可用性和补救责任人。它是正式训练任务，不是教程。fewshot skill 生成器可以从标准答案中推断工作惯例，但求解者可见提示不会泄露 SOP 或评分逻辑。

### 材料映射

`input/prompt.txt` 提供客户请求和必须使用 `<TASK_ENV_BASE_URL>` 的限制，不包含步骤清单、评分权重或答案事实。

`input/payloads/review_scope.json` 只提供 matter 背景和类别标签，不说明哪些类别受到具体损失影响。

`input/payloads/answer_template.json` 定义规范化 JSON 结构、列表排序、数值精度以及 `status`、`risk_level`、`action_type`、`owner` 等枚举。

环境中的关键 retention 事实如下：

- `RET-HARB-LAB-2019`：4 箱 2019 年实验室测试数据于 2023-01-18 销毁，早于 2024-11-14 hold，依据政策 3.1，影响类别 `B`。
- `RET-HARB-EHS-POST`：2 箱 EHS correspondence 于 2025-01-06 销毁，晚于 2024-11-14 hold，影响 `C`、`D`、`H`。
- `RET-HARB-VOICE`：voicemail 90 天自动删除，影响 `D`。
- `RET-HARB-TEAMS`：2022-02-01 以前的 Teams messages 在 active system 中丢失，影响 `D`、`E`。
- `RET-HARB-AUDIT`：2023 年 10 月 Calverley audit 缺失，但保存要求为 60 个月，影响 `E`、`F`、`I`。
- `SRC-HARB-IRONVAULT`：email archive 可用，保存 7 年，影响 `D`、`E`。

### 解答和评估依据

标准答案把五个 retention events 放入 `retention_events`，把 voicemail 和 Teams 放入 `communication_gaps`，把 IronVault 放入 `available_archives`，并在 `recommended_actions` 中给出六个排序后的补救动作。

核心法律判断是时间点。`RET-HARB-LAB-2019` 的销毁日期早于 hold，因此不是 hold 后保全失败，而是 `policy_destroyed_pre_hold`。`RET-HARB-EHS-POST` 发生在 2025-01-06，晚于 2024-11-14 hold，因此是 hold 后损失。`RET-HARB-AUDIT` 属于 2023 年 10 月记录，落入 60 个月保存期内，因此应当仍然存在。IronVault 是可用归档例外，意味着类别 `D`、`E` 中的邮件归档内容不能直接视为完全不可恢复。

评估器包含八个整点评分目标，原始权重如下：

1. `P01_matter_and_event_coverage`，权重 1：matter id 和完整五个 retention event 集合。
2. `P02_pre_hold_policy_destruction`，权重 2：实验室数据状态、低风险、类别 `B`、4 箱、2023-01-18、hold 日期和政策 3.1。
3. `P03_post_hold_loss`，权重 3：EHS correspondence 状态、高风险、类别 `C`、`D`、`H`、2 箱、销毁日期和 hold 日期。
4. `P04_communication_gaps`，权重 2：分别识别 voicemail auto-purge 和 Teams active-system loss，并给出正确类别和时间字段。
5. `P05_missing_audit_retention`，权重 3：Calverley audit 为 should-exist-missing、高风险、60 个月保存期、类别 `E`、`F`、`I`，以及由 compliance audit 负责的 locate-missing-record 动作。
6. `P06_archive_exception`，权重 2：IronVault 可用、7 年保存、类别 `D`、`E`、归档限制字段和归档收集责任人。
7. `P07_metrics`，权重 2：事件计数、箱数、归档数量、通信缺口数量和受影响类别集合。
8. `P08_recommended_actions`，权重 2：针对 hold 后损失、缺失审计、归档、Teams、voicemail 和 hold 前政策销毁的动作与责任人。

这些评分点覆盖至少四类不同业务结果：保存时间分类、保全风险、通信系统缺口、应存在记录缺失、归档例外影响、数值汇总和补救计划。每个评分点都是全得或零分，评估器只做确定性检查。它会规范化 ID、枚举大小写、整数值和类别集合，不评价自由文本质量。

常见错误包括把所有销毁记录都当成 spoliation、遗漏 2019 年实验室箱子的 hold 前政策销毁性质、漏掉 EHS 损失中的类别 `H`、把 IronVault 当作损失而不是可用来源、把 voicemail 和 Teams 合并成一个泛泛通信问题，以及忘记 Calverley audit 在 60 个月规则下应当存在。

### 迁移设计

作为训练任务，本任务通过标准答案而不是求解者可见提示来传递可迁移经验。fewshot skill 可以推断：retention 记录必须通过销毁日期和 legal hold 日期比较来分类；hold 前按政策销毁和 hold 后损失需要不同法律处理；active-system purge 不一定等同于完全不可用，因为可能存在归档；类别影响数组必须同步反映到 metrics 和 recommended actions。

本任务也传递输出约定：保留环境中的稳定 ID，受影响类别使用排序后的大写集合，通信缺口可与实物记录事件分开呈现，可用归档应放在 `available_archives` 中，补救动作应使用受控 action 和 owner 枚举。这些约定可以锚定后续 Portola Energy 和 Vireo Labs 等测试任务，但不会把那些测试任务变成 HarborStone 的简单复制。

### 构建记录

作者：Task-builder 02。创建日期：2026-07-18。更新日期：2026-07-18。主要变更：为 `train_002` 创建完整正式任务文件夹、求解者可见提示和 payload、标准答案、确定性评估器以及双语 notes。
