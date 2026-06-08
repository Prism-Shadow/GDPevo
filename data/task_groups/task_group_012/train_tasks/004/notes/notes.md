# Task Notes
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

