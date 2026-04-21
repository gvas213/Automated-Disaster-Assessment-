import { Polyline, CircleMarker, Popup } from 'react-leaflet'

// Hurricane Harvey (AL092017) NHC Best Track data
// Source: al092017_best_track.kmz (National Hurricane Center)
// [lat, lng, maxWindKts, category, label, dateUTC, mslpMb]
const HARVEY_TRACK = [
  [  21.4,   -92.3,  30, 'TD', 'Tropical Depression',  '1200 UTC AUG 23 2017', 1006],
  [  21.6,   -92.4,  35, 'TS', 'Tropical Storm',      '1800 UTC AUG 23 2017', 1005],
  [  22.0,   -92.5,  40, 'TS', 'Tropical Storm',      '0000 UTC AUG 24 2017', 1003],
  [  22.8,   -92.6,  50, 'TS', 'Tropical Storm',      '0600 UTC AUG 24 2017',  997],
  [  23.7,   -93.1,  60, 'TS', 'Tropical Storm',      '1200 UTC AUG 24 2017',  986],
  [  24.4,   -93.6,  70, 'C1', 'Category 1',          '1800 UTC AUG 24 2017',  978],
  [  25.0,   -94.4,  80, 'C1', 'Category 1',          '0000 UTC AUG 25 2017',  973],
  [  25.6,   -95.1,  90, 'C2', 'Category 2',          '0600 UTC AUG 25 2017',  966],
  [  26.3,   -95.8,  95, 'C2', 'Category 2',          '1200 UTC AUG 25 2017',  949],
  [  27.1,   -96.3, 105, 'C3', 'Category 3',          '1800 UTC AUG 25 2017',  943],
  [  27.8,   -96.8, 115, 'C4', 'Category 4',          '0000 UTC AUG 26 2017',  941],
  [  28.0,   -96.9, 115, 'C4', 'Category 4',          '0300 UTC AUG 26 2017',  937],
  [  28.2,   -97.1, 105, 'C3', 'Category 3',          '0600 UTC AUG 26 2017',  948],
  [  28.7,   -97.3,  65, 'C1', 'Category 1',          '1200 UTC AUG 26 2017',  978],
  [  29.0,   -97.5,  50, 'TS', 'Tropical Storm',      '1800 UTC AUG 26 2017',  991],
  [  29.2,   -97.4,  45, 'TS', 'Tropical Storm',      '0000 UTC AUG 27 2017',  995],
  [  29.3,   -97.6,  40, 'TS', 'Tropical Storm',      '0600 UTC AUG 27 2017',  998],
  [  29.1,   -97.5,  35, 'TS', 'Tropical Storm',      '1200 UTC AUG 27 2017',  998],
  [  29.0,   -97.2,  35, 'TS', 'Tropical Storm',      '1800 UTC AUG 27 2017',  998],
  [  28.8,   -96.8,  35, 'TS', 'Tropical Storm',      '0000 UTC AUG 28 2017',  997],
  [  28.6,   -96.5,  40, 'TS', 'Tropical Storm',      '0600 UTC AUG 28 2017',  997],
  [  28.5,   -96.2,  40, 'TS', 'Tropical Storm',      '1200 UTC AUG 28 2017',  997],
  [  28.4,   -95.9,  40, 'TS', 'Tropical Storm',      '1800 UTC AUG 28 2017',  997],
  [  28.2,   -95.4,  40, 'TS', 'Tropical Storm',      '0000 UTC AUG 29 2017',  996],
  [  28.1,   -95.0,  40, 'TS', 'Tropical Storm',      '0600 UTC AUG 29 2017',  996],
  [  28.2,   -94.6,  40, 'TS', 'Tropical Storm',      '1200 UTC AUG 29 2017',  995],
  [  28.5,   -94.2,  45, 'TS', 'Tropical Storm',      '1800 UTC AUG 29 2017',  993],
  [  28.9,   -93.8,  45, 'TS', 'Tropical Storm',      '0000 UTC AUG 30 2017',  994],
  [  29.4,   -93.6,  40, 'TS', 'Tropical Storm',      '0600 UTC AUG 30 2017',  990],
  [  29.8,   -93.5,  40, 'TS', 'Tropical Storm',      '0800 UTC AUG 30 2017',  991],
  [  30.1,   -93.4,  40, 'TS', 'Tropical Storm',      '1200 UTC AUG 30 2017',  992],
  [  30.6,   -93.1,  35, 'TS', 'Tropical Storm',      '1800 UTC AUG 30 2017',  996],
  [  31.3,   -92.6,  30, 'TD', 'Tropical Depression',  '0000 UTC AUG 31 2017',  998],
  [  31.9,   -92.2,  25, 'TD', 'Tropical Depression',  '0600 UTC AUG 31 2017',  999],
  [  32.5,   -91.7,  20, 'TD', 'Tropical Depression',  '1200 UTC AUG 31 2017', 1001],
  [  33.4,   -90.9,  25, 'TD', 'Tropical Depression',  '1800 UTC AUG 31 2017', 1001],
  [  34.1,   -89.6,  30, 'TD', 'Tropical Depression',  '0000 UTC SEP 1 2017',  1000],
]

// Standard NHC category colors
const CATEGORY_COLORS = {
  TD: '#5B9BD5',   // blue
  TS: '#00E4D0',   // cyan
  C1: '#FFFF66',   // yellow
  C2: '#FFD700',   // gold
  C3: '#FF8C00',   // dark orange
  C4: '#FF3030',   // red
  C5: '#FF00FF',   // magenta
}

// Build colored line segments between consecutive track points
// Skip the gap between index 11 and 12 (dissipation over Caribbean)
function getSegments() {
  const segments = []
  for (let i = 0; i < HARVEY_TRACK.length - 1; i++) {
    const [lat1, lng1, , cat1] = HARVEY_TRACK[i]
    const [lat2, lng2, , cat2] = HARVEY_TRACK[i + 1]
    const catOrder = ['TD', 'TS', 'C1', 'C2', 'C3', 'C4', 'C5']
    const cat = catOrder.indexOf(cat2) >= catOrder.indexOf(cat1) ? cat2 : cat1
    segments.push({
      positions: [[lat1, lng1], [lat2, lng2]],
      color: CATEGORY_COLORS[cat] || '#5B9BD5',
    })
  }
  return segments
}

const segments = getSegments()

// Legend items for the path
const LEGEND_ITEMS = [
  { label: 'Tropical Depression', color: CATEGORY_COLORS.TD },
  { label: 'Tropical Storm',     color: CATEGORY_COLORS.TS },
  { label: 'Category 1',         color: CATEGORY_COLORS.C1 },
  { label: 'Category 2',         color: CATEGORY_COLORS.C2 },
  { label: 'Category 3',         color: CATEGORY_COLORS.C3 },
  { label: 'Category 4',         color: CATEGORY_COLORS.C4 },
]

export function HurricanePathLegend({ isOpen }) {
  if (!isOpen) return null
  return (
    <div style={{
      position: 'absolute',
      bottom: '24px',
      left: '16px',
      zIndex: 1000,
      backgroundColor: '#1e1e1e',
      borderRadius: '10px',
      padding: '13px 18px',
      boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
      minWidth: '170px',
    }}>
      <div style={{
        color: '#ffffff',
        fontWeight: 700,
        fontSize: '14px',
        marginBottom: '13px',
        textAlign: 'center',
      }}>
        Hurricane Path
      </div>
      {LEGEND_ITEMS.map(({ label, color }) => (
        <div key={label} style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          marginBottom: '8px',
        }}>
          <div style={{
            width: '28px',
            height: '4px',
            backgroundColor: color,
            borderRadius: '2px',
            flexShrink: 0,
          }} />
          <span style={{ color: '#fff', fontSize: '13px' }}>{label}</span>
        </div>
      ))}
    </div>
  )
}

export default function HurricanePath() {
  return (
    <>
      {/* Colored line segments */}
      {segments.map((seg, i) => (
        <Polyline
          key={`seg-${i}`}
          positions={seg.positions}
          pathOptions={{ color: seg.color, weight: 3, opacity: 0.9 }}
        />
      ))}

      {/* Track point markers */}
      {HARVEY_TRACK.map(([lat, lng, wind, cat, label, date, mslp], i) => (
        <CircleMarker
          key={`pt-${i}`}
          center={[lat, lng]}
          radius={cat === 'C4' ? 7 : cat === 'C3' ? 6 : cat === 'C2' ? 5.5 : cat === 'C1' ? 5 : 4}
          pathOptions={{
            color: '#fff',
            weight: 1,
            fillColor: CATEGORY_COLORS[cat] || '#5B9BD5',
            fillOpacity: 0.95,
          }}
        >
          <Popup>
            <div style={{
              fontFamily: 'system-ui, sans-serif',
              fontSize: '13px',
              lineHeight: '1.5',
              color: '#1e1e1e',
              minWidth: '160px',
            }}>
              <div style={{ fontWeight: 700, fontSize: '14px', marginBottom: '4px' }}>
                Hurricane Harvey
              </div>
              <div><strong>{label}</strong></div>
              <div>Wind: {wind} kt ({Math.round(wind * 1.151)} mph)</div>
              <div>Pressure: {mslp} mb</div>
              <div>{date}</div>
              <div style={{
                marginTop: '4px',
                display: 'inline-block',
                padding: '1px 8px',
                borderRadius: '4px',
                backgroundColor: CATEGORY_COLORS[cat],
                color: cat === 'C1' || cat === 'C2' ? '#000' : '#fff',
                fontWeight: 600,
                fontSize: '12px',
              }}>
                {label}
              </div>
            </div>
          </Popup>
        </CircleMarker>
      ))}
    </>
  )
}
