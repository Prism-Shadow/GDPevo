# Task Notes / 任务说明

## English

Task definition and business objective: This train task validates leave source precedence for EMP-118, Nadia Brooks. The objective is to decide which leave policy and balance are authoritative when an employee profile summary conflicts with approved assignment and audit evidence.

Visible inputs and Web evidence: The solver-visible prompt provides the local PeopleOps Console URL, login, employee ID, and answer template. Evidence should be gathered from employee profile summary, leave ledger/assignment history, policy document viewer, message or correction context, and audit event detail.

Expected reasoning and answer basis:
- Identify `EMP-118` as Nadia Brooks.
- Compare profile summary against approved leave assignment evidence.
- Use approved assignment `LA-118-APP-02` and policy `Customer Success Standard 2026` with `16` balance days.
- Use `approved_assignment_over_profile` and `approved_assignment_current_period` to record source precedence.
- Mark `profile_policy_ignored` as `true` because audit detail says the profile summary is stale.
- Cite audit event `AUD-EMP118-LEAVE-04` with result `profile_summary_stale`.
- Use `supporting_audit_event_ids` as `["AUD-EMP118-LEAVE-04"]`.
- Exclude adjacent document audit event `AUD-DOC118-06` because this task scope is leave precedence, not document/notice readiness.
- Set `audit_scope` to `leave_source_precedence_only` and next action to `update_employee_summary`.

Transferable SOP and field conventions: This train task teaches that an approved current-period assignment can override a stale employee profile. It also teaches audit scoping: include audit events that support the requested control and exclude adjacent events that belong to another workflow. The labels `approved_assignment_current_period` and `leave_source_precedence_only` transfer to larger lifecycle tests.

Likely pitfalls: Trusting the profile summary because it is easy to find; omitting the audit result; failing to exclude `AUD-DOC118-06`; using a document/notice audit scope; or choosing a generic review action instead of `update_employee_summary`.

Evaluator/scoring basis: `eval/rubric.json` has eight exact-match scoring points covering identity, effective leave policy, approved assignment, balance, precedence source, stale-profile boolean, audit event/result/support/exclusion/scope, and next action.

Construction/rework note: This notes file was synchronized with the reworked answer and rubric, including `leave_precedence_source`, `supporting_audit_event_ids`, `excluded_audit_event_ids`, and `audit_scope`.

## 中文

任务定义和业务目标：本训练任务核验 EMP-118 Nadia Brooks 的休假来源优先级。目标是在员工 profile summary 与已批准 assignment 和审计证据冲突时，判断哪个休假政策和余额才是权威来源。

可见输入和网页证据：求解者可见 prompt 提供本地 PeopleOps Console URL、登录信息、员工 ID 和 answer template。证据应从员工 profile summary、leave ledger/assignment history、policy document viewer、消息或更正上下文，以及 audit event detail 中获取。

预期推理和答案依据：
- 确认 `EMP-118` 对应 Nadia Brooks。
- 将 profile summary 与已批准休假分配证据对比。
- 使用已批准分配 `LA-118-APP-02`，政策为 `Customer Success Standard 2026`，余额为 `16` 天。
- 使用 `approved_assignment_over_profile` 和 `approved_assignment_current_period` 记录来源优先级。
- 因审计详情说明 profile summary 已过期，将 `profile_policy_ignored` 标记为 `true`。
- 引用审计事件 `AUD-EMP118-LEAVE-04`，结果为 `profile_summary_stale`。
- `supporting_audit_event_ids` 为 `["AUD-EMP118-LEAVE-04"]`。
- 排除相邻文档审计事件 `AUD-DOC118-06`，因为本任务范围是休假来源优先级，不是文档/通知就绪度。
- 将 `audit_scope` 设为 `leave_source_precedence_only`，下一步动作为 `update_employee_summary`。

可迁移 SOP 和字段口径：本训练任务说明当前已批准 assignment 可以覆盖过期员工 profile。它也训练 audit scoping：只纳入支撑当前控制范围的审计事件，并排除属于其他流程的相邻事件。`approved_assignment_current_period` 和 `leave_source_precedence_only` 会迁移到更大的生命周期测试。

常见陷阱：因为 profile summary 易找就直接采用；遗漏 audit result；未排除 `AUD-DOC118-06`；使用 document/notice audit scope；或选择泛泛的 review action 而不是 `update_employee_summary`。

评测依据：`eval/rubric.json` 包含 8 个精确匹配评分点，覆盖身份、有效休假政策、已批准分配、余额、来源优先级、过期 profile 布尔值、审计事件/结果/支持/排除/范围，以及下一步动作。

构造/返工说明：本 notes 文件已与返工后的 answer 和 rubric 同步，包括 `leave_precedence_source`、`supporting_audit_event_ids`、`excluded_audit_event_ids` 和 `audit_scope`。
