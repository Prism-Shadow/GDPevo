# Notes / 备注

## English

This is a hidden builder note for `train_002`. The solver-visible prompt must stay English-only and should not expose the full SOP. It asks the solver to audit dialysis transfer packet readiness for TR-2604, TR-2611, TR-2620, and TR-2635 in the Northstar Care Intake Portal.

Scoring follows the shared dialysis-transfer rules:

- Required packet items are labs, infection screen, dialysis prescription, medication list, allergy list, authorization, confidentiality statement, referring contact, and transport note.
- Labs must be usable and within 30 days before/on the requested start date.
- Infection screen must be usable and within 14 days before/on the requested start date.
- Dialysis prescription must be final.
- Other packet items must not be missing, draft, or expired.
- Compatible chair statuses are `chair held` and `chair available, not held`; `capacity review` maps to capacity_review; `waitlist` maps to waitlist.
- Packet issues route to `referring_facility`; clean packet plus capacity issue routes to `capacity_coordinator`; accepted transfers route to `chart_prep` unless chart prep is complete, then `intake_complete`.

Gold-answer highlights:

- TR-2604: packet hold. Missing/unusable packet items are allergy list, authorization, confidentiality statement, labs, and transport note. Infection screen is stale. Capacity is capacity_review.
- TR-2611: packet hold. Missing/unusable packet items are confidentiality statement, dialysis prescription, infection screen, and labs. Capacity is capacity_review.
- TR-2620: packet hold. Missing/unusable packet items are authorization, confidentiality statement, infection screen, labs, and medication list. Chair availability is compatible.
- TR-2635: packet hold. Missing/unusable packet items are authorization, confidentiality statement, labs, and transport note. Infection screen is stale. Chair availability is compatible.

## 中文

这是 `train_002` 的隐藏构建备注。面向解题者的 prompt 必须只用英文，并且不要泄露完整操作规程。任务要求解题者在 Northstar Care Intake Portal 中审核 TR-2604、TR-2611、TR-2620、TR-2635 的透析转院资料包是否可接收。

评分遵循共享的透析转院规则：

- 必需资料包括 labs、infection screen、dialysis prescription、medication list、allergy list、authorization、confidentiality statement、referring contact、transport note。
- labs 必须可用，且日期在 requested start 当天或之前 30 天内。
- infection screen 必须可用，且日期在 requested start 当天或之前 14 天内。
- dialysis prescription 必须是 final。
- 其他资料不得是 missing、draft 或 expired。
- `chair held` 和 `chair available, not held` 属于 compatible；`capacity review` 属于 capacity_review；`waitlist` 属于 waitlist。
- 有资料包问题时 route_owner 为 `referring_facility`；资料包通过但容量不兼容时为 `capacity_coordinator`；可接收但 chart prep 未完成时为 `chart_prep`，已完成时为 `intake_complete`。

标准答案要点：

- TR-2604：资料包暂缓。不可用项目为 allergy list、authorization、confidentiality statement、labs、transport note。infection screen 过期于 freshness 规则。容量为 capacity_review。
- TR-2611：资料包暂缓。不可用项目为 confidentiality statement、dialysis prescription、infection screen、labs。容量为 capacity_review。
- TR-2620：资料包暂缓。不可用项目为 authorization、confidentiality statement、infection screen、labs、medication list。椅位兼容。
- TR-2635：资料包暂缓。不可用项目为 authorization、confidentiality statement、labs、transport note。infection screen 过期于 freshness 规则。椅位兼容。
