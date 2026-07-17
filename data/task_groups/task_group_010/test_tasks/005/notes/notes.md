# Hidden Notes For `test_005`

## English

This task is the CIO composite test task for `task_group_010_institutional_portfolio_risk`, based on scenario `SCN_010_institutional_investment_strategy_portfolio_risk` and source examples `E001`, `E002`, and `E003`. It uses the shared Asteria Investment Office environment under `env/` and a task-local committee packet at `input/payloads/committee_packet.json`. The solver-visible packet names `PF-MA-VEGA`, the Q3 2026 allocation focus set, the relevant equity index ids, and a committee preference for a constrained energy-credit action.

The business task is to produce a compact committee decision JSON that combines three recurring operation families: active allocation views, energy-credit portfolio action, and international equity diversification. Current environment data is the authority over the stale packet snapshot. The answer uses `PF-MA-VEGA` portfolio records as of `2026-05-29`, `POLICY_SET_2026_05`, Q3 2026 macro signals and prior views, current bond and issuer data, and index levels from `2025-05-30` through `2026-04-30`.

Allocation rows are computed for Emerging Markets, India, Latin America, Corporate Investment Grade, Corporate High Yield, and USD. The Q3 signal mapping gives EM `UW`, India `OW`, LatAm `OW`, IG credit `OW`, HY credit `UW`, and USD `UW`; changes are relative to the Q3 prior-view records whose previous quarter is Q2 2026. Signal scores are rounded to three decimals and rationale codes are copied from current macro-signal records.

The energy-credit action is a single rotation that sells USD 2.0m of `BND_BLUEGAS_2030`, sells USD 2.0m of `BND_GRANITE_2030`, and buys USD 4.0m of `BND_HELIOS_2028`. This keeps total portfolio value unchanged at USD 70.0m, leaves HY allocation at 10.00%, lowers weighted energy duration from 3.93 to 3.78 years, and reduces max issuer concentration from 14.29% to 11.43%, which passes the 12% issuer limit. The action also avoids watchlisted issuers and fits the `transition_bond_selectivity` theme. A likely model pitfall is buying more LNG because the energy signal is favorable; that worsens issuer concentration in the current Vega portfolio.

The international equity result uses monthly simple returns from consecutive index levels and Pearson correlations rounded to three decimals. Within the requested Vega index universe, the highest concentration pair is `IDX_EM`/`IDX_WORLD` at 0.974, breaching the 0.80 high-correlation threshold. The best diversifier pair is `IDX_CHINA`/`IDX_LATAM` at -0.825. The diversification action is to rotate from `IDX_EM` to `IDX_LATAM`, aligned with the EM underweight and LatAm diversifier allocation view. The committee decision is `approve_with_monitoring`, trigger `correlation_cap_breach`, with priority order `international_diversification`, `energy_credit_rotation`, then `allocation_view_update`.

Evaluation has eight exact-match scoring points with raw weights: identifiers/date/policy (1), allocation view rows (3), energy rotation action and trade tickets (3), energy metrics and constraint flags (2), correlation summary (2), international diversification action (2), committee decision and priority order (2), and final risk flags (2). Numeric values are normalized to the precision declared in `answer_template.json`; list-like business rows are normalized by stable identifiers where appropriate. The final risk flags are correlation threshold breached true, China dependence true, current issuer concentration breach true, post-trade issuer concentration breach false, HY cap pressure false, duration drift false, and HY underweight signal true.

Transfer anchors are `train_001` and `train_004` for credit constraints, source precedence, and duration/HY/issuer metrics; `train_002` and `train_005` for correlation conventions and diversification actions; and `train_003` plus `train_005` for allocation view mapping, prior-view change, conviction, and rationale-code style. The test-specific difficulty is the composite prioritization and the fact that Vega requires reconciling a positive LNG signal with issuer concentration and HY-underweight allocation signals.

Construction record: authored by task-builder 10 on 2026-06-03. Files created for `test_tasks/005` only: prompt, committee packet, answer template, standard answer, evaluator, shell wrapper, and hidden notes.

## 中文

本任务是 `task_group_010_institutional_portfolio_risk` 的 CIO 综合型测试任务，来源场景为 `SCN_010_institutional_investment_strategy_portfolio_risk`，对应源样例 `E001`、`E002`、`E003`。任务使用共享的 Asteria Investment Office 环境 `env/`，以及本任务本地的委员会资料包 `input/payloads/committee_packet.json`。可见资料包给出组合 `PF-MA-VEGA`、Q3 2026 配置关注范围、相关股票指数，以及在约束内提出能源信用动作的委员会偏好。

业务目标是生成一个紧凑的委员会决策 JSON，把三个反复出现的操作族合并起来：主动配置观点、能源信用组合动作、国际股票分散化动作。当前环境数据优先于本地资料包中的旧快照。标准答案使用 `PF-MA-VEGA` 在 `2026-05-29` 的组合记录、`POLICY_SET_2026_05`、Q3 2026 宏观信号和前期观点、当前债券与发行人数据，以及 `2025-05-30` 至 `2026-04-30` 的指数点位。

配置观点覆盖 Emerging Markets、India、Latin America、Corporate Investment Grade、Corporate High Yield 和 USD。Q3 信号映射后，EM 为 `UW`，India 为 `OW`，LatAm 为 `OW`，投资级信用为 `OW`，高收益信用为 `UW`，USD 为 `UW`；变化方向相对于 Q3 前期观点记录中的 Q2 2026。信号分数保留三位小数，理由代码来自当前宏观信号表。

能源信用动作是一个轮换：卖出 USD 2.0m 的 `BND_BLUEGAS_2030`，卖出 USD 2.0m 的 `BND_GRANITE_2030`，买入 USD 4.0m 的 `BND_HELIOS_2028`。该动作保持总市值 USD 70.0m 不变，高收益占比仍为 10.00%，能源信用加权久期从 3.93 年降至 3.78 年，最大发行人集中度从 14.29% 降至 11.43%，低于 12% 限制；同时避开观察名单发行人，并符合 `transition_bond_selectivity` 主题。常见错误是因为 LNG 信号较好而继续加仓 LNG，但在 Vega 当前组合中这会恶化发行人集中度。

国际股票部分使用连续指数点位计算月度简单收益，并计算 Pearson 相关系数，保留三位小数。在 Vega 指定指数范围内，最高集中度组合是 `IDX_EM`/`IDX_WORLD`，相关系数 0.974，超过 0.80 高相关阈值；最佳分散组合是 `IDX_CHINA`/`IDX_LATAM`，相关系数 -0.825。分散化动作是从 `IDX_EM` 轮换到 `IDX_LATAM`，与 EM 低配和 LatAm 分散化观点一致。委员会结论为 `approve_with_monitoring`，触发项为 `correlation_cap_breach`，优先顺序为 `international_diversification`、`energy_credit_rotation`、`allocation_view_update`。

评估包含八个精确匹配评分点，原始权重分别为：标识、日期和政策（1），配置观点行（3），能源轮换动作和交易票据（3），能源指标与约束标志（2），相关性摘要（2），国际分散化动作（2），委员会决策和优先顺序（2），最终风险标志（2）。数值按 `answer_template.json` 声明的精度归一化；列表型业务结果按稳定标识归一化。最终风险标志为：相关阈值触发 true，中国依赖标志 true，当前发行人集中度超限 true，交易后发行人集中度超限 false，高收益上限压力 false，久期漂移 false，高收益低配信号 true。

迁移锚点包括：`train_001` 与 `train_004` 对信用约束、数据优先级、久期/HY/发行人指标的迁移；`train_002` 与 `train_005` 对相关性计算约定和分散化动作的迁移；`train_003` 与 `train_005` 对配置观点映射、前期观点变化、信念等级和理由代码格式的迁移。本测试的特定难点在于综合排序，并且 Vega 需要把正面的 LNG 信号与发行人集中度、高收益低配信号进行协调。

构建记录：task-builder 10 于 2026-06-03 创建。仅在 `test_tasks/005` 下创建了 prompt、委员会资料包、答案模板、标准答案、评估器、shell 包装脚本和隐藏 notes。
