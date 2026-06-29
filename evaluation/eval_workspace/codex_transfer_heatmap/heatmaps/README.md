# Heatmaps

After all 12 off-diagonal cell reports are complete, run this command from the workspace
root:

```bash
python3 scripts/build_heatmaps.py
```

Outputs:

```text
heatmaps/index.html
heatmaps/data/matrices.json
heatmaps/data/fewshot_matrix.csv
heatmaps/data/reflect-3_matrix.csv
```

`index.html` is a screenshot-ready single-page render containing the `fewshot`
and `reflect-3` 3x3 heatmaps.
