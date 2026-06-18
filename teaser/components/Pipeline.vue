<template>
  <div class="diagram">
    <div class="title">GDPevo Data Pipeline</div>
    <div class="subtitle">From real-job seeds to a graded benchmark — in four steps.</div>

    <div class="rail">

      <!-- ============ CARD 1 ============ -->
      <article class="card s1">
        <div class="num">1</div>
        <div class="head">
          <span class="hdot"></span>
          <span class="step">Scenario Seed</span>
        </div>
        <h4 class="lead">Real-job seeds.</h4>
        <p class="desc">Pull seed scenarios from real-work benchmarks — one scenario, several worked examples per source.</p>
        <div class="visual">
          <div class="chips">
            <span class="chip"><Doc class="ci" :c="B"/>GDPval</span>
            <span class="chip"><Doc class="ci" :c="B"/>SOP-Bench</span>
            <span class="chip"><Doc class="ci" :c="B"/>JobBench</span>
            <span class="chip chip-dots">···</span>
          </div>
        </div>
        <div class="out"><span class="out-k">output</span><span class="out-v">seed scenarios and examples</span></div>
      </article>

      <Connector :c="GREY" label="spawn"/>

      <!-- ============ CARD 2 ============ -->
      <article class="card s2">
        <div class="num">2</div>
        <div class="head">
          <span class="hdot"></span>
          <span class="step">Multi-Agent Task Factory</span>
        </div>
        <h4 class="lead">A team of agents grows each seed into task groups.</h4>
        <p class="desc">A <b>main agent</b> writes the blueprint; an <b>env builder</b> assembles the shared sandbox; <b>10 task agents</b> author 5 train + 5 test tasks; <b>calibrators</b> tune difficulty so <i>demo/reflect</i> clearly outperforms <i>base</i>.</p>
        <div class="visual">
          <div class="actors">
            <span class="actor"><Robot class="ai" :c="G"/>main</span>
            <span class="plus">+</span>
            <span class="actor"><Robot class="ai" :c="G"/>env</span>
            <span class="actor"><Robot class="ai" :c="G"/>×10 task</span>
            <span class="plus">+</span>
            <span class="actor"><Robot class="ai" :c="G"/>calibrate</span>
          </div>
        </div>
        <div class="out"><span class="out-k">output</span><span class="out-v">12 groups: env + 5 train/tests + evaluators</span></div>
      </article>

      <Connector :c="GREY" label="check"/>

      <!-- ============ CARD 3 ============ -->
      <article class="card s3">
        <div class="num">3</div>
        <div class="head">
          <span class="hdot"></span>
          <span class="step">Quality Review</span>
        </div>
        <h4 class="lead">Six clean-context reviewers vote.</h4>
        <p class="desc">Each reviewer audits one group end-to-end: <b>structure</b>, <b>completeness</b>, <b>file presence</b>, and whether <b>hidden rules</b> were planted (the antidote to lazy "I'm done" agents).</p>
        <div class="visual">
          <div class="vote">
            <div class="bots-row">
              <Robot class="rbot" :c="O"/>
              <Robot class="rbot" :c="O"/>
              <Robot class="rbot" :c="O"/>
              <Robot class="rbot" :c="O"/>
              <Robot class="rbot" :c="O"/>
              <Robot class="rbot" :c="O"/>
            </div>
            <div class="vote-x">
              <div class="vote-num">5 / 6</div>
              <div class="vote-lab">must pass</div>
            </div>
          </div>
        </div>
        <div class="out"><span class="out-k">output</span><span class="out-v">verified 12 groups</span></div>
      </article>

      <Connector :c="GREY" label="release"/>

      <!-- ============ CARD 4 ============ -->
      <article class="card s4">
        <div class="num">4</div>
        <div class="head">
          <span class="hdot"></span>
          <span class="step">Evaluation</span>
        </div>
        <h4 class="lead">Run 12 groups × 3 modes.</h4>
        <p class="desc">Score each agent in <b>base</b>, <b>demo</b>, and <b>reflect</b> modes across all 12 task groups, then report three numbers.</p>
        <div class="visual">
          <div class="metrics">
            <span class="metric"><BarChart class="mi" :c="R"/><span class="mtxt"><b>avg@3</b><br><small>accuracy</small></span></span>
            <span class="metric"><Database class="mi" :c="R"/><span class="mtxt"><b>tokens</b><br><small>usage</small></span></span>
            <span class="metric"><Dollar class="mi" :c="R"/><span class="mtxt"><b>cost</b><br><small>in USD</small></span></span>
          </div>
        </div>
        <div class="out"><span class="out-k">output</span><span class="out-v">eval results</span></div>
      </article>

    </div>

    <!-- feedback arc: from below card 3 back UP into card 2; arrowhead points up at card 2 -->
    <div class="arc-wrap">
      <span class="arc-label">fail → revise</span>
      <svg class="arc" viewBox="0 0 1588 80" fill="none" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="none">
        <!-- start at card 3 bottom-center (x≈1000), go down then curve left, end at card 2 bottom-center (x≈587) pointing up -->
        <path d="M 1000 0 V 22 C 1000 46, 940 50, 880 50
                 L 700 50 C 632 50, 587 46, 587 22 V 6"
              stroke="#0a7a52" stroke-width="3" fill="none" stroke-linecap="round"/>
        <!-- arrowhead at (587, 0) pointing UP into card 2 -->
        <path d="M 587 0 l 8 12 l -16 0 z" fill="#0a7a52"/>
      </svg>
    </div>
  </div>
</template>

<script setup>
import { h } from 'vue'
const B = '#1452d8', G = '#10a36e', O = '#f97316', R = '#dc2626', GREY = '#6b7280'

const wrap = (children) => (p) => h('svg', { viewBox: '0 0 24 24', fill: 'none', stroke: p.c, 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, children())

const Doc = wrap(() => [
  h('path', { d: 'M7 3h7l4 4v14H7z' }), h('path', { d: 'M14 3v4h4' }),
  h('path', { d: 'M10 12h5M10 15.5h5M10 9h2' }),
])
const Robot = wrap(() => [
  h('rect', { x: 5, y: 8, width: 14, height: 11, rx: 2 }),
  h('path', { d: 'M12 8V4.5' }), h('circle', { cx: 12, cy: 3.2, r: 1.4, fill: 'currentColor', stroke: 'none' }),
  h('circle', { cx: 9.3, cy: 13, r: 1.3, fill: 'currentColor', stroke: 'none' }),
  h('circle', { cx: 14.7, cy: 13, r: 1.3, fill: 'currentColor', stroke: 'none' }),
  h('path', { d: 'M9.5 16.5h5' }),
  h('path', { d: 'M5 12H3M21 12h-2' }),
])
const Wrench = wrap(() => [
  h('path', { d: 'M15.5 6.2a4 4 0 0 0-5.3 5.3L4.5 17.2 6.8 19.5l5.7-5.7a4 4 0 0 0 5.3-5.3l-2.6 2.6-2.3-2.3 2.6-2.6z' }),
])
const Sliders = wrap(() => [
  h('line', { x1: 4, y1: 8, x2: 20, y2: 8 }), h('circle', { cx: 9, cy: 8, r: 2.3, fill: '#fff' }),
  h('line', { x1: 4, y1: 16, x2: 20, y2: 16 }), h('circle', { cx: 15, cy: 16, r: 2.3, fill: '#fff' }),
])
const People = (p) => h('svg', { viewBox: '0 0 96 32', fill: p.c, stroke: 'none' },
  Array.from({length: 6}, (_, i) => h('g', { transform: `translate(${i * 16},0)`, key: i }, [
    h('circle', { cx: 8, cy: 9, r: 4 }),
    h('path', { d: 'M2 26c0-3.3 2.7-6 6-6s6 2.7 6 6z' }),
  ])))
const BarChart = (p) => h('svg', { viewBox: '0 0 24 24', fill: p.c, stroke: 'none' }, [
  h('rect', { x: 3, y: 13, width: 4, height: 8, rx: 1 }),
  h('rect', { x: 10, y: 7, width: 4, height: 14, rx: 1 }),
  h('rect', { x: 17, y: 10, width: 4, height: 11, rx: 1 }),
])
const Database = wrap(() => [
  h('ellipse', { cx: 12, cy: 5.2, rx: 7.5, ry: 2.8 }),
  h('path', { d: 'M4.5 5.2v13.6c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8V5.2' }),
  h('path', { d: 'M4.5 12c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8' }),
])
const Dollar = wrap(() => [
  h('circle', { cx: 12, cy: 12, r: 9 }),
  h('path', { d: 'M15 8.7c-.8-1-2-1.5-3.2-1.5-1.7 0-3 .9-3 2.3 0 3.1 6.2 1.5 6.2 4.7 0 1.5-1.4 2.6-3.2 2.6-1.3 0-2.6-.6-3.4-1.7M12 5.2v13.6' }),
])

const Connector = (p) => h('div', { class: 'connector' }, [
  h('div', { class: 'cn-label' }, p.label),
  h('svg', { class: 'cn-svg', viewBox: '0 0 60 28', fill: 'none' }, [
    h('path', { d: 'M2 14 H46', stroke: '#9ca3af', 'stroke-width': 3, 'stroke-linecap': 'round' }),
    h('path', { d: 'M44 6 L58 14 L44 22 Z', fill: '#9ca3af' }),
  ]),
])
</script>

<style scoped>
.diagram, .diagram * { box-sizing: border-box; }
.diagram {
  width: 1640px;
  font-family: Inter, "Segoe UI", system-ui, sans-serif;
  color: #1f2937;
  padding: 18px 26px 28px;
  background: #fff;
}
.title { text-align: center; font-size: 42px; font-weight: 800; letter-spacing: -0.5px; margin: 0 0 6px; color: #111; }
.subtitle { text-align: center; font-size: 18px; color: #6b7280; margin: 0 0 24px; font-weight: 500; }

.rail { display: flex; align-items: stretch; gap: 0; }

.connector { display: flex; flex-direction: column; align-items: center; justify-content: center; flex: none; padding: 0 6px; min-width: 64px; }
.cn-label { font-size: 13px; color: #9ca3af; font-weight: 600; letter-spacing: 0.4px; text-transform: uppercase; margin-bottom: 4px; }
.cn-svg { width: 60px; height: 28px; }

.card {
  flex: 1; min-width: 0;
  background: #fff;
  border: 1.5px solid #e5e7eb;
  border-top: 5px solid var(--c);
  border-radius: 14px;
  padding: 18px 20px 14px;
  display: flex; flex-direction: column;
  box-shadow: 0 1px 0 #f3f4f6, 0 8px 24px -16px rgba(15,23,42,.18);
  position: relative;
}
.s1 { --c: #1452d8; --soft: #e9f0ff; --ink: #143f9e; }
.s2 { --c: #10a36e; --soft: #e7f6ef; --ink: #0a7a52; }
.s3 { --c: #f97316; --soft: #fff1e6; --ink: #c2410c; }
.s4 { --c: #dc2626; --soft: #fde8e8; --ink: #991b1b; }

.num {
  position: absolute; top: -18px; left: 22px;
  width: 38px; height: 38px; border-radius: 50%;
  background: var(--c); color: #fff;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 19px;
  box-shadow: 0 4px 12px -4px rgba(0,0,0,.25);
}
.head { display: flex; align-items: center; gap: 8px; margin: 6px 0 12px; }
.hdot { width: 8px; height: 8px; border-radius: 50%; background: var(--c); }
.step { font-size: 13px; font-weight: 700; letter-spacing: 1.2px; text-transform: uppercase; color: var(--ink); }

.lead { font-size: 21px; font-weight: 700; line-height: 1.25; margin: 0 0 6px; color: #111; }
.desc { font-size: 14.5px; line-height: 1.5; color: #374151; margin: 0 0 10px; }
.desc b { color: var(--ink); font-weight: 700; }
.desc i { font-style: normal; font-weight: 600; color: var(--ink); background: var(--soft); padding: 1px 6px; border-radius: 4px; }

.visual {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 2px 0 10px;
  min-height: 0;
}
.visual > * { width: 100%; }
.chips { display: flex; flex-direction: column; gap: 6px; align-items: stretch; justify-content: center; }
.chip {
  display: inline-flex; align-items: center; gap: 10px;
  background: var(--soft); color: var(--ink);
  padding: 9px 16px; border-radius: 10px;
  font-weight: 600; font-size: 15px;
}
.chip-dots { justify-content: center; letter-spacing: 4px; font-size: 20px; line-height: 0.8; padding: 6px 16px; }
.ci { width: 20px; height: 20px; flex: none; }
.actors {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 8px 8px;
  align-items: center;
  justify-items: stretch;
}
.actor {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  background: var(--soft); color: var(--ink);
  padding: 9px 12px; border-radius: 10px;
  font-weight: 600; font-size: 15px;
  white-space: nowrap;
}
.ai { width: 20px; height: 20px; }
.plus { color: #9ca3af; font-weight: 700; font-size: 16px; text-align: center; }

.vote { display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; padding: 14px 18px; background: var(--soft); border-radius: 12px;
  width: 100%; }
.bots-row { display: flex; gap: 6px; align-items: center; justify-content: center; }
.rbot { width: 26px; height: 26px; flex: none; }
.vote-x { display: flex; flex-direction: column; line-height: 1; align-items: center; }
.vote-num { font-size: 30px; font-weight: 800; color: var(--ink); }
.vote-lab { font-size: 12px; color: var(--ink); font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; margin-top: 4px; }

.metrics { display: flex; flex-direction: column; gap: 8px; width: 100%; justify-content: center; }
.metric {
  display: flex; align-items: center; gap: 12px;
  background: var(--soft);
  padding: 11px 14px; border-radius: 10px;
  min-width: 0;
}
.mi { width: 24px; height: 24px; flex: none; }
.mtxt { color: var(--ink); line-height: 1.2; min-width: 0; display: flex; align-items: baseline; gap: 8px; }
.mtxt b { font-weight: 700; font-size: 16px; white-space: nowrap; }
.mtxt small { color: #6b7280; font-weight: 500; font-size: 12px; }

.out {
  margin-top: auto;
  display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
  border-top: 1px dashed #e5e7eb; padding-top: 10px;
}
.out-k { color: #9ca3af; font-weight: 600; text-transform: uppercase; letter-spacing: 0.6px; font-size: 10.5px; }
.out-v { color: #1f2937; font-weight: 600; font-size: 13px; line-height: 1.3; }

.arc-wrap { position: relative; margin-top: 8px; height: 60px; }
.arc { width: 100%; height: 60px; display: block; }
.arc-label {
  position: absolute; left: 0; right: 0; top: 6px;
  text-align: center; color: #0a7a52; font-weight: 700; font-size: 17px;
  letter-spacing: 0.2px;
}
</style>
