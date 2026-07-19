# Cobalt Ridge Production Readiness Review Notes

## English

Data/source lineage: this task is `test_004` in `task_group_017`, scenario `SCN_017_white_collar_investigation_production_review`, based on source examples `E001`, `E002`, and `E003`. The task uses the shared Investigation Review Hub records for matter `MTR-COBALTRIDGE-GJ` and the task-local payloads `input/payloads/review_scope.json` and `input/payloads/answer_template.json`. No task-local payload contains answer facts.

Task definition: counsel needs a production-readiness JSON package for Cobalt Ridge acquisition communications. Solver-visible materials ask the solver to use only `<TASK_ENV_BASE_URL>` and shared environment endpoints, with the read-only query key if needed. The expected answer has `matter_id`, `readiness_statuses`, `issue_ledger`, `privilege_corrections`, `metrics`, and `priority_actions`.

Scenario fit: this is a white-collar production review task with the same workflow family as the train tasks. The solver must reconcile production statistics, document coding, QC findings, custodian-source collection status, privilege-log rows, and remediation actions to decide whether a production is ready. The difficulty comes from cross-record reconciliation and transfer of investigation review conventions, not from local file lookup.

Material map: `review_scope.json` supplies the matter ID, environment base URL placeholder, query header, endpoint inventory, and output contract. `answer_template.json` defines controlled enums, required keys, list ordering, and numeric precision. The relevant environment records include `DOC-COBALT-BANKER-SIDE`, `QC-COBALT-ZERO-CR06`, `SRC-COBALT-PARK-GMAIL`, `SRC-COBALT-PARK-PHONE`, `PRIV-COBALT-LOG-GAP`, and `PRIV-COBALT-SELLER-WAIVER`.

Solution and evaluation basis: the standard answer treats `CR-06`, `CR-11`, and `CR-15` as not ready. `DOC-COBALT-BANKER-SIDE` is responsive to `CR-06` but coded nonresponsive, and it contradicts `QC-COBALT-ZERO-CR06`. `SRC-COBALT-PARK-GMAIL` is not collected and affects `CR-06` and `CR-15`. `SRC-COBALT-PARK-PHONE` is only partially collected because Signal messages are missing and affects `CR-15`. `PRIV-COBALT-LOG-GAP` has 1290 withheld documents and 480 logged documents, so 810 documents are unlogged. `PRIV-COBALT-SELLER-WAIVER` identifies six attorney-client emails forwarded to a seller-side banker, creating a third-party waiver issue. The priority actions are recode and produce, collect personal email, collect Signal messages, supplement the privilege log, and perform waiver assessment and disclosure.

Evaluation uses eight deterministic whole-point checks with raw weights 2, 3, 2, 2, 3, 2, 1, and 3. The scored outcomes cover category readiness, CR-06 zero-claim contradiction, Gmail source gap, phone Signal gap, privilege-log arithmetic, seller-banker waiver, rollup metrics, and priority action ordering. Each point earns all assigned score or zero; there is no fractional credit inside a point.

Transfer design: the task is anchored to `train_001`, `train_004`, and `train_005`. From `train_001` and `train_004`, a solver can infer that a zero-production or zero-claim category must still be challenged when a responsive document is coded nonresponsive, and that the action is recoding and production rather than accepting the tracker. From `train_001` and `train_005`, the solver can infer that personal email and phone gaps must be tied to affected request categories, not reported as generic source notes. From `train_004`, the solver can infer privilege-log incompleteness arithmetic and third-party waiver treatment. From `train_005`, the solver can infer that source collection and recoding actions should be translated into a priority remediation package. Task-specific difficulty remains in finding the Cobalt Ridge IDs, resolving Cobalt category codes, and separating real injected records from noisy similar records.

Likely model pitfalls: accepting the CR-06 zero claim without checking QC and document records; reporting the Gmail and phone gaps without category impacts; treating the partial phone collection as collected; calculating 1290 minus 480 incorrectly; missing that the seller-side banker is a third party; using environment source files instead of the shared endpoints; and producing prose instead of the required controlled JSON.

Construction record: authored by Task-builder 09 on 2026-07-18. Files created for `task_group/task_group_017/test_tasks/004/`: prompt, review scope payload, answer template, standard answer, evaluator, rubric, eval entry point, and notes.

## 中文

数据和来源谱系：本任务是 `task_group_017` 中的 `test_004`，场景为 `SCN_017_white_collar_investigation_production_review`，依据来源示例 `E001`、`E002` 和 `E003` 设计。任务使用共享 Investigation Review Hub 中 `MTR-COBALTRIDGE-GJ` 的记录，以及本任务本地的 `input/payloads/review_scope.json` 和 `input/payloads/answer_template.json`。本地可见材料不包含答案事实。

任务定义：律师团队需要一份 Cobalt Ridge 收购沟通事项的生产准备度 JSON 包。对求解器可见的材料要求只使用 `<TASK_ENV_BASE_URL>` 和共享环境端点，如使用只读查询端点则带上查询密钥。标准输出包含 `matter_id`、`readiness_statuses`、`issue_ledger`、`privilege_corrections`、`metrics` 和 `priority_actions`。

场景匹配：这是白领调查中的文件生产审查任务，和训练任务属于同一业务流程族。求解器需要核对生产统计、文件编码、QC 发现、保管人来源采集状态、特权日志和补救行动，判断生产是否准备就绪。难度来自跨记录核对和调查审查惯例的迁移，而不是本地文件查找。

材料地图：`review_scope.json` 提供事项编号、环境基础 URL 占位符、查询头、端点清单和输出契约。`answer_template.json` 定义受控枚举、必填字段、列表排序和数值精度。相关环境记录包括 `DOC-COBALT-BANKER-SIDE`、`QC-COBALT-ZERO-CR06`、`SRC-COBALT-PARK-GMAIL`、`SRC-COBALT-PARK-PHONE`、`PRIV-COBALT-LOG-GAP` 和 `PRIV-COBALT-SELLER-WAIVER`。

解答和评估依据：标准答案将 `CR-06`、`CR-11` 和 `CR-15` 判定为未准备就绪。`DOC-COBALT-BANKER-SIDE` 对 `CR-06` 有响应性但被编码为非响应性，并且推翻了 `QC-COBALT-ZERO-CR06` 的零申明。`SRC-COBALT-PARK-GMAIL` 未采集，影响 `CR-06` 和 `CR-15`。`SRC-COBALT-PARK-PHONE` 只是部分采集，因为缺少 Signal 消息，影响 `CR-15`。`PRIV-COBALT-LOG-GAP` 有 1290 份扣留文件和 480 份已登录文件，所以未登录文件为 810 份。`PRIV-COBALT-SELLER-WAIVER` 涉及六封律师客户邮件转发给卖方投行人员，构成第三方放弃特权问题。优先行动为重新编码并生产、采集个人邮箱、采集 Signal 消息、补充特权日志，以及进行放弃特权评估和披露。

评估采用八个确定性的整体得分点，原始权重为 2、3、2、2、3、2、1 和 3。评分结果覆盖类别准备度、`CR-06` 零申明矛盾、Gmail 来源缺口、手机 Signal 缺口、特权日志算术、卖方投行人员放弃特权、汇总指标和优先行动顺序。每个得分点只有全得或不得，不在单点内部给部分分。

迁移设计：本任务锚定 `train_001`、`train_004` 和 `train_005`。从 `train_001` 和 `train_004`，求解器可以迁移出一条规则：即使生产跟踪器声称某类别为零生产，只要存在被误编码为非响应性的响应文件，也必须质疑该零申明，并采取重新编码和生产行动。从 `train_001` 和 `train_005`，求解器可以迁移出个人邮箱和手机缺口必须映射到受影响请求类别，而不是只作为一般来源备注。从 `train_004`，求解器可以迁移特权日志不完整的算术计算和第三方放弃特权处理。从 `train_005`，求解器可以迁移将来源采集和重新编码问题转化为优先补救行动包的方法。任务特有难度在于找到 Cobalt Ridge 的稳定编号、解析 Cobalt 类别代码，并从相似噪声记录中区分真正注入的关键记录。

常见模型陷阱：直接接受 `CR-06` 的零申明而不检查 QC 和文件记录；报告 Gmail 和手机缺口但不写类别影响；把部分手机采集误判为已采集；错误计算 1290 减 480；漏掉卖方投行人员是第三方；使用环境源文件而不是共享端点；以及输出散文而不是受控 JSON。

构建记录：Task-builder 09 于 2026-07-18 创建。本次在 `task_group/task_group_017/test_tasks/004/` 下创建了提示、审查范围 payload、答案模板、标准答案、评估器、rubric、评估入口脚本和说明文件。
