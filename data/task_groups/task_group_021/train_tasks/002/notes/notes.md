# Train 002 — January Fuel Reconciliation

## English

### Problem and materials

This task reconciles January fuel transactions before reporting. It uses shared transaction, alias-reference, unit-conversion, FX, snapshot, schema, and query interfaces. Generated data includes duplicate snapshots, noisy descriptions, overlapping aliases, mixed units and currencies, invalid quantities, and expected-versus-actual class differences.

### Solution basis

Choose the certified business snapshot, deduplicate logical transactions, resolve aliases with effective dates and token boundaries, keep mismatch separate from unrecognized or ambiguous descriptions, quarantine invalid records, and normalize only eligible transactions. Apply the correct unit and certified FX references before asset, merchant, and ledger routing results are computed.

### Transfer value and pitfalls

The task anchors effective-time reference selection, longest valid alias matching, recognition-versus-mismatch semantics, retained-source controls, unit/FX normalization, and ledger disposition. Frequent errors use ingest time, substring matches, provisional rates, or include quarantined transactions in totals.

### Evaluation

Eight exact whole-point gates use weights `1,2,2,2,1,1,3,3`. Every deterministic subcheck for a point must pass; no within-point fraction is awarded. Missing or extra required structure invalidates the answer contract.

## 中文

### 问题与材料

本任务在报表发布前核对一月份燃油交易，使用共享交易、别名参考、单位换算、汇率、快照、模式和查询接口。生成数据包含重复快照、噪声描述、重叠别名、混合单位与币种、非法数量，以及预期类别与实际类别不一致。

### 解题依据

选择业务上已认证的快照，按逻辑交易去重，结合生效日期和词边界解析别名，区分类别不匹配、无法识别和歧义描述，隔离非法记录，仅对合格交易做单位与认证汇率换算，然后计算资产、商户和台账路由结果。

### 迁移价值与易错点

该题锚定生效时间参考选择、最长有效别名匹配、识别与不匹配语义、保留来源控制、单位/汇率归一化和台账处置。常见错误是使用摄取时间、子串匹配、临时汇率，或把隔离交易计入总额。

### 评测

八个精确整点门槛的权重为 `1,2,2,2,1,1,3,3`。一个评分点的全部确定性子检查必须通过，不提供点内比例得分。缺少或增加必需结构会违反答案契约。
