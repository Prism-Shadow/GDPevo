# Stage 1: Scenario Discovery

语言：[English](README.md) | [中文](README.zh.md)

## 工作内容

在这个工作区，你要根据给定业务场景搜寻可归并的来源数据集原始数据，并整理成场景数据。

提示语会给出 `<target_scenario>`。你需要围绕它搜寻并归并相关原始数据。

每个候选场景放在 `scenario/<scenario_id>/` 下，包含：

- `scenario.yaml`，说明共享业务场景和归入该场景的来源数据集原始数据；
- `notes/<example_id>.md`，解释每条原始数据，以及它为什么属于这个场景；
- 可选的 `attachments/<example_id>/`，存放后续构造会用到的原始来源文件。

## 工作区结构

```text
Stage_1_Scenario_Discovery/
├── README.md
├── README.zh.md
└── scenario/
    └── SCN_001_example_scenario/
        ├── scenario.yaml
        ├── notes/
        │   ├── E001.md
        │   └── E002.md
        └── attachments/
            ├── E001/
            │   └── example_input.md
            └── E002/
```

## 场景目录

每条场景使用 `scenario/` 下的一个独立目录，目录名应与 `scenario_id` 一致。

| 路径 | 用途 |
| --- | --- |
| `scenario.yaml` | 场景定义文件，记录场景信息和 `examples` 中的来源数据集原始数据。 |
| `notes/<example_id>.md` | 单条原始数据的数据说明文件。 |
| `attachments/<example_id>/` | 单条原始数据的附件目录；没有附件时可以省略。 |

## `scenario.yaml`

```yaml
scenario_id: SCN_001_example_scenario
name: Example Scenario
domain: Example Domain
description: |
  Describe the scenario background and shared business context.
examples:
  - example_id: E001
    name: Example A
    source: GDPval
    prompt: |
      Describe one concrete source task under this scenario.
    notes: notes/E001.md
    attachments:
      - attachments/E001/example_input.md
  - example_id: E002
    name: Example B
    source: SOP-Bench
    prompt: |
      Describe another concrete source task under this scenario.
    notes: notes/E002.md
    attachments: []
```

### 场景字段

| 字段 | 是否必需 | 说明 |
| --- | --- | --- |
| `scenario_id` | 是 | 全局唯一标识，建议格式为 `SCN_###_short_slug`。 |
| `name` | 是 | 场景名称。 |
| `domain` | 是 | 领域标签，例如 CRM、ERP 或 Finance。 |
| `description` | 是 | 多条原始数据共享的业务背景和上下文。 |
| `examples` | 是 | 归入该场景的来源数据集原始数据列表。 |

### Example 字段

| 字段 | 是否必需 | 说明 |
| --- | --- | --- |
| `example_id` | 是 | 场景内唯一标识，建议格式为 `E001`、`E002` 等。 |
| `name` | 是 | 原始数据名称。 |
| `source` | 是 | 来源数据集或来源说明。 |
| `prompt` | 是 | 原始 prompt 或概括后的原始任务文本，用于后续构造。 |
| `notes` | 是 | 指向 `notes/<example_id>.md` 的路径。 |
| `attachments` | 是 | 附件路径列表，路径相对于场景目录；没有附件时写 `[]`。 |

## Notes 要求

这里的 `example` 指来源数据集中的一条原始数据。每个 example 都应有对应的数据说明文件。Notes 用于支持后续数据构造、审核和评测，不是最终答案、评测脚本或正式任务文件。

Notes 不要求固定标题，但应说明：

- 来源信息，例如来源数据集、原始任务 ID、归档文件和领域标签；
- 原始任务背景、输入材料、关键步骤、约束和预期交付物；
- 为什么这条原始数据属于当前场景，包括业务流程、对象关系、数据流转或系统协同；
- 每个附件的作用，例如 metadata、verifier、CSV、PDF、Excel、SOP 或 policy 材料；
- 后续如何评测，例如关键字段、输出格式、计算结果、状态检查、容易失败的点和评测器设计依据；
- 构造记录，例如作者、创建时间、更新时间和主要变更。

## 提示语

```text
阅读 README.md，根据 <target_scenario> 搜寻来源数据集原始数据，并在 scenario/<scenario_id>/ 下写出场景数据。
```
