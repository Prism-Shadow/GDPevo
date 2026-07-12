# Builder Notes / 构建说明

English:

- Task `train_003` covers orthopedic referral triage for `REF-3106`, `REF-3118`, `REF-3124`, `REF-3139`, and `REF-3142`.
- Solver-facing materials intentionally name only the portal, credentials, target records, and output shape. They do not expose the shared scoring rules or a step-by-step SOP.
- Hidden answer values were derived from `target_record_summary.json` and cross-checked against `env/data/generated_data.json`.
- Exact-match scoring checks seven fields/groups: readiness statuses, issue sets, coding outcomes, duplicate links, priority tiers, ready count, and follow-up practice queue.

中文：

- 任务 `train_003` 覆盖 `REF-3106`、`REF-3118`、`REF-3124`、`REF-3139`、`REF-3142` 的骨科转诊分诊。
- 给求解者可见的材料只包含门户地址、登录凭据、目标记录和输出格式，避免泄露共享判分规则或逐步 SOP。
- 隐藏答案来自 `target_record_summary.json`，并使用 `env/data/generated_data.json` 做了交叉核对。
- 精确匹配判分包含七组字段：就绪状态、问题集合、编码结果、重复转诊链接、优先级、可预约数量、需要联系的转诊诊所队列。
