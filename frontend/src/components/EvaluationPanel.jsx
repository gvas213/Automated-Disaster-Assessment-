import { useEffect, useRef } from 'react'
import ReactECharts from 'echarts-for-react'

const ACTUAL = [
  { label: 'no-damage',     count: 4168 },
  { label: 'minor-damage',  count: 871  },
  { label: 'major-damage',  count: 2374 },
  { label: 'destroyed',     count: 196  },
  { label: 'unclassified',  count: 106  },
]

const PREDICTED = [
  { label: 'no-damage',     count: 7033 },
  { label: 'minor-damage',  count: 432  },
  { label: 'major-damage',  count: 221  },
  { label: 'destroyed',     count: 29   },
]

const TOTAL   = 7715
const CORRECT = 3835 + 62 + 53 + 0
const ACCURACY = ((CORRECT / TOTAL) * 100).toFixed(1)

// confusion matrix data — rows = ground truth, cols = predicted
// order: destroyed, major-damage, minor-damage, no-damage
const CM_AXIS = ['destroyed', 'major-dmg', 'minor-dmg', 'no-damage']

// row totals for normalization (ground truth counts, excluding unclassified)
const ROW_TOTALS = {
  0: 196,   // destroyed
  1: 2374,  // major-damage
  2: 871,   // minor-damage
  3: 4168,  // no-damage
}

// [predicted_index, truth_index, value]
const CM_RAW = [
  // ground truth: destroyed
  [0, 0, 0],
  [1, 0, 5],
  [2, 0, 17],
  [3, 0, 174],

  // ground truth: major-damage
  [0, 1, 9],
  [1, 1, 53],
  [2, 1, 160],
  [3, 1, 2152],

  // ground truth: minor-damage
  [0, 2, 1],
  [1, 2, 17],
  [2, 2, 62],
  [3, 2, 791],

  // ground truth: no-damage
  [0, 3, 16],
  [1, 3, 78],
  [2, 3, 239],
  [3, 3, 3835],
]

const MAX_CM_VAL = Math.max(...CM_RAW.map(d => d[2]))

function getHeatmapOption() {
  return {
    backgroundColor: 'transparent',
    grid: {
      top: 40,
      bottom: 80,
      left: 90,
      right: 40,
    },
    xAxis: {
      type: 'category',
      data: CM_AXIS,
      name: 'Predicted',
      nameLocation: 'middle',
      nameGap: 36,
      nameTextStyle: { color: '#ffffff', fontSize: 12 },
      axisLabel: {
        color: '#ffffff',
        fontSize: 11,
      },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'category',
      data: CM_AXIS,
      name: 'Ground truth',
      nameLocation: 'middle',
      nameGap: 72,
      nameTextStyle: { color: '#ffffff', fontSize: 12 },
      axisLabel: {
        color: '#ffffff',
        fontSize: 11,
      },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: 'rgba(255,255,255,0.15)' } },
      splitLine: { show: false },
    },
    visualMap: {
      min: 0,
      max: MAX_CM_VAL,
      show: false,
      inRange: {
        color: ['#1a1a2e', '#16213e', '#0f3460', '#533483', '#7F77DD'],
      },
    },
    series: [
      {
        type: 'heatmap',
        data: CM_RAW.map(([x, y, v]) => {
          const isDiag = x === y
          const rowTotal = ROW_TOTALS[y]
          const pct = rowTotal > 0 ? ((v / rowTotal) * 100).toFixed(1) : '0.0'
          return {
            value: [x, y, v],
            pct,
            itemStyle: {
              color: isDiag
                ? `rgba(29,158,117,${v === 0 ? 0.05 : 0.15 + (v / MAX_CM_VAL) * 0.75})`
                : v === 0
                ? 'rgba(255,255,255,0.03)'
                : `rgba(210,60,60,${0.08 + (v / MAX_CM_VAL) * 0.75})`,
              borderColor: 'rgba(255,255,255,0.05)',
              borderWidth: 1,
            },
          }
        }),
        label: {
          show: true,
          rich: {
            pct: {
              fontSize: 13,
              fontWeight: 'bold',
              color: '#ffffff',
              lineHeight: 20,
            },
            count: {
              fontSize: 11,
              color: 'rgba(255,255,255,0.65)',
              lineHeight: 18,
            },
          },
          formatter: params => {
            const [, y, v] = params.value
            const rowTotal = ROW_TOTALS[y]
            const pct = rowTotal > 0 ? ((v / rowTotal) * 100).toFixed(1) : '0.0'
            const countStr = v > 0 ? v.toLocaleString() : '—'
            if (v === 0) return `{count|—}`
            return `{pct|${pct}%}\n{count|${countStr}}`
          },
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 6,
            shadowColor: 'rgba(255,255,255,0.2)',
          },
        },
      },
    ],
    tooltip: {
      formatter: params => {
        const [xi, yi, v] = params.value
        const rowTotal = ROW_TOTALS[yi]
        const pct = rowTotal > 0 ? ((v / rowTotal) * 100).toFixed(1) : '0.0'
        return `
          <div style="font-size:12px; line-height:1.8;">
            <b>Truth:</b> ${CM_AXIS[yi]}<br/>
            <b>Predicted:</b> ${CM_AXIS[xi]}<br/>
            <b>Count:</b> ${v.toLocaleString()}<br/>
            <b>Row %:</b> ${pct}%
          </div>
        `
      },
      backgroundColor: '#1c1c2e',
      borderColor: 'rgba(255,255,255,0.1)',
      textStyle: { color: '#ffffff' },
    },
  }
}

function BarChart() {
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
    const actualMap  = Object.fromEntries(ACTUAL.map(d => [d.label, d.count]))
    const predMap    = Object.fromEntries(PREDICTED.map(d => [d.label, d.count]))

    const legendH = 24
    const padL = 52, padR = 16, padT = legendH + 16, padB = 48
    const chartW = W - padL - padR
    const chartH = H - padT - padB

    const maxCount = Math.max(...categories.flatMap(c => [actualMap[c] || 0, predMap[c] || 0]))
    const yMax = Math.ceil(maxCount / 1000) * 1000

    const textCol  = 'rgba(255,255,255,0.85)'
    const gridCol  = 'rgba(255,255,255,0.08)'
    const actualCol = '#7F77DD'
    const predCol   = '#5DCAA5'

    ctx.clearRect(0, 0, W, H)

    // legend at top left
    const legendItems = [
      ['actual (ground truth)', actualCol],
      ['predicted',             predCol],
    ]
    let lx = padL
    const ly = 6
    legendItems.forEach(([label, col]) => {
      ctx.fillStyle = col
      ctx.fillRect(lx, ly, 12, 12)
      ctx.fillStyle = textCol
      ctx.font = '11px system-ui'
      ctx.textAlign = 'left'
      ctx.fillText(label, lx + 16, ly + 10)
      const textW = ctx.measureText(label).width
      lx += 16 + textW + 24
    })

    // grid lines + y axis labels
    const yTicks = 5
    for (let i = 0; i <= yTicks; i++) {
      const val = Math.round((yMax / yTicks) * i)
      const y = padT + chartH - (val / yMax) * chartH
      ctx.strokeStyle = gridCol
      ctx.lineWidth = 0.5
      ctx.beginPath(); ctx.moveTo(padL, y); ctx.lineTo(padL + chartW, y); ctx.stroke()
      ctx.fillStyle = textCol
      ctx.font = '11px system-ui'
      ctx.textAlign = 'right'
      ctx.fillText(val.toLocaleString(), padL - 6, y + 4)
    }

    // bars
    const groupW = chartW / categories.length
    const barW   = groupW * 0.28

    categories.forEach((cat, i) => {
      const gx = padL + i * groupW + groupW / 2
      const aVal = actualMap[cat] || 0
      const pVal = predMap[cat]   || 0

      const drawBar = (val, x, color) => {
        const bh = (val / yMax) * chartH
        const by = padT + chartH - bh
        ctx.fillStyle = color
        ctx.fillRect(x - barW / 2, by, barW, bh)
        ctx.fillStyle = 'rgba(255,255,255,0.9)'
        ctx.font = '10px system-ui'
        ctx.textAlign = 'center'
        ctx.fillText(val.toLocaleString(), x, by - 4)
      }

      drawBar(aVal, gx - barW * 0.6, actualCol)
      drawBar(pVal, gx + barW * 0.6, predCol)

      ctx.fillStyle = textCol
      ctx.font = '11px system-ui'
      ctx.textAlign = 'center'
      const shortCat = cat.replace('-damage', '-dmg')
      ctx.fillText(shortCat, gx, padT + chartH + 18)
    })
  }, [])

  return <canvas ref={canvasRef} style={{ width: '100%', height: '280px', display: 'block' }} />
}

function DonutAccuracy() {
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

    const cx = size / 2, cy = size / 2, r = size * 0.38, thickness = size * 0.1
    const ratio = CORRECT / TOTAL
    const trackCol = 'rgba(255,255,255,0.1)'

    ctx.clearRect(0, 0, size, size)
    ctx.strokeStyle = trackCol
    ctx.lineWidth = thickness
    ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke()

    ctx.strokeStyle = '#7F77DD'
    ctx.lineWidth = thickness
    ctx.lineCap = 'round'
    ctx.beginPath()
    ctx.arc(cx, cy, r, -Math.PI / 2, -Math.PI / 2 + ratio * Math.PI * 2)
    ctx.stroke()

    ctx.fillStyle = 'rgba(255,255,255,0.95)'
    ctx.font = `500 ${size * 0.16}px system-ui`
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(`${ACCURACY}%`, cx, cy)
  }, [])

  return <canvas ref={canvasRef} style={{ width: '140px', height: '140px', display: 'block' }} />
}

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

        {/* Summary stat cards */}
        <div className="grid grid-cols-3 gap-4">
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <p className="text-xs text-white mb-1">Total polygons</p>
            <p className="text-2xl font-medium">{TOTAL.toLocaleString()}</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <p className="text-xs text-white mb-1">Correct predictions</p>
            <p className="text-2xl font-medium text-teal-400">{CORRECT.toLocaleString()}</p>
          </div>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <p className="text-xs text-white mb-1">Overall accuracy</p>
            <p className="text-2xl font-medium text-purple-400">{ACCURACY}%</p>
          </div>
        </div>

        {/* Bar chart + donut row */}
        <div className="flex gap-4">

          {/* Bar chart */}
          <div className="flex-1 rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <p className="text-xs text-white mb-4">Predicted vs actual severity distribution</p>
            <BarChart />
          </div>

          {/* Donut */}
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 flex flex-col items-center justify-center gap-4" style={{ width: '200px' }}>
            <p className="text-xs text-white text-center">Overall accuracy</p>
            <DonutAccuracy />
            <div className="text-center flex flex-col gap-1">
              <p className="text-xs text-white">{TOTAL.toLocaleString()} total</p>
              <p className="text-xs text-white">{CORRECT.toLocaleString()} correct</p>
              <p className="text-xs text-white">{(TOTAL - CORRECT).toLocaleString()} incorrect</p>
            </div>
          </div>

        </div>

        {/* Confusion matrix — ECharts heatmap */}
        <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
          <p className="text-xs text-white mb-1">Confusion matrix</p>
          <p className="text-xs text-zinc-400 mb-1">
            Rows = ground truth &nbsp; &nbsp; Columns = predicted &nbsp; &nbsp;
            <span style={{ color: '#1D9E75' }}> green diagonal = correct</span> &nbsp; &nbsp;
            <span style={{ color: '#D23C3C' }}> red = misclassified</span>
          </p>
          {/* <p className="text-xs text-zinc-500 mb-4">
            Each cell shows <span className="text-white font-semibold">row % (normalized)</span> on top and <span className="text-zinc-300">raw count</span> below
          </p> */}
          <ReactECharts
            option={getHeatmapOption()}
            style={{ height: '360px', width: '100%' }}
            theme="dark"
          />
        </div>

      </div>
    </div>
  )
}