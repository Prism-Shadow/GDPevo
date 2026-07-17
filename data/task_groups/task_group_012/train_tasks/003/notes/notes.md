# Task Notes / 任务说明

## English

Task definition and business objective: This train task reconciles recruitment opening `REQ-DA-77`. The solver must determine candidate outcomes, accepted offer details, recruitment cost total, notice follow-up obligations, and payroll handoff readiness. It is a formal PeopleOps reconciliation task, not a tutorial.

Visible inputs and Web evidence: The solver-visible prompt gives the local PeopleOps Console URL, login, opening ID, and answer template. Evidence should be collected from Recruitment candidate review, offer register, cost ledger, notice packets/messages, related case detail, policy viewer, payroll handoff or precheck evidence, and audit evidence available through the app.

Expected reasoning and answer basis:
- Use candidate review plus offer evidence to classify `CAND-DA-7701` as selected, `CAND-DA-7702` as waitlisted, and `CAND-DA-7703` as rejected.
- Use offer `OFFER-DA-7701`, accepted status `accepted`, and salary `112000`.
- Sum cost ledger lines to `6200`.
- Use `notice_packet_inspection` as the notice quality source.
- Include `CAND-DA-7702` and `CAND-DA-7703` in `notice_followup_required`.
- Use `send_waitlist_notice` for the waitlisted candidate and `send_rejection_notice` for the rejected candidate.
- Use `accepted_offer_only` as the payroll handoff gate and `submitted_after_acceptance` as the required payroll status.
- Set `draft_payroll_allowed` to `false`, and use `no_accepted_status_or_offer` to explain why a waitlisted candidate must not be routed to offer/payroll.
- Return `create_payroll_precheck` as the onboarding handoff and `submitted_handoff_required_after_acceptance` as the final handoff control result.

Transferable SOP and field conventions: This train task teaches several conventions used later in recruitment tests: candidate outcomes must come from committee/interview plus offer confirmation; accepted offers gate payroll handoff; waitlisted candidates are not offer/payroll eligible; recruitment cost must come from the cost ledger; notice actions must distinguish waitlist notices from rejection notices; and control fields must use exact normalized labels.

Likely pitfalls: Copying only the recruitment summary; omitting the waitlisted or rejected candidate from follow-up; summing only part of the cost ledger; treating waitlisted status as an accepted offer; allowing draft payroll handoff; or using free-text status labels instead of `committee_decision_with_offer_confirmation`, `accepted_offer_only`, and `submitted_handoff_required_after_acceptance`.

Evaluator/scoring basis: `eval/rubric.json` has six exact-match scoring points: opening/outcomes, candidate outcome control, accepted offer/cost, notice follow-up, handoff gate, and draft/waitlist exclusion. High-value checks include normalized labels such as `candidate_status_source`, `candidate_outcome_control`, `notice_quality_source`, `payroll_handoff_gate`, `payroll_assignment_status_required`, and `handoff_control_result`.

Construction/rework note: This task was reworked to be Web-first and to provide reusable train coverage for recruitment normalized labels, source precedence, notice follow-up, and payroll handoff gates. This notes file now reflects all current answer and scoring fields.

## 中文

任务定义和业务目标：本训练任务核对招聘 opening `REQ-DA-77`。求解者必须确定候选人结果、已接受 offer 详情、招聘成本合计、通知 follow-up 义务，以及薪资交接准备状态。这是正式 PeopleOps 对账任务，不是教程。

可见输入和网页证据：求解者可见 prompt 提供本地 PeopleOps Console URL、登录信息、opening ID 和 answer template。证据应从 Recruitment 候选人复核、offer register、成本台账、notice packets/messages、关联 case 详情、policy viewer、薪资 handoff 或 precheck 证据，以及应用中可见的审计证据中收集。

预期推理和答案依据：
- 通过候选人复核和 offer 证据，将 `CAND-DA-7701` 判定为入选，`CAND-DA-7702` 判定为候补，`CAND-DA-7703` 判定为拒绝。
- 使用 offer `OFFER-DA-7701`、接受状态 `accepted` 和薪资 `112000`。
- 汇总成本台账为 `6200`。
- 使用 `notice_packet_inspection` 作为通知质量来源。
- 将 `CAND-DA-7702` 和 `CAND-DA-7703` 放入 `notice_followup_required`。
- 对候补候选人使用 `send_waitlist_notice`，对拒绝候选人使用 `send_rejection_notice`。
- 使用 `accepted_offer_only` 作为薪资交接门槛，使用 `submitted_after_acceptance` 作为所需薪资状态。
- 将 `draft_payroll_allowed` 设为 `false`，并用 `no_accepted_status_or_offer` 说明候补候选人不能进入 offer/payroll 路由。
- 返回 `create_payroll_precheck` 作为 onboarding handoff，并返回 `submitted_handoff_required_after_acceptance` 作为最终 handoff 控制结果。

可迁移 SOP 和字段口径：本训练任务教授后续招聘测试会使用的约定：候选人结果必须来自委员会/面试结果加 offer confirmation；已接受 offer 才能触发 payroll handoff；候补候选人没有 offer/payroll 资格；招聘成本必须来自成本台账；通知动作必须区分 waitlist notice 与 rejection notice；控制字段必须使用精确规范化标签。

常见陷阱：只复制招聘摘要；遗漏候补或拒绝候选人的 follow-up；只汇总部分成本台账；把候补状态当成 accepted offer；允许草稿 payroll handoff；或用自由文本标签代替 `committee_decision_with_offer_confirmation`、`accepted_offer_only` 和 `submitted_handoff_required_after_acceptance`。

评测依据：`eval/rubric.json` 包含 6 个精确匹配评分点：opening/outcomes、candidate outcome control、accepted offer/cost、notice follow-up、handoff gate、draft/waitlist exclusion。高价值检查包含 `candidate_status_source`、`candidate_outcome_control`、`notice_quality_source`、`payroll_handoff_gate`、`payroll_assignment_status_required` 和 `handoff_control_result` 等规范化标签。

构造/返工说明：本任务已返工为 Web-first，并为招聘规范化标签、来源优先级、通知 follow-up 和 payroll handoff gates 提供可复用训练覆盖。本 notes 文件现已反映当前所有 answer 和 scoring fields。
