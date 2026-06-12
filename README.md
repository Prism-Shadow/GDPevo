# GDPevo

Languages: [English](README.md) | [Chinese](README.zh.md)

GDPevo is a public benchmark for evaluating self-evolving agents on
economically valuable, real business tasks. To our knowledge, it is the first
GDP-valued benchmark that treats agent evaluation as a stateful process: an
agent first works through related train tasks, turns experience into reusable
skills, and is then evaluated on held-out tasks from the same business
environment.

Most agent benchmarks still evaluate stateless task completion. GDPevo instead
asks whether agents can improve through experience: can they learn business
rules, source precedence, operating procedures, and output discipline from
earlier work, and can that learning make later work more accurate and cheaper
to execute?

The benchmark can be used to evaluate:

- self-evolving or continual-learning agents;
- skill creators and skill optimizers;
- end-to-end agent memory systems.

The first release contains 120 tasks organized into 12 task groups. Each task
group has one shared business environment, five train tasks, and five test
tasks. The task groups are constructed from economically meaningful industry
workflows, including finance, enterprise CRM, and ERP automation.

In the released Codex GPT-5.5 xhigh run, evolved agents improve accuracy by
18.21 percentage points on average after inductive learning, while reducing
token cost by 25.75% on average. The released artifacts include executable task
groups, evaluation reports, generated skill packages, and a reusable evaluation
workspace that can automate the full scoring flow.

## Repository Layout

| Path | Purpose |
| --- | --- |
| `data/` | Released task group data, data board, shared environments, train/test tasks, answers, evaluators, and data notes. |
| `experiments/` | Released evaluation protocol, evaluation workspaces, result reports, generated skills, and experiment board. |
| `site/` | GitHub Pages scaffold and public site assets. |
| `assets/` | Figures, logos, and visual assets used by released materials. |

## Data

Each task group contains one shared business environment, five train tasks, and
five test tasks. Train tasks provide the experience source, and test tasks
measure whether the resulting skills improve later work in the same business
environment.

Released task groups are summarized in [data/DATA_BOARD.md](data/DATA_BOARD.md).
See [data/README.md](data/README.md) for the data layout and task group format.

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
The workspace describes how Codex can run the full evaluation workflow with
clean-context skill-generation and solver agents, aggregate `avg@3`, record
token and cost metrics, and write the final report.
