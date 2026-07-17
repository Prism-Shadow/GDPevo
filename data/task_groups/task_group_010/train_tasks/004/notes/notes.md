# train_004 Notes - Fixed-Income Risk Rebalance For PF-FI-LUMEN

## English

Data/source lineage: This task belongs to `SCN_010_institutional_investment_strategy_portfolio_risk` using source examples `E001`, `E002`, and `E003`, with the fixed-income risk-reduction family anchored mainly in the energy/fixed-income strategy example. The shared generated environment is `task_group/task_group_010_institutional_portfolio_risk/env/`; the task uses `env/data/portfolios.json`, `env/data/bonds.json`, `env/data/issuers.json`, and `env/data/policies.json` through the public API or equivalent current records. The task-local visible payload is `input/payloads/risk_meeting_memo.json`, a stale risk-meeting context memo.

Task definition: The solver prepares a JSON rebalance recommendation for `PF-FI-LUMEN`. The business goal is to lower high-yield and watchlist exposure while preserving duration within the 3.0-5.0 year range under `POL_CREDIT_RISK_REDUCTION`. The expected output follows `input/payloads/answer_template.json`: trade tickets, post-trade metrics, exception flags, watchlist handling, and a controlled risk note code.

Scenario fit and material map: The task mirrors an institutional credit-risk desk workflow: reconcile portfolio holdings, security master attributes, issuer watchlist research, and policy constraints before converting the decision into a committee-ready JSON object. `PF-FI-LUMEN` has current holdings of 78.0 USD million, including HY positions in `BND_JUNIPER_2028`, `BND_LUMEN_AUTO_2029`, and `BND_NOVA_2029`. `BND_JUNIPER_2028` is the watchlisted issuer exposure. Candidate IG replacements include `BND_QUARTZ_2031`, `BND_IRONORE_2030`, and `BND_BLUEGAS_2030`, which provide duration support without adding watchlist risk.

Solution and evaluation basis: The standard answer sells `BND_JUNIPER_2028` for 12.0 and `BND_NOVA_2029` for 8.0, then buys `BND_BLUEGAS_2030` for 5.0, `BND_IRONORE_2030` for 7.0, and `BND_QUARTZ_2031` for 8.0. Current HY exposure is 31.0/78.0 = 39.74%. Post-trade HY exposure is only the remaining 11.0 in `BND_LUMEN_AUTO_2029`, or 14.10%. The HY reduction is 25.64 percentage points. Weighted modified duration moves from about 3.99 years to 4.33 years, inside the policy band. Watchlist exposure falls from 12.0 to 0.0 USD million. The six scoring goals are: correct trade package, weight 3; correct post-trade HY allocation, weight 2; correct post-trade duration, weight 2; correct exception flags, weight 2; correct downgrade/watchlist handling, weight 2; correct risk note code, weight 1. Exact matching uses normalized trade ordering and numeric rounding as declared in the answer template.

Transfer design: As a train task, this is a real calibration task rather than a worked example. It lets the solver infer reusable fixed-income conventions for later tasks: use current portfolio/security/issuer records when local desk materials are stale, calculate HY allocation from post-trade market value, calculate weighted modified duration from post-trade bond market value, treat issuer watchlist records as risk-reduction priorities, and convert the final risk judgment into controlled enum fields. These conventions transfer directly to the energy-credit and multi-asset credit-risk test tasks without exposing their specific portfolios or answers.

Likely model pitfalls: A solver may use the stale Juniper quantity in the memo, buy a watchlisted high-yield candidate because of yield, reduce HY by the target amount but leave the portfolio above the HY cap, calculate duration over only traded bonds, or provide prose instead of controlled fields.

Construction record: Created by task-builder 4 on 2026-06-03. Files created under `train_tasks/004/` only. No environment, scratch, sibling task, or task-group index files were edited.

## 中文

数据和来源：本任务属于 `SCN_010_institutional_investment_strategy_portfolio_risk`，来源示例为 `E001`、`E002`、`E003`，其中固定收益降风险工作流主要对应能源与固定收益策略示例。共享生成环境位于 `task_group/task_group_010_institutional_portfolio_risk/env/`；本任务通过公开 API 或等价的当前记录使用 `env/data/portfolios.json`、`env/data/bonds.json`、`env/data/issuers.json` 和 `env/data/policies.json`。任务本地可见材料是 `input/payloads/risk_meeting_memo.json`，它是一份略有滞后的风险会议背景备忘录。

任务定义：求解者需要为 `PF-FI-LUMEN` 准备 JSON 格式的再平衡建议。业务目标是在 `POL_CREDIT_RISK_REDUCTION` 的约束下，降低高收益债和观察名单暴露，同时把久期保持在 3.0 到 5.0 年区间内。预期输出遵循 `input/payloads/answer_template.json`，包括交易票据、交易后指标、例外标志、观察名单处理和受控风险备注代码。

场景适配和材料地图：该任务模拟机构信用风险团队的工作：在给出委员会可用 JSON 结果前，需要核对组合持仓、证券主数据、发行人观察名单研究和政策约束。`PF-FI-LUMEN` 当前规模为 78.0 百万美元，其中高收益债包括 `BND_JUNIPER_2028`、`BND_LUMEN_AUTO_2029` 和 `BND_NOVA_2029`。`BND_JUNIPER_2028` 是观察名单发行人暴露。可用的投资级替代券包括 `BND_QUARTZ_2031`、`BND_IRONORE_2030` 和 `BND_BLUEGAS_2030`，它们能支持久期且不新增观察名单风险。

解答和评估依据：标准答案卖出 `BND_JUNIPER_2028` 12.0 和 `BND_NOVA_2029` 8.0，买入 `BND_BLUEGAS_2030` 5.0、`BND_IRONORE_2030` 7.0、`BND_QUARTZ_2031` 8.0。当前高收益债暴露为 31.0/78.0 = 39.74%。交易后只剩 `BND_LUMEN_AUTO_2029` 的 11.0 高收益债暴露，即 14.10%。高收益债比例下降 25.64 个百分点。加权修正久期从约 3.99 年上升到 4.33 年，仍在政策区间内。观察名单暴露从 12.0 降至 0.0 百万美元。六个评分目标为：正确交易组合，权重 3；正确交易后高收益债比例，权重 2；正确交易后久期，权重 2；正确例外标志，权重 2；正确降级/观察名单处理，权重 2；正确风险备注代码，权重 1。评估使用标准化交易排序，并按答案模板声明的小数精度进行数值匹配。

迁移设计：这是一个真实训练任务，不是教程或样例题。通过解题和对照答案，求解者可以归纳后续任务会用到的固定收益约定：本地材料过期时应以当前组合、证券和发行人记录为准；高收益债比例按交易后市值计算；加权修正久期按交易后债券市值计算；发行人观察名单是降风险优先项；最终风险判断应写入受控枚举字段。这些经验会迁移到能源信用和多资产信用风险测试任务，但不会暴露测试组合或答案。

常见陷阱：模型可能采用备忘录中的过期 Juniper 数量；因为收益率高而买入观察名单高收益候选券；只达到最低高收益债下降目标但仍超过高收益债上限；只按交易券计算久期；或用自由文本代替受控字段。

构建记录：由 task-builder 4 于 2026-06-03 创建。只在 `train_tasks/004/` 下创建文件；未编辑环境、scratch、其他任务目录或任务组索引。
