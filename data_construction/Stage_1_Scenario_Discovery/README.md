# Stage 1: Scenario Discovery

Languages: [English](README.md) | [Chinese](README.zh.md)

## What To Do

Use this workspace to collect raw data items from source benchmark datasets that fit a given business scenario, then write them as scenario data.

The prompt provides `<target_scenario>`. Use it to search and group relevant raw data.

For each candidate scenario, create `scenario/<scenario_id>/` with:

- `scenario.yaml`, describing the shared business scenario and grouped raw source data;
- `notes/<example_id>.md`, explaining each raw data item and why it belongs to the scenario;
- optional `attachments/<example_id>/`, storing source files from the original dataset when needed for later construction.

## Workspace Layout

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

## Scenario Directory

Each scenario uses one directory under `scenario/`. The directory name should match `scenario_id`.

| Path | Purpose |
| --- | --- |
| `scenario.yaml` | Scenario definition, including scenario metadata and raw source data in `examples`. |
| `notes/<example_id>.md` | Notes for one raw source-data item. |
| `attachments/<example_id>/` | Optional source files for one raw data item. Omit it when there are no attachments. |

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

### Scenario Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `scenario_id` | Yes | Globally unique ID, preferably `SCN_###_short_slug`. |
| `name` | Yes | Scenario name. |
| `domain` | Yes | Domain label, such as CRM, ERP, or Finance. |
| `description` | Yes | Shared context across the raw data items. |
| `examples` | Yes | Raw source-dataset data items grouped under this scenario. |

### Example Fields

| Field | Required | Meaning |
| --- | --- | --- |
| `example_id` | Yes | Scenario-local ID, preferably `E001`, `E002`, etc. |
| `name` | Yes | Raw data item name. |
| `source` | Yes | Source dataset or source note. |
| `prompt` | Yes | Original prompt or summarized raw task text for later construction. |
| `notes` | Yes | Path to `notes/<example_id>.md`. |
| `attachments` | Yes | List of attachment paths relative to the scenario directory; use `[]` when empty. |

## Notes Requirements

Each `example` means one raw data item from a source dataset. Each example should have a notes file. Notes support later construction, review, and evaluation; they are not final answers, evaluators, or task files.

The notes do not need a fixed heading structure, but they should explain:

- source information, such as source dataset, original task ID, archived files, and domain label;
- the original task background, input materials, key steps, constraints, and expected deliverable;
- why this raw data item belongs to the scenario, including business process, object relationships, data movement, or system coordination;
- what each attachment is for, such as metadata, verifier, CSV, PDF, spreadsheet, SOP, or policy material;
- how the future task could be evaluated, including key fields, output shape, computed results, state checks, likely failure modes, and evaluator design;
- construction provenance, including author, creation time, update time, and major changes when available.

## Prompt

```text
Read README.md, search raw data in source benchmark datasets according to <target_scenario>, and write scenario data under scenario/<scenario_id>/.
```
