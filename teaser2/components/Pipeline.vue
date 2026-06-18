<template>
  <div class="diagram">
    <h1 class="title">GDPevo Data Pipeline</h1>

    <div class="board">
      <!-- ===== Stage 1: Scenario Seed ===== -->
      <section class="stage st-1">
        <h3 class="stage-title">Stage 1: Scenario Seed</h3>
        <div class="stage-body">
          <div class="seed-card">
            <div class="seed-head">Real-job seeds</div>
            <div class="seed-list">
              <span class="seed-chip"><DocB class="seed-ci" :c="B"/>GDPval</span>
              <span class="seed-chip"><DocB class="seed-ci" :c="B"/>SOP-Bench</span>
              <span class="seed-chip"><DocB class="seed-ci" :c="B"/>JobBench</span>
              <span class="seed-chip seed-dots">···</span>
            </div>
            <div class="seed-foot">1 scenario · n examples</div>
          </div>
        </div>
      </section>

      <div class="arrow arrow-12"><BlackArrow/></div>

      <!-- ===== Stage 2: Multi-Agent Task Factory ===== -->
      <section class="stage st-2">
        <h3 class="stage-title">Stage 2: Multi-Agent Task Factory</h3>
        <div class="stage-body st-2-body">
          <!-- Group A: Main → T-split → Env/Tasks builders -->
          <div class="grp">
            <div class="box box-main">
              <Robot class="box-icon" :c="G"/>
              <span><b>Main Agent:</b> blueprint + integration</span>
            </div>

            <!-- T-split SVG (14x10 arrowheads, matching forward/fail/pass) -->
            <svg class="t-split" width="632" height="28" viewBox="0 0 632 28" fill="none">
              <path d="M 316 -2 V 10" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
              <path d="M 65 10 H 386" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
              <path d="M 65 10 V 20" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
              <polygon points="58,20 72,20 65,30" fill="#10a36e"/>
              <path d="M 386 10 V 20" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
              <polygon points="379,20 393,20 386,30" fill="#10a36e"/>
            </svg>

            <!-- Env + Tasks row -->
            <div class="row-builders">
              <div class="box box-env">
                <Robot class="box-icon" :c="G"/>
                <div class="env-text">Env Builder<br>Agent</div>
              </div>
              <div class="box box-tasks">
                <div class="tasks-title">Task Builder Agents (per task)</div>
                <div class="tasks-row">
                  <div class="task-cell"><Robot class="task-bot" :c="G"/><span>train<br>1</span></div>
                  <div class="task-cell"><Robot class="task-bot" :c="G"/><span>train<br>2</span></div>
                  <div class="task-cell task-dots">···</div>
                  <div class="task-cell"><Robot class="task-bot" :c="G"/><span>train<br>5</span></div>
                  <div class="task-cell"><Robot class="task-bot" :c="G"/><span>test<br>1</span></div>
                  <div class="task-cell"><Robot class="task-bot" :c="G"/><span>test<br>2</span></div>
                  <div class="task-cell task-dots">···</div>
                  <div class="task-cell"><Robot class="task-bot" :c="G"/><span>test<br>5</span></div>
                </div>
              </div>
            </div>
          </div>

          <!-- Group B: forward arrow Tasks→Calib (straight vertical), Calibration, fail arrow (straight vertical) -->
          <div class="tc-wrap">
            <div class="forward-block">
              <div class="forward-line"></div>
              <svg class="forward-head" width="14" height="10" viewBox="0 0 14 10" fill="none">
                <polygon points="0,0 14,0 7,10" fill="#10a36e"/>
              </svg>
            </div>
            <div class="box box-calib">
              <Robot class="box-icon" :c="G"/>
              <span>Calibration Solvers</span>
            </div>
            <div class="fail-loop">
              <div class="fail-line"></div>
              <svg class="fail-head" width="14" height="10" viewBox="0 0 14 10" fill="none">
                <polygon points="0,10 14,10 7,0" fill="#10a36e"/>
              </svg>
            </div>
            <span class="loop-label">fail</span>
          </div>

          <!-- Group C: pass arrow + outputs (pass-block flexes to fill remaining height) -->
          <div class="grp grp-c">
            <div class="pass-block">
              <div class="pass-line"></div>
              <svg class="pass-head" width="14" height="10" viewBox="0 0 14 10" fill="none">
                <polygon points="0,0 14,0 7,10" fill="#10a36e"/>
              </svg>
              <span class="pass-label">pass</span>
            </div>
            <div class="outputs-flat">
              <div class="out-cell"><Globe class="out-icon" :c="G"/><span>Shared Env</span></div>
              <div class="out-cell"><DocG class="out-icon" :c="G"/><span>5 Train Tasks</span></div>
              <div class="out-cell"><DocG class="out-icon" :c="G"/><span>5 Test Tasks</span></div>
              <div class="out-cell"><Shield class="out-icon" :c="G"/><span>Evaluators</span></div>
              <div class="out-cell"><DocG class="out-icon" :c="G"/><span>Task Notes</span></div>
            </div>
          </div>
        </div>
      </section>

      <div class="arrow arrow-23"><BlackArrow/></div>

      <!-- ===== Stage 3: Quality Review ===== -->
      <section class="stage st-3">
        <h3 class="stage-title">Stage 3: Quality Review</h3>
        <div class="stage-body st-3-body">
          <div class="box box-struct">
            <Clipboard class="box-icon" :c="O"/>
            <span>Structure<br>Check</span>
          </div>

          <DownArrowO/>

          <div class="box box-rev">
            <div class="bots-three">
              <Robot class="bot3" :c="O"/>
              <Robot class="bot3" :c="O"/>
              <Robot class="bot3" :c="O"/>
            </div>
            <div class="rev-text">6 Clean-Context<br>Agent Reviewers</div>
          </div>

          <DownArrowO/>

          <div class="box box-pass">
            <ShieldCheck class="box-icon" :c="O"/>
            <span><b>5 / 6 Pass</b></span>
          </div>
        </div>
      </section>

      <div class="arrow arrow-34"><BlackArrow/></div>

      <!-- ===== Stage 4: Evaluation Release ===== -->
      <section class="stage st-4">
        <h3 class="stage-title">Stage 4: Evaluation Release</h3>
        <div class="stage-body st-4-body">
          <div class="box box-metric">
            <BarChart class="m-icon" :c="R"/>
            <span>avg@3</span>
          </div>
          <div class="box box-metric">
            <Database class="m-icon" :c="R"/>
            <span>Token Metrics</span>
          </div>
          <div class="box box-metric">
            <Dollar class="m-icon" :c="R"/>
            <span>Cost Metrics</span>
          </div>
          <div class="box box-metric">
            <Reports class="m-icon" :c="R"/>
            <span>Reports +<br>Skill Packages</span>
          </div>
        </div>
      </section>

      <!-- bottom fail->revise arc:
           start = Stage 3 bottom-edge midpoint (overlaps border at y=-2)
           end   = Stage 2 bottom-edge midpoint (arrow head into border at y=-2) -->
      <svg class="fail-arc" width="1474" height="36" viewBox="0 0 1474 36" fill="none" overflow="visible">
        <path d="M 1091 -2 V 18 H 608 V 4"
              stroke="#10a36e" stroke-width="3" fill="none"
              stroke-linecap="round" stroke-linejoin="round"/>
        <polygon points="601,4 615,4 608,-6" fill="#10a36e"/>
      </svg>
      <div class="fail-revise-lab">fail -&gt; revise</div>
    </div>
  </div>
</template>

<script setup>
import { h } from 'vue'
const B = '#1d4ed8', G = '#10a36e', O = '#ea580c', R = '#dc2626'

const wrap = (children, size = 24, sw = 2) => (p) => h('svg', {
  viewBox: '0 0 24 24', width: size, height: size, fill: 'none',
  stroke: p.c, 'stroke-width': sw, 'stroke-linecap': 'round', 'stroke-linejoin': 'round'
}, children())

const DocB = wrap(() => [
  h('path', { d: 'M7 3h7l4 4v14H7z' }),
  h('path', { d: 'M14 3v4h4' }),
  h('path', { d: 'M10 12h5M10 15.5h5M10 9h2' }),
])
const Robot = wrap(() => [
  h('rect', { x: 5, y: 8, width: 14, height: 11, rx: 2 }),
  h('path', { d: 'M12 8V4.5' }),
  h('circle', { cx: 12, cy: 3.2, r: 1.4, fill: 'currentColor', stroke: 'none' }),
  h('circle', { cx: 9.3, cy: 13, r: 1.3, fill: 'currentColor', stroke: 'none' }),
  h('circle', { cx: 14.7, cy: 13, r: 1.3, fill: 'currentColor', stroke: 'none' }),
  h('path', { d: 'M9.5 16.5h5' }),
])
const Globe = wrap(() => [
  h('circle', { cx: 12, cy: 12, r: 9 }),
  h('ellipse', { cx: 12, cy: 12, rx: 4, ry: 9 }),
  h('line', { x1: 3, y1: 12, x2: 21, y2: 12 }),
])
const DocG = wrap(() => [
  h('path', { d: 'M7 3h7l4 4v14H7z' }),
  h('path', { d: 'M14 3v4h4' }),
  h('path', { d: 'M10 12h5M10 15.5h5M10 9h2' }),
])
const Shield = (p) => h('svg', { viewBox: '0 0 24 24', width: 22, height: 22, fill: p.c, stroke: 'none' }, [
  h('path', { d: 'M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5z' }),
  h('path', { d: 'M9.2 11.6 11.4 13.8 15.4 9.6', stroke: '#fff', 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', fill: 'none' }),
])
const Clipboard = (p) => h('svg', { viewBox: '0 0 24 24', width: 32, height: 32, fill: 'none', stroke: p.c, 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('rect', { x: 5, y: 4, width: 14, height: 17, rx: 2 }),
  h('rect', { x: 9, y: 2.4, width: 6, height: 3.2, rx: 0.8, fill: p.c, stroke: 'none' }),
  h('path', { d: 'M8.5 10 L10 11.5 12 9.5' }),
  h('path', { d: 'M13 10.5 H 16.5' }),
  h('path', { d: 'M8.5 14.5 L10 16 12 14' }),
  h('path', { d: 'M13 15 H 16.5' }),
])
const ShieldCheck = (p) => h('svg', { viewBox: '0 0 24 24', width: 32, height: 32, fill: p.c, stroke: 'none' }, [
  h('path', { d: 'M12 2 4 5v6c0 5 3.5 9 8 11 4.5-2 8-6 8-11V5z' }),
  h('path', { d: 'M9 11.6 11.2 13.8 15.4 9.4', stroke: '#fff', 'stroke-width': 2.4, 'stroke-linecap': 'round', 'stroke-linejoin': 'round', fill: 'none' }),
])
const BarChart = (p) => h('svg', { viewBox: '0 0 24 24', width: 28, height: 28, fill: p.c, stroke: 'none' }, [
  h('rect', { x: 3, y: 13, width: 4, height: 8, rx: 1 }),
  h('rect', { x: 10, y: 7, width: 4, height: 14, rx: 1 }),
  h('rect', { x: 17, y: 10, width: 4, height: 11, rx: 1 }),
])
const Database = (p) => h('svg', { viewBox: '0 0 24 24', width: 28, height: 28, fill: p.c, stroke: 'none' }, [
  h('ellipse', { cx: 12, cy: 5.2, rx: 7.5, ry: 2.6 }),
  h('path', { d: 'M4.5 5.2v13.6c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8V5.2 c 0 1.5 -3.4 2.8 -7.5 2.8 s -7.5 -1.3 -7.5 -2.8 z' }),
  h('path', { d: 'M4.5 12c0 1.5 3.4 2.8 7.5 2.8s7.5-1.3 7.5-2.8 V 9.5 c 0 1.5 -3.4 2.8 -7.5 2.8 s -7.5 -1.3 -7.5 -2.8 z' }),
])
const Dollar = (p) => h('svg', { viewBox: '0 0 24 24', width: 28, height: 28, fill: 'none', stroke: p.c, 'stroke-width': 2.2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('circle', { cx: 12, cy: 12, r: 9, fill: p.c, stroke: 'none' }),
  h('path', { d: 'M15 8.7c-.8-1-2-1.5-3.2-1.5-1.7 0-3 .9-3 2.3 0 3.1 6.2 1.5 6.2 4.7 0 1.5-1.4 2.6-3.2 2.6-1.3 0-2.6-.6-3.4-1.7M12 5.2v13.6', stroke: '#fff', 'stroke-width': 2 }),
])
const Reports = (p) => h('svg', { viewBox: '0 0 28 28', width: 28, height: 28, fill: 'none', stroke: p.c, 'stroke-width': 2, 'stroke-linecap': 'round', 'stroke-linejoin': 'round' }, [
  h('path', { d: 'M5 3 H17 L21 7 V25 H5 Z', fill: '#fff' }),
  h('path', { d: 'M17 3 V7 H21' }),
  h('path', { d: 'M8 12 H16 M 8 16 H 14 M 8 20 H 13' }),
  h('rect', { x: 14, y: 16, width: 8, height: 8, rx: 1, fill: p.c, stroke: p.c }),
])

const BlackArrow = () => h('svg', { width: 38, height: 22, viewBox: '0 0 38 22', fill: 'none' }, [
  h('path', { d: 'M2 11 H 24', stroke: '#1f2937', 'stroke-width': 3, 'stroke-linecap': 'round' }),
  h('polygon', { points: '22,3 36,11 22,19', fill: '#1f2937' }),
])
const DownArrowO = () => h('svg', {
  width: 22, viewBox: '0 0 22 60', fill: 'none', preserveAspectRatio: 'none',
  class: 'down-arrow-o',
  style: 'display:block; overflow:visible'
}, [
  h('path', { d: 'M11 0 V 50', stroke: '#ea580c', 'stroke-width': 3, 'stroke-linecap': 'round', 'vector-effect': 'non-scaling-stroke' }),
  h('polygon', { points: '3,48 11,60 19,48', fill: '#ea580c' }),
])
</script>

<style scoped>
.diagram, .diagram * { box-sizing: border-box; }
.diagram {
  width: 1700px;
  font-family: Inter, "Segoe UI", system-ui, sans-serif;
  color: #1f2937;
  padding: 14px 28px 50px;
  background: #fff;
}
.title {
  text-align: center;
  font-size: 38px;
  font-weight: 800;
  letter-spacing: -0.5px;
  margin: 0 0 12px;
  color: #111;
}

.board {
  position: relative;
  display: grid;
  grid-template-columns: 240px 38px 660px 38px 230px 38px 230px;
  align-items: stretch;
  gap: 0;
}

.stage {
  border: 2px dashed var(--c);
  border-radius: 6px;
  padding: 8px 14px 12px;
  display: flex; flex-direction: column;
  min-height: 280px;
}
.stage-title {
  margin: 0 0 8px;
  font-size: 18px;
  font-weight: 700;
  color: var(--c);
}
.stage-body { flex: 1; display: flex; flex-direction: column; align-items: center; gap: 0; }

.st-1 { --c: #1d4ed8; }
.st-2 { --c: #10a36e; }
.st-3 { --c: #ea580c; }
.st-4 { --c: #dc2626; }

.arrow { display: flex; align-items: center; justify-content: center; }

/* ===== Stage 1 ===== */
.seed-card {
  flex: 1;
  width: 100%;
  border: 2.5px solid #1d4ed8;
  border-radius: 14px;
  background: #fff;
  display: flex; flex-direction: column;
  gap: 10px;
  padding: 12px 12px 14px;
}
.seed-head {
  font-size: 16px; font-weight: 800; color: #111; text-align: center;
}
.seed-list {
  display: flex; flex-direction: column; gap: 10px;
  flex: 1;
  justify-content: space-evenly;
}
.seed-chip {
  display: flex; align-items: center; gap: 10px;
  background: #e9f0ff; color: #1d4ed8;
  padding: 10px 12px; border-radius: 10px;
  font-weight: 700; font-size: 15px;
}
.seed-ci { width: 18px; height: 18px; flex: none; }
.seed-dots {
  justify-content: center; letter-spacing: 4px; font-size: 18px;
  padding: 4px 12px;
}
.seed-foot {
  margin-top: auto;
  padding-top: 8px;
  border-top: 1px dashed #cbd5e1;
  text-align: center;
  font-size: 13px; font-weight: 600; color: #475569;
}

/* ===== Stage 2 ===== */
.st-2-body { gap: 0; justify-content: flex-start; flex: 1; }
.grp { width: 100%; display: flex; flex-direction: column; align-items: center; }

.box {
  background: #fff;
  border: 2px solid #10a36e;
  border-radius: 10px;
  padding: 6px 14px;
  display: inline-flex; align-items: center; gap: 10px;
  font-size: 15px; color: #111;
  line-height: 1.2;
}
.box-icon { flex: none; width: 22px; height: 22px; }
.box-main { font-size: 16px; }
.box-main b { font-weight: 700; }

.t-split, .pass-svg, .forward-svg {
  display: block;
  margin: -2px 0;          /* overlap into top/bottom box borders */
  width: 632px;
  overflow: visible;
}

/* Calibration block + forward arrow + fail-loop overlay */
.tc-wrap {
  position: relative;
  width: 632px;
  align-self: center;
  display: flex; flex-direction: column; align-items: center;
  flex: 0 0 auto;       /* size to content; pass-block flexes for vertical fill */
}

/* Forward arrow: straight vertical line at x=290 from Tasks-bottom to Calibration-top */
.forward-block {
  position: relative;
  width: 632px;
  flex: 1;
  min-height: 24px;
  max-height: 36px;
  display: flex; flex-direction: column;
}
.forward-line {
  position: absolute;
  left: 290px;
  top: -2px;             /* overlap into Tasks bottom border */
  width: 3px;
  bottom: 8px;           /* leave room for arrowhead (10px tall) */
  background: #10a36e;
}
.forward-head {
  position: absolute;
  left: 284px;           /* center 290 → 14/2=7 → 290-7=283; +1 alignment */
  bottom: -2px;          /* overlap into Calibration top border */
  display: block;
}

.tc-wrap .box-calib {
  width: 230px;
  height: 42px;
  justify-content: center;
  font-size: 15px; font-weight: 700;
}
.tc-wrap .box-calib .box-icon { width: 24px; height: 24px; }

/* Fail arrow: straight vertical line at x=342, from Calibration-top to Tasks-bottom */
.fail-loop {
  position: absolute;
  left: 0; right: 0;
  top: 0; bottom: 0;
  pointer-events: none;
}
.fail-line {
  position: absolute;
  left: 342px;
  top: 8px;
  bottom: 40px;          /* land 2px into Calibration top (calib height 42 - 2) */
  width: 3px;
  background: #10a36e;
}
.fail-head {
  position: absolute;
  left: 335px;           /* center 342 - 7 */
  top: -2px;             /* overlap into Tasks bottom border */
}
.loop-label {
  position: absolute;
  left: 360px;
  top: auto;
  bottom: 50px;          /* above Calibration top */
  transform: none;
  font-size: 14px;
  font-weight: 700;
  color: #10a36e;
}

/* pass arrow + label — pass-block grows to push outputs to the bottom */
.pass-block {
  position: relative;
  width: 632px;
  align-self: center;
  flex: 1;
  min-height: 24px;
  max-height: 36px;
  display: flex; flex-direction: column; align-items: center;
  margin-top: -2px;
}
.pass-line {
  width: 3px;
  flex: 1;
  background: #10a36e;
  border-radius: 2px;
  margin-bottom: -1px;  /* meet arrowhead cleanly */
}
.pass-head {
  display: block;
  margin-top: -1px;
}
.pass-label {
  position: absolute;
  left: 326px;
  top: 50%;
  transform: translateY(-50%);
  font-size: 14px;
  font-weight: 700;
  color: #10a36e;
}

.grp-c { flex: 1; justify-content: stretch; gap: 0; }

.row-builders {
  display: flex; align-items: stretch; gap: 10px;
  width: 100%;
  justify-content: center;
}
.box-env {
  flex-direction: column; gap: 2px;
  text-align: center;
  padding: 6px 12px;
  align-self: stretch; justify-content: center;
  width: 130px;
}
.box-env .box-icon { width: 24px; height: 24px; }
.env-text { font-size: 14px; font-weight: 700; line-height: 1.15; }

.box-tasks {
  flex: 1;
  flex-direction: column; align-items: stretch; gap: 4px;
  padding: 6px 12px 8px;
}
.tasks-title {
  font-size: 14px; font-weight: 700;
  text-align: center;
}
.tasks-row { display: grid; grid-template-columns: repeat(8, 1fr); gap: 5px; }
.task-cell {
  display: flex; flex-direction: column; align-items: center; gap: 2px;
  background: #fff;
  border: 1.5px solid #10a36e;
  border-radius: 7px;
  padding: 4px 2px 5px;
  font-size: 11px; font-weight: 600; color: #0a7a52;
  line-height: 1.2;
  text-align: center;
}
.task-bot { width: 18px; height: 18px; flex: none; }
.task-dots {
  border: none; padding: 0;
  font-size: 18px; color: #10a36e; letter-spacing: 2px;
  display: flex; align-items: center; justify-content: center;
}

.loop-arrows-old { display: none; }

/* Flat outputs row — no wrapper box, no title */
.outputs-flat {
  width: 100%;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}
.outputs-flat .out-cell {
  background: #fff;
  border: 1.5px solid #10a36e;
  border-radius: 8px;
  padding: 5px 6px;
  display: flex; flex-direction: row; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 700; color: #0a7a52;
  text-align: left; line-height: 1.2;
  white-space: nowrap;
  justify-content: center;
}
.outputs-flat .out-icon { width: 18px; height: 18px; flex: none; }

/* ===== Stage 3 ===== */
.st-3-body { gap: 0; justify-content: stretch; flex: 1; }
.down-arrow-o { flex: 1; min-height: 22px; max-height: 32px; align-self: center; margin: -2px 0; }
.box-struct, .box-rev, .box-pass {
  width: 100%;
  border: 2px solid #ea580c;
  flex-direction: column; gap: 6px;
  text-align: center;
  padding: 10px 12px;
  font-size: 16px; font-weight: 700; color: #111;
  line-height: 1.2;
  flex-shrink: 0;
}
.box-struct .box-icon, .box-pass .box-icon { width: 32px; height: 32px; }
.bots-three { display: flex; gap: 8px; justify-content: center; }
.bot3 { width: 32px; height: 32px; }
.rev-text { font-size: 16px; font-weight: 700; }

/* ===== Stage 4 ===== */
.st-4-body { gap: 8px; justify-content: stretch; flex: 1; }
.box-metric {
  width: 100%;
  flex: 1;
  max-height: 56px;
  border: 2px solid #dc2626;
  padding: 10px 14px;
  font-size: 16px; font-weight: 700;
  color: #111;
  justify-content: flex-start;
  line-height: 1.2;
}
.m-icon { width: 28px; height: 28px; flex: none; }

/* ===== Bottom fail->revise arc ===== */
.fail-arc {
  position: absolute;
  left: 0;
  top: 100%;
  width: 1474px; height: 36px;
  pointer-events: none;
  overflow: visible;
}
.fail-revise-lab {
  position: absolute;
  left: 0; right: 0;
  top: calc(100% + 22px);
  text-align: center;
  font-size: 14px; font-weight: 700;
  color: #10a36e;
  letter-spacing: 0.2px;
}
</style>
