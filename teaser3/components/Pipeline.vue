<script setup>
// Single-SVG pipeline diagram. Compact 1340 x 600 canvas (narrower than v3.1).

const C_BLUE   = '#1d4ed8'
const C_GREEN  = '#10a36e'
const C_ORANGE = '#ea580c'
const C_RED    = '#dc2626'
const C_DARK   = '#111827'

// Stage frames (narrower)
const stages = [
  { x:  20, y:  44, w: 210, h: 488, color: C_BLUE,   title: 'Stage 1: Scenario Seed' },
  { x: 252, y:  44, w: 560, h: 488, color: C_GREEN,  title: 'Stage 2: Multi-Agent Task Factory' },
  { x: 834, y:  44, w: 210, h: 488, color: C_ORANGE, title: 'Stage 3: Quality Review' },
  { x:1066, y:  44, w: 246, h: 488, color: C_RED,    title: 'Stage 4: Evaluation Release' },
]

const seeds = [
  { kind: 'doc',  label: 'GDPval' },
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
  <svg class="pipe" width="1340" height="600" viewBox="-15 -8 1370 612"
       preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
    <!-- ===== Title ===== -->
    <text x="666" y="28" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
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
    <g v-for="(x, i) in [232, 814, 1046]" :key="'ar'+i">
      <line :x1="x" y1="308" :x2="x+10" y2="308" stroke="#1f2937" stroke-width="3" stroke-linecap="round"/>
      <polygon :points="`${x+8},301 ${x+19},308 ${x+8},315`" fill="#1f2937"/>
    </g>

    <!-- =====================================================
         Stage 1: Scenario Seed - chips list
         Card x=40..210, y=72..504
         ===================================================== -->
    <g>
      <rect x="40" y="72" width="170" height="432" rx="14" ry="14"
            fill="#fff" :stroke="C_BLUE" stroke-width="2.5"/>

      <text x="125" y="100" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:800" :fill="C_DARK">Real-job seeds</text>

      <g v-for="(s, i) in seeds" :key="'seed'+i">
        <template v-if="s.kind === 'doc'">
          <rect x="54" :y="120 + i * 64" width="142" height="42" rx="8" ry="8"
                fill="#e9f0ff" stroke="none"/>
          <g :transform="`translate(66, ${127 + i * 64})`">
            <path d="M 4 2 H 12 L 17 7 V 28 H 4 Z" fill="none" :stroke="C_BLUE" stroke-width="1.8" stroke-linejoin="round"/>
            <path d="M 12 2 V 7 H 17" fill="none" :stroke="C_BLUE" stroke-width="1.8" stroke-linejoin="round"/>
            <line x1="7"  y1="13" x2="14" y2="13" :stroke="C_BLUE" stroke-width="1.6" stroke-linecap="round"/>
            <line x1="7"  y1="18" x2="14" y2="18" :stroke="C_BLUE" stroke-width="1.6" stroke-linecap="round"/>
            <line x1="7"  y1="23" x2="13" y2="23" :stroke="C_BLUE" stroke-width="1.6" stroke-linecap="round"/>
          </g>
          <text x="96" :y="146 + i * 64" font-family="Inter, system-ui, sans-serif"
                style="font-size:14px;font-weight:700" :fill="C_BLUE">{{ s.label }}</text>
        </template>
        <template v-else>
          <rect x="54" :y="120 + i * 64" width="142" height="32" rx="8" ry="8"
                fill="#e9f0ff" stroke="none"/>
          <text x="125" :y="142 + i * 64" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:18px;font-weight:700" :fill="C_BLUE" letter-spacing="3">···</text>
        </template>
      </g>

      <line x1="54" y1="468" x2="196" y2="468" stroke="#cbd5e1" stroke-width="1" stroke-dasharray="3 3"/>
      <text x="125" y="490" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:12px;font-weight:700" fill="#475569">1 scenario · n examples</text>
    </g>

    <!-- =====================================================
         Stage 2: Multi-Agent Task Factory  (frame x=252..812, center=532)
         ===================================================== -->

    <!-- Main Agent box (center=532, w=380) -->
    <g>
      <rect x="342" y="76" width="380" height="36" rx="8" ry="8"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <g transform="translate(360, 82)">
        <line x1="13" y1="2" x2="13" y2="6" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        <circle cx="13" cy="2" r="1.6" :fill="C_GREEN"/>
        <rect x="3" y="6" width="20" height="16" rx="3" ry="3" fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
        <circle cx="9"  cy="13" r="1.6" :fill="C_GREEN"/>
        <circle cx="17" cy="13" r="1.6" :fill="C_GREEN"/>
        <line x1="9" y1="18" x2="17" y2="18" :stroke="C_GREEN" stroke-width="1.8" stroke-linecap="round"/>
      </g>
      <text x="397" y="100" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px" :fill="C_DARK">
        <tspan style="font-weight:700">Main Agent: </tspan>
        <tspan>blueprint + integration</tspan>
      </text>
    </g>

    <!-- T-split: vertical at 532, horizontal from 324 (env center) to 658 -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" fill="none">
      <line x1="532" y1="112" x2="532" y2="128"/>
      <line x1="324" y1="128" x2="658" y2="128"/>
      <line x1="324" y1="128" x2="324" y2="140"/>
      <line x1="658" y1="128" x2="658" y2="140"/>
    </g>
    <polygon points="317,138 324,150 331,138" :fill="C_GREEN"/>
    <polygon points="651,138 658,150 665,138" :fill="C_GREEN"/>

    <!-- Env Builder Agent box: x=270..380, w=110, center=325 -->
    <g>
      <rect x="270" y="150" width="110" height="92" rx="10" ry="10"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <g transform="translate(313, 158)">
        <line x1="13" y1="2" x2="13" y2="6" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        <circle cx="13" cy="2" r="1.7" :fill="C_GREEN"/>
        <rect x="2" y="6" width="22" height="18" rx="3" ry="3" fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
        <circle cx="9"  cy="14" r="1.7" :fill="C_GREEN"/>
        <circle cx="17" cy="14" r="1.7" :fill="C_GREEN"/>
        <line x1="9" y1="20" x2="17" y2="20" :stroke="C_GREEN" stroke-width="1.8" stroke-linecap="round"/>
      </g>
      <text x="325" y="210" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:13px;font-weight:700" :fill="C_DARK">Env Builder</text>
      <text x="325" y="228" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:13px;font-weight:700" :fill="C_DARK">Agent</text>
    </g>

    <!-- Task Builder Agents box: x=400..794, w=394 -->
    <g>
      <rect x="400" y="150" width="394" height="92" rx="10" ry="10"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <text x="597" y="168" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:13px;font-weight:700" :fill="C_DARK">Task Builder Agents (per task)</text>

      <!-- 8 cells, each 42w x 56h, gap 5, padding 10 -->
      <g v-for="(c, i) in taskCells" :key="'tc'+i">
        <template v-if="c.kind === 'agent'">
          <rect :x="410 + i * 47" y="178" width="42" height="56" rx="6" ry="6"
                fill="#fff" :stroke="C_GREEN" stroke-width="1.5"/>
          <g :transform="`translate(${410 + i * 47 + 11}, 184)`">
            <line x1="10" y1="0" x2="10" y2="2.5" :stroke="C_GREEN" stroke-width="1.4" stroke-linecap="round"/>
            <circle cx="10" cy="0.5" r="1.1" :fill="C_GREEN"/>
            <rect x="2.5" y="2.5" width="15" height="12" rx="2.5" ry="2.5" fill="#fff" :stroke="C_GREEN" stroke-width="1.4"/>
            <circle cx="6.8"  cy="8" r="1.2" :fill="C_GREEN"/>
            <circle cx="13.2" cy="8" r="1.2" :fill="C_GREEN"/>
            <line x1="7" y1="12" x2="13" y2="12" :stroke="C_GREEN" stroke-width="1.3" stroke-linecap="round"/>
          </g>
          <text :x="410 + i * 47 + 21" y="217" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:10px;font-weight:600" fill="#0a7a52">{{ c.label1 }}</text>
          <text :x="410 + i * 47 + 21" y="229" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:10px;font-weight:600" fill="#0a7a52">{{ c.label2 }}</text>
        </template>
        <template v-else>
          <text :x="410 + i * 47 + 21" y="212" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:18px;font-weight:700" :fill="C_GREEN" letter-spacing="1">···</text>
        </template>
      </g>
    </g>

    <!-- Forward arrow from Tasks (597,242) -> down -> left -> Calibration top (532,278) -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none">
      <path d="M 597 242 V 260 H 532 V 270"/>
    </g>
    <polygon points="525,268 539,268 532,280" :fill="C_GREEN"/>

    <!-- Calibration Solvers: x=432..632, w=200, center=532 -->
    <g>
      <rect x="432" y="282" width="200" height="36" rx="8" ry="8"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <g transform="translate(445, 287)">
        <line x1="13" y1="2" x2="13" y2="6" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        <circle cx="13" cy="2" r="1.6" :fill="C_GREEN"/>
        <rect x="3" y="6" width="20" height="16" rx="3" ry="3" fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
        <circle cx="9"  cy="13" r="1.6" :fill="C_GREEN"/>
        <circle cx="17" cy="13" r="1.6" :fill="C_GREEN"/>
        <line x1="9" y1="18" x2="17" y2="18" :stroke="C_GREEN" stroke-width="1.8" stroke-linecap="round"/>
      </g>
      <text x="485" y="305" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Calibration Solvers</text>
    </g>

    <!-- "fail" loop: from Calibration right (632, 300) -> right (652) -> up to Tasks bottom -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none">
      <path d="M 632 300 H 652 V 248"/>
    </g>
    <polygon points="645,250 659,250 652,238" :fill="C_GREEN"/>
    <text x="662" y="276" font-family="Inter, system-ui, sans-serif"
          style="font-size:12px;font-weight:700" :fill="C_GREEN">fail</text>

    <!-- pass arrow: Calibration bottom (532,318) down to Outputs top (532,350) -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" fill="none">
      <line x1="532" y1="318" x2="532" y2="338"/>
    </g>
    <polygon points="524,336 540,336 532,350" :fill="C_GREEN"/>
    <text x="540" y="332" font-family="Inter, system-ui, sans-serif"
          style="font-size:12px;font-weight:700" :fill="C_GREEN">pass</text>

    <!-- Outputs group: x=270..794, w=524 -->
    <g>
      <rect x="270" y="350" width="524" height="168" rx="10" ry="10"
            fill="none" :stroke="C_GREEN" stroke-width="1.5" stroke-dasharray="6 4"/>
      <text x="532" y="370" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:13px;font-weight:700" :fill="C_GREEN">Outputs</text>

      <!-- 5 cells, 92 wide, gap 8, padding 16 -->
      <g v-for="(o, i) in outputs" :key="'o'+i">
        <rect :x="286 + i * 100" y="382" width="92" height="124" rx="10" ry="10"
              fill="#fff" :stroke="C_GREEN" stroke-width="1.5"/>

        <g v-if="o.icon === 'globe'" :transform="`translate(${286 + i * 100 + 34}, 404)`">
          <circle cx="12" cy="12" r="11" fill="none" :stroke="C_GREEN" stroke-width="2"/>
          <ellipse cx="12" cy="12" rx="5" ry="11" fill="none" :stroke="C_GREEN" stroke-width="2"/>
          <line x1="1" y1="12" x2="23" y2="12" :stroke="C_GREEN" stroke-width="2"/>
        </g>
        <g v-else-if="o.icon === 'docG'" :transform="`translate(${286 + i * 100 + 34}, 404)`">
          <path d="M 4 1 H 14 L 20 7 V 23 H 4 Z"
                fill="#fff" :stroke="C_GREEN" stroke-width="2" stroke-linejoin="round"/>
          <path d="M 14 1 V 7 H 20" fill="none" :stroke="C_GREEN" stroke-width="2" stroke-linejoin="round"/>
          <line x1="7"  y1="11" x2="9"  y2="11" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
          <line x1="7"  y1="15" x2="17" y2="15" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
          <line x1="7"  y1="19" x2="17" y2="19" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        </g>
        <g v-else-if="o.icon === 'shield'" :transform="`translate(${286 + i * 100 + 34}, 404)`">
          <path d="M 12 1 L 2 4 V 11 c 0 6 4 10 10 12 c 6 -2 10 -6 10 -12 V 4 Z" :fill="C_GREEN" stroke="none"/>
          <path d="M 7 12 L 10.5 15.5 L 17 9" stroke="#fff" stroke-width="2.5"
                stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        </g>

        <text :x="286 + i * 100 + 46" y="468" text-anchor="middle"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:12px;font-weight:700" fill="#0a7a52">{{ o.label1 }}</text>
        <text v-if="o.label2" :x="286 + i * 100 + 46" y="486" text-anchor="middle"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:12px;font-weight:700" fill="#0a7a52">{{ o.label2 }}</text>
      </g>
    </g>

    <!-- =====================================================
         Stage 3: Quality Review (frame 834..1044, center=939)
         ===================================================== -->
    <g>
      <!-- Structure Check -->
      <rect x="852" y="78" width="174" height="78" rx="10" ry="10"
            fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
      <g transform="translate(924, 86)">
        <rect x="2" y="6" width="26" height="32" rx="3" ry="3" fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
        <rect x="9" y="2" width="12" height="7" rx="1.5" ry="1.5" :fill="C_ORANGE" stroke="none"/>
        <path d="M 6 16 L 9 19 L 13 14" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <line x1="15" y1="17" x2="24" y2="17" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round"/>
        <path d="M 6 26 L 9 29 L 13 24" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <line x1="15" y1="27" x2="24" y2="27" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round"/>
      </g>
      <text x="939" y="138" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Structure</text>
      <text x="939" y="153" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Check</text>

      <line x1="939" y1="156" x2="939" y2="194" :stroke="C_ORANGE" stroke-width="3" stroke-linecap="round"/>
      <polygon points="931,192 947,192 939,206" :fill="C_ORANGE"/>

      <!-- Reviewers (6 mini robots in 2 rows × 3 cols) -->
      <rect x="852" y="212" width="174" height="116" rx="10" ry="10"
            fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
      <g v-for="(pos, ri) in [
        {x: 903, y: 222}, {x: 939, y: 222}, {x: 975, y: 222},
        {x: 903, y: 254}, {x: 939, y: 254}, {x: 975, y: 254},
      ]" :key="'rb'+ri" :transform="`translate(${pos.x - 12}, ${pos.y})`">
        <line x1="12" y1="0" x2="12" y2="4" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round"/>
        <circle cx="12" cy="0.5" r="1.6" :fill="C_ORANGE"/>
        <rect x="2" y="4" width="20" height="16" rx="3" ry="3" fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
        <circle cx="8"  cy="11" r="1.6" :fill="C_ORANGE"/>
        <circle cx="16" cy="11" r="1.6" :fill="C_ORANGE"/>
        <line x1="8" y1="16" x2="16" y2="16" :stroke="C_ORANGE" stroke-width="1.8" stroke-linecap="round"/>
      </g>
      <text x="939" y="300" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">6 Clean-Context</text>
      <text x="939" y="318" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Agent Reviewers</text>

      <line x1="939" y1="328" x2="939" y2="366" :stroke="C_ORANGE" stroke-width="3" stroke-linecap="round"/>
      <polygon points="931,364 947,364 939,378" :fill="C_ORANGE"/>

      <!-- 5/6 Pass -->
      <rect x="852" y="384" width="174" height="90" rx="10" ry="10"
            fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
      <g transform="translate(924, 394)">
        <path d="M 17 1 L 4 5 V 14 c 0 9 6 15 13 18 c 7 -3 13 -9 13 -18 V 5 Z" :fill="C_ORANGE" stroke="none"/>
        <path d="M 11 16 L 15 20 L 23 12" stroke="#fff" stroke-width="3"
              stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      </g>
      <text x="939" y="452" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:16px;font-weight:700" :fill="C_DARK">5 / 6 Pass</text>
    </g>

    <!-- =====================================================
         Stage 4: Evaluation Release (frame 1066..1312, center=1189)
         ===================================================== -->
    <g>
      <g v-for="(m, i) in metrics" :key="'m'+i">
        <rect x="1082" :y="80 + i * 112" width="214" height="96" rx="10" ry="10"
              fill="#fff" :stroke="C_RED" stroke-width="2"/>

        <g v-if="m.icon === 'bar'" :transform="`translate(${1100}, ${80 + i*112 + 28})`">
          <rect x="0"  y="22" width="9" height="20" rx="1.5" :fill="C_RED"/>
          <rect x="14" y="6"  width="9" height="36" rx="1.5" :fill="C_RED"/>
          <rect x="28" y="14" width="9" height="28" rx="1.5" :fill="C_RED"/>
        </g>
        <g v-else-if="m.icon === 'db'" :transform="`translate(${1100}, ${80 + i*112 + 26})`">
          <ellipse cx="20" cy="6" rx="18" ry="5.5" :fill="C_RED"/>
          <path d="M 2 6 V 36 c 0 3 8 5.5 18 5.5 s 18 -2.5 18 -5.5 V 6
                   C 38 9 30 11.5 20 11.5 S 2 9 2 6 Z" :fill="C_RED"/>
          <path d="M 2 19 c 0 3 8 5.5 18 5.5 s 18 -2.5 18 -5.5"
                fill="none" stroke="#fff" stroke-width="2"/>
          <path d="M 2 30 c 0 3 8 5.5 18 5.5 s 18 -2.5 18 -5.5"
                fill="none" stroke="#fff" stroke-width="2"/>
        </g>
        <g v-else-if="m.icon === 'dollar'" :transform="`translate(${1100}, ${80 + i*112 + 28})`">
          <circle cx="20" cy="20" r="19" :fill="C_RED"/>
          <text x="20" y="29" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
                style="font-size:26px;font-weight:800" fill="#fff">$</text>
        </g>
        <g v-else-if="m.icon === 'reports'" :transform="`translate(${1100}, ${80 + i*112 + 26})`">
          <path d="M 4 2 H 24 L 32 10 V 42 H 4 Z" fill="#fff" :stroke="C_RED" stroke-width="2.2" stroke-linejoin="round"/>
          <path d="M 24 2 V 10 H 32" fill="none" :stroke="C_RED" stroke-width="2.2" stroke-linejoin="round"/>
          <line x1="9"  y1="18" x2="22" y2="18" :stroke="C_RED" stroke-width="2" stroke-linecap="round"/>
          <line x1="9"  y1="24" x2="20" y2="24" :stroke="C_RED" stroke-width="2" stroke-linecap="round"/>
          <line x1="9"  y1="30" x2="18" y2="30" :stroke="C_RED" stroke-width="2" stroke-linecap="round"/>
          <rect x="20" y="28" width="13" height="13" rx="1.5" :fill="C_RED"/>
        </g>

        <text x="1154" :y="80 + i * 112 + 50"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:15px;font-weight:700" :fill="C_DARK">{{ m.label1 }}</text>
        <text v-if="m.label2" x="1154" :y="80 + i * 112 + 70"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:15px;font-weight:700" :fill="C_DARK">{{ m.label2 }}</text>
      </g>
    </g>

    <!-- =====================================================
         Bottom "fail -> revise" arc + label
         ===================================================== -->
    <g :stroke="C_GREEN" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <path d="M 939 532 V 562 H 532 V 538"/>
    </g>
    <polygon points="525,538 539,538 532,524" :fill="C_GREEN"/>
    <text x="735" y="555" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
          style="font-size:13px;font-weight:700" :fill="C_GREEN">fail -&gt; revise</text>
  </svg>
</template>

<style scoped>
.pipe {
  width: 1340px;
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
