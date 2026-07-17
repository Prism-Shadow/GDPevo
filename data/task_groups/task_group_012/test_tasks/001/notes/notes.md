# Notes

## English

Data/source lineage: This test task belongs to `SCN_012_erp_hr_employee_lifecycle`, using the ERP HR employee lifecycle scenario and transfer patterns from the local train tasks, especially the authoritative-record selection in `train_tasks/001` and lifecycle communication/compliance checks in the recruiting and policy tasks. The solver-visible materials are `input/prompt.txt` and `input/payloads/answer_template.json`; the business evidence is expected to be gathered from the PeopleOps Console at runtime.

Task definition: The solver must decide final lifecycle clearance for `EMP-255`, Erin Novak, by combining employee detail, leave, payroll, document folder status, messages, approval history, and audit log. The expected output is structured JSON with the final decision, leave policy and assignment, leave balance, payroll assignment and salary, missing folder files, notice defects, controlling audit event, and escalation owner.

Scenario fit and material map: The task exercises the same cross-system HR operations pattern as the source scenario: lifecycle decisions depend on HRMS records, payroll assignments, document controls, notification quality, approvals, and audit evidence. `answer_template.json` defines the output contract without revealing the result. `output/answer.json` records the gold answer. `eval/rubric.json` defines exact-match scoring, and `eval/eval.sh` calls `eval/evaluate.py`.

Solution and evaluation basis: The gold answer identifies `EMP-255`, sets `clearance_decision` to `hold`, selects `R&D Flex Leave 2026` through `LA-255-APP-03`, records `leave_balance_days` as `21`, selects submitted payroll assignment `PAY-255-SUB-02` with `base_salary` `142000`, excludes `PAY-255-DRAFT-03`, flags missing folder files `benefits-election.pdf` and `executive-exception-approval.pdf`, records that the required tag is not fully present, flags notice defects `missing_ack_deadline` and `missing_appeal_instructions`, and ties the hold to audit event `AUD-CASE445-03` with escalation owner `People Ops Compliance`. The evaluator uses source-precedence, control-result, folder, notice, audit, and escalation scoring points; list fields are normalized by the shared helper, so order is not material.

Transfer design: This is a test task. Transfer should come from train tasks that teach authoritative submitted/approved record selection, exclusion of draft or stale lifecycle data, and compliance hold decisions when required documents or notice controls are defective. High-value scoring depends on transferring that SOP to a larger evidence set rather than merely copying fields from one page.

Likely pitfalls: A model may approve the clearance because leave and payroll are valid, choose a draft payroll or obsolete leave record, ignore the missing folder file, treat the notice message as adequate despite no acknowledgement deadline, or cite a non-controlling audit event.

Construction record: Author: Codex task-builder. Created: 2026-06-05. Updated: 2026-06-05. Major changes: created the complete `test_tasks/001` prompt, schema, gold answer, bilingual notes, rubric, and evaluator.

## 中文

数据和来源：本测试任务属于 `SCN_012_erp_hr_employee_lifecycle`，基于 ERP 人力资源员工生命周期场景，并借鉴本地训练任务中的可迁移模式，尤其是 `train_tasks/001` 中对权威记录的选择，以及招聘、政策任务中的沟通和合规检查。求解者可见材料是 `input/prompt.txt` 和 `input/payloads/answer_template.json`；业务证据需要在运行时从 PeopleOps Console 中收集。

任务定义：求解者需要结合员工详情、休假、薪资、文件夹状态、消息、审批历史和审计日志，判断 `EMP-255` Erin Novak 的最终生命周期清算结果。预期输出为结构化 JSON，包括最终决定、休假政策和分配、休假余额、薪资分配和基本工资、缺失文件、通知缺陷、控制性审计事件和升级负责人。

场景适配和材料地图：该任务体现了源场景中的跨系统 HR 运营流程：生命周期决策依赖 HRMS 记录、薪资分配、文档管控、通知质量、审批和审计证据。`answer_template.json` 定义输出格式但不泄露答案；`output/answer.json` 保存标准答案；`eval/rubric.json` 定义精确匹配评分；`eval/eval.sh` 调用 `eval/evaluate.py`。

答案和评估依据：标准答案识别 `EMP-255`，将 `clearance_decision` 设为 `hold`，通过 `LA-255-APP-03` 选择 `R&D Flex Leave 2026`，休假余额为 `21` 天，选择已提交的薪资分配 `PAY-255-SUB-02` 且基本工资为 `142000`，排除 `PAY-255-DRAFT-03`，标记缺失文件 `benefits-election.pdf` 和 `executive-exception-approval.pdf`，记录必需标签并未全部存在，标记通知缺陷 `missing_ack_deadline` 和 `missing_appeal_instructions`，并将暂停决定关联到审计事件 `AUD-CASE445-03` 和升级负责人 `People Ops Compliance`。评估器使用来源优先级、控制结果、文件夹、通知、审计和升级评分点；列表字段由共享评分工具归一化，因此顺序不影响得分。

迁移设计：这是测试任务。迁移知识来自训练任务中的 SOP：选择已提交或已批准的权威记录，排除草稿或过期生命周期数据，并在必需文件或通知控制存在缺陷时作出合规暂停决定。高权重得分点依赖将这些规则迁移到更大的证据集合，而不是只从单个页面复制字段。

常见陷阱：模型可能因为休假和薪资本身有效就错误批准清算，选择草稿薪资或过期休假记录，忽略缺失文件，将缺少确认截止日期的通知误判为合格，或引用非控制性的审计事件。

构建记录：作者：Codex task-builder。创建日期：2026-06-05。更新日期：2026-06-05。主要变更：创建完整的 `test_tasks/001` 提示、输出 schema、标准答案、双语 notes、rubric 和评估脚本。
