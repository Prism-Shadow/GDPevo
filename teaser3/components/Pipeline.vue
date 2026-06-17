<script setup>
// Single-SVG pipeline diagram. Compact 1450 x 610 canvas.

const C_BLUE   = '#1d4ed8'
const C_GREEN  = '#10a36e'
const C_ORANGE = '#ea580c'
const C_RED    = '#dc2626'
const C_DARK   = '#111827'

// Stage frames
const stages = [
  { x:  20, y:  44, w: 220, h: 488, color: C_BLUE,   title: 'Stage 1: Scenario Seed' },
  { x: 270, y:  44, w: 620, h: 488, color: C_GREEN,  title: 'Stage 2: Multi-Agent Task Factory' },
  { x: 920, y:  44, w: 220, h: 488, color: C_ORANGE, title: 'Stage 3: Quality Review' },
  { x:1170, y:  44, w: 260, h: 488, color: C_RED,    title: 'Stage 4: Evaluation Release' },
]

// Stage 1 chips (real-job seeds)
const seeds = [
  { kind: 'doc',  label: 'GDPVal' },
  { kind: 'doc',  label: 'SOP-Bench' },
  { kind: 'doc',  label: 'JobBench' },
  { kind: 'dots' },
]

const taskCells = [
  { kind: 'agent', label1: 'train', label2: '1' },
  { kind: 'agent', label1: 'train', label2: '2' },
  { kind: 'dots' },
  { kind: 'agent', label1: 'train', label2: '5' },
  { kind: 'agent', label1: 'test',  label2: '1' },
  { kind: 'agent', label1: 'test',  label2: '2' },
  { kind: 'dots' },
  { kind: 'agent', label1: 'test',  label2: '5' },
]

const outputs = [
  { icon: 'globe',  label1: 'Shared',  label2: 'Env' },
  { icon: 'docG',   label1: '5 Train', label2: 'Tasks' },
  { icon: 'docG',   label1: '5 Test',  label2: 'Tasks' },
  { icon: 'shield', label1: 'Evaluators', label2: '' },
  { icon: 'docG',   label1: 'Task',    label2: 'Notes' },
]

const metrics = [
  { icon: 'bar',     label1: 'avg@3',     label2: '' },
  { icon: 'db',      label1: 'Token Metrics', label2: '' },
  { icon: 'dollar',  label1: 'Cost Metrics',  label2: '' },
  { icon: 'reports', label1: 'Reports +',     label2: 'Skill Packages' },
]
</script>

<template>
  <svg class="pipe" width="1450" height="600" viewBox="-15 -8 1480 612"
       preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
    <!-- ===== Title ===== -->
    <text x="725" y="28" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
          style="font-size:26px;font-weight:800" :fill="C_DARK">
      GDPevo Data Construction Pipeline
    </text>

    <!-- ===== 4 Stage frames (dashed) ===== -->
    <g v-for="(s, i) in stages" :key="'frame'+i">
      <rect :x="s.x" :y="s.y" :width="s.w" :height="s.h" rx="8" ry="8"
            fill="none" :stroke="s.color" stroke-width="2" stroke-dasharray="6 5"/>
      <text :x="s.x + s.w/2" :y="s.y + 22" text-anchor="middle"
            font-family="Inter, system-ui, sans-serif"
            style="font-size:15px;font-weight:700" :fill="s.color">
        {{ s.title }}
      </text>
    </g>

    <!-- ===== Black inter-stage arrows (mid-vertical y=308) ===== -->
    <g v-for="(x, i) in [245, 895, 1145]" :key="'ar'+i">
      <line :x1="x" y1="308" :x2="x+13" y2="308" stroke="#1f2937" stroke-width="3" stroke-linecap="round"/>
      <polygon :points="`${x+11},301 ${x+22},308 ${x+11},315`" fill="#1f2937"/>
    </g>

    <!-- =====================================================
         Stage 1: Scenario Seed - Real-job seeds card with chips
         Card x=42..218, y=72..540
         ===================================================== -->
    <g>
      <rect x="42" y="72" width="176" height="432" rx="14" ry="14"
            fill="#fff" :stroke="C_BLUE" stroke-width="2.5"/>

      <!-- "Real-job seeds" header -->
      <text x="130" y="100" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:800" :fill="C_DARK">Real-job seeds</text>

      <!-- chips: 3 doc chips + 1 dots chip -->
      <g v-for="(s, i) in seeds" :key="'seed'+i">
        <template v-if="s.kind === 'doc'">
          <rect x="58" :y="120 + i * 64" width="144" height="42" rx="8" ry="8"
                fill="#e9f0ff" stroke="none"/>
          <!-- doc icon -->
          <g :transform="`translate(70, ${127 + i * 64})`">
            <path d="M 4 2 H 12 L 17 7 V 28 H 4 Z" fill="none" :stroke="C_BLUE" stroke-width="1.8" stroke-linejoin="round"/>
            <path d="M 12 2 V 7 H 17" fill="none" :stroke="C_BLUE" stroke-width="1.8" stroke-linejoin="round"/>
            <line x1="7"  y1="13" x2="14" y2="13" :stroke="C_BLUE" stroke-width="1.6" stroke-linecap="round"/>
            <line x1="7"  y1="18" x2="14" y2="18" :stroke="C_BLUE" stroke-width="1.6" stroke-linecap="round"/>
            <line x1="7"  y1="23" x2="13" y2="23" :stroke="C_BLUE" stroke-width="1.6" stroke-linecap="round"/>
          </g>
          <text x="100" :y="146 + i * 64" font-family="Inter, system-ui, sans-serif"
                style="font-size:14px;font-weight:700" :fill="C_BLUE">{{ s.label }}</text>
        </template>
        <template v-else>
          <rect x="58" :y="120 + i * 64" width="144" height="32" rx="8" ry="8"
                fill="#e9f0ff" stroke="none"/>
          <text x="130" :y="142 + i * 64" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:18px;font-weight:700" :fill="C_BLUE" letter-spacing="3">···</text>
        </template>
      </g>

      <!-- Footer: "1 Scenario · n Examples" -->
      <line x1="58" y1="468" x2="202" y2="468" stroke="#cbd5e1" stroke-width="1" stroke-dasharray="3 3"/>
      <text x="130" y="490" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:12px;font-weight:700" fill="#475569">1 scenario · n examples</text>
    </g>

    <!-- =====================================================
         Stage 2: Multi-Agent Task Factory  (frame x=270..890, y=44..568)
         y layout:
           Main Agent      : 76..112
           T-split         : 112..142
           Env / Tasks row : 142..240
           forward arrow   : 240..278
           Calibration box : 278..318
           pass arrow      : 318..360
           Outputs group   : 360..540
         ===================================================== -->

    <!-- Main Agent box (centered x=580) -->
    <g>
      <rect x="370" y="76" width="420" height="36" rx="8" ry="8"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <!-- Robot icon at left -->
      <g transform="translate(388, 82)">
        <line x1="13" y1="2" x2="13" y2="6" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        <circle cx="13" cy="2" r="1.6" :fill="C_GREEN"/>
        <rect x="3" y="6" width="20" height="16" rx="3" ry="3" fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
        <circle cx="9"  cy="13" r="1.6" :fill="C_GREEN"/>
        <circle cx="17" cy="13" r="1.6" :fill="C_GREEN"/>
        <line x1="9" y1="18" x2="17" y2="18" :stroke="C_GREEN" stroke-width="1.8" stroke-linecap="round"/>
      </g>
      <text x="425" y="100" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px" :fill="C_DARK">
        <tspan style="font-weight:700">Main Agent: </tspan>
        <tspan>blueprint + integration</tspan>
      </text>
    </g>

    <!-- T-split: 112..142 -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" fill="none">
      <line x1="580" y1="112" x2="580" y2="128"/>
      <line x1="350" y1="128" x2="720" y2="128"/>
      <line x1="350" y1="128" x2="350" y2="140"/>
      <line x1="720" y1="128" x2="720" y2="140"/>
    </g>
    <polygon points="343,138 350,150 357,138" :fill="C_GREEN"/>
    <polygon points="713,138 720,150 727,138" :fill="C_GREEN"/>

    <!-- Env Builder Agent box: x=290..410, y=150..240 -->
    <g>
      <rect x="290" y="150" width="120" height="92" rx="10" ry="10"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <!-- Robot icon (replacing wrench) - centered at (350, 174) -->
      <g transform="translate(338, 158)">
        <line x1="13" y1="2" x2="13" y2="6" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        <circle cx="13" cy="2" r="1.7" :fill="C_GREEN"/>
        <rect x="2" y="6" width="22" height="18" rx="3" ry="3" fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
        <circle cx="9"  cy="14" r="1.7" :fill="C_GREEN"/>
        <circle cx="17" cy="14" r="1.7" :fill="C_GREEN"/>
        <line x1="9" y1="20" x2="17" y2="20" :stroke="C_GREEN" stroke-width="1.8" stroke-linecap="round"/>
      </g>
      <text x="350" y="210" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:13px;font-weight:700" :fill="C_DARK">Env Builder</text>
      <text x="350" y="228" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:13px;font-weight:700" :fill="C_DARK">Agent</text>
    </g>

    <!-- Task Builder Agents box: x=430..870, y=150..240 -->
    <g>
      <rect x="430" y="150" width="440" height="92" rx="10" ry="10"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <text x="650" y="168" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:13px;font-weight:700" :fill="C_DARK">Task Builder Agents (per task)</text>

      <!-- 8 cells: each 48w x 56h, gap 4 -->
      <g v-for="(c, i) in taskCells" :key="'tc'+i">
        <template v-if="c.kind === 'agent'">
          <rect :x="442 + i * 53" y="178" width="48" height="56" rx="6" ry="6"
                fill="#fff" :stroke="C_GREEN" stroke-width="1.5"/>
          <!-- mini robot -->
          <g :transform="`translate(${442 + i * 53 + 14}, 184)`">
            <line x1="10" y1="0" x2="10" y2="2.5" :stroke="C_GREEN" stroke-width="1.4" stroke-linecap="round"/>
            <circle cx="10" cy="0.5" r="1.1" :fill="C_GREEN"/>
            <rect x="2.5" y="2.5" width="15" height="12" rx="2.5" ry="2.5" fill="#fff" :stroke="C_GREEN" stroke-width="1.4"/>
            <circle cx="6.8"  cy="8" r="1.2" :fill="C_GREEN"/>
            <circle cx="13.2" cy="8" r="1.2" :fill="C_GREEN"/>
            <line x1="7" y1="12" x2="13" y2="12" :stroke="C_GREEN" stroke-width="1.3" stroke-linecap="round"/>
          </g>
          <text :x="442 + i * 53 + 24" y="217" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:10px;font-weight:600" fill="#0a7a52">{{ c.label1 }}</text>
          <text :x="442 + i * 53 + 24" y="229" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:10px;font-weight:600" fill="#0a7a52">{{ c.label2 }}</text>
        </template>
        <template v-else>
          <text :x="442 + i * 53 + 24" y="212" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:18px;font-weight:700" :fill="C_GREEN" letter-spacing="1">···</text>
        </template>
      </g>
    </g>

    <!-- Forward arrow Tasks(650,242) -> down -> left -> Calibration top(580,278) -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none">
      <path d="M 650 242 V 260 H 580 V 270"/>
    </g>
    <polygon points="573,268 587,268 580,280" :fill="C_GREEN"/>

    <!-- Calibration Solvers box (no Internal Reviewer text): x=485..675, y=282..318 -->
    <g>
      <rect x="485" y="282" width="190" height="36" rx="8" ry="8"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <!-- Robot icon (replacing sliders) -->
      <g transform="translate(500, 287)">
        <line x1="13" y1="2" x2="13" y2="6" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        <circle cx="13" cy="2" r="1.6" :fill="C_GREEN"/>
        <rect x="3" y="6" width="20" height="16" rx="3" ry="3" fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
        <circle cx="9"  cy="13" r="1.6" :fill="C_GREEN"/>
        <circle cx="17" cy="13" r="1.6" :fill="C_GREEN"/>
        <line x1="9" y1="18" x2="17" y2="18" :stroke="C_GREEN" stroke-width="1.8" stroke-linecap="round"/>
      </g>
      <text x="540" y="305" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Calibration Solvers</text>
    </g>

    <!-- "fail" loop: from Calibration right edge (675,300) -> right (700) -> up to Tasks bottom (700,242) -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none">
      <path d="M 675 300 H 700 V 248"/>
    </g>
    <polygon points="693,250 707,250 700,238" :fill="C_GREEN"/>
    <text x="710" y="276" font-family="Inter, system-ui, sans-serif"
          style="font-size:12px;font-weight:700" :fill="C_GREEN">fail</text>

    <!-- pass arrow: Calibration bottom (580,318) down to Outputs top (580,348) -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" fill="none">
      <line x1="580" y1="318" x2="580" y2="338"/>
    </g>
    <polygon points="572,336 588,336 580,350" :fill="C_GREEN"/>
    <text x="588" y="332" font-family="Inter, system-ui, sans-serif"
          style="font-size:12px;font-weight:700" :fill="C_GREEN">pass</text>

    <!-- Outputs group: x=290..870, y=350..518 -->
    <g>
      <rect x="290" y="350" width="580" height="168" rx="10" ry="10"
            fill="none" :stroke="C_GREEN" stroke-width="1.5" stroke-dasharray="6 4"/>
      <text x="580" y="370" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:13px;font-weight:700" :fill="C_GREEN">Outputs</text>

      <!-- 5 cells -->
      <g v-for="(o, i) in outputs" :key="'o'+i">
        <rect :x="304 + i * 112" y="382" width="100" height="124" rx="10" ry="10"
              fill="#fff" :stroke="C_GREEN" stroke-width="1.5"/>

        <!-- Icon: globe -->
        <g v-if="o.icon === 'globe'" :transform="`translate(${304 + i * 112 + 38}, 404)`">
          <circle cx="12" cy="12" r="11" fill="none" :stroke="C_GREEN" stroke-width="2"/>
          <ellipse cx="12" cy="12" rx="5" ry="11" fill="none" :stroke="C_GREEN" stroke-width="2"/>
          <line x1="1" y1="12" x2="23" y2="12" :stroke="C_GREEN" stroke-width="2"/>
        </g>
        <!-- Icon: document -->
        <g v-else-if="o.icon === 'docG'" :transform="`translate(${304 + i * 112 + 38}, 404)`">
          <path d="M 4 1 H 14 L 20 7 V 23 H 4 Z"
                fill="#fff" :stroke="C_GREEN" stroke-width="2" stroke-linejoin="round"/>
          <path d="M 14 1 V 7 H 20" fill="none" :stroke="C_GREEN" stroke-width="2" stroke-linejoin="round"/>
          <line x1="7"  y1="11" x2="9"  y2="11" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
          <line x1="7"  y1="15" x2="17" y2="15" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
          <line x1="7"  y1="19" x2="17" y2="19" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        </g>
        <!-- Icon: shield -->
        <g v-else-if="o.icon === 'shield'" :transform="`translate(${304 + i * 112 + 38}, 404)`">
          <path d="M 12 1 L 2 4 V 11 c 0 6 4 10 10 12 c 6 -2 10 -6 10 -12 V 4 Z" :fill="C_GREEN" stroke="none"/>
          <path d="M 7 12 L 10.5 15.5 L 17 9" stroke="#fff" stroke-width="2.5"
                stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        </g>

        <text :x="304 + i * 112 + 50" y="468" text-anchor="middle"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:12px;font-weight:700" fill="#0a7a52">{{ o.label1 }}</text>
        <text v-if="o.label2" :x="304 + i * 112 + 50" y="486" text-anchor="middle"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:12px;font-weight:700" fill="#0a7a52">{{ o.label2 }}</text>
      </g>
    </g>

    <!-- =====================================================
         Stage 3: Quality Review (frame 920..1140, y=44..532)
         ===================================================== -->
    <g>
      <!-- Structure Check: y=78..156 -->
      <rect x="942" y="78" width="176" height="78" rx="10" ry="10"
            fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
      <g transform="translate(1015, 86)">
        <rect x="2" y="6" width="26" height="32" rx="3" ry="3" fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
        <rect x="9" y="2" width="12" height="7" rx="1.5" ry="1.5" :fill="C_ORANGE" stroke="none"/>
        <path d="M 6 16 L 9 19 L 13 14" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <line x1="15" y1="17" x2="24" y2="17" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round"/>
        <path d="M 6 26 L 9 29 L 13 24" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <line x1="15" y1="27" x2="24" y2="27" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round"/>
      </g>
      <text x="1030" y="138" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Structure</text>
      <text x="1030" y="153" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Check</text>

      <!-- Down arrow 1 -->
      <line x1="1030" y1="156" x2="1030" y2="194" :stroke="C_ORANGE" stroke-width="3" stroke-linecap="round"/>
      <polygon points="1022,192 1038,192 1030,206" :fill="C_ORANGE"/>

      <!-- Reviewers: y=212..328 -->
      <rect x="942" y="212" width="176" height="116" rx="10" ry="10"
            fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
      <g v-for="(rx, ri) in [994, 1030, 1066]" :key="'rb'+ri" :transform="`translate(${rx-12}, 226)`">
        <line x1="12" y1="0" x2="12" y2="4" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round"/>
        <circle cx="12" cy="0.5" r="1.6" :fill="C_ORANGE"/>
        <rect x="2" y="4" width="20" height="16" rx="3" ry="3" fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
        <circle cx="8"  cy="11" r="1.6" :fill="C_ORANGE"/>
        <circle cx="16" cy="11" r="1.6" :fill="C_ORANGE"/>
        <line x1="8" y1="16" x2="16" y2="16" :stroke="C_ORANGE" stroke-width="1.8" stroke-linecap="round"/>
      </g>
      <text x="1030" y="290" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">6 Clean-Context</text>
      <text x="1030" y="310" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Agent Reviewers</text>

      <!-- Down arrow 2 -->
      <line x1="1030" y1="328" x2="1030" y2="366" :stroke="C_ORANGE" stroke-width="3" stroke-linecap="round"/>
      <polygon points="1022,364 1038,364 1030,378" :fill="C_ORANGE"/>

      <!-- 5/6 Pass: y=384..474 -->
      <rect x="942" y="384" width="176" height="90" rx="10" ry="10"
            fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
      <g transform="translate(1015, 394)">
        <path d="M 17 1 L 4 5 V 14 c 0 9 6 15 13 18 c 7 -3 13 -9 13 -18 V 5 Z" :fill="C_ORANGE" stroke="none"/>
        <path d="M 11 16 L 15 20 L 23 12" stroke="#fff" stroke-width="3"
              stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      </g>
      <text x="1030" y="452" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:16px;font-weight:700" :fill="C_DARK">5 / 6 Pass</text>
    </g>

    <!-- =====================================================
         Stage 4: Evaluation Release (frame 1170..1430, y=44..568)
         4 cards stacked
         ===================================================== -->
    <g>
      <g v-for="(m, i) in metrics" :key="'m'+i">
        <rect x="1186" :y="80 + i * 112" width="228" height="96" rx="10" ry="10"
              fill="#fff" :stroke="C_RED" stroke-width="2"/>

        <!-- Icon: bar chart -->
        <g v-if="m.icon === 'bar'" :transform="`translate(${1208}, ${80 + i*112 + 28})`">
          <rect x="0"  y="22" width="9" height="20" rx="1.5" :fill="C_RED"/>
          <rect x="14" y="6"  width="9" height="36" rx="1.5" :fill="C_RED"/>
          <rect x="28" y="14" width="9" height="28" rx="1.5" :fill="C_RED"/>
        </g>
        <!-- Icon: database -->
        <g v-else-if="m.icon === 'db'" :transform="`translate(${1208}, ${80 + i*112 + 26})`">
          <ellipse cx="20" cy="6" rx="18" ry="5.5" :fill="C_RED"/>
          <path d="M 2 6 V 36 c 0 3 8 5.5 18 5.5 s 18 -2.5 18 -5.5 V 6
                   C 38 9 30 11.5 20 11.5 S 2 9 2 6 Z" :fill="C_RED"/>
          <path d="M 2 19 c 0 3 8 5.5 18 5.5 s 18 -2.5 18 -5.5"
                fill="none" stroke="#fff" stroke-width="2"/>
          <path d="M 2 30 c 0 3 8 5.5 18 5.5 s 18 -2.5 18 -5.5"
                fill="none" stroke="#fff" stroke-width="2"/>
        </g>
        <!-- Icon: dollar -->
        <g v-else-if="m.icon === 'dollar'" :transform="`translate(${1208}, ${80 + i*112 + 28})`">
          <circle cx="20" cy="20" r="19" :fill="C_RED"/>
          <text x="20" y="29" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
                style="font-size:26px;font-weight:800" fill="#fff">$</text>
        </g>
        <!-- Icon: reports -->
        <g v-else-if="m.icon === 'reports'" :transform="`translate(${1208}, ${80 + i*112 + 26})`">
          <path d="M 4 2 H 24 L 32 10 V 42 H 4 Z" fill="#fff" :stroke="C_RED" stroke-width="2.2" stroke-linejoin="round"/>
          <path d="M 24 2 V 10 H 32" fill="none" :stroke="C_RED" stroke-width="2.2" stroke-linejoin="round"/>
          <line x1="9"  y1="18" x2="22" y2="18" :stroke="C_RED" stroke-width="2" stroke-linecap="round"/>
          <line x1="9"  y1="24" x2="20" y2="24" :stroke="C_RED" stroke-width="2" stroke-linecap="round"/>
          <line x1="9"  y1="30" x2="18" y2="30" :stroke="C_RED" stroke-width="2" stroke-linecap="round"/>
          <rect x="20" y="28" width="13" height="13" rx="1.5" :fill="C_RED"/>
        </g>

        <!-- Labels -->
        <text x="1262" :y="80 + i * 112 + 50"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:15px;font-weight:700" :fill="C_DARK">{{ m.label1 }}</text>
        <text v-if="m.label2" x="1262" :y="80 + i * 112 + 70"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:15px;font-weight:700" :fill="C_DARK">{{ m.label2 }}</text>
      </g>
    </g>

    <!-- =====================================================
         Bottom "fail -> revise" arc with label inside
         ===================================================== -->
    <g :stroke="C_GREEN" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <path d="M 1030 532 V 562 H 580 V 538"/>
    </g>
    <polygon points="573,538 587,538 580,524" :fill="C_GREEN"/>
    <text x="800" y="555" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
          style="font-size:13px;font-weight:700" :fill="C_GREEN">fail -&gt; revise</text>
  </svg>
</template>

<style scoped>
.pipe {
  width: 1450px;
  height: 600px;
  display: block;
  background: #fff;
  flex: none;
}
.pipe :deep(text) {
  white-space: pre;
  font-family: Inter, system-ui, sans-serif;
  font-size: inherit;
}
</style>
