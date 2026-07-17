# train_002 construction notes

## Current whole-point evaluation boundary / 当前整点评分边界

The final evaluator has eight points with raw weights `[1,3,3,3,3,3,3,2]`. A point passes only when every named subcheck for that business outcome is complete; it then earns its full `weight/21`, otherwise zero. Any subcheck fraction shown in evaluator output is unscored diagnostic evidence. This policy supersedes any historical partial-credit language below.

最终评估器包含八个评分点，原始权重为 `[1,3,3,3,3,3,3,2]`。只有当某一业务结果的全部命名子检查完整通过时，该点才获得完整的 `weight/21`，否则为零。评估器输出中的子检查比例只是不计分的诊断证据。本政策取代下文任何历史部分分表述。

## English

### Scope and evidence provenance

This training task belongs to `SCN_023_public_health_statistical_modeling_audit` and preserves its independent county scenario: adult obesity is the outcome, poverty is the exposure, physical inactivity is the mediator, and the requested geography is the Midwest and South. The primary cross-sectional system remains anchored in 2023. The algorithmic audit uses the four public release years 2021 through 2024 so that two instrumented change rows and a four-year trajectory can be audited without changing the primary year.

All gold evidence was derived on 2026-07-15 from the running Web-only Public Health Observatory portal and its public CSV download links. Construction did not read the environment database, generators, manifests, seed material, or server implementation. The public geography download supplied FIPS, state, region, and RUCC. The county-health download supplied crude final adult-obesity and physical-inactivity releases. The county-socioeconomic download supplied poverty, median income, bachelor's attainment, unemployment, net migration, and uninsured values.

### Formal protocol registry and transfer purpose

The solved standard answer carries a top-level `protocol_registry_record` for `PHO_COUNTY_MEDIATION_TRANSPORT_V1`. It contains exactly one child, the exact-ID-triggered `portable_protocol_profile`. The profile is the self-contained reusable V1 method contract: it defines deterministic direct and `_overrides` resolution while carrying no request snapshot or instance binding.

The training task remains a formal business task. Its solver-visible request contains only task-specific entities, years, sources, filters, variables, feature maps, grids, seed, thresholds, precision, standard method names, and requested evidence. Reusable formulas and detailed procedures appear only in the solved-answer snapshot, allowing few-shot transfer without turning the input into a tutorial.

Round-two formal calibration produced only `+0.05276` overall few-shot gain. Review of the three archived skills showed that attempt 02 preserved four exact protocol-ID-to-method mappings, while attempts 01 and 03 generalized statistical advice across protocol families and made this mediation mapping less reliable. The registry therefore now consists solely of a concise `portable_protocol_profile`. It binds the exact ID, version, and family to executable reusable mechanics and override rules, while excluding all instance entities, calendar/geography values, seeds, grid values, business cutoffs, cohort values, results, flags, and conclusions.

### Publication reconciliation and linked cohorts

The two requested regions contain 696 geography rows. After the declared final/crude filters and greatest-version selection, the selected health-row counts for 2021 through 2024 are `1325`, `1324`, `1338`, and `1323`; the selected socioeconomic counts are `696` in every year. Suppressed or null selected releases remain in the publication audit but are never imputed.

Annual basic-complete counts are `573`, `564`, `571`, and `580`. The 2023 primary cohort therefore has 571 counties in 29 state blocks. Intersecting completeness across all four years gives 315 balanced counties. Requiring the additional 2023 machine-learning predictors gives 553 counties, still in 29 states. Every downstream module uses exactly its declared cohort and deterministic county/state order.

### Multi-period difference GMM

The balanced system has 630 rows: two rows for each of 315 counties, ordered as 2023 then 2024 within FIPS. Poverty and physical-inactivity levels lagged two years instrument their respective changes. Income and bachelor's attainment changes plus the 2024 indicator enter both the structural and instrument matrices.

The total poverty coefficient is `-1.5009` with cluster SE `0.8709`; path a is `0.5503` with SE `0.8569`; path b is `1.8019` with SE `3.1423`; and direct poverty is `-2.4926` with SE `3.2106`. The two first-stage partial F statistics are `1.1813` and `1.0512`. The cross-equation correction is `1.0432` and selected covariance is `1.4496`, producing a stacked indirect estimate `0.9917`, SE `2.8722`, and interval `[-4.8918, 6.8752]`. It does not exclude zero, so this module is not supported. The answer retains all 29 ascending delete-one-state refits rather than reducing this instability to a single summary.

### Nested state-blocked ridge and grouped conformal audit

The nested ridge audit compares a 20-feature socioeconomic/nonlinear/RUCC map with a 24-feature map that appends physical inactivity and its declared nonlinear interactions. Every outer state has its own complete inner leave-state-out grid over `[0.02, 0.2, 2, 20, 200]`. The compact answer stores two five-value inner-RMSE arrays per outer fold, positionally aligned to the global grid, plus both selected lambdas and both outer RMSE values. This preserves the complete high-dimensional audit while keeping the serialized answer below the requested size ceiling.

Pooling all 553 outer predictions gives base RMSE `2.5549` and augmented RMSE `2.0658`; the augmented model wins in 26 of 29 states. The state-grouped conformal audit fixes augmented lambda at `2`. Five deterministic train/calibration/test cycles yield overall coverage `0.9928`, mean width `11.9003`, and all 29 states at or above 80% coverage. The answer retains every cycle and every state coverage/width row.

### Restricted-null bootstrap, sensitivity, and trajectories

The cluster bootstrap uses the three 2023 primary OLS systems, 2,047 restricted-null replicates, and one continuous unsigned xorshift32 stream initialized to the training-specific seed `23032023`. One state sign is reused across all three equations within a replicate. The final state is `633790947`. The total-poverty, path-a-poverty, and path-b-inactivity bootstrap p-values are all `0.0005`; their bootstrap-t intervals are `[0.7228, 1.1302]`, `[0.6832, 1.0353]`, and `[0.5969, 0.7762]`. All twelve declared PRNG/t-statistic checkpoints remain in the gold answer.

The partial-R2 surface starts from path a `0.8562`, path b `0.6862`, classical path-b SE `0.0358`, and 558 residual degrees of freedom. Its equal-strength tipping R2 is `0.5468`. All 50 ordered direction/grid rows are retained, and the controlled low-R2 sign condition passes.

The trajectory matrix contains 29 states by 12 year-variable features. Deterministic PCA gives leading eigenvalues `10.9691`, `0.8450`, and `0.0420`, explaining `0.9141`, `0.0704`, and `0.0035`. K-means converges in five updates. Leave-one-year-out ARIs are `0.7530`, `1.0000`, `1.0000`, and `1.0000`; mean and minimum are `0.9383` and `0.7530`, so trajectory stability passes. Full signed loadings, state scores, counts, and clusters are retained.

### Controlled result, answer size, and evaluator verification

Five of six controlled modules pass; difference GMM alone fails. The ordered decision is `PARTIAL_OBESITY_MEDIATION_AUDIT`. The serialized gold answer is exactly `56,302` bytes and retains the portable method-only profile and all analytical evidence arrays.

The evaluator contains exactly eight business-result points with weights `[1, 3, 3, 3, 3, 3, 3, 2]`, totaling 21. Registry metadata is completely unscored: omission or mutation does not change the score. SP001 scores only publication reconciliation and linked cohorts; SP008 scores only the controlled classification. Gold scores exactly `1.0`.

### No-leak transfer boundary

The paired held-out task can learn only reusable procedure: deterministic publication reconciliation, linked cohorts, explicitly instrumented difference systems, group-score covariance, cross-equation product uncertainty, ordered group deletion, nested blocked tuning, restricted-null paired group bootstrap, state-grouped conformal calibration, partial-R2 surfaces, deterministic PCA signs, clustering, and label-invariant stability. The profile makes this boundary machine-readable and versioned while requiring scope, exposure, mediator, outcome, sources, years, seeds, thresholds, flags, and controlled vocabulary to come from the future request.

No held-out coefficient, interval, cohort total, state diagnostic, random seed or state, checkpoint, predictive result, trajectory result, flag vector, or conclusion is supplied in the registry object. This task's analytical gold values were computed from its own obesity/poverty/inactivity releases, Midwest/South cohorts, 2023 primary system, and training-specific random stream. The base condition receives no solved-train registry; few-shot skill generation can infer the inheritance contract from the standard answer but receives no held-out evidence. Method can transfer; answers cannot.

## 中文

### 范围与证据来源

本训练题属于 `SCN_023_public_health_statistical_modeling_audit`，并保留独立县域场景：结局为成人肥胖，暴露为贫困，中介为身体活动不足，请求地区为 Midwest 与 South，主横截面年份仍为 2023。为同时审计两行工具变量变化系统和四年轨迹，算法审计使用 2021 至 2024 年公开发布，但不改变主年份。

全部金标准证据于 2026-07-15 从运行中的纯 Web 公共卫生观测门户及其公开 CSV 下载链接推导。构建过程没有读取环境数据库、生成器、清单、种子材料或服务端实现。公开地理下载提供 FIPS、州、地区与 RUCC；县健康下载提供成人肥胖与身体活动不足粗率最终发布；县社会经济下载提供贫困、收入中位数、本科学历比例、失业率、净迁移和未保险比例。

### 正式协议注册与迁移目的

已解标准答案以顶层 `protocol_registry_record` 注册 `PHO_COUNTY_MEDIATION_TRANSPORT_V1`。注册对象只有精确 ID 触发的 `portable_protocol_profile` 一个子项；该 profile 是自包含的 V1 可复用方法契约，定义确定性直接键与 `_overrides` 解析，但不含请求快照或实例绑定。

训练题仍是正式业务任务。求解者可见请求只含题目专属实体、年份、来源、筛选、变量、特征图、网格、种子、门槛、精度、标准方法名和所需证据；可迁移公式与详细流程只存在于已解答案 snapshot，从而支持 few-shot 迁移而不把输入变成教程。

### 发布选择与联动队列

两个地区共有 696 条县地理记录。应用声明的 `FINAL/CRUDE` 筛选与最高版本选择后，2021 至 2024 年选中健康行数依次为 `1325`、`1324`、`1338`、`1323`；每年选中社会经济行均为 `696`。被抑制或为空的选中发布仍计入发布审计，但绝不填补。

四年基本完整县数依次为 `573`、`564`、`571`、`580`。2023 主队列因此包含 571 县与 29 个州块；四年完整交集为 315 县；再要求额外机器学习字段后为 553 县，仍覆盖 29 州。所有模块严格使用声明队列与确定性顺序。

### 多期差分 GMM

平衡系统含 630 行，即每个 315 县按 2023、2024 排列两行。两年前的贫困与活动不足水平分别作为其变化的工具变量，收入和本科学历比例变化及 2024 指示进入声明矩阵。

总贫困系数为 `-1.5009`、聚类 SE `0.8709`；路径 a 为 `0.5503`、SE `0.8569`；路径 b 为 `1.8019`、SE `3.1423`；直接贫困为 `-2.4926`、SE `3.2106`。两项第一阶段部分 F 为 `1.1813`、`1.0512`。跨方程修正为 `1.0432`，选中协方差为 `1.4496`；堆叠间接效应为 `0.9917`、SE `2.8722`、区间 `[-4.8918, 6.8752]`，包含零，因此本模块不支持。金答案仍保留全部 29 个按州排序的删除重拟合。

### 嵌套州块岭回归与分组 conformal

嵌套岭回归比较 20 维社会经济/非线性/RUCC 特征与追加活动不足非线性交互后的 24 维特征。每个外层州都有完整的内层逐州留出网格 `[0.02, 0.2, 2, 20, 200]`。答案用与全局网格位置对齐的两个五值 RMSE 数组存储每折网格，同时保留两项选择 lambda 与两项外层 RMSE；这既保留完整高维审计，也控制答案体积。

汇总 553 个外层预测后，基础与增强 RMSE 为 `2.5549`、`2.0658`，增强模型在 29 州中的 26 州获胜。分州 conformal 固定增强 lambda 为 `2`；五个确定性循环给出总体覆盖率 `0.9928`、平均宽度 `11.9003`，全部 29 州覆盖率不低于 80%。金答案保留每个循环和每州覆盖/宽度。

### 受限零假设 bootstrap、敏感性与轨迹

聚类 bootstrap 使用三套 2023 主 OLS 方程、2,047 次受限零假设重复，以及以训练专属种子 `23032023` 初始化的一条连续无符号 xorshift32 流。每次重复中同一州符号由三条方程共享。最终状态为 `633790947`。总贫困、路径 a 贫困与路径 b 活动不足的 p 值均为 `0.0005`，bootstrap-t 区间分别为 `[0.7228, 1.1302]`、`[0.6832, 1.0353]`、`[0.5969, 0.7762]`。答案保留全部十二个 PRNG/t 检查点。

部分 R2 曲面以路径 a `0.8562`、路径 b `0.6862`、路径 b 经典 SE `0.0358` 和 558 个残差自由度为基线；等强度临界 R2 为 `0.5468`。全部 50 条有序方向/网格行均保留，受控低 R2 符号条件通过。

轨迹矩阵为 29 州乘 12 个年份-变量特征。确定性 PCA 的前三特征值为 `10.9691`、`0.8450`、`0.0420`，解释比例为 `0.9141`、`0.0704`、`0.0035`；K-means 五次更新收敛。逐年删除 ARI 为 `0.7530`、`1.0000`、`1.0000`、`1.0000`，均值和最小值为 `0.9383`、`0.7530`，轨迹稳定条件通过。完整符号载荷、州得分、县数、聚类与稳定性行均保留。

### 受控结论、体积与评估器验证

六个模块中五个通过，仅差分 GMM 不通过；有序结论为 `PARTIAL_OBESITY_MEDIATION_AUDIT`。金答案序列化体积恰为 `65,306` 字节，保留自包含规范 snapshot 与全部分析证据数组。

评估器恰有八个业务结果点，权重为 `[1, 3, 3, 3, 3, 3, 3, 2]`，总计 21。Registry 元数据完全不计分，省略或篡改均不影响得分；SP001 只评分发布对账与联动队列，SP008 只评分受控分类。金答案精确得 `1.0`。

### 无泄漏迁移边界

配对留出题只能学习可复用流程：确定性发布对账、联动队列、显式工具变量差分系统、组得分协方差、乘积跨方程不确定性、按组删除、嵌套块调参、受限零假设配对组 bootstrap、分州 conformal、部分 R2 曲面、确定性 PCA 符号、聚类和标签不变稳定性。已解答案 registry 把该边界变成可解析且带版本的契约，同时允许范围、暴露、中介、结局、来源、年份、种子、阈值、标志和受控结论词汇被显式覆盖。

注册对象不提供任何留出题系数、区间、队列总数、州诊断、随机种子或状态、检查点、预测结果、轨迹结果、标志向量或结论。本题分析金值由自身肥胖/贫困/活动不足发布、Midwest/South 队列、2023 主系统和训练专属随机流计算。基础条件不会获得已解训练 registry；few-shot 技能生成可从标准答案推断继承契约，但得不到留出证据。方法可以迁移，答案不能迁移。

第二轮正式校准的总体 few-shot 增益仅为 `+0.05276`。复核三个归档技能后发现，attempt 02 保留了四个精确的“协议 ID→方法”映射，而 attempt 01 与 03 更倾向于跨协议族泛化统计建议，使本中介协议映射不够可靠。因此 registry 现仅由精炼的 `portable_protocol_profile` 构成：它把精确 ID、版本和协议族绑定到可执行的可复用机制与覆盖规则，同时排除全部实例实体、日历/地域值、种子、网格数值、业务门槛、队列值、结果、标志和结论。

## Lineage and construction record

- Scenario: `SCN_023_public_health_statistical_modeling_audit`.
- Source example `E001`: abstracts multi-source public-health joins, nested regression audits, clustered inference, confounder diagnostics, and decision-oriented sensitivity checks.
- Source example `E002`: abstracts multivariate preprocessing, missingness and anomaly review, deterministic PCA/clustering, and ordered cross-source evidence.
- Source example `E003`: closest county-mediation analogue; abstracts long-format health and socioeconomic reconciliation, FIPS/RUCC controls, static-versus-dynamic models, mediation pathways, and spatial or stability diagnostics.
- Author: Codex task builder for `train_002`.
- Created: 2026-07-15.
- Updated: 2026-07-16.
- Major changes: constructed the county obesity mediation audit; expanded its algorithmic modules; registered `PHO_COUNTY_MEDIATION_TRANSPORT_V1`; compacted solver-visible inputs; reduced solved-answer registry metadata to an optional, unscored, instance-free exact-ID method profile; removed registry-name disclosure from the response template.

## 沿袭与构建记录

- 场景：`SCN_023_public_health_statistical_modeling_audit`。
- 来源样例 `E001`：抽象多源公共卫生连接、嵌套回归审计、聚类推断、混杂诊断和面向决策的敏感性检查。
- 来源样例 `E002`：抽象多变量预处理、缺失与异常复核、确定性 PCA/聚类，以及有序跨源证据。
- 来源样例 `E003`：最接近的县级中介参照；抽象长表健康与社会经济记录对账、FIPS/RUCC 控制、静态与动态模型、中介路径，以及空间或稳定性诊断。
- 作者：`train_002` 的 Codex 任务构建代理。
- 创建日期：2026-07-15。
- 更新日期：2026-07-16。
- 主要变更：构建县级肥胖中介审计并扩展算法模块；注册 `PHO_COUNTY_MEDIATION_TRANSPORT_V1`；精简求解者可见输入；将已解答案 registry 收敛为可选、不计分且不含实例值的精确 ID 方法 profile；从响应模板删除注册名称披露。
