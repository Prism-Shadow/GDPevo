# Task Notes
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

