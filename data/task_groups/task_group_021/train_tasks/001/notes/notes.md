# Train 001 — Partner Contact Certification

## English

### Problem and materials

This task certifies the partner-onboarding contact population before automated outreach. The solver receives a scope memo and output contract, then uses the shared contact, snapshot, catalog, schema, and query interfaces at `<TASK_ENV_BASE_URL>`. The large contact population is generated from overlapping source systems with duplicate identities, conflicting fields, explicit null markers, unusable channels, and late or stale evidence.

### Solution basis

Select evidence by business cutoff and source status, normalize email and phone keys, form identity clusters without name-only merging, choose deterministic master rows, and resolve each canonical field by the applicable source and verification precedence. Quarantine rows without a usable contact channel, apply consent only after canonicalization, and compute readiness and regional rollups from canonical entities.

### Transfer value and pitfalls

The task anchors contact-key normalization, survivor-versus-field selection, provenance controls, quarantine behavior, and post-merge readiness. Common failures are merging on names, using ingest order, applying consent before identity resolution, or counting raw rows as canonical entities.

### Evaluation

There are eight non-duplicate business points with raw weights `1,3,3,2,3,2,1,2`. Each point is an exact whole-point gate: all deterministic subchecks belonging to the stated goal must pass, or the point receives zero. The evaluator also requires the complete answer structure.

## 中文

### 问题与材料

本任务在自动触达前认证合作伙伴联系人主数据。解题者根据范围说明和输出契约，通过 `<TASK_ENV_BASE_URL>` 的联系人、快照、目录、模式和查询接口处理大规模重叠来源。数据包含重复身份、字段冲突、显式空值、不可用渠道以及迟到或陈旧证据。

### 解题依据

按业务截止时间和来源状态选证据，规范化邮箱与电话键，禁止仅凭姓名合并，确定稳定主记录，并按来源可信度与验证优先级逐字段取值。无可用联系方式的记录进入隔离；先完成实体合并，再判断同意状态和渠道就绪度；区域汇总按规范实体计算。

### 迁移价值与易错点

该题提供联系人键规范化、实体主记录与字段来源分离、来源追踪控制、隔离规则和合并后就绪判断等可迁移经验。常见错误包括按姓名合并、按摄取顺序选值、在身份解析前套用同意规则，以及把原始行数当作实体数。

### 评测

共有八个互不重复的业务评分点，原始权重为 `1,3,3,2,3,2,1,2`。每个评分点都是精确整点门槛：属于该目标的全部确定性子检查必须通过，否则该点为零。评测器同时要求完整答案结构。
