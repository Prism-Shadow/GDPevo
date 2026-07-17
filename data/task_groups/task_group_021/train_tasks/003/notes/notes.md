# Train 003 — Q1 Maintenance Integrity

## English

### Problem and materials

This task certifies Q1 maintenance history before reliability modeling. Shared maintenance, snapshot, unit, catalog, schema, and query interfaces expose overlapping event sources with duplicate logical events, malformed timestamps, impossible values, mixed odometer units, and asset-level regressions.

### Solution basis

Select the certified snapshot by business status and cutoff, identify logical duplicates and their retained representatives, classify missing, parse, range, and sequence defects, normalize odometers, reconstruct reliable asset histories, and compute corrected distance and risk outputs only from the accepted population.

### Transfer value and pitfalls

The task anchors certified-snapshot selection, deterministic overlap retention, issue-class separation, reliable-predecessor logic, unit-normalized sequence testing, history routing, and corrected aggregation. Typical mistakes use filenames or ingestion recency, double-count overlaps, or treat a regression as an isolated range error.

### Evaluation

Eight exact whole-point gates use weights `2,2,3,2,3,2,2,1`. A point passes only when its complete deterministic business result is correct. Structural completeness is a prerequisite.

## 中文

### 问题与材料

本任务在可靠性建模前认证第一季度维修历史。共享维修、快照、单位、目录、模式和查询接口提供重叠事件来源，其中包含逻辑重复、时间戳解析错误、非法值、混合里程单位和资产级里程回退。

### 解题依据

按业务认证状态和截止时间选择快照，识别逻辑重复及保留记录，分别统计缺失、解析、范围和序列问题，统一里程单位，重建可靠的资产历史，只用合格事件计算修正里程与风险结果。

### 迁移价值与易错点

该题锚定认证快照选择、重叠来源的稳定保留、问题类型分离、可靠前驱逻辑、统一单位后的序列检查、历史路由和修正汇总。常见错误是按文件名或摄取新旧选来源、重复计数，或把回退误当成单行范围问题。

### 评测

八个精确整点门槛的权重为 `2,2,3,2,3,2,2,1`。只有完整确定性业务结果正确，评分点才通过；完整结构是前置条件。
