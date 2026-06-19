# GDPevo

Languages: [English](README.md) | [Chinese](README.zh.md)

**GDPevo** is a public benchmark for evaluating agent self-evolution on real business work. The release contains 120 tasks across 12 task groups in customer relationship management (CRM), enterprise resource planning (ERP), and Finance; each group has one shared business environment, 5 train tasks, and 5 held-out test tasks. For the full motivation, construction pipeline, and findings, read the [project blog](https://prism-shadow.github.io/GDPevo/blog.html).

## Evaluation Results

Accuracy is reported as `acc@3`, averaged over 12 task groups. Cost is reported in USD.

| Harness | Model | Thinking level | `base` acc@3 | `demo` acc@3 | `reflect` acc@3 | Accuracy lift | Cost change |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| Codex | GPT-5.5 | xhigh | 48.35% | 65.99% | 67.13% | +18.21 pp | -25.75% |
| Claude Code | Opus 4.8 | xhigh | 49.11% | 70.90% | 67.94% | +20.31 pp | -8.69% |
| Panofy | Opus 4.6 | high | 50.17% | 68.24% | 67.98% | +17.94 pp | +11.82% |

See the full experiment board in [`experiments/EXPERIMENT_BOARD.md`](experiments/EXPERIMENT_BOARD.md).

Per-task reports are under:

- [`experiments/codex_gpt5_5_xhigh/`](experiments/codex_gpt5_5_xhigh/)
- [`experiments/claude_code_opus_4_8_xhigh/`](experiments/claude_code_opus_4_8_xhigh/)
- [`experiments/panofy_claude_opus_4_6_high/`](experiments/panofy_claude_opus_4_6_high/)

## Repository Layout

| Path | Purpose |
| --- | --- |
| [`data/`](data/) | Released benchmark data, including task groups, shared environments, train/test tasks, reference answers, and rule-based evaluators. |
| [`experiments/`](experiments/) | Released evaluation results, reusable evaluation workspaces, report YAMLs, and the aggregate experiment board. |
| [`site/`](site/) | Public website and blog for the benchmark release. |

## How To Use This Repo

- Benchmark data: read the summary in [`data/DATA_BOARD.md`](data/DATA_BOARD.md), then inspect task groups under [`data/task_groups/`](data/task_groups/).
- Evaluation results: read [`experiments/EXPERIMENT_BOARD.md`](experiments/EXPERIMENT_BOARD.md), then open the per-task reports under the three experiment directories.
- Evaluation workspace: start from [`experiments/eval_workspace/`](experiments/eval_workspace/) to rerun or adapt the workflow. Each workspace contains its own guides, task group inputs, run artifacts, and report directory.
- Local site preview:

```bash
cd site
npm ci
npm run build
npm run preview
```

## Citation

```bibtex
@misc{gdpevo2026,
  title  = {GDPevo: Measuring agent self-evolution on real business work},
  author = {PrismShadow Team},
  year   = {2026},
  url    = {https://github.com/Prism-Shadow/GDPevo}
}
```
