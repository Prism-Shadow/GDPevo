# Task Notes / 任务说明

## English

Task definition and business objective: This train task asks the solver to verify whether EMP-104, Mira Chen, can be approved for onboarding closeout after checking leave setup and payroll setup. The business objective is not only to find a policy and salary, but to apply source precedence before closing the HR workflow.

Visible inputs and Web evidence: The solver-visible prompt provides the local PeopleOps Console URL, login, employee ID, and the JSON answer template. The public Web evidence should be gathered from employee detail, leave assignment history, payroll assignment records, approval/closeout context, and any supporting audit or policy detail exposed by the app. The prompt and template do not contain the answer facts.

Expected reasoning and answer basis:
- Identify `EMP-104` as Mira Chen.
- Use leave assignment history as the authoritative source and choose `LA-104-2026-B`.
- Exclude the older leave assignment `LA-104-2026-A` and draft leave record `LA-104-2026-DRAFT`.
- Report `Engineering Flex Leave 2026` and `18` annual days.
- Use submitted payroll assignment `PAY-104-2026-SUB`, salary `128000`, and status `submitted`.
- Exclude draft payroll record `PAY-104-2026-DRAFT`.
- Because both leave and payroll records are clean, set `closeout_action` to `approve_onboarding_close`, `approval_closeout_gate` to `approval_sufficient_when_records_clean`, and `final_control_result` to `approve_closeout`.

Transferable SOP and field conventions: This train task teaches that current approved/submitted records control over old or draft records. It establishes reusable labels used later by test tasks: `leave_assignment_history`, `approved_assignment_current_period`, `submitted`, `approval_sufficient_when_records_clean`, and `approve_closeout`. It also teaches that source/status fields should use normalized labels rather than prose.

Likely pitfalls: Using the draft leave or payroll record because it appears newer; omitting excluded IDs; returning a free-text closeout explanation instead of normalized labels; or approving closeout without verifying both leave and payroll sources.

Evaluator/scoring basis: `eval/rubric.json` has eight exact-match scoring points covering identity, leave policy, leave source and days, assignment ID, excluded leave records, submitted payroll assignment, payroll salary/status, excluded payroll record, closeout action, approval gate, and final control result. Lists are compared as normalized sets by the shared evaluator helper.

Construction/rework note: This notes file was synchronized after the transfer-matrix rework so it now covers all current `output/answer.json` and rubric fields, including `leave_precedence_source`, `payroll_source_status`, `approval_closeout_gate`, and `final_control_result`.

## 中文

任务定义和业务目标：本训练任务要求求解者核验 EMP-104 Mira Chen 是否可以在休假配置和薪资配置均确认后批准关闭入职流程。业务目标不只是找到政策和薪资，而是在关闭 HR 流程前正确应用来源优先级。

可见输入和网页证据：求解者可见 prompt 提供本地 PeopleOps Console URL、登录信息、员工 ID 和 JSON answer template。公开网页证据应从员工详情、休假分配历史、薪资分配记录、审批/关闭上下文，以及应用中公开的审计或政策详情中获取。prompt 和 template 不包含答案事实。

预期推理和答案依据：
- 确认 `EMP-104` 对应 Mira Chen。
- 使用休假分配历史作为权威来源，并选择 `LA-104-2026-B`。
- 排除旧休假分配 `LA-104-2026-A` 和草稿休假记录 `LA-104-2026-DRAFT`。
- 报告 `Engineering Flex Leave 2026` 和年度 `18` 天。
- 使用已提交薪资分配 `PAY-104-2026-SUB`，薪资 `128000`，状态 `submitted`。
- 排除草稿薪资记录 `PAY-104-2026-DRAFT`。
- 因休假和薪资记录均干净，`closeout_action` 应为 `approve_onboarding_close`，`approval_closeout_gate` 应为 `approval_sufficient_when_records_clean`，`final_control_result` 应为 `approve_closeout`。

可迁移 SOP 和字段口径：本训练任务说明当前已批准/已提交记录优先于旧记录或草稿记录。它建立后续测试会复用的标签：`leave_assignment_history`、`approved_assignment_current_period`、`submitted`、`approval_sufficient_when_records_clean` 和 `approve_closeout`。它也训练 source/status 字段应使用规范化标签，而不是自由文本。

常见陷阱：因为草稿记录看起来更新就采用草稿休假或薪资；遗漏被排除的 ID；用自由文本解释 closeout 而不是规范化标签；或在未同时核验休假和薪资来源前批准关闭。

评测依据：`eval/rubric.json` 包含 8 个精确匹配评分点，覆盖员工身份、休假政策、休假来源和天数、分配 ID、排除的休假记录、已提交薪资分配、薪资金额/状态、排除的薪资记录、关闭动作、审批门槛和最终控制结果。列表由共享 evaluator helper 归一化为集合比较。

构造/返工说明：本 notes 文件已在 transfer-matrix rework 后同步，现已覆盖当前 `output/answer.json` 和 rubric 中的所有字段，包括 `leave_precedence_source`、`payroll_source_status`、`approval_closeout_gate` 和 `final_control_result`。
