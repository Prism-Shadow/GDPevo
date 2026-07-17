# Train 004 — Field-Service Contact Readiness

## English

### Problem and materials

This task merges field-service personnel evidence and certifies dispatchable contact channels. The shared contact environment contains HR, dispatch, and directory records with duplicate people, recycled identifiers, shared contacts, conflicting field values, source timestamps, and consent states.

### Solution basis

Normalize identifiers, prohibit name-only merges, distinguish contested identifiers from valid memberships, choose master IDs independently from field-level values, apply source and verification precedence, then determine dispatchability and depot readiness from canonical contact and consent state.

### Transfer value and pitfalls

The task independently reinforces the contact SOP from train 001 in a different population. It emphasizes recycled-identifier containment, canonical field provenance, outreach controls, and readiness after merge. Common errors merge households or co-workers, inherit a survivor's entire row, or count a contact channel that consent blocks.

### Evaluation

Eight exact whole-point gates use weights `1,3,3,2,2,2,2,1`. Every point earns its complete normalized weight or zero, based on all deterministic subchecks for that business outcome.

## 中文

### 问题与材料

本任务合并现场服务人员证据并认证可调度联系方式。共享联系人环境包含人力、调度和目录记录，数据具有重复人员、回收标识符、共享联系方式、字段冲突、来源时间戳和同意状态。

### 解题依据

规范化标识符，禁止仅按姓名合并，区分争议标识符与有效成员关系，将主实体选择与逐字段规范值选择分开，应用来源与验证优先级，再根据规范联系方式和同意状态判断可调度性及站点就绪度。

### 迁移价值与易错点

该题在不同人员群体中独立强化 train 001 的联系人方法，重点是回收标识符隔离、字段来源追踪、触达控制和合并后就绪判断。常见错误是合并家庭成员或同事、整行继承主记录，或把被同意规则禁止的渠道计为可用。

### 评测

八个精确整点门槛的权重为 `1,3,3,2,2,2,2,1`。每个评分点根据该业务结果的全部确定性子检查，只能获得完整归一化分数或零分。
