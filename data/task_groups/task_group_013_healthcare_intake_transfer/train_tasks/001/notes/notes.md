# train_001 Notes / 任务说明

## English

This task trains the registration-readiness conventions for Northstar new-patient records. Solver-visible material should only ask the solver to log into the portal, inspect the four target patients, and produce the structured JSON answer. It should not disclose the scoring rules as a step-by-step SOP.

Expected interpretation:

- Medical insurance passes only when coverage is active and network is in network.
- PBM and pharmacy are required for all four target patients because all four have medication-managed intake.
- Demographics pass only when identity, address, phone, emergency contact, and consent are all complete.
- Risk is based on smoking, alcohol, exercise, and high-risk conditions. High risk adds `clinical_review_required` to blocked reasons, but a patient with any administrative blocker remains `blocked` overall rather than `manual_review`.

Answer rationale:

- `NSP-1008`: inactive medical coverage, incomplete emergency contact, high risk from lifestyle score; overall blocked.
- `NSP-1014`: terminated/inactive coverage and PBM not located; moderate risk; overall blocked.
- `NSP-1022`: all required administrative gates pass and risk is moderate; overall ready.
- `NSP-1031`: PBM not located, identity and phone incomplete, high lifestyle risk; overall blocked and highest-risk patient.

Scoring uses exact-match JSON fields with sorted patient arrays and sorted set arrays. Total weight is 13 points across seven checks.

## 中文

本任务用于训练 Northstar 新患者注册就绪审核规则。给求解者看的材料只应要求其登录门户、查看四个目标患者，并按结构化 JSON 返回结果，不应暴露逐步 SOP 或评分规则。

预期判定逻辑：

- 医疗保险只有在 coverage 为 active 且 network 为 in network 时通过。
- 四个目标患者均为 medication-managed intake，因此 PBM 和 pharmacy 都是必需门槛。
- 人口学信息只有在身份、地址、电话、紧急联系人和同意书都完整时通过。
- 风险等级由吸烟、饮酒、运动和高风险疾病共同决定。高风险会加入 `clinical_review_required`，但只要存在行政门槛阻断，最终结果仍为 `blocked`，而不是 `manual_review`。

答案依据：

- `NSP-1008`：医疗保险 inactive，紧急联系人不完整，生活方式风险高；最终 blocked。
- `NSP-1014`：保险 terminated/inactive，PBM not located；中等风险；最终 blocked。
- `NSP-1022`：所有必需行政门槛通过，风险中等；最终 ready。
- `NSP-1031`：PBM not located，身份和电话不完整，生活方式风险高；最终 blocked，且为最高风险患者。

评分为精确匹配 JSON，患者数组与集合数组均应排序。总分 13 分，分为七个评分点。
