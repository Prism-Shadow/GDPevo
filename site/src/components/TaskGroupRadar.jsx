import { useEffect, useMemo, useRef, useState } from "react";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip
} from "recharts";
import { leaderboardModes, radarRuns, taskGroups } from "../content/benchmark.js";

const seriesColors = [
  "#77829a", "#2dab78", "#bc7613", "#4165cf",
  "#168b99", "#d05b63", "#7b61c9", "#d46f2c",
  "#16865b", "#5b78df", "#a85b9e", "#b99318",
  "#147b78", "#de5873", "#74853a", "#9068c8",
  "#2c87b8", "#c96c82", "#4b9368", "#c55c2a",
  "#6878d1", "#9d7040", "#3d9b88", "#b6538a"
];
const methodLabels = {
  none: "—",
  "skill-creator": "Skill Creator",
  "agent-training": "Agent Training"
};
const filterProperties = {
  runIds: "runId",
  harnesses: "harness",
  modes: "mode",
  methods: "method"
};

const copy = {
  en: {
    title: "Task-group performance explorer",
    subtitle: "Compare ACC profiles across task groups 001–012",
    builder: "Comparison filters",
    builderHint: "Select any combination. Empty groups mean no restriction.",
    model: "Model",
    harness: "Harness",
    source: "Evolution source",
    method: "Evolution method",
    all: "All",
    noMethod: "No evolution method",
    matches: "matching lines",
    quick: "Quick compare",
    modelModes: "Selected model · all sources",
    modelModesHint: "Select exactly one model first",
    allFewshot: "All models · fewshot",
    allReflect: "All models · reflect-3",
    active: "Lines on chart",
    clear: "Clear",
    empty: "Choose conditions or use a quick comparison to add radar lines.",
    average: "ACC",
    changeColor: "Change line color",
    remove: "Remove comparison line",
    accuracy: "ACC"
  },
  zh: {
    title: "任务组表现对比",
    subtitle: "比较任务组 001–012 上的 ACC 分布",
    builder: "对比条件",
    builderHint: "可以同时勾选多个条件；某组未勾选时表示不限。",
    model: "模型",
    harness: "Harness",
    source: "进化来源",
    method: "进化方法",
    all: "不限",
    noMethod: "无进化方法",
    matches: "条匹配曲线",
    quick: "快捷比较",
    modelModes: "所选模型 · 全部来源",
    modelModesHint: "请先只勾选一个模型",
    allFewshot: "全部模型 · fewshot",
    allReflect: "全部模型 · reflect-3",
    active: "当前曲线",
    clear: "清空",
    empty: "请选择实验条件，或使用快捷比较添加雷达曲线。",
    average: "ACC",
    changeColor: "调整曲线颜色",
    remove: "移除对比曲线",
    accuracy: "ACC"
  }
};

const experiments = radarRuns.flatMap((run) =>
  leaderboardModes.map((mode) => ({
    key: `${run.id}:${mode}`,
    runId: run.id,
    model: run.model,
    harness: run.harness,
    thinking: run.thinking,
    mode,
    method: mode === "base" ? "none" : run.method,
    scores: run.scores[mode]
  }))
);
const experimentMap = new Map(experiments.map((experiment) => [experiment.key, experiment]));
const experimentColorMap = new Map(experiments.map((experiment, index) => [
  experiment.key,
  seriesColors[index % seriesColors.length]
]));

function mean(values) {
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function matchesFilters(experiment, filters, ignoredField) {
  return Object.entries(filterProperties).every(([field, property]) =>
    field === ignoredField || filters[field].length === 0 || filters[field].includes(experiment[property])
  );
}

function seriesName(series) {
  return `${series.model} · ${series.harness} · ${series.mode}`;
}

function RadarAxisTick({ payload, x, y, textAnchor }) {
  return (
    <text className="radar-axis-label" dy="0.32em" textAnchor={textAnchor} x={x} y={y}>
      {payload.value}
    </text>
  );
}

function InteractiveRadarShape({
  fill,
  fillOpacity,
  onSelect,
  points,
  seriesKey,
  stroke,
  strokeOpacity,
  strokeWidth
}) {
  if (!points?.length) return null;
  const polygonPoints = points.map(({ x, y }) => `${x},${y}`).join(" ");

  return (
    <g>
      <polygon
        fill={fill}
        fillOpacity={fillOpacity}
        points={polygonPoints}
        pointerEvents="none"
        stroke={stroke}
        strokeLinejoin="round"
        strokeOpacity={strokeOpacity}
        strokeWidth={strokeWidth}
        vectorEffect="non-scaling-stroke"
      />
      <polygon
        className="radar-hit-target"
        data-series-key={seriesKey}
        fill="none"
        onClick={(event) => {
          event.stopPropagation();
          onSelect();
        }}
        points={polygonPoints}
        pointerEvents="stroke"
        stroke="transparent"
        strokeLinejoin="round"
        strokeWidth="10"
        vectorEffect="non-scaling-stroke"
      />
    </g>
  );
}

function RadarTooltip({ active, payload, lang }) {
  if (!active || !payload?.length) return null;
  const row = payload[0]?.payload;
  if (!row) return null;

  return (
    <div className={`radar-tooltip ${payload.length > 12 ? "is-dense" : ""}`}>
      <strong>{row.axis}</strong>
      <span>{row[`${lang}Name`]}</span>
      <div>
        {payload.map((entry) => (
          <p key={entry.dataKey}>
            <i style={{ background: entry.color }} />
            <span>{entry.name}</span>
            <b>{Number(entry.value).toFixed(2)}%</b>
          </p>
        ))}
      </div>
    </div>
  );
}

function FilterOption({ checked, disabled, label, meta, onChange }) {
  return (
    <label className={`radar-filter-option ${checked ? "is-checked" : ""} ${disabled ? "is-disabled" : ""}`}>
      <span>
        {label}
        {meta ? <small>{meta}</small> : null}
      </span>
      <input checked={checked} disabled={disabled} onChange={onChange} type="checkbox" />
      <i aria-hidden="true" />
    </label>
  );
}

export function TaskGroupRadar({ lang = "en" }) {
  const t = copy[lang] ?? copy.en;
  const defaultRun = radarRuns[0];
  const [filters, setFilters] = useState({ runIds: [defaultRun.id], harnesses: [], modes: [], methods: [] });
  const [selectedKeys, setSelectedKeys] = useState(
    leaderboardModes.map((mode) => `${defaultRun.id}:${mode}`)
  );
  const [colorOverrides, setColorOverrides] = useState({});
  const [focusedKey, setFocusedKey] = useState(null);
  const seriesRowRefs = useRef(new Map());

  const facetDefinitions = useMemo(() => [
    {
      field: "runIds",
      label: t.model,
      options: radarRuns.map((run) => ({ value: run.id, label: run.model, meta: run.thinking }))
    },
    {
      field: "harnesses",
      label: t.harness,
      options: [...new Set(radarRuns.map((run) => run.harness))].map((harness) => ({ value: harness, label: harness }))
    },
    {
      field: "modes",
      label: t.source,
      options: leaderboardModes.map((mode) => ({ value: mode, label: mode }))
    },
    {
      field: "methods",
      label: t.method,
      options: ["none", "skill-creator", "agent-training"].map((method) => ({
        value: method,
        label: method === "none" ? t.noMethod : methodLabels[method]
      }))
    }
  ], [t]);

  const matches = useMemo(
    () => experiments.filter((experiment) => matchesFilters(experiment, filters)),
    [filters]
  );
  const selectedSeries = selectedKeys.map((key) => experimentMap.get(key)).filter(Boolean);
  const styledSeries = selectedSeries.map((series, index) => ({
    ...series,
    color: colorOverrides[series.key] ?? experimentColorMap.get(series.key),
    dataKey: `series_${index}`,
    label: seriesName(series)
  }));
  const denseChart = styledSeries.length > 10;
  const renderedSeries = focusedKey
    ? [...styledSeries.filter((series) => series.key !== focusedKey), ...styledSeries.filter((series) => series.key === focusedKey)]
    : styledSeries;
  const chartData = taskGroups.slice(0, 12).map((group, groupIndex) => {
    const row = { axis: `TG${group.id}`, enName: group.en, zhName: group.zh };
    styledSeries.forEach((series) => {
      row[series.dataKey] = series.scores[groupIndex];
    });
    return row;
  });

  const toggleFilter = (field, value) => {
    setFilters((current) => ({
      ...current,
      [field]: current[field].includes(value)
        ? current[field].filter((item) => item !== value)
        : [...current[field], value]
    }));
  };
  const optionAvailable = (field, value) => experiments.some((experiment) =>
    experiment[filterProperties[field]] === value && matchesFilters(experiment, filters, field)
  );
  const compareSelectedModel = () => {
    if (filters.runIds.length !== 1) return;
    setFilters({ runIds: [filters.runIds[0]], harnesses: [], modes: [], methods: [] });
  };
  const compareModeAcrossModels = (mode) => {
    setFilters({ runIds: [], harnesses: [], modes: [mode], methods: [] });
  };
  const removeSeries = (key) => setSelectedKeys((current) => current.filter((item) => item !== key));
  const changeSeriesColor = (key, color) => {
    setColorOverrides((current) => ({ ...current, [key]: color }));
  };
  const toggleFocusedSeries = (key) => setFocusedKey((current) => current === key ? null : key);

  useEffect(() => {
    setSelectedKeys(matches.map((item) => item.key));
    setFocusedKey(null);
  }, [matches]);

  useEffect(() => {
    if (!focusedKey) return;
    if (!selectedKeys.includes(focusedKey)) {
      setFocusedKey(null);
      return;
    }
    seriesRowRefs.current.get(focusedKey)?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [focusedKey, selectedKeys]);

  return (
    <figure className="panel radar-explorer shown" id="chart">
      <figcaption className="panel-head radar-head">
        <span>
          <strong className="panel-title">{t.title}</strong>
          <small>{t.subtitle}</small>
        </span>
        <span className="radar-scale">0–100 · {t.accuracy}</span>
      </figcaption>

      <div className="radar-controls" aria-label={t.builder}>
        <div className="radar-control-heading">
          <strong>{t.builder}</strong>
          <span>{t.builderHint}</span>
        </div>
        <div className="radar-facets">
          {facetDefinitions.map((facet) => (
            <section className={`radar-facet radar-facet-${facet.field}`} key={facet.field}>
              <header>
                <strong>{facet.label}</strong>
                <button
                  type="button"
                  disabled={!filters[facet.field].length}
                  onClick={() => setFilters((current) => ({ ...current, [facet.field]: [] }))}
                >
                  {t.all}
                </button>
              </header>
              <div>
                {facet.options.map((option) => {
                  const checked = filters[facet.field].includes(option.value);
                  return (
                    <FilterOption
                      checked={checked}
                      disabled={!checked && !optionAvailable(facet.field, option.value)}
                      key={option.value}
                      label={option.label}
                      meta={option.meta}
                      onChange={() => toggleFilter(facet.field, option.value)}
                    />
                  );
                })}
              </div>
            </section>
          ))}
        </div>

        <div className="radar-command-bar">
          <div className="radar-match-row">
            <span>
              <b>{matches.length}</b> {t.matches}
            </span>
          </div>
          <div className="radar-quick">
            <strong>{t.quick}</strong>
            <button
              type="button"
              disabled={filters.runIds.length !== 1}
              title={filters.runIds.length === 1 ? undefined : t.modelModesHint}
              onClick={compareSelectedModel}
            >
              {t.modelModes}
            </button>
            <button type="button" onClick={() => compareModeAcrossModels("fewshot")}>{t.allFewshot}</button>
            <button type="button" onClick={() => compareModeAcrossModels("reflect-3")}>{t.allReflect}</button>
          </div>
        </div>
      </div>

      <div className="radar-body">
        <aside className="radar-active">
          <div className="radar-active-head">
            <strong>{t.active}</strong>
            <button type="button" onClick={() => setSelectedKeys([])} disabled={!selectedKeys.length}>{t.clear}</button>
          </div>
          <div className="radar-series-list">
            {styledSeries.map((series) => (
              <div
                className={`radar-series-row ${focusedKey === series.key ? "is-focused" : ""}`}
                key={series.key}
                ref={(node) => {
                  if (node) seriesRowRefs.current.set(series.key, node);
                  else seriesRowRefs.current.delete(series.key);
                }}
              >
                <label
                  className="radar-color-picker"
                  title={`${t.changeColor}: ${series.label}`}
                >
                  <input
                    aria-label={`${t.changeColor}: ${series.label}`}
                    onInput={(event) => changeSeriesColor(series.key, event.currentTarget.value)}
                    type="color"
                    value={series.color}
                  />
                  <i aria-hidden="true" style={{ background: series.color }} />
                </label>
                <button
                  aria-pressed={focusedKey === series.key}
                  className="radar-series-select"
                  onClick={() => toggleFocusedSeries(series.key)}
                  type="button"
                >
                  <span>
                    <strong>{series.model} · {series.mode}</strong>
                    <small>{series.harness} · {methodLabels[series.method]} · {t.average} {mean(series.scores).toFixed(2)}%</small>
                  </span>
                </button>
                <button
                  className="radar-series-remove"
                  type="button"
                  title={t.remove}
                  aria-label={`${t.remove}: ${series.label}`}
                  onClick={() => removeSeries(series.key)}
                >×</button>
              </div>
            ))}
          </div>
        </aside>

        <div className="radar-stage">
          {styledSeries.length ? (
            <ResponsiveContainer width="100%" height="100%" minHeight={500}>
              <RadarChart data={chartData} margin={{ top: 36, right: 48, bottom: 36, left: 48 }} outerRadius="72%">
                <PolarGrid gridType="polygon" stroke="var(--line)" />
                <PolarAngleAxis dataKey="axis" tick={<RadarAxisTick />} tickLine={false} />
                <PolarRadiusAxis
                  angle={90}
                  axisLine={false}
                  domain={[0, 100]}
                  tick={{ fill: "var(--muted)", fontSize: 10 }}
                  tickCount={5}
                  tickFormatter={(value) => value === 100 ? "" : value}
                />
                <Tooltip
                  content={<RadarTooltip lang={lang} />}
                  cursor={false}
                  wrapperStyle={{ pointerEvents: "auto" }}
                />
                {renderedSeries.map((series) => {
                  const isFocused = focusedKey === series.key;
                  const isMuted = Boolean(focusedKey) && !isFocused;
                  return (
                  <Radar
                    dataKey={series.dataKey}
                    dot={isFocused
                      ? { fill: series.color, r: 3.4, stroke: "var(--surface)", strokeWidth: 1.4 }
                      : denseChart || isMuted ? false : { fill: series.color, r: 2.2, strokeWidth: 0 }}
                    fill={series.color}
                    fillOpacity={isFocused ? 0.12 : isMuted ? 0.004 : denseChart ? 0.015 : 0.045}
                    isAnimationActive={false}
                    key={series.key}
                    name={series.label}
                    shape={(shapeProps) => (
                      <InteractiveRadarShape
                        {...shapeProps}
                        onSelect={() => toggleFocusedSeries(series.key)}
                        seriesKey={series.key}
                      />
                    )}
                    stroke={series.color}
                    strokeOpacity={isFocused ? 1 : isMuted ? 0.16 : denseChart ? 0.82 : 1}
                    strokeWidth={isFocused ? 4 : isMuted ? 1 : denseChart ? 1.45 : 2.2}
                  />
                  );
                })}
              </RadarChart>
            </ResponsiveContainer>
          ) : (
            <div className="radar-empty">{t.empty}</div>
          )}
        </div>
      </div>
    </figure>
  );
}
