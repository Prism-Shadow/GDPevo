# test_001 Notes / 任务说明

## English

This task tests registration QA transfer from `train_001`, with manual-review risk handling also anchored to the chronic-risk escalation pattern in `train_005`. Solver-visible material should only ask the solver to log into the portal, inspect the five target patients, and produce the structured JSON answer. It should not disclose the underlying SOP or scoring rules.

Hidden transfer anchors:

- From `train_001`: keep medical insurance, PBM, pharmacy, demographics, and risk as separate gates; do not merge PBM and pharmacy outcomes.
- From `train_001`: stale or missing card images do not override the portal-verified eligibility fields; coverage and network fields drive the insurance gate.
- From `train_001` and `train_005`: high clinical/lifestyle risk adds `clinical_review_required`; if all administrative gates pass, the final decision is `manual_review`, otherwise it remains `blocked`.

Answer rationale:

- `NSP-1042`: active in-network medical insurance and active PBM, but preferred pharmacy is out of network. Risk is high because of heart failure and three active conditions. Overall blocked.
- `NSP-1057`: coverage is not active, demographics are incomplete because consent is not signed, and risk is high from chronic kidney disease/heart failure/three conditions. PBM and pharmacy pass. Overall blocked.
- `NSP-1073`: active in-network insurance, active PBM, and in-network pharmacy pass, but identity and phone verification are incomplete. Lifestyle score is moderate. Overall blocked.
- `NSP-1088`: coverage is not active, while PBM, pharmacy, and demographics pass. Risk is high because of chronic kidney disease. Overall blocked.
- `NSP-1096`: medication management is not required, so PBM and pharmacy are `not_required`. Administrative gates pass, but lifestyle risk is high, so the patient routes to manual review.

Scoring uses exact-match JSON fields with normalized sorted patient arrays and sorted set arrays. Total weight is 10 points across seven checks.

## 中文

本任务测试从 `train_001` 迁移来的注册 QA 规则，并结合 `train_005` 中慢病风险升级/复核的处理方式。给求解者看的材料只应要求其登录门户、查看五个目标患者，并按结构化 JSON 返回结果，不应暴露底层 SOP 或评分规则。

隐藏迁移锚点：

- 来自 `train_001`：医疗保险、PBM、药房、人口学信息和风险必须作为独立门槛判断；不要把 PBM 和药房结果混在一起。
- 来自 `train_001`：过期或缺失的卡片图片不能覆盖门户中已验证的资格字段；保险门槛由 coverage 和 network 字段决定。
- 来自 `train_001` 与 `train_005`：高临床/生活方式风险会加入 `clinical_review_required`；如果所有行政门槛都通过，则最终结果为 `manual_review`，否则仍为 `blocked`。

答案依据：

- `NSP-1042`：医疗保险 active 且 in network，PBM active，但首选药房 out of network。因心衰和三个活动病情为高风险。最终 blocked。
- `NSP-1057`：保险不是 active，且同意书未签导致人口学信息不完整；因慢性肾病、心衰和三个病情为高风险。PBM 和药房通过。最终 blocked。
- `NSP-1073`：保险、PBM、药房均通过，但身份和电话验证不完整；生活方式风险为中等。最终 blocked。
- `NSP-1088`：保险不是 active，PBM、药房和人口学信息通过；因慢性肾病为高风险。最终 blocked。
- `NSP-1096`：不需要 medication management，因此 PBM 和药房为 `not_required`。行政门槛均通过，但生活方式风险高，因此进入人工复核。

评分为精确匹配 JSON，并会规范化患者数组与集合数组排序。总分 10 分，分为七个评分点。
