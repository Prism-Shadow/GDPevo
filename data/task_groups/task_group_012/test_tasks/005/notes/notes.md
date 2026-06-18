# Task Notes
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
