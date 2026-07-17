# train_004 construction and evaluation notes

## Current whole-point evaluation boundary / 当前整点评分边界

The final evaluator uses eight whole points with raw weights `[1,3,3,3,3,3,3,2]`. Every named check inside a point must pass before the point earns its complete `weight/21`; otherwise that point earns zero. Detailed list/table comparisons are reported for auditability but do not create fractional credit. This statement supersedes older evaluator-probe wording below.

最终评估器采用八个整点评分，原始权重为 `[1,3,3,3,3,3,3,2]`。一个评分点内部的全部命名检查都通过后，才获得完整的 `weight/21`；否则该点为零。列表和表格的详细比较仅用于审计，不产生部分分。本说明取代下文旧的评估器探针表述。

## English record

### Solved-answer V1 transfer registry

The versioned registry for `PHO_STATE_ROBUSTNESS_TRANSPORT_V1` in family `PHO_STATE_ALGORITHMIC_TRANSPORT_FAMILY_V1` appears only as optional top-level `protocol_registry_record` metadata in the solved standard answer. It contains exactly one child, the exact-ID-triggered `portable_protocol_profile`, and carries no request snapshot or instance binding. The solver-visible request remains a formal business task containing task-local entities, years, sources, cohorts, variables, features, grids, random settings, thresholds, precision, standard method names, and requested evidence.

This placement makes transfer learnable from a completed training example without putting formulas, matrices, coordinate updates, fold-allocation recipes, PRNG bit operations, pseudocode, or generic tie/aggregation tutorials in solver-visible input. The template does not name or describe the registry. The evaluator ignores it completely: omission or mutation has no score effect, SP001 remains release/cohort work, and the task still has exactly eight business-aligned points.

### Scenario and evidence lineage

This R4 difficulty rework preserves the training task's original substantive scenario and data lineage: the 2024 reliability-weighted state association between age-adjusted direct-survey `food_insecurity` and age-adjusted direct-survey `diagnosed_diabetes`, adjusted for `physical_inactivity`, median income, and region. The selected diagnosed-diabetes direct-record sample size remains the reliability weight. Evidence is limited to the read-only Web portal's state geography, state-health, state-socioeconomic, catalog, and methodology pages.

The registered audit now has six high-difficulty but reusable computational modules:

1. a nine-cluster delete-one-Census-division jackknife of the reliability-weighted 2024 coefficient, including every ordered deletion fit and bias-corrected inference;
2. nine outer and eight inner division-grouped elastic-net folds, six lambdas, nine nonlinear features, weighted fold-local standardization, zero-start coordinate descent, convergence-cycle audits, and pooled out-of-fold metrics;
3. 1,999 wild-division bootstrap-t draws driven by a continuous training-specific xorshift32 stream, with seven registered state/statistic checkpoints;
4. nine grouped out-of-fold conformal calibrations that reuse the selected outer lambdas and report every finite-sample rank and division interval diagnostic;
5. a 20-feature five-year trajectory PCA over the strict balanced cohort, deterministic farthest-first k-means, ordered scores and assignments, and five leave-one-year stability refits;
6. all 4,096 direct-versus-rollup outcome scenarios over twelve paired states, thirteen replacement-count strata, a maximum-mask audit, and an exact twelve-player Shapley decomposition.

Every reusable convention capable of changing an answer is preserved in the method-only profile: release precedence, complete-case rules, matrices, fold and solver details, stream operations, checkpoints, conformal rank, PCA orientation, clustering ties, bitmask semantics, Shapley aggregation, and precedence. Thresholds and every instance binding come only from the invoking request. The slim solver-visible request retains this task's business specification and named methods. Difficulty comes from executing the formal audit, not from a prompt-embedded implementation tutorial.

### Gold result

Annual complete-case counts for 2020 through 2024 are 42, 43, 43, 41, and 41. The 2024 primary cohort has 41 states; the strict five-year balanced cohort has 20. The full weighted food-insecurity coefficient is 0.4559. Division deletion yields a bias-corrected coefficient of 0.4649, jackknife standard error 0.1338, p-value 0.0084, and maximum change 21.8809%, so the registered jackknife flag passes.

The nested elastic net has pooled OOF RMSE 0.6844, MAE 0.5400, and R-squared 0.7894. The wild bootstrap uses seed `24071544`; six of 1,999 statistics exceed the observed 3.7680, giving plus-one p-value 0.0035 and terminal unsigned state 3944843368. Grouped conformal calibration covers 38 of 41 states, or 0.9268. The minimum leave-one-year adjusted Rand index is 0.6611.

All 4,096 source scenarios retain a positive, weighted-HC3-significant coefficient, but bitmask 1839 reaches a 31.5776% coefficient shift. This exceeds the registered 25% stability limit. The first five module flags therefore pass, `source_exhaustive_stable` fails, and the training-specific conclusion is `NOT_ROBUST_AT_SOURCE_EXHAUSTIVE`.

After the final method-only boundary reduction, the self-contained gold answer is 35,536 bytes. The added profile is optional and unscored; the analytical response contract and all ordered diagnostics are unchanged. Its analytical projection, obtained by removing only `protocol_registry_record`, remains byte-equivalent to the prior gold. It was independently generated from the environment SQLite source using the same release and data definitions exposed through the Web portal. The transient construction program and numerical container were removed after answer and evaluator validation.

The response template now keeps answer-derived collection sizes out of solver-visible input. It specifies the primary exclusion list and strict balanced list as complete semantic sets; requires trajectory assignments to align one-for-one with the derived balanced-state list; defines `M` from the parsed primary-cohort states with eligible paired direct and rollup records; requires replacement strata for every integer from zero through `M`; and aligns Shapley effects one-for-one with the derived rollup order. Request-declared dimensions remain explicit, including the five study years, Census-division folds, lambda grid, cluster count, bootstrap checkpoints, and other fixed registered settings. This changes only non-scored template guidance: the request, standard answer, evaluator, and eight-point rubric behavior are unchanged.

### Evaluator and probes

The evaluator has exactly eight isolated rubric points with raw weights `[1, 3, 3, 3, 3, 3, 3, 2]`, totaling 21:

- SP001, weight 1: release reconciliation, primary cohort, and balanced cohort;
- SP002, weight 3: the ordered division jackknife and bias-corrected inference;
- SP003, weight 3: every nested elastic-net grid, convergence audit, outer fold, and pooled metric;
- SP004, weight 3: bootstrap setup, seven checkpoints, distribution, test, and terminal generator state;
- SP005, weight 3: all grouped conformal calibration and held-out diagnostics;
- SP006, weight 3: PCA spectrum, initialization, centroids, state scores, assignments, and stability refits;
- SP007, weight 3: exhaustive source strata, maximum scenario, and exact Shapley effects;
- SP008, weight 2: six flags, first failure, and conclusion.

Each point provides field-level partial credit. Ordered lists are scored position by position and excess entries are penalized. Numeric values must be finite and agree at the declared four-decimal precision; integers, Booleans, and strings retain strict JSON types. A missing input, malformed JSON, or non-object root scores zero. The gold answer scores 1.0. Eight isolated mutations, one per point, produced scores 0.9976190476, 0.9942857143, 0.9961904762, 0.9961904762, 0.9942857143, 0.9928571429, 0.9942857143, and 0.9780952381; every mutation reduced only its intended rubric point.

### Method transfer and no-leak boundary

The paired held-out task and this training task share only the six reusable algorithm families and the discipline of exposing ordered intermediate audits. This training instance keeps its own 2024 diagnosed-diabetes/food-insecurity entities, reliability weights, 41-state primary cohort, 20-state balanced cohort, division deletion results, nine-feature grids, selected lambdas and convergence counts, seed `24071544`, checkpoint stream, conformal radii, trajectory scores and clusters, twelve-state rollup ordering, 4,096 scenario values, Shapley effects, thresholds, flags, and `SOURCE_EXHAUSTIVE` failure.

No held-out smoking or premature-mortality values, held-out cohorts, held-out deletion coefficients, held-out selected lambdas, held-out random seed or generator states, held-out intervals, held-out clusters, held-out source masks, or held-out conclusion appear in this task. Transfer is therefore implementation-level: a solver can reuse coordinate descent, grouped resampling, conformal ranking, PCA/k-means, subset enumeration, and Shapley code, but cannot reuse a held-out numeric answer.

- Original task builder: `/root/build_train_004`
- Second difficulty rework: `/root/hard2_train_004`
- Third difficulty rework: `/root/hard3_train_004`
- Updated: 2026-07-16

## 中文记录

### 已解答标准答案中的 V1 迁移注册记录

协议 `PHO_STATE_ROBUSTNESS_TRANSPORT_V1` 及协议族 `PHO_STATE_ALGORITHMIC_TRANSPORT_FAMILY_V1` 的版本化注册记录，仅作为已解答标准答案中的可选顶层 `protocol_registry_record` 元数据出现。它只有精确 ID 触发的 `portable_protocol_profile` 一个子项，不含请求快照或实例绑定。求解者可见请求仍是正式业务任务，保留本题实体、年份、来源、队列、变量、特征、网格、随机设置、门槛、精度、标准方法名称和所需证据。

这种位置使技能生成器能够从已解答训练示例学习迁移信号，又不会在求解前暴露公式、矩阵、坐标更新、折分配步骤、PRNG 位运算、伪代码或通用并列/汇总教程。模板不命名也不描述注册对象。评测器完全忽略注册对象：省略或篡改都不影响得分，SP001 仍只负责发布与队列，任务仍恰有八个业务评分点。

### 场景、证据链与算法重构

R4 难度重构保留训练题原有业务场景与数据链：审计 2024 年州级年龄调整直接调查 `food_insecurity` 与年龄调整直接调查 `diagnosed_diabetes` 的可靠性加权关联，调整 `physical_inactivity`、收入中位数和地区；可靠性权重仍是所选糖尿病直接记录的样本量。所有证据仅来自只读 Web 门户中的州地理、州健康、州社会经济、目录和方法页面。

本次登记六类高难度但可迁移的计算模块：九个 Census division 的逐簇删除 jackknife；九层外折、八层内折、六个 lambda、九个非线性特征以及从零开始的加权弹性网坐标下降；训练专属 xorshift32 连续随机流驱动的 1,999 次 wild-division bootstrap-t 和七个检查点；复用外折所选 lambda 的九组 OOF 共形校准；严格平衡队列上的 20 维五年轨迹 PCA、确定性最远点初始化聚类和逐年删除稳定性；以及十二个配对州的 4,096 个直接值/汇总值场景、十三个替换数量分层和精确 Shapley 分解。

全部会影响答案的可复用约定均保存在只含方法的 profile 中，包括发布优先级、完整案例规则、矩阵、折与求解器细节、随机流操作、检查点、共形秩、PCA 方向、聚类并列规则、位掩码、Shapley 汇总和决策优先级。阈值及全部实例绑定仅来自调用请求。精简后的求解输入保留本题业务规格和标准方法名称；难度来自执行正式审计，而不是提示内嵌实现教程。

### 金标准与结论

2020 至 2024 年完整案例数依次为 42、43、43、41、41；2024 年主队列有 41 州，严格五年平衡队列有 20 州。完整加权食物不安全系数为 0.4559。逐 division 删除的偏差校正系数为 0.4649，jackknife 标准误为 0.1338，p 值为 0.0084，最大变化为 21.8809%，故该模块通过。

嵌套弹性网的汇总 OOF RMSE 为 0.6844、MAE 为 0.5400、R 平方为 0.7894。野生簇 bootstrap 使用种子 `24071544`；1,999 次中有 6 次超过观测统计量 3.7680，加一 p 值为 0.0035，最终无符号状态为 3944843368。分组共形区间覆盖 41 州中的 38 州，覆盖率为 0.9268。逐年删除的最小调整 Rand 指数为 0.6611。

4,096 个来源场景的系数均保持正向且加权 HC3 显著，但位掩码 1839 的系数偏移达到 31.5776%，超过登记的 25% 稳定阈值。因此前五个模块通过，`source_exhaustive_stable` 失败，训练题专属结论为 `NOT_ROBUST_AT_SOURCE_EXHAUSTIVE`。最终方法边界收敛后，金标准答案为 35,536 字节；便携档案仅为可选且无评分的方法元数据，分析提交契约与全部有序诊断不变。仅移除注册对象得到的分析投影与旧金标逐字节等价。答案由环境底层数据按 Web 门户公开的同一发布与字段定义独立生成；验证结束后已清理临时构建程序和数值容器。

响应模板现已移除从标准答案反推的结果集合长度。主队列排除列表和严格平衡列表改由“完整集合”语义约束；轨迹 assignment 必须与派生出的平衡州列表逐项对齐；`M` 由主队列中同时具有符合条件的直接记录和汇总记录的州集合确定；替换数量分层必须完整覆盖零至 `M`；Shapley 效应必须与派生的汇总州顺序逐项一一对应。请求明确声明的维度仍保持显式，包括五个研究年份、Census division 折、lambda 网格、聚类数、bootstrap 检查点和其他固定登记设置。该整改只改变不计分的模板指引；请求、标准答案、评测器与八点 rubric 行为均未改变。

### 评测、探针与防泄漏

评测器恰有八个隔离评分点，原始权重为 `[1, 3, 3, 3, 3, 3, 3, 2]`，总权重 21。SP001 只覆盖发布和队列；SP002 至 SP007 分别覆盖 jackknife、嵌套弹性网、带检查点的野生簇 bootstrap、分组共形、轨迹 PCA/聚类稳定性、穷举来源场景与 Shapley；SP008 覆盖六个标志、首个失败模块和结论。注册元数据完全不参与评分。金标、无注册对象版本和任意篡改注册对象版本均得 1.0；业务队列变异只降低 SP001，决策变异只降低 SP008。

与配对测试题共享的只有六类算法和有序审计思路。本训练实例保留自己的 2024 糖尿病/食物不安全实体、可靠性权重、41 州主队列、20 州平衡队列、division 删除结果、九特征网格、所选 lambda 与迭代次数、种子和随机流、共形半径、轨迹分数与聚类、十二州来源顺序、4,096 个场景、Shapley 效应、阈值、标志以及 `SOURCE_EXHAUSTIVE` 失败。题目不包含测试题的吸烟或过早死亡数值、队列、删除系数、所选 lambda、随机种子或状态、区间、聚类、位掩码或结论。可迁移的是实现方法，而不是任何测试数值答案。

## Lineage and construction record

- Scenario: `SCN_023_public_health_statistical_modeling_audit`.
- Source example `E001`: abstracts long-form public-health release reconciliation, exact cohort filtering, missingness handling, and regression audit evidence.
- Source example `E002`: abstracts competing-source and cross-level reconciliation, revision precedence, identifier alignment, and anomaly handling.
- Source example `E003`: abstracts multivariable modeling, dimension reduction, deterministic clustering, sensitivity analysis, and a controlled operational conclusion.
- Author: `/root/build_train_004`.
- Created: 2026-07-15.
- Updated: 2026-07-16.
- Major changes: initial Web-evidence task construction; two high-difficulty algorithmic reworks; protocol/deproceduralization and evaluator-integrity reworks; reduction to optional, unscored method-only solved-answer metadata; solver-visible SOP and registry-name redaction; replacement of six answer-derived template lengths with semantic/cardinality relations.

## 谱系与构建记录

- 场景：`SCN_023_public_health_statistical_modeling_audit`。
- 来源示例 `E001`：抽象长表公共卫生发布对账、精确队列筛选、缺失处理和回归审计证据。
- 来源示例 `E002`：抽象竞争来源与跨层级对账、修订优先级、标识符匹配和异常处理。
- 来源示例 `E003`：抽象多变量建模、降维、确定性聚类、敏感性分析和受控业务结论。
- 作者：`/root/build_train_004`。
- 创建日期：2026-07-15。
- 更新日期：2026-07-16。
- 主要变更：初始 Web 证据任务构建；两轮高难度算法改造；协议化/去过程泄漏与评测完整性改造；将注册记录收敛为可选、不评分且只含方法的已解答答案元数据；整改求解侧 SOP 与注册名称泄露；将模板中六个由答案推导的长度常量改为语义/基数关系。

## Portable protocol profile rework

Formal calibration round 2 achieved only `+0.052760` overall transfer because two independently generated skills omitted exact protocol mappings. The optional, unscored solved-answer registry now consists solely of a concise `portable_protocol_profile` with exact identity and activation, deterministic direct/`*_overrides` resolution, an explicit instance-value boundary, and executable reusable definitions for weighted inference, deletion jackknife, nested elastic net, seeded bootstrap, grouped conformal, trajectory stability, exhaustive source scenarios, Shapley aggregation, and controlled precedence. It contains no train- or test-instance entities, years, regions, seeds, grids, thresholds, cohorts, results, flags, or decisions. The final independent-review rework removed the registry name from the response template; the evaluator, test artifacts, and Web data did not change.

## 便携协议档案返工

第二轮正式校准的总体迁移仅为 `+0.052760`，因为两份独立生成技能遗漏了精确协议映射。可选且不评分的已解答答案注册记录现仅含简洁 `portable_protocol_profile`，包含精确身份和激活规则、确定性的直接键/`*_overrides` 解析、明确实例值边界，以及加权推断、删除 jackknife、嵌套弹性网、带种子的 bootstrap、分组 conformal、轨迹稳定性、穷举来源场景、Shapley 汇总和受控优先级的可执行复用定义。它不含任何训练或测试实例的实体、年份、地域、种子、网格、阈值、队列、结果、标志或结论。最终独立复核整改从响应模板删除注册名称；评分器、测试产物和 Web 数据保持不变。
