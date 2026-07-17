# Notes

## English

- Builder-facing task notes for `train_001`, the Q4 2025 Identity Platform portfolio mix review.
- Hidden answer was computed with effective status from `status_history` through `2025-12-31T23:59:59`; `Verified`, `Done`, and `Closed` are eligible, while open and cancelled work is excluded.
- Category precedence follows the common brief. Security-sensitive token, compliance, vulnerability, credential, audit, and access-control signals take precedence over reliability, tech-debt, and feature signals.
- The evaluator implements seven scoring points: eligible set, category counts, mix metrics, under-invested categories, largest negative gap, follow-up actions, and evidence samples.

## 中文

- 这是 `train_001` 的构建说明，任务内容是 Identity Platform 在 2025 年第四季度的组合工作类型复盘。
- 隐藏答案使用截至 `2025-12-31T23:59:59` 的 `status_history` 计算有效状态；`Verified`、`Done`、`Closed` 计入范围，未完成和取消项不计入。
- 分类优先级遵循公共说明。与 token、合规、漏洞、凭据、审计、访问控制相关的安全信号优先于可靠性、技术债和功能信号。
- 评测脚本包含七个得分点：候选工作项集合、分类计数、占比和差距、投入不足类别、最大负差距类别、后续动作以及证据样本。

## Integration Audit Addendum

Lineage and materials: this task is derived from source example `E001` and uses generated shared environment data: `work_items`, `status_history`, `portfolio_targets`, `teams`, and policy documents. Solver-visible inputs are only `prompt.txt`, `request_context.json`, and `answer_template.json`; the full business data is accessed through `<TASK_ENV_BASE_URL>`.

Solution and evaluation basis: the standard answer filters Identity Platform work by 2025-Q4 quarter-end effective state, excludes cancelled work, classifies completed items into controlled portfolio categories, compares mix against targets, and emits exact follow-up actions. Seven exact-match points cover eligible set, counts, percentages/gaps, under-investment, largest gap, action ownership, and evidence IDs.

Transfer role: as a train task, it lets the solver infer work-mix conventions by attempting a real task and comparing with the answer. These conventions anchor `test_001`, `test_004`, and `test_005`.

## 集成审核补充

数据来源与材料：本任务来自 `E001`，使用生成共享环境中的 `work_items`、`status_history`、`portfolio_targets`、`teams` 和政策文档。求解者可见输入只有 `prompt.txt`、`request_context.json` 和 `answer_template.json`；完整业务数据通过 `<TASK_ENV_BASE_URL>` 访问。

解法与评测依据：标准答案按 2025-Q4 季末有效状态筛选 Identity Platform 工单，排除取消项，将已完成项归入受控组合类别，对比目标比例，并输出精确跟进行动。七个精确匹配点覆盖 eligible 集合、计数、百分比/gap、低配、最大 gap、动作归属和证据 ID。

迁移作用：作为训练任务，它让求解者通过真实尝试和答案对比推断 work-mix 约定。这些约定锚定 `test_001`、`test_004` 和 `test_005`。
