# Builder Notes / 构建说明

English:

- Task `test_003` covers referral board triage for `REF-3151`, `REF-3167`, `REF-3175`, `REF-3182`, `REF-3190`, and `REF-3196`.
- Transfer anchors are `train_003` referral readiness rules: ICD chapter and narrative fit, laterality consistency, records/imaging/auth gaps, duplicate links, urgency-based tiering, and referring-practice follow-up.
- Solver-facing materials intentionally name only the portal, credentials, target records, and output shape. They do not expose shared answer rules or a step-by-step SOP.
- Same-condition and same-physician hints without a patient-demographic duplicate match are distractors in this cohort; target records have no direct duplicate linked referral IDs.
- Hidden answer values were derived from `target_record_summary.json` and cross-checked against `env/data/generated_data.json`.
- Exact-match scoring has seven groups and a 12-point maximum: readiness statuses, issue sets, coding outcomes, duplicate links, priority tiers, follow-up queue by practice, and ready count. Priority tiers carry additional weight after review because direct attempts were near-saturated while still missing the train-derived urgency-tier convention.

中文：

- 任务 `test_003` 覆盖 `REF-3151`、`REF-3167`、`REF-3175`、`REF-3182`、`REF-3190`、`REF-3196` 的转诊看板分诊。
- 迁移锚点来自 `train_003` 的转诊就绪规则：ICD 章节与叙述匹配、左右侧一致性、病历/影像/授权缺口、重复转诊链接、基于紧急程度的分层，以及转诊诊所跟进。
- 给求解者可见的材料只包含门户地址、登录凭据、目标记录和输出格式，避免泄露共享答案规则或逐步 SOP。
- 本组中，只有相同病情或相同医生但没有患者人口学重复匹配的提示属于干扰项；目标记录没有直接重复转诊链接。
- 隐藏答案来自 `target_record_summary.json`，并使用 `env/data/generated_data.json` 做交叉核对。
- 精确匹配判分包含七组、最高 12 分：就绪状态、问题集合、编码结果、重复链接、优先级、按诊所汇总的跟进队列、可预约数量。评审后提高了优先级分层权重，因为直接尝试接近满分但仍漏掉训练迁移来的 urgency-tier 规则。
