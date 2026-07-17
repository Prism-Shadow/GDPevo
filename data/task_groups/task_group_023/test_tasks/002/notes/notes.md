# test_002 construction and evaluation notes

## Current whole-point evaluation boundary / 当前整点评分边界

The final eight binary points use weights `[1,3,3,3,3,3,3,2]` and score, respectively: linked-cohort totals, GMM design dimensions, pooled ridge errors, restricted-null distributions, pooled conformal performance, the equal-strength tipping boundary, trajectory stability, and the controlled evidence classification. A point earns its entire `weight/21` only when the named required subcheck passes; otherwise zero. All other module fractions are unscored diagnostics.

最终八个二元评分点的权重为 `[1,3,3,3,3,3,3,2]`，依次评估：关联队列总量、GMM 设计维度、ridge 汇总误差、受限零假设分布、conformal 汇总表现、等强度临界边界、轨迹稳定性和受控证据分类。只有命名的必需子检查通过时，该点才获得完整 `weight/21`，否则为零。其他模块比例均为不计分诊断。

## English

### Protocol-transfer purpose

This held-out county mediation audit is paired with `train_002` through registered protocol `PHO_COUNTY_MEDIATION_TRANSPORT_V1`. The training request is the full computational SOP: it specifies difference-GMM construction and clustered cross-equation inference, ordered state deletion, nested state-blocked ridge fitting and selection, restricted-null paired-state bootstrap-t, state-grouped conformal calibration, signed partial-R2 sensitivity, and deterministic PCA/K-means/stability analysis. The test prompt and request now invoke that protocol instead of reproducing its implementation.

This makes the intended dependency real. A skill learned from `train_002` can transfer reusable solvers and serialization routines to this task, while a solver cannot obtain the hard-module implementation merely by transcribing duplicated test instructions. The protocol ID is explicit in both the prompt and `analysis_request.json`; every unoverridden convention is inherited from the paired SOP.

### Held-out facts and overrides retained

The solver-facing test input still supplies every fact that is specific to this independent analysis:

- the Web-only Public Health Observatory evidence source;
- Northeast and South counties for 2021–2024, with a 2024 primary analysis;
- depression, severe housing cost burden, and short sleep as outcome, exposure, and mediator;
- health and socioeconomic filters, revision selection, completeness definitions, linked primary/balanced/machine-learning cohorts, and row ordering;
- the primary OLS specifications, GMM change periods, change controls, period indicator, and task-variable lag instruments;
- the complete ordered base and sleep-augmented feature maps and the test-specific ridge grid;
- the three bootstrap target labels and the independent seed `23022024`;
- the held-out conformal source model and fixed lambda `10`;
- both held-out sensitivity ranges `[0.05, 0.10, 0.20, 0.30, 0.40]` and the task-specific baseline variables;
- trajectory years, source measures, and within-year feature order;
- four-decimal reporting, all six module thresholds, classification thresholds, and every requested output key and type.

The exact answer remains discoverable from public Web downloads plus the registered procedure. No cohort count, fitted coefficient, interval, selected hyperparameter, random-stream result, checkpoint value, state diagnostic, sensitivity result, PCA result, cluster, flag, or final classification is exposed by the test input.

### Transferable duplication removed

The test no longer restates protocol defaults already taught in `train_002`: difference-GMM matrix/weight construction; finite-sample cluster covariance, stacked covariance, delta inference, partial-F, and deletion refit conventions; ridge standardization, solver, inner/outer fold mechanics, pooled-error selection, and tie handling; bootstrap null construction, state-sign stream mechanics, replicate refits, quantile rules, and checkpoint schedule; conformal partition/rank/interval mechanics; sensitivity adjustment, direction/order, and tipping equations; or PCA scaling/sign, farthest-seed K-means, convergence, and ARI solver rules.

The answer template remains a schema rather than a second SOP. It preserves all output keys and types, but refers protocol-defined orders back to the registered protocol and task-specific orders back to the request.

### Fairness and task-specific exploration

The paired training scenario uses adult obesity, poverty, physical inactivity, a 2023 primary system, Midwest/South geography, a different predictor map, a different ridge grid, and a different random seed. This held-out scenario therefore requires new Web retrieval, publication reconciliation, cohorts, matrices, fits, resampling, sensitivity rows, and trajectories. Training covers how to perform the analysis, not what this task's answers are.

A generated skill is fair only if it carries generic protocol implementation and validation guidance. It must not contain this test task's counts, numerical results, state rows, seed outcomes, flags, or conclusion. That boundary creates useful few-shot transfer without leaking held-out gold.

### Contract and evaluator preservation

The rework changes only `test_tasks/002` solver-facing input and these notes. The recursive answer-template key contract is unchanged. The gold answer, evaluator scripts, eight rubric goals, raw weights `[1, 3, 3, 3, 3, 3, 3, 2]`, tolerances, and controlled decision are unchanged. The untouched gold answer still evaluates to exactly `1.0`.

## 中文

### 协议迁移目标

本留出县域中介审计通过注册协议 `PHO_COUNTY_MEDIATION_TRANSPORT_V1` 与 `train_002` 配对。训练请求承担完整计算 SOP：包括差分 GMM 构造与州聚类跨方程推断、按州删除、嵌套州分块 ridge 拟合与选择、受限零假设配对州 bootstrap-t、州分组 conformal 校准、带符号 partial-R2 敏感性，以及确定性 PCA/K-means/稳定性分析。测试提示和请求现在只调用该协议，不再重复实现。

这样形成真实迁移依赖：由 `train_002` 学得的 skill 可以迁移通用求解器与序列化能力，但求解者不能仅抄写测试中的重复步骤来获得困难模块实现。提示和 `analysis_request.json` 均明确给出协议 ID；未被覆盖的计算约定全部继承配对训练 SOP。

### 保留的留出事实与覆盖项

测试求解输入仍提供本独立分析所需的全部任务专属事实：

- 纯 Web Public Health Observatory 证据来源；
- 2021–2024 年 Northeast 与 South 县，2024 年主分析；
- 抑郁、严重住房成本负担与短睡眠分别作为结局、暴露与中介；
- 健康/社会经济筛选、修订选择、完整性定义、主/平衡/机器学习联动队列与行顺序；
- 主 OLS 规格、GMM 变化期、变化控制项、时期指示和任务变量滞后工具；
- 完整有序的基础及睡眠增强特征图和测试专属 ridge 网格；
- 三个 bootstrap 目标标签与独立种子 `23022024`；
- 留出 conformal 来源模型和固定 lambda `10`；
- 两个留出敏感性范围 `[0.05, 0.10, 0.20, 0.30, 0.40]` 及任务专属基线变量；
- 轨迹年份、来源指标与年内特征顺序；
- 四位小数报告、六个模块阈值、分类阈值，以及全部请求输出键与类型。

精确答案仍可由公开 Web 下载和注册流程独立计算。测试输入不暴露任何队列计数、拟合系数、区间、所选超参数、随机流结果、检查点值、州诊断、敏感性结果、PCA 结果、聚类、标志或最终分类。

### 移除的可迁移重复内容

测试不再重述 `train_002` 已教授的协议默认项：差分 GMM 矩阵/权重构造；有限样本聚类协方差、堆叠协方差、delta 推断、部分 F 与删州重拟合约定；ridge 标准化、求解器、内外折、汇总误差选择与并列处理；bootstrap 零假设施工、州符号随机流、重复拟合、分位数与检查点计划；conformal 分折/秩/区间机制；敏感性调整、方向/顺序与临界方程；以及 PCA 缩放/符号、最远种子 K-means、收敛与 ARI 求解规则。

答案模板只承担 schema，不再成为第二份 SOP。所有输出键与类型均保留；协议定义顺序回指注册协议，任务专属顺序回指分析请求。

### 公平性与任务专属探索

配对训练场景使用成人肥胖、贫困、身体活动不足、2023 主系统、Midwest/South 地理、不同预测特征图、不同 ridge 网格和不同随机种子。本留出场景必须重新完成 Web 数据获取、发布核对、队列、矩阵、拟合、重采样、敏感性行与轨迹分析。训练覆盖“如何做”，并不提供本题“答案是什么”。

生成 skill 仅可携带通用协议实现与验证指导，不得包含本测试题的计数、数值结果、州行、种子结果、标志或结论。该边界既产生有效 few-shot 迁移，也避免留出金标泄露。

### 契约与评测器保持

本次整改只修改 `test_tasks/002` 的求解输入和本说明。答案模板递归键契约不变；金标答案、评测脚本、八个评分目标、原始权重 `[1, 3, 3, 3, 3, 3, 3, 2]`、容差与受控决策均未改变。未修改的金标答案仍精确评分为 `1.0`。

## Lineage and construction record

- Scenario: `SCN_023_public_health_statistical_modeling_audit`.
- Source relevance: `E003` is the primary lineage for county long-table reconciliation, FIPS/RUCC discipline, dynamic models, and mediation; `E001` anchors confounding, clustered inference, sensitivity checks, and claim auditing; `E002` anchors standardized multivariate trajectories, PCA, clustering, and cross-source quality control.
- Task brief: perform a held-out county depression/housing-cost/sleep mediation audit with six independently reproducible modules and a controlled decision.
- Environment lineage: all health and socioeconomic publications come from the shared seeded Public Health Observatory Web portal. SQLite, generated files, seeds, manifests, and implementation code remain inside the environment container and are not solver-visible.
- Payload lineage: the request contains only held-out geography, measures, years, grids, seed, thresholds, and registered-protocol overrides; the template fixes types and controlled choices. No cohort count, coefficient, random checkpoint, cluster assignment, flag, or decision is supplied.
- Author: independent task-builder agent `/root/build_test_002`.
- Created: 2026-07-15.
- Updated: 2026-07-15.
- Major changes: long-horizon module expansion; procedural leakage removal; anti-dilution evaluator hardening; protocol-based train/test transfer; final lineage completion.

## 沿袭与构建记录

- 场景：`SCN_023_public_health_statistical_modeling_audit`。
- 来源关联：`E003` 是县级长表对账、FIPS/RUCC 纪律、动态模型和中介分析的主要沿袭；`E001` 提供混杂控制、聚类推断、敏感性检查和主张审计；`E002` 提供标准化多变量轨迹、PCA、聚类及跨来源质量控制。
- 任务简述：对留出的县级抑郁—住房成本—睡眠关系完成六个可独立复现模块的中介审计，并给出受控结论。
- 环境沿袭：全部健康与社会经济发布来自共享、固定种子的公共卫生观测站 Web 门户；SQLite、生成文件、种子、清单和实现代码均留在环境容器内，对求解者不可见。
- 载荷沿袭：请求只提供留出地域、指标、年份、网格、种子、门槛和注册协议覆盖项；模板固定类型与受控选项。队列数、系数、随机检查点、聚类、标志和结论均未提供。
- 作者：独立任务构建代理 `/root/build_test_002`。
- 创建日期：2026-07-15。
- 更新日期：2026-07-15。
- 主要变更：扩展长程模块；移除程序化泄漏；强化防元素稀释评分；建立协议式训练—测试迁移；补齐最终沿袭记录。
