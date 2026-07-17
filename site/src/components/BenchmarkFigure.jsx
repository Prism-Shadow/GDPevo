import { useMemo, useState } from "react";
import { leaderboardDataset, leaderboardModes } from "../content/benchmark.js";
import { blogBenchmark } from "../content/blog.js";
import { Lang } from "../lib/i18n.jsx";

const benchmarkMetrics = [
  {
    key: "acc",
    label: { en: "ACC@3", zh: "准确率" },
    direction: "desc",
    max: 100,
    display: (value) => `${value.toFixed(2)}%`
  },
  {
    key: "lift",
    label: { en: "LIFT", zh: "准确率提升" },
    direction: "desc",
    display: (value) => (value === 0 ? "—" : `+${value.toFixed(2)} pp`)
  },
  {
    key: "cost",
    label: { en: "COST", zh: "费用" },
    direction: "asc",
    display: (value) => `$${value < 0.1 ? value.toFixed(3) : value.toFixed(2)}`
  },
  {
    key: "rounds",
    label: { en: "ROUNDS", zh: "轮次" },
    direction: "asc",
    display: (value) => value.toFixed(2)
  },
  {
    key: "tokens",
    label: { en: "TOKENS", zh: "令牌数" },
    direction: "asc",
    display: (value) => `${value.toFixed(1)}k`
  }
];

const methodLabels = {
  "skill-creator": "Skill Creator",
  "agent-training": "Agent Training"
};

function compareRows(left, right, sort) {
  const valueDelta = left[sort.key] - right[sort.key];
  if (valueDelta !== 0) return sort.direction === "asc" ? valueDelta : -valueDelta;
  return `${left.model}-${left.mode}`.localeCompare(`${right.model}-${right.mode}`);
}

export function BenchmarkFigure({ className = "", modeLabels = {}, caption = blogBenchmark.caption }) {
  const [sort, setSort] = useState({ key: "acc", direction: "desc" });
  const dataset = leaderboardDataset;
  const versionRows = dataset.rows;
  const activeMetric = benchmarkMetrics.find((metric) => metric.key === sort.key) ?? benchmarkMetrics[0];
  const activeMax = activeMetric.max
    ?? Math.max(...versionRows.map((row) => Math.abs(row[activeMetric.key])), 1);
  const orderedMetrics = [
    activeMetric,
    ...benchmarkMetrics.filter((metric) => metric.key !== activeMetric.key)
  ];
  const modeLabel = (mode) => modeLabels[mode] ?? mode;
  const rows = useMemo(
    () => [...versionRows].sort((left, right) => compareRows(left, right, sort)),
    [sort, versionRows]
  );

  const selectMetric = (metric) => {
    setSort((current) => ({
      key: metric.key,
      direction:
        current.key === metric.key
          ? current.direction === "asc" ? "desc" : "asc"
          : metric.direction
    }));
  };

  return (
    <figure className={["blog-benchmark-figure", "blog-leaderboard", className].filter(Boolean).join(" ")}>
      <figcaption className="blog-benchmark-head">
        <div className="blog-benchmark-copy">
          <strong>
            <Lang en="GDPevo Benchmark Leaderboard" zh="GDPevo 评测排行榜" />
          </strong>
          <span>
            <Lang {...caption} />
            <em className="blog-benchmark-range">
              <Lang
                en={`task groups ${dataset.taskRange}`}
                zh={`任务组 ${dataset.taskRange}`}
              />
            </em>
          </span>
        </div>
        <div className="blog-benchmark-actions">
          <span className="blog-benchmark-legend" aria-label="Chart legend">
            {leaderboardModes.map((mode) => (
              <i key={mode}>
                <b className={`sw sw-${mode}`} />
                {modeLabel(mode)}
              </i>
            ))}
          </span>
        </div>
      </figcaption>

      <div className="blog-benchmark-table" id="gdpevo-leaderboard">
        <table>
          <thead>
            <tr>
              <th className="rank-column" scope="col">#</th>
              <th className="model-column" scope="col">
                <Lang en="Model" zh="模型" />
              </th>
              <th className="harness-column" scope="col">Harness</th>
              <th className="mode-column" scope="col">
                <Lang en="Evolution source" zh="进化来源" />
              </th>
              <th className="method-column" scope="col">
                <Lang en="Evolution method" zh="进化方法" />
              </th>
              {orderedMetrics.map((metric) => {
                const isActive = metric.key === activeMetric.key;
                return (
                  <th
                    className={["metric-column", isActive ? "is-active" : ""].filter(Boolean).join(" ")}
                    scope="col"
                    key={metric.key}
                    aria-sort={isActive ? (sort.direction === "asc" ? "ascending" : "descending") : "none"}
                  >
                    <button type="button" onClick={() => selectMetric(metric)}>
                      <span className="metric-heading">
                        <Lang {...metric.label} />
                        <span className="sort-arrow" aria-hidden="true">
                          {isActive ? (sort.direction === "asc" ? "↑" : "↓") : "↕"}
                        </span>
                      </span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr className={`mode-${row.mode}`} key={row.id}>
                <td className="rank-column">
                  <span className={index < 3 ? `rank rank-${index + 1}` : "rank"}>{index + 1}</span>
                </td>
                <th className="model-column" scope="row">
                  <strong>{row.model}</strong>
                  <small>{row.thinking}</small>
                </th>
                <td className="harness-column">{row.harness}</td>
                <td className="mode-column">
                  <code>
                    <i aria-hidden="true" />
                    {modeLabel(row.mode)}
                  </code>
                </td>
                <td className="method-column">
                  {row.mode === "base" ? "-" : methodLabels[row.method]}
                </td>
                {orderedMetrics.map((metric) => {
                  const isActive = metric.key === activeMetric.key;
                  return (
                    <td
                      className={["metric-column", isActive ? "is-active" : ""].filter(Boolean).join(" ")}
                      key={metric.key}
                    >
                      {isActive ? (
                        <div className="leaderboard-measure">
                          <div className="leaderboard-track" aria-hidden="true">
                            <span style={{ "--w": `${(Math.abs(row[metric.key]) / activeMax) * 100}%` }} />
                          </div>
                          <b>{metric.display(row[metric.key])}</b>
                        </div>
                      ) : (
                        <span className="metric-value">{metric.display(row[metric.key])}</span>
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
