# Heatmaps

运行完全部 12 个非对角线 cell reports 后，在工作区根目录执行：

```bash
python3 scripts/build_heatmaps.py
```

输出：

```text
heatmaps/index.html
heatmaps/data/matrices.json
heatmaps/data/fewshot_matrix.csv
heatmaps/data/reflect-3_matrix.csv
```

`index.html` 是截图用的单页 HTML，包含 `fewshot` 和 `reflect-3` 两张 3x3 热力图。
