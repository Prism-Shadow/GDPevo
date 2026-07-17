# `train_005` — West/Northeast diabetes six-algorithm audit

## Current whole-point evaluation boundary / 当前整点评分边界

The final eight-point rubric has raw weights `[1,3,3,3,3,3,3,2]`. All named semantic checks for a point must pass for the point to earn its full `weight/21`; otherwise it earns zero. Completeness tiers and recursive fractions retained in diagnostics are construction aids only and are not scored. This section supersedes historical partial-credit wording below.

最终八点评分的原始权重为 `[1,3,3,3,3,3,3,2]`。一个评分点的全部命名语义检查必须通过，才能获得完整的 `weight/21`；否则为零。诊断中保留的完整性档位和递归比例仅用于构建审计，不参与评分。本节取代下文历史部分分表述。

## English construction record

### Objective and difficulty rework

This third difficulty rework preserves the training task's independent West/Northeast diagnosed-diabetes and poverty setting while replacing the former ridge/permutation/stability pipeline with six specialized, independently auditable algorithms. The Observatory must decide whether a county diabetes-dynamics model is reproducible, transportable, and stable enough for a 2026 briefing. A favorable full-panel coefficient cannot determine the result by itself.

The six specialized modules carry 18 of 21 raw rubric weight: delete-state two-step GMM; a complete nested elastic-net/ridge grid; null-restricted wild-cluster bootstrap-t; cross-fold grouped conformal coverage and calibration; county-trajectory PCA, deterministic clustering, and delete-state ARI; and a six-group perturbation surface. The gold answer contains 22 delete-state GMM fits, five ordered 12-row inner-grid surfaces, 80 selected outer coefficients, nine PRNG checkpoints, 22 state coverages, ten calibration deciles, three 15-value PCA loading vectors, 22 delete-state clustering fits, and a 6-by-5 source-deletion RMSE surface. Selective aggregate guessing therefore earns little, while fixed-weight semantic subchecks preserve structured partial credit without allowing long arrays to dilute critical summaries.

### Formal protocol registry and transfer purpose

The solved standard answer carries a top-level `protocol_registry_record` for `PHO_COUNTY_PANEL_TRANSPORT_V1` in family `PHO_COUNTY_ALGORITHMIC_TRANSPORT_FAMILY_V1`. It contains exactly one child, the exact-ID-triggered `portable_protocol_profile`. The profile is the self-contained reusable V1 method contract and defines deterministic direct section and `_overrides` resolution without carrying a request snapshot or instance binding.

The training task remains a formal business task. Its solver-visible request now contains only scenario-specific scope, variables, filters, grids, seeds, thresholds, standard method names, reporting precision, and required audit outputs; reusable formulas and procedural mechanics appear only inside the solved-answer snapshot. Few-shot skill generation can recover the versioned workflow from solved examples, while the base solver is not given a tutorial.

Round-two formal calibration produced only `+0.05276` overall few-shot gain. Among the three archived skills, attempt 02 succeeded in preserving four exact protocol-ID-to-method mappings; attempts 01 and 03 over-generalized statistical recipes across protocol families and weakened this panel protocol's identity. The registry now consists solely of a concise `portable_protocol_profile` so an independent skill generator can preserve the exact ID, version, family, override semantics, and executable module mechanics. The profile contains no instance entities, calendar/geography values, seeds, grid values, business cutoffs, cohort values, results, flags, or conclusions.

### Publication cohort

The read-only Web portal pages `/catalog`, `/methodology`, `/geographies/counties`, `/data/county-health`, and `/data/county-socioeconomic`, together with their filtered CSV downloads, expose all required evidence. The construction uses:

- West and Northeast counties;
- years 2021 through 2024;
- crude diagnosed-diabetes health observations;
- poverty, unemployment, median income, and net migration socioeconomic observations;
- the highest FINAL revision, with later `released_at` breaking a revision tie;
- nonsuppressed, nonmissing health values, complete socioeconomic values, and RUCC 1-9.

The balanced cohort contains 305 counties in 22 states. Three adjacent-year rows per county yield 915 rows. State census order is alphabetical. The state county counts are `AK 17, AZ 17, CA 13, CO 14, CT 9, HI 15, ID 13, MA 18, ME 14, MT 15, NH 13, NJ 15, NM 13, NV 9, NY 13, OR 12, PA 18, RI 11, UT 15, VT 15, WA 17, WY 9`.

### Common design and GMM

The outcome is adjacent-year diagnosed-diabetes change. Baseline terms are lagged diabetes, lagged poverty, fixed RUCC 2-9 indicators, and fixed 2023/2024 interval indicators. The four ordered dynamic terms are poverty, unemployment, median-income-per-$10,000, and net-migration changes.

For each full or delete-state GMM fit, the outcome, dynamics, and eight instruments are residualized anew on the intercept and baseline terms. The first step uses an identity moment weight; the second uses state score outer products. The declared `1e-12` singular-value rule fixes all pseudoinverses. Full two-step coefficients are `[0.046090, -0.017956, -0.022895, 0.000576]`, with Hansen J `3.807725`. Delete-state jackknife bias correction gives `[0.047250, -0.026551, -0.038346, 0.001394]`; maximum absolute delete-state shifts are `[0.008991, 0.015336, 0.022139, 0.001890]`.

### Nested elastic-net/ridge audit

The greedy state allocator uses balanced-county counts and is rerun for each inner training set. Every fit uses training-only population moments for the six continuous columns, fixed indicator columns, an unpenalized intercept, and penalties on all 16 other coefficients. The ordered grid crosses alpha `[0.02, 0.2, 2, 20]` with l1 ratio `[0, 0.45, 0.8]`; l1 ratio zero is the explicit ridge member. Coordinate initialization, updates, convergence, and exact tie-breaking are fixed in the request.

The five outer diagnostics are:

1. `ID,MA,NY,UT`: 177 rows; alpha/l1 `0.02/0.8`; RMSE `0.792900`.
2. `NH,OR,PA,VT`: 174 rows; alpha/l1 `0.02/0.8`; RMSE `0.724043`.
3. `AK,CO,HI,RI,WY`: 198 rows; alpha/l1 `0.02/0.8`; RMSE `0.843469`.
4. `AZ,CT,ME,MT,NV`: 192 rows; alpha/l1 `0.02/0.8`; RMSE `0.882968`.
5. `CA,NJ,NM,WA`: 174 rows; alpha/l1 `0.02/0.8`; RMSE `0.895921`.

Pooled OOF RMSE is `0.831560`, and OOF R-squared is `0.123257`. The gold retains every grid-row RMSE and every selected standardized coefficient rather than only these aggregates.

### Wild bootstrap and conformal calibration

The wild state-cluster bootstrap targets the unpenalized poverty-change coefficient. Its observed coefficient, CR1 SE, and t statistic are `0.035692`, `0.018558`, and `1.923308`. A restricted-null fit and one continuous XORSHIFT32 stream with training-only seed `7152026` generate 399 Rademacher state-weight replicates. There are 25 absolute-tail exceedances, giving plus-one p `0.065000`. The nearest-rank bootstrap t quantiles are `[-1.895591, 0.011561, 2.213941]`. Nine ordered checkpoints make PRNG consumption auditable.

Grouped conformal intervals use each held-out fold's OOF errors and calibration residuals from the other four folds. The inclusive overall coverage is `0.901639`; minimum unrounded state coverage, reported after rounding, is `0.733333`. Gold includes all fold radii/ranks, all 22 state coverages, all three RUCC-band coverages, and all ten rank-defined prediction-decile signed gaps.

### Trajectory and perturbation audits

Each county contributes 15 variable-major trajectory features: three interval changes for diabetes and each of the four socioeconomic variables. Population standardization, covariance divisor, eigen ordering, sign orientation, farthest-first centers, assignment ties, Lloyd stopping, silhouette, and ARI are all fixed.

The first five eigenvalues are `[1.988493, 1.802771, 1.659571, 1.597471, 1.558787]`; their explained shares are `[0.132566, 0.120185, 0.110638, 0.106498, 0.103919]`. Silhouette selects five clusters. Re-estimating the full trajectory pipeline after each alphabetical state deletion yields median ARI `0.630937` and minimum ARI `0.298847`.

Deleting each ordered source group without retuning gives pooled RMSE deteriorations: lagged outcome `0.059391`, lagged poverty `0.039506`, rurality `0.000000`, interval context `-0.000533`, poverty dynamics `0.000939`, and companion economic dynamics `-0.001848`. The answer also reports all five fold RMSEs, worse-fold counts, removed-term lists, and deterioration ranks.

### Decision, rubric, and evaluator validation

Only three gates pass: the bias-corrected poverty GMM coefficient, OOF RMSE, and overall conformal coverage gates. Wild-bootstrap significance, median delete-state ARI, and poverty-deletion deterioration fail. Under the declared precedence, the controlled result is `RETAIN_LAGGED_DIABETES`, which is distinct from the paired held-out scenario's controlled result.

The evaluator has exactly eight points with raw weights `[1,3,3,3,3,3,3,2]`: cohort, GMM, nested elastic net/ridge, wild bootstrap, grouped conformal, trajectory PCA/clustering, source perturbation, and decision. Registry metadata is completely unscored: a candidate may omit or alter it without penalty. SP001 scores only the publication cohort and state census; SP008 scores only the controlled decision.

Each point now uses explicit business-semantic subcheck shares instead of recursively counting section leaves. Within SP002, dimensions carry 5%; complete full-sample GMM coefficients 20%; Hansen J 10%; complete bias-corrected coefficients 25%; complete maximum-shift summaries 15%; ordered delete-state coefficient evidence 15%; and ordered delete-state Hansen evidence 10%. Thus the four critical GMM summaries carry 70% of SP002, while the long delete-state table carries 25%. Ordered arrays and tables receive deterministic completeness tiers of 1.00, 0.75, 0.50, or 0.25, so useful incomplete evidence earns structured partial credit but one nearly complete long table cannot hide a missing business conclusion. Regression probes score the gold at `1.0`, an empty object at `0.0`, deletion of the four critical GMM summaries at `0.9` overall (SP002 `0.3`), deletion of the GMM diagnostic array at `0.964285714286` (SP002 `0.75`), and deletion of representative long arrays across six modules at `0.671428571429`.

### Transfer and no-leak boundary

The transferable material is procedural: publication reconciliation, balanced panels, state deletion, clustered moments, nested state blocking, training-only scaling, deterministic coordinate descent, restricted wild bootstrap, continuous PRNG accounting, cross-fold conformal calibration, deterministic PCA/clustering, ARI, and no-retune group deletion. The solved-answer profile makes that transfer boundary self-contained and versioned while the compact input keeps task-local obligations visible. No held-out result or test fact is embedded. The training answer is 43,543 bytes.

This is fair to both calibration conditions. The base condition receives no solved-train registry. Few-shot skill generation can infer the versioned contract from the standard answer, but receives no held-out answer values or test-specific facts. Success on a future invoking request still requires independent evidence retrieval and computation.

Common errors include selecting provisional records, treating suppression as zero, losing FIPS leading zeros, using record rows rather than highest revisions, changing dummy columns by fold, leaking validation moments, resetting the PRNG, using row weights rather than state weights, calibrating on a held-out fold's own residuals, allowing arbitrary PCA signs or k-means seeds, comparing unaligned labels directly instead of ARI, retuning after a source deletion, or ranking rounded rather than unrounded deterioration.

- Author: Codex task builder for `train_005`
- Third difficulty rework: 2026-07-15

## 中文构建记录

### 目标与难度重构

第三轮难度重构保留训练题独立的西部/东北部县级确诊糖尿病—贫困场景，把原有 ridge/置换/稳定性流程替换为六个可独立复核的算法：删州两步 GMM、完整 elastic-net/ridge 嵌套网格、受限零假设 wild-cluster bootstrap-t、跨折分组 conformal 校准、县轨迹 PCA/确定性聚类/删州 ARI，以及六组来源扰动面。六个模块占 21 点中的 18 点，金标包含大量有序诊断数组，不能只猜汇总量。

### 正式协议注册与迁移目的

已解标准答案以顶层 `protocol_registry_record` 注册 `PHO_COUNTY_PANEL_TRANSPORT_V1`。注册对象只有精确 ID 触发的 `portable_protocol_profile` 一个子项；该 profile 是自包含的 V1 可复用方法契约，定义确定性直接分区与 `_overrides` 解析，但不携带请求快照或实例绑定。

训练题仍是正式业务任务。求解者可见请求只保留题目专属范围、变量、筛选、网格、种子、门槛、标准方法名、精度和必需审计输出；可迁移公式与流程机制只存在于已解答案 snapshot。few-shot 技能可从已解样例恢复带版本流程，而基础求解者不会获得教程。

第二轮正式校准的总体 few-shot 增益仅为 `+0.05276`。三个归档技能中，attempt 02 成功保留四个精确的“协议 ID→方法”映射；attempt 01 与 03 则跨协议族过度泛化统计配方，削弱了本面板协议的身份。Registry 现仅由精炼的 `portable_protocol_profile` 构成，使独立技能生成器能够保存精确 ID、版本、协议族、覆盖语义和可执行模块机制。该 profile 不包含任何实例实体、日历/地域值、种子、网格数值、业务门槛、队列值、结果、标志或结论。

### 发布队列与设计

所有证据均来自只读 Web 门户。对西部与东北部 2021-2024 年记录，健康与社会经济来源分别选择最高 FINAL 修订，相同修订号取更晚发布时间；糖尿病值必须非空且未抑制，四项经济值必须完整，RUCC 必须为 1-9。最终保留 305 县、22 州、915 条相邻年度面板行。

共同设计以糖尿病变化为结局，基线包含滞后糖尿病、滞后贫困、RUCC 2-9 和 2023/2024 年区间指示变量；动态变量依次为贫困、失业、每万美元收入和净迁移变化。全部列顺序在请求中固定。

### 六项算法结果

删州两步 GMM 的全样本系数为 `[0.046090,-0.017956,-0.022895,0.000576]`，J 统计量为 `3.807725`；删州偏差校正后为 `[0.047250,-0.026551,-0.038346,0.001394]`。每次删州都重新执行残差化与两步估计。

嵌套模型使用 5 个外折、4 个内折和 12 行完整网格，其中 l1 ratio `0` 是 ridge。每次拟合只使用训练总体矩标准化。五折选择均为 alpha/l1 `0.02/0.8`，折 RMSE 为 `0.792900,0.724043,0.843469,0.882968,0.895921`；合并 OOF RMSE/R² 为 `0.831560/0.123257`。

贫困变化的 wild-bootstrap 观测 t 为 `1.923308`。训练专用种子 `7152026` 的 399 次连续 XORSHIFT32 重复产生 25 个绝对尾部超越，加一 p 值 `0.065000`。分组 conformal 总覆盖率为 `0.901639`，最低州覆盖率为 `0.733333`。

15 维县轨迹的前五特征值为 `1.988493,1.802771,1.659571,1.597471,1.558787`。silhouette 选择 5 类；22 次删州重估的 ARI 中位数/最小值为 `0.630937/0.298847`。六组删除的 RMSE 恶化依次为 `0.059391,0.039506,0.000000,-0.000533,0.000939,-0.001848`，并保留全部 6×5 折面。

### 决策、评分与防泄漏

六个门槛中仅通过偏差校正贫困系数、OOF RMSE 和总体 conformal 覆盖率三个门槛；wild-bootstrap、聚类稳定性和贫困删除恶化未通过。因此受控结论是 `RETAIN_LAGGED_DIABETES`。

评分器恰好八点，权重 `[1,3,3,3,3,3,3,2]`。Registry 元数据完全不计分，候选可省略或篡改而不受罚；SP001 只评分发布队列与州清单，SP008 只评分受控决策。每点改用显式业务语义子检查权重，不再递归统计整个分区的叶子数量。

SP002 内部权重为：维度 5%；完整全样本 GMM 系数 20%；Hansen J 10%；完整偏差校正系数 25%；完整最大位移汇总 15%；有序删州系数证据 15%；有序删州 Hansen 证据 10%。因此四类关键 GMM 汇总占 SP002 的 70%，长删州表只占 25%。有序数组和表按 `1.00/0.75/0.50/0.25` 完整性档位给予确定性结构化部分分，长表即使接近完整也不能掩盖关键业务结论缺失。回归探针结果为：金标 `1.0`，空对象 `0.0`，删除四类关键 GMM 汇总后总分 `0.9`（SP002 为 `0.3`），删除 GMM 长诊断数组后总分 `0.964285714286`（SP002 为 `0.75`），跨六个模块删除代表性长数组后总分 `0.671428571429`。金标答案仍为 43,543 字节，标准答案数值未改动。

只迁移方法，不迁移留出题答案：已解答案中的正式注册对象把这一边界变成可解析且带版本的契约，同时允许题目局部的范围、结局、来源、年份、种子、阈值和受控决策词汇被显式覆盖。训练题与注册对象均没有复制任何留出数值、实体队列、州结果、随机种子、检查点、阈值组合或结论。

这种设计对两种校准条件都公平：基础条件不会获得已解训练 registry；few-shot 技能生成可从标准答案推断带版本的契约，却得不到任何留出答案值或测试专属事实。未来协议调用题仍必须独立检索证据并完成计算。常见错误包括发布版本选择错误、把抑制当零、折间泄漏标准化矩、重置随机流、按行而非州加权、使用自身折残差校准、任意 PCA 符号/聚类初始化、删除来源后重新调参，以及用舍入值排序恶化程度。

## Lineage and construction record

- Scenario: `SCN_023_public_health_statistical_modeling_audit`.
- Source example `E001`: abstracts multi-source public-health record reconciliation, nested regression auditing, clustered inference, confounder control, and decision-oriented sensitivity review.
- Source example `E002`: abstracts multivariate preprocessing, deterministic PCA and clustering, missingness/anomaly auditing, and ordered cross-source statistical evidence.
- Source example `E003`: closest county-level analogue; abstracts long-format health/socioeconomic reconciliation, FIPS and RUCC handling, static-versus-dynamic modeling, mediation, and stability diagnostics.
- Author: Codex task builder for `train_005`.
- Created: 2026-07-15.
- Updated: 2026-07-16.
- Major changes: constructed the six-algorithm county transport audit; calibrated complete ordered evidence; registered `PHO_COUNTY_PANEL_TRANSPORT_V1`; compacted solver-visible inputs; reduced solved-answer registry metadata to an optional, unscored, instance-free exact-ID method profile; removed registry-name disclosure from the response template; replaced recursive leaf-count scoring with fixed-weight semantic subchecks and regression-tested critical-summary versus long-array losses.

## 沿袭与构建记录

- 场景：`SCN_023_public_health_statistical_modeling_audit`。
- 来源样例 `E001`：抽象多源公共卫生记录对账、嵌套回归审计、聚类推断、混杂控制和面向决策的敏感性复核。
- 来源样例 `E002`：抽象多变量预处理、确定性 PCA 与聚类、缺失/异常审计，以及有序跨源统计证据。
- 来源样例 `E003`：最接近的县级参照；抽象长表健康/社会经济记录对账、FIPS 与 RUCC 处理、静态与动态模型比较、中介和稳定性诊断。
- 作者：`train_005` 的 Codex 任务构建代理。
- 创建日期：2026-07-15。
- 更新日期：2026-07-16。
- 主要变更：构建六算法县级迁移审计并校准完整有序证据；注册 `PHO_COUNTY_PANEL_TRANSPORT_V1`；精简求解者可见输入；将已解答案 registry 收敛为可选、不计分且不含实例值的精确 ID 方法 profile；从响应模板删除注册名称披露；以固定业务语义子检查替代递归叶子计数，并对关键汇总与长数组缺失的分差完成回归验证。
