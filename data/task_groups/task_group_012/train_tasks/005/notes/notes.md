# Task Notes
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

