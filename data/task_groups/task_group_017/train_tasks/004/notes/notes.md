# train_004 hidden notes

## English

Data/source lineage: this task belongs to `task_group_017`, scenario `SCN_017_white_collar_investigation_production_review`, derived from source examples `E001`, `E002`, and `E003`. The design brief assigns `train_004` to matter `M-RDL-304`, "Radialon Compliance Whistleblower Production." The task uses only the shared generated environment under `task_group/task_group_017/env/`, especially `matters.json`, `subpoena_categories.json`, `production_logs.json`, `privilege_logs.json`, `qc_events.json`, and `documents.json`. The only task-local solver-visible payload is `input/payloads/answer_template.json`.

Task definition: the solver must review the production tracker, privilege logs, QC events, subpoena categories, and document records for matter `M-RDL-304` and return a structured JSON production-readiness review. The visible prompt deliberately does not list the answer path or a checklist. It asks for affected subpoena categories, category-level status, privilege metrics, miscoding findings, and remediation actions. The answer schema uses controlled enums, sorted lists, integer counts, booleans, and stable IDs so the evaluator can avoid subjective memo grading.

Scenario fit: the task exercises a white-collar production review workflow where subpoena category scope, production tracker rows, privilege log completeness, QC findings, and document coding must be reconciled. It fits the group transfer band because later tasks reuse the same judgment patterns: broad subpoena categories override narrow review coding, privilege log counts must be reconciled against withholdings, all-withheld counsel categories need overdesignation review, and privileged material coded non-privileged creates clawback risk.

Material map: `/api/matters/M-RDL-304` gives the matter context, flags, and deadline. `/api/subpoena_categories?matter_id=M-RDL-304` identifies relevant categories: `R-01` for whistleblower complaints and compliance escalations, `R-10` for privilege review and coding quality, and `R-11` for counsel communications on compliance response. `/api/production_logs?matter_id=M-RDL-304` has current canonical rows: `R-01` with zero produced despite two complaint documents, `R-10` with 2,910 withheld privileged and 2,102 logged, and `R-11` with all 612 responsive records withheld. The same endpoint also contains noise rows from other batches that should not override the current rows. `/api/privilege_logs?matter_id=M-RDL-304` corroborates `R-10` as partially logged and `R-11` as not logged with overdesignation risk. `/api/qc_events?matter_id=M-RDL-304` provides `QC-0005` for two miscoded complaint documents and `QC-0006` for 31 privileged records coded non-privileged. `/api/documents?matter_id=M-RDL-304` provides marker documents `DOC-RDL-COMP-001`, `DOC-RDL-COMP-002`, `DOC-RDL-PRIV-001`, and `DOC-RDL-PRIV-031`.

Solution and evaluation basis: the standard answer has affected categories `["R-01", "R-10", "R-11"]`. `R-01` is `blocked_zero_production` because the production log shows `produced_count` 0 for the broad whistleblower/compliance category while QC and document records show two complaint documents, `DOC-RDL-COMP-001` and `DOC-RDL-COMP-002`, miscoded non-responsive and not produced. `R-10` is `privilege_log_incomplete`: 2,910 withheld privileged records minus 2,102 logged records leaves 808 unlogged privileged records. `R-11` is `overdesignation_review`: all 612 responsive counsel-category records are withheld, zero produced, and privilege log data flags overdesignation risk. QC also shows 31 privileged records coded non-privileged, represented by endpoint marker documents `DOC-RDL-PRIV-001` and `DOC-RDL-PRIV-031`, requiring clawback assessment. Required action records are supplemental production for `R-01`, privilege log supplement for `R-10`, clawback review for `R-10`, and privilege review for `R-10` plus `R-11`.

The evaluator has eight exact-match weighted points with raw weights `[2, 2, 3, 3, 3, 2, 2, 2]`: identity and affected categories; core category statuses; `R-01` zero-production and complaint miscoding; `R-10` unlogged privilege gap; `R-11` all-withheld overdesignation risk; 31 privileged-coded-nonprivileged clawback issue; category required action types; and action records. Lists are normalized as sets for checked fields, but each point is all-or-nothing. The standard answer self-checks to score 1.0.

Likely model pitfalls: solvers may use noisy production rows instead of current rows, omit `R-11` because it looks like privilege rather than production, calculate the 808 gap incorrectly, treat the two complaint documents as non-responsive because of their review coding, miss the endpoint-marker convention for the 31-document clawback set, or return a prose memo instead of structured JSON.

Transfer design: as a train task, this teaches the reusable production-review convention that current tracker rows must be reconciled with QC and document evidence, not read in isolation. It also teaches the field conventions used in this group: stable category IDs, integer count arithmetic, issue/action enums, sorted sets, marker-document IDs for counted batches, and separate handling of supplemental production, privilege-log supplementation, privilege review, and clawback review.

Construction record: authored by task-builder subagent for `task_group_017/train_004` on 2026-07-07. Initial version created `prompt.txt`, `answer_template.json`, `answer.json`, `eval.sh`, `eval.py`, and this bilingual notes file. No seed scenario, environment data, task group metadata, or other tasks were modified.

## 中文

数据与来源：本任务属于 `task_group_017`，场景为 `SCN_017_white_collar_investigation_production_review`，来源示例为 `E001`、`E002` 和 `E003`。设计简报指定 `train_004` 处理事项 `M-RDL-304`，即 Radialon 的合规举报生产审查。任务只使用 `task_group/task_group_017/env/` 下的共享生成数据，重点文件包括 `matters.json`、`subpoena_categories.json`、`production_logs.json`、`privilege_logs.json`、`qc_events.json` 和 `documents.json`。求解者可见的本地载荷只有 `input/payloads/answer_template.json`。

任务定义：求解者需要审查 `M-RDL-304` 的生产跟踪、特权日志、质控事件、传票类别和文档记录，并输出结构化 JSON。可见提示没有给出答案路径或操作清单，只要求识别受影响类别、类别状态、特权指标、错码发现和补救动作。答案模板使用枚举、排序列表、整数计数、布尔值和稳定 ID，以便评估器进行客观评分。

场景适配：本任务对应白领调查中的生产审查流程，需要把传票范围、生产记录、特权日志完整性、质控发现和文档编码综合起来判断。它与任务组的迁移目标一致：广义传票类别优先于狭窄审阅编码，特权扣留数要与日志数核对，全部扣留的律师沟通类别需要过度标记审查，特权材料被编码为非特权会产生 clawback 风险。

材料地图：`/api/matters/M-RDL-304` 提供事项背景、标志和期限。`/api/subpoena_categories?matter_id=M-RDL-304` 显示关键类别：`R-01` 是举报投诉和合规升级，`R-10` 是特权审查和编码质量，`R-11` 是合规回应相关的律师沟通。`/api/production_logs?matter_id=M-RDL-304` 中的当前标准行显示：`R-01` 生产数为 0 但存在两个投诉文档，`R-10` 有 2,910 条特权扣留且仅 2,102 条已记录，`R-11` 的 612 条响应记录全部扣留。该端点也包含其他批次噪声行，不能覆盖当前行。`/api/privilege_logs?matter_id=M-RDL-304` 佐证 `R-10` 只部分记录，`R-11` 未记录且存在过度标记风险。`/api/qc_events?matter_id=M-RDL-304` 给出 `QC-0005` 的两个投诉文档错码和 `QC-0006` 的 31 条特权记录被编码为非特权。`/api/documents?matter_id=M-RDL-304` 给出标记文档 `DOC-RDL-COMP-001`、`DOC-RDL-COMP-002`、`DOC-RDL-PRIV-001` 和 `DOC-RDL-PRIV-031`。

答案与评估依据：标准答案的受影响类别为 `["R-01", "R-10", "R-11"]`。`R-01` 是 `blocked_zero_production`，因为生产日志对广义举报/合规类别显示生产数为 0，而质控和文档记录显示两个投诉文档 `DOC-RDL-COMP-001` 与 `DOC-RDL-COMP-002` 被错标为 non-responsive 且未生产。`R-10` 是 `privilege_log_incomplete`：2,910 条特权扣留减去 2,102 条已记录，得到 808 条未记录特权记录。`R-11` 是 `overdesignation_review`：律师沟通类别 612 条响应记录全部扣留，生产数为 0，且特权日志数据提示过度标记风险。质控还显示 31 条特权记录被编码为非特权，用端点标记文档 `DOC-RDL-PRIV-001` 和 `DOC-RDL-PRIV-031` 表示，需要 clawback 评估。动作包括对 `R-01` 补充生产，对 `R-10` 补充特权日志，对 `R-10` 进行 clawback 审查，以及对 `R-10` 和 `R-11` 进行特权审查。

评估器包含 8 个精确匹配评分点，原始权重为 `[2, 2, 3, 3, 3, 2, 2, 2]`：身份和受影响类别；核心类别状态；`R-01` 零生产和投诉错码；`R-10` 未记录特权差额；`R-11` 全部扣留和过度标记风险；31 条特权记录编码为非特权及 clawback；类别所需动作类型；以及动作记录。被检查的列表按集合归一化，但每个评分点只有全对或全错。标准答案自检得分为 1.0。

常见陷阱：模型可能使用噪声生产行而不是当前行；因为 `R-11` 看起来是特权问题而漏掉它；把 808 的差额算错；因 review coding 为 non-responsive 而忽略两个投诉文档；不理解 31 条记录使用端点标记文档表示；或者输出普通备忘录而不是结构化 JSON。

迁移设计：作为训练任务，本任务让求解者学习生产审查中的可迁移规则：当前生产跟踪必须与质控和文档证据相互核对，不能孤立读取。它还展示了本任务组的字段约定：稳定类别 ID、整数计数计算、问题和动作枚举、排序集合、用标记文档代表批量记录，以及将补充生产、补充特权日志、特权审查和 clawback 审查分开处理。

构造记录：由 `task_group_017/train_004` 的 task-builder subagent 于 2026-07-07 创建。初版新增 `prompt.txt`、`answer_template.json`、`answer.json`、`eval.sh`、`eval.py` 和本双语 notes 文件。未修改 seed scenario、环境数据、任务组元数据或其他任务。
