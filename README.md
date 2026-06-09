# GDPevo

Languages: [English](README.md) | [Chinese](README.zh.md)

GDPevo is a public benchmark for evaluating how agents learn and
transfer skills in real business production environments. Following the spirit
of real-world work evaluations such as GDPVal, the tasks are designed around
productivity-bearing office work rather than isolated puzzle prompts.

The benchmark focuses on three questions:

- Can agents complete long-horizon tasks in real business production environments?
- Can they learn reusable skills from train tasks and transfer them to related
  test tasks.
- Do those skills make downstream solving more accurate and less costly, as
  reflected by score, token, and cost metrics?

The released artifacts include executable task groups, evaluation reports,
generated skill packages, and a reusable evaluation workspace.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `data/task_groups/` | Released task groups with shared environments, train tasks, test tasks, answers, evaluators, and data notes. |
| `experiments/` | Released evaluation protocol, evaluation workspaces, result reports, generated skills, and experiment board. |
| `site/` | Static website and blog content for GitHub Pages. |
| `assets/` | Figures, logos, and visual assets used by released materials. |

## Data

Each task group contains one shared business environment, five train tasks, and
five test tasks. Train tasks are used to derive skills, and test tasks measure
whether those skills transfer to related tasks in the same environment.

See [data/task_groups/README.md](data/task_groups/README.md) for the task group
format.

## Experiments

The released evaluation run compares three conditions:

- `no_skill`
- `demonstration_skill`
- `reflection_skill`

Results are summarized in
[experiments/EXPERIMENT_BOARD.md](experiments/EXPERIMENT_BOARD.md).

See [experiments/README.md](experiments/README.md) for details.

## Evaluation Workspace

The reusable evaluation workspace is available at
[experiments/eval_workspace/](experiments/eval_workspace/). A Chinese mirror is
available at [experiments/eval_workspace_zh/](experiments/eval_workspace_zh/).
The workspace describes how to run `avg@3` evaluation with clean-context
skill-generation and solver agents, how to record token/time metrics, and how
to write the final report.
