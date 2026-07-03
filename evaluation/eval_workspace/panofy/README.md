# Evaluation Workspace — Panofy

This workspace evaluates **one task group** on the **Panofy agent platform**,
using `acc@3`, population `std@3`, and solver turn-count efficiency metrics across four conditions: `base`, `fewshot`, `self`, and
`reflect-3`.

You are the **main evaluation agent**. You run the evaluation by **calling the
Panofy SDK directly** (`train`, `predict`) and running each task's official
`eval/eval.sh` — there is no fixed driver to invoke. Write whatever small,
throwaway SDK / aggregation scripts you need under `scratch/`; the formal
outputs are the run records and the report.

The solver is a **trained agent reached over the SDK**. The agent **evolves from
the train tasks during training** — the training instruction tells it to learn
from them and get better at this family of tasks; nothing is extracted. So each
condition is a different **training setup** over the same input/output contract,
and the test-time call is `predict()`.

The trained agent runs remotely and **can make outbound HTTP requests**, so the
task environment is served at a **remote URL given at run time**; you put that
URL into every `predict()` input as `api_base_url`, and the agent fetches it
live exactly as a local solver would.

## Directories

| Path | Purpose |
| --- | --- |
| `guides/` | Workflow, the four conditions, metrics/scoring, report format |
| `task_group/` | The single official task group currently under evaluation |
| `agents/` | Notes / a small registry of the trained agent ids per condition/attempt |
| `runs/` | Per condition / test task / attempt: `func_input.json`, `answer.json`, `score.yaml`, `run_metadata.yaml` |
| `report/` | The final `report/<task_group_id>.yaml` |
| `scratch/` | Training materials you stage + any temporary SDK / aggregation scripts |

## Guides

Read in order before evaluating:

1. `guides/workflow.md` — the end-to-end train → predict → score → aggregate flow you drive
2. `guides/evolve_modes.md` — the four conditions, realised through training, and the information boundary
3. `guides/metric_and_scoring.md` — `acc@3`, population `std@3`, scoring via `eval/eval.sh`, and Panofy token/turn accounting
4. `guides/report_format.md` — the final report YAML

## Connection inputs (`.env`)

The hosted Panofy service and the task environment are remote. Put their
addresses in a `.env` file — copy `.env.example` to `.env` and fill in:

- `PANOFY_BASE_URL` — Panofy SDK base URL (e.g. a Railway URL)
- `PANOFY_API_KEY` — Panofy API key (`da_...`)
- `PANOFY_ENV_BASE_URL` — the remote task-environment API endpoint the agent fetches
- `PANOFY_JUDGE_PATH` — train-only judge endpoint path, default `/api/judge`
- `PANOFY_MODEL_ID` — optional, `PANOFY_PRO` (default) or `PANOFY_AIR`

`.env` is gitignored — never commit real keys; the values for a given run come
from the launch prompt. Load them before running your scripts, e.g.
`set -a && source .env && set +a`.

## Setup

Each workspace installs its own environment. Manage it with `uv` (the panofy
SDK needs Python ≥ 3.10). Install the SDK **from GitHub** — that copy carries
the fixed adapter; do not use the PyPI package:

```bash
uv venv --python 3.12
uv pip install "git+https://github.com/Prism-Shadow/panofy.git#subdirectory=python" pyyaml
```

Run any script you stage under `scratch/` with `uv run python scratch/<script>.py`.

## Launch Prompt

```text
Evaluate task_group/<task_group_id> on Panofy using README.md and guides/.
Panofy base URL: <url>   API key: <da_...>   Env API URL: <url>
Run all four conditions with acc@3/std@3 and write report/<task_group_id>.yaml.
```

## Boundaries

- You may read the whole task group to stage training materials, score, and
  aggregate — but a **test** `FUNC_INPUT` only ever carries `task_id`, `prompt`,
  `api_base_url`, and `answer_template`. Never the gold answer, the task notes,
  or the evaluator.
- Training materials follow `guides/evolve_modes.md`: `fewshot` may include
  train gold answers; `self` may not; `reflect-3` may use only train inputs plus
  train-only judge feedback during training. Never include any test task, test
  answer, note, evaluator source, or judge API usage instruction in test-time
  material.
- Mode-allowed training exposure is not contamination: for example, fewshot
  training may use train gold answers. Contamination is about forbidden material
  leaking into test-time inputs, instructions, responses, or run artifacts.
- The hosted agent only sees the **remote** env URL. Confirm that URL exposes
  the same public projection as `task_group/env` — do not expose hidden fields.
- Store every test call under a fresh `runs/<condition>/<task_id>/attempt_<nn>/`
  directory. If a test agent response or run artifact shows that forbidden
  material leaked into `FUNC_INPUT` or the test-time agent saw a test answer,
  note, evaluator, env source, judge instruction, disallowed train material, or
  another run's files, report it immediately, mark that attempt contaminated,
  exclude it from aggregation, and rerun the affected test with corrected input
  in a new clean run directory.
