# Task Notes / 任务说明

## English

Task definition and business objective: This test task asks the solver to produce an audit-led escalation decision for cross-module package `AUD-XMODULE-77`. The objective is to map linked payroll, leave, policy closeout, and recruitment anomalies to the correct affected entities, supporting events, owner, and SLA.

Visible inputs and Web evidence: The solver-visible prompt gives the local PeopleOps Console entry point and the audit package ID. Public evidence should be gathered from Audit Log package detail, linked audit event detail, employee detail, policy case detail, payroll/leave records, recruitment records, documents/messages as needed, and policy viewer content for control interpretation.

Expected reasoning and answer basis:
- Identify audit package `AUD-XMODULE-77`.
- Determine `escalation_required` is `true` because the package links multiple lifecycle control failures.
- Report affected entities `EMP-255`, `CASE-445`, and `REQ-OPS-19`.
- Classify `primary_risk` as `payroll_and_policy_closeout_control`.
- Map leave and payroll issues to `EMP-255`.
- Map policy closeout issue to `CASE-445`.
- Map recruitment issue to `REQ-OPS-19`.
- Include audit events `AUD-CASE445-03`, `AUD-PAY255-02`, and `AUD-REQOPS-11`.
- Assign `People Ops Compliance` as escalation owner and set `remediation_sla_days` to `5`.

Train anchors and transferred knowledge: This test combines several train anchors. `train_001` and `train_004` transfer leave source precedence and employee-level issue mapping. `train_005` transfers submitted payroll readiness and draft exclusion as payroll-control concepts. `train_002` transfers policy closeout blocking, document/notice defects, and compliance remediation. `train_003` transfers recruitment outcome/notice/payroll handoff reasoning. The test-specific work is following an audit package across modules and assigning each linked anomaly to its controlling entity.

Likely pitfalls: Reporting only the audit package without linked event details; omitting one affected entity; assigning the policy issue to the employee instead of `CASE-445`; assigning the recruitment issue to a candidate instead of `REQ-OPS-19`; missing `AUD-PAY255-02`; or using a vague primary risk label rather than `payroll_and_policy_closeout_control`.

Evaluator/scoring basis: `eval/rubric.json` has nine equal-weight exact-match points: package/escalation, affected entities, primary risk, employee leave/payroll entities, policy issue entity, recruitment issue entity, audit events, escalation owner, and remediation SLA. Lists are normalized by the shared evaluator helper.

Construction/rework note: This notes file was expanded after reviewer feedback to document the cross-train transfer matrix and to synchronize with current answer/rubric fields. No task behavior, answer, evaluator, or calibration artifact was changed.

## 中文

任务定义和业务目标：本测试任务要求求解者为跨模块审计包 `AUD-XMODULE-77` 生成由审计证据驱动的升级决定。目标是把关联的薪资、休假、政策关闭和招聘异常映射到正确受影响实体、支撑事件、负责人和 SLA。

可见输入和网页证据：求解者可见 prompt 提供本地 PeopleOps Console 入口和审计包 ID。公开证据应从 Audit Log package detail、关联 audit event detail、employee detail、policy case detail、payroll/leave records、recruitment records、必要的 documents/messages，以及解释控制含义的 policy viewer 中获取。

预期推理和答案依据：
- 确认审计包 `AUD-XMODULE-77`。
- 因该包关联多个生命周期控制失败，判断 `escalation_required` 为 `true`。
- 报告受影响实体 `EMP-255`、`CASE-445` 和 `REQ-OPS-19`。
- 将 `primary_risk` 分类为 `payroll_and_policy_closeout_control`。
- 将休假和薪资问题映射到 `EMP-255`。
- 将政策关闭问题映射到 `CASE-445`。
- 将招聘问题映射到 `REQ-OPS-19`。
- 包含审计事件 `AUD-CASE445-03`、`AUD-PAY255-02` 和 `AUD-REQOPS-11`。
- 将升级负责人设为 `People Ops Compliance`，将 `remediation_sla_days` 设为 `5`。

训练锚点和迁移知识：该测试组合多个训练锚点。`train_001` 和 `train_004` 迁移休假来源优先级和员工级问题映射。`train_005` 迁移 submitted payroll readiness 和 draft exclusion 作为薪资控制概念。`train_002` 迁移 policy closeout blocking、文档/通知缺陷和合规整改。`train_003` 迁移招聘结果、通知和 payroll handoff 推理。测试特有工作是沿着审计包跨模块追踪，并把每个关联异常分配到控制性实体。

常见陷阱：只报告审计包而不查看 linked event detail；漏掉一个受影响实体；把 policy issue 分配给员工而不是 `CASE-445`；把 recruitment issue 分配给候选人而不是 `REQ-OPS-19`；遗漏 `AUD-PAY255-02`；或使用模糊 primary risk 标签而不是 `payroll_and_policy_closeout_control`。

评测依据：`eval/rubric.json` 包含 9 个等权精确匹配点：package/escalation、affected entities、primary risk、employee leave/payroll entities、policy issue entity、recruitment issue entity、audit events、escalation owner 和 remediation SLA。列表由共享 evaluator helper 归一化。

构造/返工说明：本 notes 文件已根据 reviewer 反馈扩展，记录跨训练任务迁移矩阵，并与当前 answer/rubric 字段同步。本次未修改任何任务行为、答案、评测器或校准产物。
