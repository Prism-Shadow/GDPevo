<template>
  <div class="diagram">
    <h1 class="title">GDPevo Data Construction Pipeline</h1>

    <div class="board">
      <!-- ===== Stage 1: Scenario Seed ===== -->
      <section class="stage st-1">
        <h3 class="stage-title">Stage 1: Scenario Seed</h3>
        <div class="stage-body">
          <div class="seed-card">
            <div class="seed-head">Real-job seeds</div>
            <div class="seed-list">
              <span class="seed-chip"><DocB class="seed-ci" :c="B"/>GDPVal</span>
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
          <!-- Main Agent -->
          <div class="box box-main">
            <Robot class="box-icon" :c="G"/>
            <span><b>Main Agent:</b> blueprint + integration</span>
          </div>

          <!-- T-split SVG: vertical from main + horizontal bar + two down arrows into env / tasks -->
          <svg class="t-split" width="600" height="50" viewBox="0 0 600 50" fill="none">
            <!-- vertical drop from main -->
            <path d="M 300 0 V 12" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
            <!-- horizontal bar -->
            <path d="M 70 12 H 530" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
            <!-- down to env (env card center ~70px from card left) -->
            <path d="M 70 12 V 38" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
            <polygon points="62,36 70,48 78,36" fill="#10a36e"/>
            <!-- down to tasks (tasks card center) -->
            <path d="M 365 12 V 38" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
            <polygon points="357,36 365,48 373,36" fill="#10a36e"/>
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

          <!-- Tasks → Calibration (down) + Calibration → Tasks fail loop (up on right side) -->
          <div class="loop-block">
            <svg class="loop-svg" width="600" height="60" viewBox="0 0 600 60" fill="none">
              <!-- down arrow: tasks center to calibration -->
              <path d="M 365 0 V 46" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
              <polygon points="357,44 365,56 373,44" fill="#10a36e"/>
              <!-- fail loop: vertical line going up on right side -->
              <path d="M 480 56 V 6" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
              <polygon points="472,8 480,-4 488,8" fill="#10a36e"/>
            </svg>
            <span class="loop-label">fail</span>
          </div>

          <!-- Calibration -->
          <div class="box box-calib">
            <Robot class="box-icon" :c="G"/>
            <span>Calibration Solvers</span>
          </div>

          <!-- Calibration → Outputs (pass) -->
          <div class="pass-block">
            <svg class="pass-svg" width="600" height="46" viewBox="0 0 600 46" fill="none">
              <path d="M 300 4 V 32" stroke="#10a36e" stroke-width="3" stroke-linecap="round"/>
              <polygon points="292,30 300,42 308,30" fill="#10a36e"/>
            </svg>
            <span class="pass-label">pass</span>
          </div>

          <!-- Outputs -->
          <div class="outputs">
            <div class="outputs-title">Outputs</div>
            <div class="outputs-row">
              <div class="out-cell"><Globe class="out-icon" :c="G"/><span>Shared<br>Env</span></div>
              <div class="out-cell"><DocG class="out-icon" :c="G"/><span>5 Train<br>Tasks</span></div>
              <div class="out-cell"><DocG class="out-icon" :c="G"/><span>5 Test<br>Tasks</span></div>
              <div class="out-cell"><Shield class="out-icon" :c="G"/><span>Evaluators</span></div>
              <div class="out-cell"><DocG class="out-icon" :c="G"/><span>Task<br>Notes</span></div>
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

      <!-- bottom fail->revise arc -->
      <svg class="fail-arc" viewBox="0 0 1000 100" preserveAspectRatio="none">
        <path d="M 670 4 V 60 H 350 V 36"
              stroke="#10a36e" stroke-width="3" fill="none"
              stroke-linecap="round" stroke-linejoin="round"
              vector-effect="non-scaling-stroke"/>
        <polygon points="350,30 343,50 357,50" fill="#10a36e"/>
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
const DownArrowO = () => h('svg', { width: 22, height: 32, viewBox: '0 0 22 32', fill: 'none' }, [
  h('path', { d: 'M11 2 V 22', stroke: '#ea580c', 'stroke-width': 3, 'stroke-linecap': 'round' }),
  h('polygon', { points: '3,20 11,32 19,20', fill: '#ea580c' }),
])
</script>

<style scoped>
.diagram, .diagram * { box-sizing: border-box; }
.diagram {
  width: 1700px;
  font-family: Inter, "Segoe UI", system-ui, sans-serif;
  color: #1f2937;
  padding: 20px 28px 60px;
  background: #fff;
}
.title {
  text-align: center;
  font-size: 44px;
  font-weight: 800;
  letter-spacing: -0.5px;
  margin: 0 0 22px;
  color: #111;
}

.board {
  position: relative;
  display: grid;
  grid-template-columns: 240px 38px 600px 38px 280px 38px 280px;
  align-items: stretch;
  gap: 0;
}

.stage {
  border: 2px dashed var(--c);
  border-radius: 6px;
  padding: 14px 14px 22px;
  display: flex; flex-direction: column;
}
.stage-title {
  margin: 0 0 14px;
  font-size: 19px;
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
  gap: 14px;
  padding: 16px 14px 18px;
}
.seed-head {
  font-size: 16px; font-weight: 800; color: #111; text-align: center;
}
.seed-list { display: flex; flex-direction: column; gap: 8px; }
.seed-chip {
  display: flex; align-items: center; gap: 10px;
  background: #e9f0ff; color: #1d4ed8;
  padding: 10px 14px; border-radius: 10px;
  font-weight: 700; font-size: 15px;
}
.seed-ci { width: 18px; height: 18px; flex: none; }
.seed-dots {
  justify-content: center; letter-spacing: 4px; font-size: 18px;
  padding: 6px 14px;
}
.seed-foot {
  margin-top: auto;
  padding-top: 10px;
  border-top: 1px dashed #cbd5e1;
  text-align: center;
  font-size: 13px; font-weight: 600; color: #475569;
}

/* ===== Stage 2 ===== */
.st-2-body { gap: 0; }

.box {
  background: #fff;
  border: 2px solid #10a36e;
  border-radius: 10px;
  padding: 10px 14px;
  display: inline-flex; align-items: center; gap: 10px;
  font-size: 15px; color: #111;
  line-height: 1.25;
}
.box-icon { flex: none; width: 22px; height: 22px; }
.box-main { font-size: 16px; }
.box-main b { font-weight: 700; }

.t-split, .loop-svg, .pass-svg {
  width: 100%;
  height: auto;
  display: block;
  margin: 0;
  max-width: 570px;
}

.loop-block, .pass-block {
  position: relative;
  width: 100%;
}
.loop-label {
  position: absolute;
  left: 84%;
  top: 38%;
  transform: translateY(-50%);
  font-size: 13px;
  font-weight: 700;
  color: #10a36e;
}
.pass-label {
  position: absolute;
  left: 56%;
  top: 50%;
  transform: translateY(-50%);
  font-size: 13px;
  font-weight: 700;
  color: #10a36e;
}

.loop-block, .pass-block {
  position: relative;
  width: 100%;
}
.loop-label {
  position: absolute;
  left: 84%;
  top: 38%;
  transform: translateY(-50%);
  font-size: 13px;
  font-weight: 700;
  color: #10a36e;
}
.pass-label {
  position: absolute;
  left: 56%;
  top: 50%;
  transform: translateY(-50%);
  font-size: 13px;
  font-weight: 700;
  color: #10a36e;
}

.box-calib {
  font-size: 15px; font-weight: 700;
}
.box-calib .box-icon { width: 26px; height: 26px; }

.row-builders {
  display: flex; align-items: stretch; gap: 10px;
  width: 100%;
  justify-content: center;
}
.box-env {
  flex-direction: column; gap: 6px;
  text-align: center;
  padding: 12px 14px;
  align-self: stretch; justify-content: center;
  width: 130px;
}
.box-env .box-icon { width: 28px; height: 28px; }
.env-text { font-size: 14px; font-weight: 700; line-height: 1.2; }

.box-tasks {
  flex: 1;
  flex-direction: column; align-items: stretch; gap: 8px;
  padding: 10px 12px 12px;
}
.tasks-title {
  font-size: 15px; font-weight: 700;
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

.outputs {
  width: 100%;
  border: 2px dashed #10a36e;
  border-radius: 10px;
  padding: 10px 12px 12px;
  display: flex; flex-direction: column; gap: 8px;
}
.outputs-title {
  font-size: 16px; font-weight: 700;
  color: #10a36e;
  text-align: center;
}
.outputs-row { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.out-cell {
  background: #fff;
  border: 1.5px solid #10a36e;
  border-radius: 8px;
  padding: 8px 4px;
  display: flex; flex-direction: column; align-items: center; gap: 4px;
  font-size: 12.5px; font-weight: 700; color: #0a7a52;
  text-align: center; line-height: 1.2;
}
.out-icon { width: 22px; height: 22px; flex: none; }

/* ===== Stage 3 ===== */
.st-3-body { gap: 12px; justify-content: flex-start; }
.box-struct, .box-rev, .box-pass {
  width: 100%;
  border: 2px solid #ea580c;
  flex-direction: column; gap: 8px;
  text-align: center;
  padding: 14px 12px;
  font-size: 16px; font-weight: 700; color: #111;
  line-height: 1.25;
}
.box-struct .box-icon, .box-pass .box-icon { width: 38px; height: 38px; }
.bots-three { display: flex; gap: 8px; justify-content: center; }
.bot3 { width: 36px; height: 36px; }
.rev-text { font-size: 16px; font-weight: 700; }

/* ===== Stage 4 ===== */
.st-4-body { gap: 12px; justify-content: space-between; }
.box-metric {
  width: 100%;
  border: 2px solid #dc2626;
  padding: 14px 14px;
  font-size: 18px; font-weight: 700;
  color: #111;
  justify-content: flex-start;
  line-height: 1.25;
}
.m-icon { width: 32px; height: 32px; flex: none; }

/* ===== Bottom fail->revise arc ===== */
.fail-arc {
  position: absolute;
  left: 0; right: 0;
  bottom: -42px;
  width: 100%; height: 80px;
  pointer-events: none;
}
.fail-revise-lab {
  position: absolute;
  left: 0; right: 0;
  bottom: -56px;
  text-align: center;
  font-size: 18px; font-weight: 700;
  color: #10a36e;
  letter-spacing: 0.2px;
}
</style>
