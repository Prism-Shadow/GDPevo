# test_004 construction and evaluation notes

## Current whole-point evaluation boundary / 当前整点评分边界

The final evaluator has eight binary points with weights `[1,3,3,3,3,3,3,2]`: release/cohort integrity, jackknife inference, pooled elastic-net prediction, bootstrap test, pooled conformal coverage, complete deterministic clustering/stability, source-scenario stability count, and the controlled conclusion. Every point earns all of `weight/21` only when all of its named required checks pass; otherwise zero. Detailed integrity fractions remain diagnostics only.

最终评估器包含八个二元评分点，权重为 `[1,3,3,3,3,3,3,2]`：发布与队列完整性、jackknife 推断、elastic-net 汇总预测、bootstrap 检验、conformal 汇总覆盖率、完整确定性聚类与稳定性、来源场景稳定数量、受控结论。每点只有在其全部命名必需检查通过时才获得完整 `weight/21`，否则为零；详细完整性比例只用于诊断。

## English record

### Registered train-transfer protocol

This held-out state robustness audit is paired with `train_tasks/004` through registered protocol `PHO_STATE_ROBUSTNESS_TRANSPORT_V1`. The solver-visible training request is a task-specific business specification, not an SOP. The solved training answer alone carries a method-only portable profile for release reconciliation; weighted and unweighted linear-model conventions; delete-one-cluster jackknife aggregation and inference; grouped nested elastic-net fitting, grid evaluation, selection, and diagnostics; restricted-null wild-cluster bootstrap-t generation and checkpoints; grouped out-of-fold conformal calibration and finite-sample ranks; covariance PCA, deterministic farthest-first/Lloyd clustering, label alignment, leave-one-year stability; and exhaustive source-scenario construction with exact Shapley aggregation.

The held-out prompt and `analysis_request.json` now invoke that protocol instead of reproducing those procedures. In particular, they no longer embed jackknife formulas, elastic-net coordinate updates and fold mechanics, xorshift operations and bootstrap checkpoint defaults, conformal order-statistic rules, PCA/k-means solver and stability recipes, or bitmask/Shapley aggregation formulas. `answer_template.json` remains an output contract and does not duplicate the SOP.

### Held-out overrides and fairness boundary

The solver-facing request retains every test-specific input that determines this independent audit: the 2020-2024 study window and 2022 reference year; final age-adjusted direct-survey premature-mortality and adult-smoking evidence; final poverty, uninsured, median-income, and region evidence; primary and strict five-year balanced cohorts; the unweighted primary and two-way-within designs; state clustering; the ordered fourteen-feature nonlinear map; alpha `0.65` and the six-lambda test grid; state-bootstrap null target and held-out seed `20220715`; 90% grouped conformal target; the four ordered five-year trajectory blocks; the direct-versus-county-rollup source pair; four-decimal reporting; and all six business thresholds and decision precedence rules.

The protocol supplies only transferable computation. It supplies no held-out selected states, complete-case counts, fitted coefficients, inner or outer diagnostics, bootstrap draws or terminal state, conformal radii, PCA scores, clusters, source ordering, scenario mask, Shapley effects, flags, or conclusion. A solver must independently use the Web portal to discover those values. The training and test tasks also differ in year, measures, covariates, weighting, cohort structure, cluster unit, feature map, regularization settings, random seed, source-pair size, and business thresholds. Skill gain can therefore come from reusable implementation knowledge, not from copying training answers.

### Gold, evaluator, and contract invariants

The held-out request, gold output, and evaluator remain byte-for-byte unchanged. A post-production leakage audit changed only five result-dependent cardinality declarations in `answer_template.json`: delete-one and trajectory rows now align one-to-one with the independently resolved `balanced_state_codes`; the rollup list defines `M` as the independently resolved eligible-rollup-state count; replacement-count strata cover the integers from zero through `M`; and Shapley rows align one-to-one with the resolved rollup order. This preserves response keys, field types, precision requirements, allowed enum values, and ordering semantics without disclosing the gold cohort or rollup cardinalities.

Lengths that are explicit consequences of the request remain fixed in the contract: the declared study years, lambda grid, cluster/PCA configuration, and the fixed Census-division universe still determine their corresponding structures. Thus the repair removes solved-result hints while retaining legitimate request-derived shape constraints.

The evaluator still has exactly eight isolated rubric points covering release/cohort reconciliation, cluster jackknife, nested elastic net, wild-cluster bootstrap, grouped conformal calibration, trajectory PCA/clustering, exhaustive source/Shapley analysis, and the precedence decision. Their raw weights remain `[1, 3, 3, 3, 3, 3, 3, 2]`. Gold scores 1.0, malformed or missing submissions score zero, and structured high-volume outputs receive semantic-module partial credit without long-array element dilution.

- Original task builder: `/root/build_test_004`
- Earlier difficulty reworks: `/root/finish_test_004`, `/root/hard2_test_004`, `/root/hard3_test_004`
- Procedural-leakage rework: `/root/deproc_test_004`
- Protocol-dependency rework: `/root/protocol_test_004`
- Length-leakage audit and repair: `/root/test004_template_rework`
- Updated: 2026-07-16

## 中文记录

### 注册的训练迁移协议

本留出州级稳健性审计通过注册协议 `PHO_STATE_ROBUSTNESS_TRANSPORT_V1` 与 `train_tasks/004` 配对。求解者可见训练请求是本题专属业务规格，而不是 SOP。只有已解训练答案携带只含方法的便携档案，覆盖发布记录对账、加权与非加权线性模型、逐簇删除 jackknife 汇总与推断、分组嵌套弹性网的拟合/网格评估/选择/诊断、受限零假设 wild-cluster bootstrap-t 及检查点、分组 OOF 共形校准与有限样本秩、协方差 PCA、确定性最远点初始化与 Lloyd 聚类、标签对齐和逐年删除稳定性，以及穷举来源场景和精确 Shapley 汇总。

测试提示和 `analysis_request.json` 现在只调用该协议，不再复述这些程序。解题输入尤其不再内嵌 jackknife 公式、弹性网坐标更新与折构造、xorshift 位运算和 bootstrap 检查点默认值、共形次序统计量、PCA/K-means 求解与稳定性步骤、位掩码和 Shapley 汇总公式。`answer_template.json` 仍仅定义输出契约，不重复 SOP。

### 留出覆盖项与公平性边界

解题侧仍保留决定本独立审计结果的全部测试专属输入：2020-2024 年研究窗口和 2022 年参考年；最终发布的年龄调整直接调查过早死亡与成人吸烟证据；最终发布的贫困、未投保、收入中位数和地区证据；主队列及严格五年平衡队列；非加权主模型与双向组内模型；州聚类；十四个有序非线性特征；`0.65` 的 alpha 和测试专属六档 lambda；州级 bootstrap 零假设目标与留出种子 `20220715`；90% 分组共形目标；四组有序五年轨迹特征；直接调查与县级汇总来源对；四位小数规则；以及六项业务阈值和决策优先级。

协议只提供可迁移计算知识，不提供测试题的入选州、完整案例数、拟合系数、内外折诊断、bootstrap 抽样或最终状态、共形半径、PCA 得分、聚类、来源顺序、场景位掩码、Shapley 效应、标志或结论；这些值必须由求解者通过 Web 门户独立发现。训练与测试还在年份、指标、协变量、权重、队列结构、聚类单元、特征图、正则参数、随机种子、来源配对规模和业务阈值上不同。因此技能增益只能来自可复用实现知识，不能来自复制训练答案。

### 金标、评测器与契约不变量

留出题请求、金标输出和评测器均保持逐字节不变。产后泄漏审计只修改了 `answer_template.json` 中五项依赖结果的基数声明：逐州删除结果和轨迹分配与独立解析出的 `balanced_state_codes` 一一对齐；汇总州列表把 `M` 定义为独立解析出的合格汇总州数量；替换数量分层覆盖从零到 `M` 的所有整数；Shapley 行与解析出的汇总顺序一一对齐。这样既保留响应键、字段类型、精度、枚举值和排序语义，又不披露金标队列或汇总州的数量。

凡长度由请求显式决定的结构仍保留固定约束，包括已声明的研究年份、lambda 网格、聚类/PCA 配置以及固定的 Census division 全集。该修复因此只移除已解结果提示，不削弱合法的请求派生形状约束。

评测器仍恰有八个隔离评分点，依次覆盖发布/队列、簇 jackknife、嵌套弹性网、wild-cluster bootstrap、分组共形、轨迹 PCA/聚类、来源/Shapley 和优先级结论；原始权重仍为 `[1, 3, 3, 3, 3, 3, 3, 2]`。金标得 1.0，畸形或缺失提交得零分；高容量结构化输出按语义模块提供部分分，避免长数组元素稀释。

- 原始任务构建者：`/root/build_test_004`
- 较早难度改造：`/root/finish_test_004`、`/root/hard2_test_004`、`/root/hard3_test_004`
- 过程泄漏改造：`/root/deproc_test_004`
- 协议依赖改造：`/root/protocol_test_004`
- 长度泄漏审计与修复：`/root/test004_template_rework`
- 更新日期：2026-07-16

## Lineage and construction record

- Scenario: `SCN_023_public_health_statistical_modeling_audit`.
- Source relevance: `E001` anchors state release selection, covariate adjustment, clustered diagnostics, and claim robustness; `E002` anchors PCA, clustering, standardized trajectories, and source anomaly audits; `E003` contributes long-format publication reconciliation and direct-versus-rollup source auditing.
- Task brief: determine whether the held-out state premature-mortality/smoking model remains reliable under clustered deletion, predictive, resampling, calibration, trajectory, and exhaustive source perturbation audits.
- Environment lineage: the task uses only shared Public Health Observatory Web endpoints backed by the fixed generated SQLite release. Environment source, database files, generator, seed manifest, and judge are never staged for solvers.
- Payload lineage: the request carries test-specific entities, scopes, seed, thresholds, and protocol overrides; the template carries only response shape, types, precision, and controlled choices. The solved training answer is the sole transfer carrier for reusable protocol defaults.
- Author: independent task-builder agent `/root/build_test_004`.
- Created: 2026-07-15.
- Updated: 2026-07-16.
- Major changes: difficulty expansion; procedure de-duplication; registered transfer protocol; final lineage completion; result-dependent template cardinalities replaced by request/parsed-set alignment rules.

## 沿袭与构建记录

- 场景：`SCN_023_public_health_statistical_modeling_audit`。
- 来源关联：`E001` 提供州级发布筛选、协变量调整、聚类诊断和主张稳健性沿袭；`E002` 提供 PCA、聚类、标准化轨迹和来源异常审计；`E003` 提供长表发布对账以及直接来源与汇总来源审计。
- 任务简述：通过删簇、预测、重采样、校准、轨迹和穷举来源扰动审计，判断留出的州级过早死亡—吸烟模型是否可靠。
- 环境沿袭：任务只使用由固定生成 SQLite 支撑的共享公共卫生观测站 Web 端点；环境源码、数据库文件、生成器、种子清单和裁判从不提供给求解者。
- 载荷沿袭：请求承载测试专属实体、范围、种子、门槛和协议覆盖项；模板仅承载响应形状、类型、精度与受控选项。标准训练答案是可复用协议默认值的唯一迁移载体。
- 作者：独立任务构建代理 `/root/build_test_004`。
- 创建日期：2026-07-15。
- 更新日期：2026-07-16。
- 主要变更：扩展难度；去除程序重复；建立注册迁移协议；补齐最终沿袭记录；将依赖结果的模板基数替换为请求/解析集合对齐规则。
