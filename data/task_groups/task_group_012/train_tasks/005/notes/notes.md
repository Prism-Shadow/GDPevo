# Task Notes / 任务说明

## English

Task definition and business objective: This train task inspects payroll assignment and accrual readiness for EMP-122, Omar Patel. The objective is to select the controlling submitted payroll assignment, exclude draft data, and determine whether the April 2026 accrual batch can proceed.

Visible inputs and Web evidence: The solver-visible prompt gives the local PeopleOps Console URL, login, employee ID, and answer template. Evidence should be gathered from payroll assignment records, accrual readiness/batch detail, employee context, and audit log detail.

Expected reasoning and answer basis:
- Identify `EMP-122` as Omar Patel.
- Select submitted salary assignment `PAY-122-SUB-03`.
- Report base salary `98000` and effective date `2026-04-01`.
- Exclude draft assignment `PAY-122-DRAFT-04`.
- Set `payroll_source_status` to `submitted` and `draft_exclusion_rule` to `exclude_draft_assignment`.
- Confirm `accrual_ready` is `true` for batch `ACCR-2026-04-B`.
- Cite audit event `AUD-PAY122-07`.
- Set `audit_scope` to `payroll_assignment_readiness`.
- Return final payroll control result `ready_with_monitoring`.

Transferable SOP and field conventions: This train task anchors submitted-versus-draft payroll precedence. It transfers the rule that current payroll and accrual readiness must use a submitted assignment, not a draft, and that audit scope should match payroll assignment readiness. These conventions support later lifecycle and cross-module test tasks.

Likely pitfalls: Choosing the draft assignment because it is visible; returning payroll status with UI capitalization instead of normalized `submitted`; omitting `draft_exclusion_rule`; treating accrual readiness as unknown despite audit support; or using a broad audit scope.

Evaluator/scoring basis: `eval/rubric.json` has eight exact-match scoring points: identity, submitted salary assignment/source status, salary/effective date, excluded draft assignment/draft rule, accrual readiness, accrual batch, audit event/scope, and control result.

Construction/rework note: This notes file was synchronized after rework so it now covers `payroll_source_status`, `draft_exclusion_rule`, and `audit_scope`, not just the original salary and batch fields.

## 中文

任务定义和业务目标：本训练任务检查 EMP-122 Omar Patel 的薪资分配和应计准备状态。目标是选择控制性的已提交薪资分配，排除草稿数据，并判断 2026 年 4 月应计批次是否可以继续。

可见输入和网页证据：求解者可见 prompt 提供本地 PeopleOps Console URL、登录信息、员工 ID 和 answer template。证据应从薪资分配记录、应计准备/批次详情、员工上下文和 audit log detail 中获取。

预期推理和答案依据：
- 确认 `EMP-122` 对应 Omar Patel。
- 选择已提交薪资分配 `PAY-122-SUB-03`。
- 报告基本工资 `98000` 和生效日期 `2026-04-01`。
- 排除草稿分配 `PAY-122-DRAFT-04`。
- 将 `payroll_source_status` 设为 `submitted`，将 `draft_exclusion_rule` 设为 `exclude_draft_assignment`。
- 确认批次 `ACCR-2026-04-B` 的 `accrual_ready` 为 `true`。
- 引用审计事件 `AUD-PAY122-07`。
- 将 `audit_scope` 设为 `payroll_assignment_readiness`。
- 返回最终薪资控制结果 `ready_with_monitoring`。

可迁移 SOP 和字段口径：本训练任务锚定 submitted 与 draft 薪资优先级。它迁移的规则是：当前薪资和应计准备必须使用已提交分配，而不是草稿；审计范围应匹配 payroll assignment readiness。这些约定支持后续生命周期和跨模块测试。

常见陷阱：因为草稿分配可见就选择草稿；用 UI 大写状态而不是规范化 `submitted`；遗漏 `draft_exclusion_rule`；尽管有审计支持仍把 accrual readiness 视为未知；或使用过宽的 audit scope。

评测依据：`eval/rubric.json` 包含 8 个精确匹配评分点：身份、已提交薪资分配/source status、薪资/生效日期、排除草稿分配/draft rule、应计准备、应计批次、审计事件/scope 和控制结果。

构造/返工说明：本 notes 文件已在 rework 后同步，现已覆盖 `payroll_source_status`、`draft_exclusion_rule` 和 `audit_scope`，而不只是原始薪资和批次字段。
