import { useEffect, useRef, useState } from 'react'
import ReactECharts from 'echarts-for-react'

// ─── TRAIN DATA ───────────────────────────────────────────────────────────────

const TRAIN_ACTUAL = [
  { label: 'no-damage',     count: 4168 },
  { label: 'minor-damage',  count: 871  },
  { label: 'major-damage',  count: 2374 },
  { label: 'destroyed',     count: 196  },
  { label: 'unclassified',  count: 106  },
]

const TRAIN_PREDICTED = [
  { label: 'no-damage',     count: 7033 },
  { label: 'minor-damage',  count: 432  },
  { label: 'major-damage',  count: 221  },
  { label: 'destroyed',     count: 29   },
]

const TRAIN_TOTAL    = 7715
const TRAIN_CORRECT  = 3835 + 62 + 53 + 0
const TRAIN_ACCURACY = ((TRAIN_CORRECT / TRAIN_TOTAL) * 100).toFixed(1)
const TRAIN_PARTIAL  = 66.4

const TRAIN_ROW_TOTALS = { 0: 196, 1: 2374, 2: 871, 3: 4168 }

const TRAIN_CM_RAW = [
  [0,0,0],[1,0,5],[2,0,17],[3,0,174],
  [0,1,9],[1,1,53],[2,1,160],[3,1,2152],
  [0,2,1],[1,2,17],[2,2,62],[3,2,791],
  [0,3,16],[1,3,78],[2,3,239],[3,3,3835],
]

// ─── TEST DATA ────────────────────────────────────────────────────────────────

const TEST_ACTUAL = [
  { label: 'no-damage',     count: 11423 },
  { label: 'minor-damage',  count: 2663  },
  { label: 'major-damage',  count: 8238  },
  { label: 'destroyed',     count: 401   },
  { label: 'unclassified',  count: 289   },
]

const TEST_PREDICTED = [
  { label: 'no-damage',     count: 10426 + 7337 + 2414 + 358 + 215 },
  { label: 'minor-damage',  count: 705 + 622 + 182 + 32 + 35 },
  { label: 'major-damage',  count: 262 + 258 + 63 + 9 + 29 },
  { label: 'destroyed',     count: 30 + 21 + 4 + 2 + 10 },
]

const TEST_TOTAL    = 23014
const TEST_CORRECT  = 10426 + 182 + 258 + 2
const TEST_ACCURACY = ((TEST_CORRECT / TEST_TOTAL) * 100).toFixed(1)
const TEST_PARTIAL  = 63.8

const TEST_ROW_TOTALS = {
  0: 401,
  1: 8238,
  2: 2663,
  3: 11423,
}

const TEST_CM_RAW = [
  [0,0,2],[1,0,9],[2,0,32],[3,0,358],
  [0,1,21],[1,1,258],[2,1,622],[3,1,7337],
  [0,2,4],[1,2,63],[2,2,182],[3,2,2414],
  [0,3,30],[1,3,262],[2,3,705],[3,3,10426],
]

// ─── SHARED ───────────────────────────────────────────────────────────────────

const CM_AXIS = ['destroyed', 'major-dmg', 'minor-dmg', 'no-damage']

function getHeatmapOption(cmRaw, rowTotals) {
  const maxVal = Math.max(...cmRaw.map(d => d[2]))
  return {
    backgroundColor: 'transparent',
    grid: { top: 40, bottom: 80, left: 90, right: 40 },
    xAxis: {
      type: 'category', data: CM_AXIS, name: 'Predicted',
      nameLocation: 'middle', nameGap: 36,
      nameTextStyle: { color: '#ffffff', fontSize: 12 },
      axisLabel: { color: '#ffffff', fontSize: 11 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'category', data: CM_AXIS, name: 'Ground truth',
      nameLocation: 'middle', nameGap: 72,
      nameTextStyle: { color: '#ffffff', fontSize: 12 },
      axisLabel: { color: '#ffffff', fontSize: 11 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      splitLine: { show: false },
    },
    visualMap: {
      min: 0, max: maxVal, show: false,
      inRange: { color: ['#1a1a2e','#16213e','#0f3460','#533483','#7F77DD'] },
    },
    series: [{
      type: 'heatmap',
      data: cmRaw.map(([x, y, v]) => {
        const isDiag = x === y
        const rowTotal = rowTotals[y]
        const pct = rowTotal > 0 ? ((v / rowTotal) * 100).toFixed(1) : '0.0'
        return {
          value: [x, y, v], pct,
          itemStyle: {
            color: isDiag
              ? `rgba(29,158,117,${v === 0 ? 0.05 : 0.15 + (v / maxVal) * 0.75})`
              : v === 0
              ? 'rgba(255,255,255,0.03)'
              : `rgba(210,60,60,${0.08 + (v / maxVal) * 0.75})`,
            borderColor: 'rgba(255,255,255,0.05)', borderWidth: 1,
          },
        }
      }),
      label: {
        show: true,
        rich: {
          pct:   { fontSize: 13, fontWeight: 'bold', color: '#ffffff', lineHeight: 20 },
          count: { fontSize: 11, color: 'rgba(255,255,255,0.65)', lineHeight: 18 },
        },
        formatter: params => {
          const [, y, v] = params.value
          const rowTotal = rowTotals[y]
          const pct = rowTotal > 0 ? ((v / rowTotal) * 100).toFixed(1) : '0.0'
          if (v === 0) return `{count|—}`
          return `{pct|${pct}%}\n{count|${v.toLocaleString()}}`
        },
      },
      emphasis: { itemStyle: { shadowBlur: 6, shadowColor: 'rgba(255,255,255,0.2)' } },
    }],
    tooltip: {
      formatter: params => {
        const [xi, yi, v] = params.value
        const rowTotal = rowTotals[yi]
        const pct = rowTotal > 0 ? ((v / rowTotal) * 100).toFixed(1) : '0.0'
        return `<div style="font-size:12px;line-height:1.8;">
          <b>Truth:</b> ${CM_AXIS[yi]}<br/>
          <b>Predicted:</b> ${CM_AXIS[xi]}<br/>
          <b>Count:</b> ${v.toLocaleString()}<br/>
          <b>Row %:</b> ${pct}%
        </div>`
      },
      backgroundColor: '#1c1c2e',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#ffffff' },
    },
  }
}

// ─── BAR CHART ────────────────────────────────────────────────────────────────

function BarChart({ actual, predicted }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    const dpr = window.devicePixelRatio || 1
    const W = canvas.offsetWidth
    const H = canvas.offsetHeight
    canvas.width  = W * dpr
    canvas.height = H * dpr
    ctx.scale(dpr, dpr)

    const categories = ['no-damage', 'minor-damage', 'major-damage', 'destroyed']
    const actualMap  = Object.fromEntries(actual.map(d => [d.label, d.count]))
    const predMap    = Object.fromEntries(predicted.map(d => [d.label, d.count]))

    const padL = 60, padR = 16, padT = 36, padB = 48
    const chartW = W - padL - padR
    const chartH = H - padT - padB

    const maxCount = Math.max(...categories.flatMap(c => [actualMap[c] || 0, predMap[c] || 0]))
    const yMax = Math.ceil(maxCount / 1000) * 1000

    const textCol   = 'rgba(255,255,255,0.85)'
    const gridCol   = 'rgba(255,255,255,0.08)'
    const actualCol = '#7F77DD'
    const predCol   = '#5DCAA5'

    ctx.clearRect(0, 0, W, H)

    ctx.font = '11px system-ui'
    const legendItems = [['actual (ground truth)', actualCol], ['predicted', predCol]]
    const itemWidths = legendItems.map(([label]) => 12 + 6 + ctx.measureText(label).width)
    const legendGap = 20
    const totalLegendW = itemWidths.reduce((a,b) => a+b, 0) + legendGap * (legendItems.length - 1)
    let lx = W - padR - totalLegendW
    legendItems.forEach(([label, col], i) => {
      ctx.fillStyle = col; ctx.fillRect(lx, 8, 12, 12)
      ctx.fillStyle = textCol; ctx.font = '11px system-ui'; ctx.textAlign = 'left'
      ctx.fillText(label, lx + 18, 18)
      lx += itemWidths[i] + legendGap
    })

    for (let i = 0; i <= 5; i++) {
      const val = Math.round((yMax / 5) * i)
      const y = padT + chartH - (val / yMax) * chartH
      ctx.strokeStyle = gridCol; ctx.lineWidth = 0.5
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + chartW, y); ctx.stroke()
      ctx.fillStyle = textCol; ctx.font = '11px system-ui'; ctx.textAlign = 'right'
      ctx.fillText(val.toLocaleString(), padL - 6, y + 4)
    }

    const groupW = chartW / categories.length
    const barW   = groupW * 0.28

    categories.forEach((cat, i) => {
      const gx = padL + i * groupW + groupW / 2
      const aVal = actualMap[cat] || 0
      const pVal = predMap[cat]   || 0

      const drawBar = (val, x, color) => {
        const bh = (val / yMax) * chartH
        const by = padT + chartH - bh
        ctx.fillStyle = color; ctx.fillRect(x - barW/2, by, barW, bh)
        ctx.fillStyle = 'rgba(255,255,255,0.9)'
        ctx.font = '10px system-ui'; ctx.textAlign = 'center'
        ctx.fillText(val.toLocaleString(), x, by - 4)
      }

      drawBar(aVal, gx - barW * 0.6, actualCol)
      drawBar(pVal, gx + barW * 0.6, predCol)

      ctx.fillStyle = textCol; ctx.font = '11px system-ui'; ctx.textAlign = 'center'
      ctx.fillText(cat.replace('-damage', '-dmg'), gx, padT + chartH + 18)
    })
  }, [actual, predicted])

  return <canvas ref={canvasRef} style={{ width: '100%', height: '280px', display: 'block' }} />
}

// ─── DONUT ────────────────────────────────────────────────────────────────────

function DonutAccuracy({ correct, total, accuracy }) {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr  = window.devicePixelRatio || 1
    const size = canvas.offsetWidth
    canvas.width  = size * dpr
    canvas.height = size * dpr
    const ctx = canvas.getContext('2d')
    ctx.scale(dpr, dpr)

    const cx = size/2, cy = size/2, r = size * 0.38, thickness = size * 0.1
    const ratio = correct / total

    ctx.clearRect(0, 0, size, size)
    ctx.strokeStyle = 'rgba(255,255,255,0.1)'
    ctx.lineWidth = thickness
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke()

    ctx.strokeStyle = '#7F77DD'
    ctx.lineWidth = thickness
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.arc(cx, cy, r, -Math.PI/2, -Math.PI/2 + ratio * Math.PI * 2)
    ctx.stroke()

    ctx.fillStyle = 'rgba(255,255,255,0.95)'
    ctx.font = `500 ${size * 0.16}px system-ui`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(`${accuracy}%`, cx, cy)
  }, [correct, total, accuracy])

  return <canvas ref={canvasRef} style={{ width: '140px', height: '140px', display: 'block' }} />
}

// ─── SECTION COMPONENT ────────────────────────────────────────────────────────

function EvalSection({ label, actual, predicted, total, correct, accuracy, partial, cmRaw, rowTotals }) {
  const incorrect = total - correct
  return (
    <div className="flex flex-col gap-6">

      {/* Section label */}
      <div className="flex items-center gap-3">
        <span className="text-xl font-bold uppercase tracking-widest text-white px-2 py-1">
          {label} DATA
        </span>
      </div>

      {/* Summary stat cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-xs text-zinc-400 mb-1">Total polygons</p>
          <p className="text-2xl font-medium">{total.toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-xs text-zinc-400 mb-1">Correct predictions</p>
          <p className="text-2xl font-medium">{correct.toLocaleString()}</p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-xs text-zinc-400 mb-1">Exact accuracy</p>
          <p className="text-2xl font-medium text-purple-400">{accuracy}%</p>
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-xs text-zinc-400 mb-1">Partial score</p>
          <p className="text-2xl font-medium text-teal-400">{partial}%</p>
        </div>
      </div>

      {/* Bar chart + donut row */}
      <div className="flex gap-4">
        <div className="flex-1 rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-sm font-medium text-white mb-4">Predicted vs actual severity distribution</p>
          <BarChart actual={actual} predicted={predicted} />
        </div>
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 flex flex-col items-center justify-center gap-4" style={{ width: '200px' }}>
          <p className="text-xs text-zinc-400 text-center">Exact accuracy</p>
          <DonutAccuracy correct={correct} total={total} accuracy={accuracy} />
          <div className="text-center flex flex-col gap-1">
            <p className="text-xs text-zinc-400">{total.toLocaleString()} total</p>
            <p className="text-xs text-teal-400">{correct.toLocaleString()} correct</p>
            <p className="text-xs text-red-400">{incorrect.toLocaleString()} incorrect</p>
          </div>
        </div>
      </div>

      {/* Confusion matrix */}
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <p className="text-sm font-medium text-white mb-1">Confusion matrix</p>
            <p className="text-xs text-zinc-500">
              Each cell shows <span className="text-white font-semibold">row % (normalized)</span> on top and <span className="text-zinc-300">raw count</span> below
            </p>
          </div>
          <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-xs shrink-0 ml-6">
            <span className="text-zinc-400">Rows = Ground Truth</span>
            <span style={{ color: '#1D9E75' }}>Green = Correct</span>
            <span className="text-zinc-400">Columns = Predicted</span>
            <span style={{ color: '#D23C3C' }}>Red = Misclassified</span>
          </div>
        </div>
        <ReactECharts
          option={getHeatmapOption(cmRaw, rowTotals)}
          style={{ height: '360px', width: '100%' }}
          theme="dark"
        />
      </div>

    </div>
  )
}

// ─── ACCORDION TOGGLE SECTION ─────────────────────────────────────────────────

function AccordionSection({ title, children }) {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
      <button
        onClick={() => setOpen(prev => !prev)}
        className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-zinc-800 transition-colors"
      >
        <span className="text-sm font-semibold text-white tracking-wide">{title}</span>
        <svg
          xmlns="http://www.w3.org/2000/svg"
          viewBox="0 0 24 24"
          fill="currentColor"
          style={{
            width: 16,
            height: 16,
            color: 'rgba(255,255,255,0.5)',
            transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.2s ease',
            flexShrink: 0,
          }}
        >
          <path fillRule="evenodd" d="M12.53 16.28a.75.75 0 0 1-1.06 0l-7.5-7.5a.75.75 0 0 1 1.06-1.06L12 14.69l6.97-6.97a.75.75 0 1 1 1.06 1.06l-7.5 7.5Z" clipRule="evenodd" />
        </svg>
      </button>

      {open && (
        <div className="px-5 pb-5 border-t border-zinc-800">
          {children}
        </div>
      )}
    </div>
  )
}

// ─── SCORING TABLE ────────────────────────────────────────────────────────────

function ScoringTable() {
  const rows = [
    {
      rule: 'Correct Prediction',
      score: '1.00 pt',
      scoreColor: '#FFFFFF',
      desc: "The model's prediction was spot on with the ground truth label.",
    },
    {
      rule: 'Off by 1 Level',
      score: '0.50 pt',
      scoreColor: '#FFFFFF',
      desc: "The model's prediction was off by one severity level — e.g. ground truth was \"Minor Damage\" but the model predicted \"No Damage\" or \"Major Damage\".",
    },
    {
      rule: 'Off by 2 Levels',
      score: '0.25 pt',
      scoreColor: '#FFFFFF',
      desc: "The model's prediction was off by two severity levels — e.g. ground truth was \"Minor Damage\" but the model predicted \"Destroyed\".",
    },
    {
      rule: 'Off by 3 Levels',
      score: '0.00 pt',
      scoreColor: '#FFFFFF',
      desc: "The model's prediction was off by three severity levels — e.g. ground truth was \"No Damage\" but the model predicted \"Destroyed\".",
    },
  ]

 return (
  <div className="rounded-lg overflow-hidden border border-zinc-700 mt-4">
    <table style={{ width: '100%', borderCollapse: 'collapse' }}>
      <thead>
        <tr style={{ backgroundColor: 'rgba(255,255,255,0.05)' }}>
          <th className="text-left text-xs font-semibold text-zinc-300 px-4 py-3" style={{ borderRight: '1px solid rgba(255,255,255,0.08)' }}>Rule</th>
          <th className="text-left text-xs font-semibold text-zinc-300 px-4 py-3" style={{ borderRight: '1px solid rgba(255,255,255,0.08)' }}>Score</th>
          <th className="text-left text-xs font-semibold text-zinc-300 px-4 py-3">Description</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr
            key={i}
            style={{
              borderTop: '1px solid rgba(255,255,255,0.06)',
              // backgroundColor: i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.02)',
            }}
          >
            <td className="px-4 py-3 text-xs text-white font-medium whitespace-nowrap" style={{ borderRight: '1px solid rgba(255,255,255,0.08)' }}>{row.rule}</td>
            <td className="px-4 py-3 text-xs font-bold whitespace-nowrap text-white" style={{ borderRight: '1px solid rgba(255,255,255,0.08)' }}>{row.score}</td>
            <td className="px-4 py-3 text-xs text-zinc-400 leading-relaxed">{row.desc}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
)
}

// ─── INFO SECTIONS CONTENT ────────────────────────────────────────────────────

function PartialVsExactContent() {
  return (
    <div className="flex flex-col gap-4 pt-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-zinc-700 bg-zinc-800 p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-bold px-0 py-0.5 rounded-full text-white">Exact Accuracy</span>
          </div>
          <p className="text-xs text-zinc-300 leading-relaxed">
            Indicates how often the model is correct according to the ground truth label. A prediction is measured based on if is right or wrong, where no partial credit is given.
          </p>
        </div>
        <div className="rounded-lg border border-zinc-700 bg-zinc-800 p-4">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-bold px-0 py-0.5 rounded-full text-white">Partial Score</span>
          </div>
          <p className="text-xs text-zinc-300 leading-relaxed">
            Indicates how close the model’s predictions were to the ground truth label when incorrect. Partial credit is given, if the prediction was a near-miss. 
          </p>
        </div>
      </div>

     
    </div>
  )
}

function PartialScoringContent() {
  return (
    <div className="flex flex-col gap-4 pt-4">
      {/* <div>
        <p className="text-xs font-semibold text-zinc-300 mb-3">Severity Levels</p>
        <div className="flex gap-2 flex-wrap">
          {[
            { level: '0', label: 'No Damage',    color: '#5DCAA5' },
            { level: '1', label: 'Minor Damage',  color: '#7F77DD' },
            { level: '2', label: 'Major Damage',  color: '#F59E0B' },
            { level: '3', label: 'Destroyed',     color: '#EF4444' },
          ].map(({ level, label, color }) => (
            <div
              key={level}
              className="flex items-center gap-2 rounded-lg border border-zinc-700 bg-zinc-800 px-3 py-2"
            >
              <span
                className="text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center flex-shrink-0"
                style={{ backgroundColor: `${color}22`, color }}
              >
                {level}
              </span>
              <span className="text-xs text-zinc-300">{label}</span>
            </div>
          ))}
        </div>
      </div> */}

      <div className="mb-6">
        <p className="text-xs font-semibold text-zinc-300 mb-1">Scoring Rules</p>
        <p className="text-xs text-zinc-400 mb-2">
          Partial scoring, scores the VLM predictions based on how close the categorization prediction was correspondent to the ground truth damage level.
          For each polygon that the VLM predicts, its is scored through this system: 
        </p>
        <ScoringTable />
      </div>

      
      <div className="flex flex-col gap-1">
        {/* Title */}
        <p className="text-xs font-semibold text-zinc-300 mb-1">
          Partial Scoring Calculation
        </p>

        {/* Description */}
        <p className="text-xs text-zinc-400 leading-relaxed">
          The partial score is the average of all partial scores calculated for every polygon prediction. It results in a higher value than the exact accuracy, since near-misses are given partial credit rather than being treated as complete failures.
        </p>

        {/* Formula */}
        <div className="flex justify-center mt-2">
          <p className="text-xs font-mono text-zinc-300 text-center">
            partial score = Σ(partial credits) / total polygons
          </p>
        </div>
      </div>
 
    </div>
  )
}

function ProblemsFacedContent() {
  return (
    <div className="flex flex-col gap-4 pt-4">
      <div className="rounded-lg border border-zinc-700 bg-zinc-800 p-4">
        <div className="flex items-start gap-3">
          <div
            className="w-2 h-2 rounded-full mt-1.5 shrink-0"
            style={{ backgroundColor: '#EF4444' }}
          />
          <div>
            <p className="text-xs font-semibold text-white mb-2">Prediction Behavior Under Uncertainty</p>
            <ul className="flex flex-col gap-2">
              <li className="text-xs text-zinc-400 leading-relaxed">
                The model has a tendency to predict <span className="text-white font-medium">"no-damage"</span> when faced with uncertainty rather than categorizing a building to a higher severity level. However, when the ground truth label is no-damaged, the model is highly accurate in identifying it. 
              </li>
            
            </ul>
          </div>
        </div>
      </div>

      <div className="rounded-lg border border-zinc-700 bg-zinc-800 p-4">
        <div className="flex items-start gap-3">
          <div
            className="w-2 h-2 rounded-full mt-1.5 shrink-0"
            style={{ backgroundColor: '#EF4444' }}
          />
          <div>
            <p className="text-xs font-semibold text-white mb-2">Precise Classification</p>
            <p className="text-xs text-zinc-400 leading-relaxed">
              The model captures the overall severity scale, but can inaccurately predict adjacent categories lacking precise predictions.
            </p>
          </div>
        </div>
      </div>

    </div>
  )
}

// ─── MAIN PANEL ───────────────────────────────────────────────────────────────

export default function EvaluationPanel({ onClose }) {
  return (
    <div className="fixed inset-0 z-20000 bg-zinc-950 text-white overflow-y-auto">

      {/* Top bar */}
      <div className="sticky top-0 z-10 bg-zinc-950 border-b border-zinc-800 px-6 py-4 flex items-center gap-4">
        <button
          onClick={onClose}
          className="flex items-center gap-2 text-white hover:text-white transition-colors text-sm"
        >
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" style={{ width: 18, height: 18 }}>
            <path fillRule="evenodd" d="M7.72 12.53a.75.75 0 0 1 0-1.06l7.5-7.5a.75.75 0 1 1 1.06 1.06L9.31 12l6.97 6.97a.75.75 0 1 1-1.06 1.06l-7.5-7.5Z" clipRule="evenodd" />
          </svg>
          Back to map
        </button>
        <div className="w-px h-4 bg-zinc-700" />
        <span className="text-white text-sm font-medium">Model evaluation</span>
      </div>

      {/* Page content */}
      <div className="max-w-5xl mx-auto px-6 py-8 flex flex-col gap-6">

        {/* ── TRAIN SECTION ── */}
        <EvalSection
          label="Train"
          actual={TRAIN_ACTUAL}
          predicted={TRAIN_PREDICTED}
          total={TRAIN_TOTAL}
          correct={TRAIN_CORRECT}
          accuracy={TRAIN_ACCURACY}
          partial={TRAIN_PARTIAL}
          cmRaw={TRAIN_CM_RAW}
          rowTotals={TRAIN_ROW_TOTALS}
        />

        {/* ── DIVIDER ── */}
        <div className="flex items-center py-2">
          <div className="w-full h-px bg-zinc-700" />
        </div>

        {/* ── TEST SECTION ── */}
        <EvalSection
          label="Test"
          actual={TEST_ACTUAL}
          predicted={TEST_PREDICTED}
          total={TEST_TOTAL}
          correct={TEST_CORRECT}
          accuracy={TEST_ACCURACY}
          partial={TEST_PARTIAL}
          cmRaw={TEST_CM_RAW}
          rowTotals={TEST_ROW_TOTALS}
        />

        {/* ── DIVIDER ── */}
        <div className="flex items-center py-2">
          <div className="w-full h-px bg-zinc-700" />
        </div>

        {/* ── ACCORDION INFO SECTIONS ── */}
        <div className="flex flex-col gap-3">
          <AccordionSection title="Exact Accuracy vs Partial Score">
            <PartialVsExactContent />
          </AccordionSection>

          <AccordionSection title="Partial Scoring">
            <PartialScoringContent />
          </AccordionSection>

          <AccordionSection title="Problems Faced">
            <ProblemsFacedContent />
          </AccordionSection>
        </div>

      </div>
    </div>
  )
}