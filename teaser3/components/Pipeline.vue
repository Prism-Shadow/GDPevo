<script setup>
// Single-SVG implementation. Everything (boxes, icons, arrows, text)
// is drawn at absolute coordinates inside one <svg> root.

// Color palette
const C_BLUE   = '#1d4ed8'
const C_GREEN  = '#10a36e'
const C_ORANGE = '#ea580c'
const C_RED    = '#dc2626'
const C_TEXT   = '#1f2937'
const C_DARK   = '#111827'

// Stage frame coordinates (x, y, width, height).
// Canvas viewBox: 1600 x 740. Frames span y=58..678.
const stages = [
  { x:  30, y:  56, w: 240, h: 596, color: C_BLUE,   title: 'Stage 1: Scenario Seed' },
  { x: 300, y:  56, w: 700, h: 596, color: C_GREEN,  title: 'Stage 2: Multi-Agent Task Factory' },
  { x:1030, y:  56, w: 240, h: 596, color: C_ORANGE, title: 'Stage 3: Quality Review' },
  { x:1300, y:  56, w: 270, h: 596, color: C_RED,    title: 'Stage 4: Evaluation Release' },
]

// 8 task cells inside the Task Builder Agents box
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

// 5 output cells
const outputs = [
  { icon: 'globe',  label1: 'Shared',  label2: 'Env' },
  { icon: 'docG',   label1: '5 Train', label2: 'Tasks' },
  { icon: 'docG',   label1: '5 Test',  label2: 'Tasks' },
  { icon: 'shield', label1: 'Evaluators', label2: '' },
  { icon: 'docG',   label1: 'Task',    label2: 'Notes' },
]

// 4 evaluation metrics
const metrics = [
  { icon: 'bar',     label1: 'avg@3',     label2: '' },
  { icon: 'db',      label1: 'Token Metrics', label2: '' },
  { icon: 'dollar',  label1: 'Cost Metrics',  label2: '' },
  { icon: 'reports', label1: 'Reports +',     label2: 'Skill Packages' },
]
</script>

<template>
  <svg class="pipe" width="1600" height="740" viewBox="-20 -10 1640 760"
       preserveAspectRatio="xMidYMid meet" xmlns="http://www.w3.org/2000/svg">
    <!-- ===== Title ===== -->
    <text x="800" y="36" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
          style="font-size:30px;font-weight:800" :fill="C_DARK">
      GDPevo Data Construction Pipeline
    </text>

    <!-- ===== 4 Stage frames (dashed rounded rect + colored title) ===== -->
    <g v-for="(s, i) in stages" :key="'frame'+i">
      <rect :x="s.x" :y="s.y" :width="s.w" :height="s.h" rx="8" ry="8"
            fill="none" :stroke="s.color" stroke-width="2" stroke-dasharray="6 5"/>
      <text :x="s.x + s.w/2" :y="s.y + 24" text-anchor="middle"
            font-family="Inter, system-ui, sans-serif"
            style="font-size:16px;font-weight:700" :fill="s.color">
        {{ s.title }}
      </text>
    </g>

    <!-- ===== Black inter-stage arrows (mid-vertical, y=370) ===== -->
    <g v-for="(x, i) in [275, 1005, 1275]" :key="'ar'+i">
      <line :x1="x" y1="370" :x2="x+15" y2="370" stroke="#1f2937" stroke-width="3" stroke-linecap="round"/>
      <polygon :points="`${x+13},362 ${x+25},370 ${x+13},378`" fill="#1f2937"/>
    </g>

    <!-- =====================================================
         Stage 1: Scenario Seed
         Card spans y=92..620 (within frame y=56..652)
         ===================================================== -->
    <g>
      <rect x="56" y="92" width="188" height="528" rx="14" ry="14"
            fill="#fff" :stroke="C_BLUE" stroke-width="2.5"/>

      <!-- Document with sprout, centered around (150, 320) -->
      <g transform="translate(105, 240)">
        <!-- Doc body -->
        <path d="M 5 0 H 60 L 90 30 V 130 H 5 Z"
              fill="#fff" :stroke="C_BLUE" stroke-width="3" stroke-linejoin="round"/>
        <!-- Folded corner -->
        <path d="M 60 0 V 30 H 90" fill="none" :stroke="C_BLUE" stroke-width="3" stroke-linejoin="round"/>
        <!-- Sprout stem -->
        <path d="M 48 110 V 70" :stroke="C_BLUE" stroke-width="3" stroke-linecap="round" fill="none"/>
        <!-- Left leaf -->
        <path d="M 48 90 C 32 90 22 80 22 64 C 40 64 48 74 48 90 Z"
              :fill="C_BLUE" :stroke="C_BLUE" stroke-width="2" stroke-linejoin="round"/>
        <!-- Right leaf -->
        <path d="M 48 78 C 64 78 74 68 74 52 C 56 52 48 62 48 78 Z"
              :fill="C_BLUE" :stroke="C_BLUE" stroke-width="2" stroke-linejoin="round"/>
        <!-- Soil bar -->
        <line x1="32" y1="112" x2="64" y2="112" :stroke="C_BLUE" stroke-width="3" stroke-linecap="round"/>
      </g>

      <!-- Caption -->
      <text x="150" y="430" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:18px;font-weight:700" :fill="C_TEXT">1 Scenario</text>
      <text x="150" y="456" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:18px;font-weight:700" :fill="C_TEXT">n Examples</text>
    </g>

    <!-- =====================================================
         Stage 2: Multi-Agent Task Factory
         y layout (within frame 56..676):
           Main Agent      : 92..132
           T-split         : 132..162
           Env / Tasks row : 162..280
           forward arrow   : 280..330
           Calibration box : 330..382
           pass arrow      : 382..438
           Outputs group   : 438..620
         ===================================================== -->

    <!-- Main Agent box (centered x=650) -->
    <g>
      <rect x="430" y="92" width="440" height="40" rx="8" ry="8"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <!-- Robot icon -->
      <g transform="translate(450, 100)">
        <line x1="13" y1="2" x2="13" y2="6" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        <circle cx="13" cy="2" r="1.6" :fill="C_GREEN"/>
        <rect x="3" y="6" width="20" height="16" rx="3" ry="3" fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
        <circle cx="9"  cy="13" r="1.6" :fill="C_GREEN"/>
        <circle cx="17" cy="13" r="1.6" :fill="C_GREEN"/>
        <line x1="9" y1="18" x2="17" y2="18" :stroke="C_GREEN" stroke-width="1.8" stroke-linecap="round"/>
      </g>
      <text x="490" y="118" font-family="Inter, system-ui, sans-serif"
            style="font-size:15px" :fill="C_DARK">
        <tspan font-weight="700">Main Agent: </tspan>
        <tspan>blueprint + integration</tspan>
      </text>
    </g>

    <!-- T-split: 132..162 -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" fill="none">
      <line x1="650" y1="132" x2="650" y2="148"/>
      <line x1="395" y1="148" x2="800" y2="148"/>
      <line x1="395" y1="148" x2="395" y2="160"/>
      <line x1="800" y1="148" x2="800" y2="160"/>
    </g>
    <polygon points="388,156 395,170 402,156" :fill="C_GREEN"/>
    <polygon points="793,156 800,170 807,156" :fill="C_GREEN"/>

    <!-- Env Builder Agent box: x=325..465, y=170..280 -->
    <g>
      <rect x="325" y="170" width="140" height="110" rx="10" ry="10"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <!-- Wrench icon -->
      <g transform="translate(379, 184)">
        <path d="M 22 4 a 8 8 0 1 0 6 11 L 18 6 z"
              :fill="C_GREEN" :stroke="C_GREEN" stroke-width="1.5" stroke-linejoin="round"/>
        <path d="M 18 6 L 4 22 a 2.6 2.6 0 0 0 3.5 3.5 L 24 10"
              :fill="C_GREEN" :stroke="C_GREEN" stroke-width="1.5" stroke-linejoin="round"/>
      </g>
      <text x="395" y="244" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Env Builder</text>
      <text x="395" y="262" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Agent</text>
    </g>

    <!-- Task Builder Agents box: x=485..965, y=170..280 -->
    <g>
      <rect x="485" y="170" width="480" height="110" rx="10" ry="10"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <text x="725" y="190" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:15px;font-weight:700" :fill="C_DARK">Task Builder Agents (per task)</text>

      <!-- 8 cells horizontally -->
      <g v-for="(c, i) in taskCells" :key="'tc'+i">
        <template v-if="c.kind === 'agent'">
          <rect :x="497 + i * 58" y="202" width="54" height="66" rx="6" ry="6"
                fill="#fff" :stroke="C_GREEN" stroke-width="1.5"/>
          <!-- mini robot -->
          <g :transform="`translate(${497 + i * 58 + 16}, 208)`">
            <line x1="11" y1="0" x2="11" y2="3" :stroke="C_GREEN" stroke-width="1.6" stroke-linecap="round"/>
            <circle cx="11" cy="0.5" r="1.2" :fill="C_GREEN"/>
            <rect x="3" y="3" width="16" height="13" rx="2.5" ry="2.5" fill="#fff" :stroke="C_GREEN" stroke-width="1.6"/>
            <circle cx="7.5"  cy="9" r="1.3" :fill="C_GREEN"/>
            <circle cx="14.5" cy="9" r="1.3" :fill="C_GREEN"/>
            <line x1="7.5" y1="13" x2="14.5" y2="13" :stroke="C_GREEN" stroke-width="1.4" stroke-linecap="round"/>
          </g>
          <text :x="497 + i * 58 + 27" y="246" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:11px;font-weight:600" fill="#0a7a52">{{ c.label1 }}</text>
          <text :x="497 + i * 58 + 27" y="260" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:11px;font-weight:600" fill="#0a7a52">{{ c.label2 }}</text>
        </template>
        <template v-else>
          <text :x="497 + i * 58 + 27" y="244" text-anchor="middle"
                font-family="Inter, system-ui, sans-serif"
                style="font-size:22px;font-weight:700" :fill="C_GREEN" letter-spacing="1">···</text>
        </template>
      </g>
    </g>

    <!-- Forward arrow Tasks(725,280) -> down -> left -> Calibration top(650,330) -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none">
      <path d="M 725 280 V 304 H 650 V 318"/>
    </g>
    <polygon points="643,316 657,316 650,330" :fill="C_GREEN"/>

    <!-- Calibration Solvers + Internal Reviewer Agent box: x=495..805, y=330..386 -->
    <g>
      <rect x="495" y="330" width="310" height="56" rx="10" ry="10"
            fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      <!-- Sliders icon -->
      <g transform="translate(510, 339)">
        <line x1="0"  y1="6"  x2="32" y2="6"  :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        <line x1="0"  y1="20" x2="32" y2="20" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        <line x1="0"  y1="34" x2="32" y2="34" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        <circle cx="9"  cy="6"  r="3.2" fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
        <circle cx="22" cy="20" r="3.2" fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
        <circle cx="14" cy="34" r="3.2" fill="#fff" :stroke="C_GREEN" stroke-width="2"/>
      </g>
      <text x="660" y="352" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Calibration Solvers +</text>
      <text x="660" y="372" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:14px;font-weight:700" :fill="C_DARK">Internal Reviewer Agent</text>
    </g>

    <!-- "fail" loop: Calibration right edge (805,358) -> right (840) -> up to Tasks bottom (840,280) -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" fill="none">
      <path d="M 805 358 H 840 V 286"/>
    </g>
    <polygon points="833,288 847,288 840,276" :fill="C_GREEN"/>
    <text x="852" y="320" font-family="Inter, system-ui, sans-serif"
          style="font-size:14px;font-weight:700" :fill="C_GREEN">fail</text>

    <!-- pass arrow: Calibration bottom (650,386) down to Outputs top (650,438) -->
    <g :stroke="C_GREEN" stroke-width="3" stroke-linecap="round" fill="none">
      <line x1="650" y1="386" x2="650" y2="424"/>
    </g>
    <polygon points="640,422 660,422 650,438" :fill="C_GREEN"/>
    <text x="660" y="412" font-family="Inter, system-ui, sans-serif"
          style="font-size:14px;font-weight:700" :fill="C_GREEN">pass</text>

    <!-- Outputs group: dashed rounded rect with title + 5 cells -->
    <g>
      <rect x="320" y="438" width="660" height="200" rx="10" ry="10"
            fill="none" :stroke="C_GREEN" stroke-width="1.5" stroke-dasharray="6 4"/>
      <text x="650" y="460" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:15px;font-weight:700" :fill="C_GREEN">Outputs</text>

      <!-- 5 cells, each 116w x 144h, gap 12 -->
      <g v-for="(o, i) in outputs" :key="'o'+i">
        <rect :x="336 + i * 128" y="476" width="116" height="146" rx="10" ry="10"
              fill="#fff" :stroke="C_GREEN" stroke-width="1.5"/>

        <!-- Icon: globe -->
        <g v-if="o.icon === 'globe'" :transform="`translate(${336 + i * 128 + 46}, 502)`">
          <circle cx="12" cy="12" r="11" fill="none" :stroke="C_GREEN" stroke-width="2"/>
          <ellipse cx="12" cy="12" rx="5" ry="11" fill="none" :stroke="C_GREEN" stroke-width="2"/>
          <line x1="1" y1="12" x2="23" y2="12" :stroke="C_GREEN" stroke-width="2"/>
        </g>
        <!-- Icon: document -->
        <g v-else-if="o.icon === 'docG'" :transform="`translate(${336 + i * 128 + 46}, 502)`">
          <path d="M 4 1 H 14 L 20 7 V 23 H 4 Z"
                fill="#fff" :stroke="C_GREEN" stroke-width="2" stroke-linejoin="round"/>
          <path d="M 14 1 V 7 H 20" fill="none" :stroke="C_GREEN" stroke-width="2" stroke-linejoin="round"/>
          <line x1="7"  y1="11" x2="9"  y2="11" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
          <line x1="7"  y1="15" x2="17" y2="15" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
          <line x1="7"  y1="19" x2="17" y2="19" :stroke="C_GREEN" stroke-width="2" stroke-linecap="round"/>
        </g>
        <!-- Icon: shield with check -->
        <g v-else-if="o.icon === 'shield'" :transform="`translate(${336 + i * 128 + 46}, 502)`">
          <path d="M 12 1 L 2 4 V 11 c 0 6 4 10 10 12 c 6 -2 10 -6 10 -12 V 4 Z" :fill="C_GREEN" stroke="none"/>
          <path d="M 7 12 L 10.5 15.5 L 17 9" stroke="#fff" stroke-width="2.5"
                stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        </g>

        <text :x="336 + i * 128 + 58" y="568" text-anchor="middle"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:13px;font-weight:700" fill="#0a7a52">{{ o.label1 }}</text>
        <text v-if="o.label2" :x="336 + i * 128 + 58" y="588" text-anchor="middle"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:13px;font-weight:700" fill="#0a7a52">{{ o.label2 }}</text>
      </g>
    </g>

    <!-- =====================================================
         Stage 3: Quality Review (frame 1030..1270, y=56..676)
         Inner content y=98..644
         ===================================================== -->
    <g>
      <!-- Structure Check: y=110..210 -->
      <rect x="1052" y="110" width="196" height="100" rx="10" ry="10"
            fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
      <g transform="translate(1135, 122)">
        <rect x="2" y="6" width="26" height="32" rx="3" ry="3" fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
        <rect x="9" y="2" width="12" height="7" rx="1.5" ry="1.5" :fill="C_ORANGE" stroke="none"/>
        <path d="M 6 16 L 9 19 L 13 14" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <line x1="15" y1="17" x2="24" y2="17" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round"/>
        <path d="M 6 26 L 9 29 L 13 24" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
        <line x1="15" y1="27" x2="24" y2="27" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round"/>
      </g>
      <text x="1150" y="180" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:16px;font-weight:700" :fill="C_DARK">Structure</text>
      <text x="1150" y="200" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:16px;font-weight:700" :fill="C_DARK">Check</text>

      <!-- Down arrow 1: y=210..256 -->
      <line x1="1150" y1="210" x2="1150" y2="252" :stroke="C_ORANGE" stroke-width="3" stroke-linecap="round"/>
      <polygon points="1140,250 1160,250 1150,266" :fill="C_ORANGE"/>

      <!-- Reviewers: y=276..406 -->
      <rect x="1052" y="276" width="196" height="130" rx="10" ry="10"
            fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
      <g v-for="(rx, ri) in [1112, 1150, 1188]" :key="'rb'+ri" :transform="`translate(${rx-12}, 296)`">
        <line x1="12" y1="0" x2="12" y2="4" :stroke="C_ORANGE" stroke-width="2" stroke-linecap="round"/>
        <circle cx="12" cy="0.5" r="1.6" :fill="C_ORANGE"/>
        <rect x="2" y="4" width="20" height="16" rx="3" ry="3" fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
        <circle cx="8"  cy="11" r="1.6" :fill="C_ORANGE"/>
        <circle cx="16" cy="11" r="1.6" :fill="C_ORANGE"/>
        <line x1="8" y1="16" x2="16" y2="16" :stroke="C_ORANGE" stroke-width="1.8" stroke-linecap="round"/>
      </g>
      <text x="1150" y="362" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:16px;font-weight:700" :fill="C_DARK">6 Clean-Context</text>
      <text x="1150" y="384" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:16px;font-weight:700" :fill="C_DARK">Agent Reviewers</text>

      <!-- Down arrow 2: y=406..452 -->
      <line x1="1150" y1="406" x2="1150" y2="448" :stroke="C_ORANGE" stroke-width="3" stroke-linecap="round"/>
      <polygon points="1140,446 1160,446 1150,462" :fill="C_ORANGE"/>

      <!-- 5/6 Pass: y=472..580 -->
      <rect x="1052" y="472" width="196" height="108" rx="10" ry="10"
            fill="#fff" :stroke="C_ORANGE" stroke-width="2"/>
      <g transform="translate(1133, 484)">
        <path d="M 17 1 L 4 5 V 14 c 0 9 6 15 13 18 c 7 -3 13 -9 13 -18 V 5 Z" :fill="C_ORANGE" stroke="none"/>
        <path d="M 11 16 L 15 20 L 23 12" stroke="#fff" stroke-width="3"
              stroke-linecap="round" stroke-linejoin="round" fill="none"/>
      </g>
      <text x="1150" y="552" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
            style="font-size:18px;font-weight:700" :fill="C_DARK">5 / 6 Pass</text>
    </g>

    <!-- =====================================================
         Stage 4: Evaluation Release (frame 1300..1570, y=56..652)
         4 cards stacked vertically inside; card x=1316..1554
         ===================================================== -->
    <g>
      <g v-for="(m, i) in metrics" :key="'m'+i">
        <rect x="1316" :y="98 + i * 132" width="238" height="112" rx="10" ry="10"
              fill="#fff" :stroke="C_RED" stroke-width="2"/>

        <!-- Icon: bar chart -->
        <g v-if="m.icon === 'bar'" :transform="`translate(${1342}, ${98 + i*132 + 36})`">
          <rect x="0"  y="22" width="9" height="20" rx="1.5" :fill="C_RED"/>
          <rect x="14" y="6"  width="9" height="36" rx="1.5" :fill="C_RED"/>
          <rect x="28" y="14" width="9" height="28" rx="1.5" :fill="C_RED"/>
        </g>
        <!-- Icon: database -->
        <g v-else-if="m.icon === 'db'" :transform="`translate(${1342}, ${98 + i*132 + 34})`">
          <ellipse cx="20" cy="6" rx="18" ry="5.5" :fill="C_RED"/>
          <path d="M 2 6 V 36 c 0 3 8 5.5 18 5.5 s 18 -2.5 18 -5.5 V 6
                   C 38 9 30 11.5 20 11.5 S 2 9 2 6 Z" :fill="C_RED"/>
          <path d="M 2 19 c 0 3 8 5.5 18 5.5 s 18 -2.5 18 -5.5"
                fill="none" stroke="#fff" stroke-width="2"/>
          <path d="M 2 30 c 0 3 8 5.5 18 5.5 s 18 -2.5 18 -5.5"
                fill="none" stroke="#fff" stroke-width="2"/>
        </g>
        <!-- Icon: dollar -->
        <g v-else-if="m.icon === 'dollar'" :transform="`translate(${1342}, ${98 + i*132 + 36})`">
          <circle cx="20" cy="20" r="19" :fill="C_RED"/>
          <text x="20" y="29" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
                style="font-size:26px;font-weight:800" fill="#fff">$</text>
        </g>
        <!-- Icon: reports -->
        <g v-else-if="m.icon === 'reports'" :transform="`translate(${1342}, ${98 + i*132 + 34})`">
          <path d="M 4 2 H 24 L 32 10 V 42 H 4 Z" fill="#fff" :stroke="C_RED" stroke-width="2.2" stroke-linejoin="round"/>
          <path d="M 24 2 V 10 H 32" fill="none" :stroke="C_RED" stroke-width="2.2" stroke-linejoin="round"/>
          <line x1="9"  y1="18" x2="22" y2="18" :stroke="C_RED" stroke-width="2" stroke-linecap="round"/>
          <line x1="9"  y1="24" x2="20" y2="24" :stroke="C_RED" stroke-width="2" stroke-linecap="round"/>
          <line x1="9"  y1="30" x2="18" y2="30" :stroke="C_RED" stroke-width="2" stroke-linecap="round"/>
          <rect x="20" y="28" width="13" height="13" rx="1.5" :fill="C_RED"/>
        </g>

        <!-- Labels (right of icon) -->
        <text x="1396" :y="98 + i * 132 + 58"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:17px;font-weight:700" :fill="C_DARK">{{ m.label1 }}</text>
        <text v-if="m.label2" x="1396" :y="98 + i * 132 + 80"
              font-family="Inter, system-ui, sans-serif"
              style="font-size:17px;font-weight:700" :fill="C_DARK">{{ m.label2 }}</text>
      </g>
    </g>

    <!-- =====================================================
         Bottom "fail -> revise" arc:
         from Stage 3 bottom-mid (1150, 652) down,
         left to (650), then up into Stage 2 bottom-mid (650, 652)
         ===================================================== -->
    <g :stroke="C_GREEN" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round">
      <path d="M 1150 652 V 678 H 650 V 658"/>
    </g>
    <polygon points="643,658 657,658 650,644" :fill="C_GREEN"/>
    <text x="900" y="700" text-anchor="middle" font-family="Inter, system-ui, sans-serif"
          style="font-size:15px;font-weight:700" :fill="C_GREEN">fail -&gt; revise</text>
  </svg>
</template>

<style scoped>
.pipe {
  width: 1600px;
  height: 740px;
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
