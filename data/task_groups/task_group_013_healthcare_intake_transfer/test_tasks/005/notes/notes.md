# Hidden Notes / 隐藏说明

These notes are for task builders and evaluators only. Do not expose them in solver-visible input.

## English

Task `test_005` is the mixed-queue transfer task. It requires solvers to classify each queue item first, then apply the relevant family rule learned from `train_001` through `train_005`.

Transfer anchors:

- `Q-5203` links to `TR-2620`, a renal transfer. The packet has missing/unusable authorization, expired confidentiality statement, expired infection screen, missing labs, and draft medication list. Chair availability is compatible, but packet issues control the route. Action is `transfer_packet_followup`, owner `Intake Pool`, due `today` because the queue urgency is same day.
- `Q-5255` links to `TR-2688`, another renal transfer. The packet has missing authorization, expired infection screen, and missing labs. The chair is waitlisted, but packet follow-up still takes precedence. Because the item is routine and waiting external follow-up, due priority is `two_business_days`.

Other family anchors:

- `Q-5219` links to orthopedic referral `REF-3151`. Coding and laterality are valid, records and imaging are present, but authorization is pending. Action is `referral_authorization_followup`, owner `Referral Desk`.
- `Q-5226` links to chronic program record `NSP-1014`. Diabetes program support is present, but consent is only verbal pending signature and the form is incomplete. Renal risk affects cadence, but the queue-level action is consent/form follow-up by `Program Coordinator`.
- `Q-5237` links to registration benefits for `NSP-1057`. Medical coverage is not active, demographics are incomplete because consent is not signed, and clinical risk is high due kidney/heart conditions. Action is `registration_benefits_followup`, owner `Benefit Desk`.
- `Q-5241` links to chart `CHR-2094`. The chart exists, vitals/history/problems/orientation are acceptable, and the remaining chart blocker is demographics. Action is `chart_demographics_update`, owner `Clinical Intake`.

Scoring is exact-match structured scoring with ten groups and a 14-point maximum: task metadata, family classifications, next actions, transfer owner routing, non-transfer owner routing, transfer blockers, referral/program/chart blockers, registration blockers, due priorities, and rollup counts. The split is intentional because post-skill attempts showed real transfer on transfer owner routing and cross-family blocker sets that broad all-or-nothing groups hid.

## 中文

本文件仅供任务构建者和评测器使用，不应出现在解题者可见材料中。

`test_005` 是混合队列迁移测试。解题者需要先判断每个队列项所属业务族，再把 `train_001` 至 `train_005` 中学到的规则迁移到对应的链接记录。

转院规则锚点：

- `Q-5203` 链接到肾病转院 `TR-2620`。资料包中 authorization 缺失、confidentiality statement 过期、infection screen 过期、labs 缺失、medication list 为 draft。椅位兼容，但资料包问题优先。动作为 `transfer_packet_followup`，负责人为 `Intake Pool`；由于队列紧急度为 same day，due 为 `today`。
- `Q-5255` 链接到肾病转院 `TR-2688`。资料包中 authorization 缺失、infection screen 过期、labs 缺失。椅位为 waitlist，但仍先处理资料包问题。该项为 routine 且等待外部补件，因此 due 为 `two_business_days`。

其他业务族锚点：

- `Q-5219` 链接骨科转诊 `REF-3151`。编码和侧别有效，病历和影像均已收到，但授权 pending。动作为 `referral_authorization_followup`，负责人为 `Referral Desk`。
- `Q-5226` 链接慢病项目 `NSP-1014`。糖尿病项目有诊断和近期数据支持，但同意书只是 verbal pending signature，表单 incomplete。肾脏风险影响随访频率，但队列层面的动作是由 `Program Coordinator` 跟进同意书和表单。
- `Q-5237` 链接 `NSP-1057` 的注册福利记录。医疗保险不是 active，人口学信息因 consent 未签而不完整，且肾脏/心脏疾病带来高临床风险。动作为 `registration_benefits_followup`，负责人为 `Benefit Desk`。
- `Q-5241` 链接图表 `CHR-2094`。图表已创建，生命体征、病史、问题列表和 orientation 可接受，剩余阻断项是 demographics。动作为 `chart_demographics_update`，负责人为 `Clinical Intake`。

评分采用精确匹配结构化评分，共十组，最高 14 分：任务元数据、业务族分类、下一步动作、转院负责人路由、非转院负责人路由、转院阻断集合、转诊/项目/图表阻断集合、注册阻断集合、due priority、汇总计数。这样拆分是有意设计的，因为 post-skill 尝试在转院负责人路由和跨业务族阻断集合上已有真实迁移收益，旧的大块全对评分没有体现出来。
