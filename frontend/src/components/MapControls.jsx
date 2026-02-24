import { useState } from 'react'
import { useMap } from 'react-leaflet'

// Severity Level Legend Items
const SEVERITY_LEVELS = [
  { label: 'No Damage', color: '#4ade80' },
  { label: 'Minor',     color: '#d9e96b' },
  { label: 'Moderate',  color: '#fbb363' },
  { label: 'Severe',    color: '#b91c1c' },
];

// Severity Legend
export function SeverityLegend({ isOpen }) {
  return isOpen ? (
    <div style={{
      position: 'absolute',
      bottom: '24px',
      right: '68px',  
      zIndex: 1000,
      backgroundColor: '#1e1e1e',
      borderRadius: '8px',
      padding: '10px 14px',  
      boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
      minWidth: '120px',    
    }}>
      {/* Legend Title */}
      <div style={{
        color: '#ffffff',
        fontWeight: '700',
        fontSize: '11px',     
        marginBottom: '10px',
        textAlign: 'center',
      }}>
        Severity Level
      </div>

      {/* Legend Rows */}
      {SEVERITY_LEVELS.map(({ label, color }) => (
        <div key={label} style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',           
          marginBottom: '6px', 
        }}>
          {/* Color Box of Severity*/}
          <div style={{
            width: '18px',      
            height: '18px',     
            backgroundColor: color,
            borderRadius: '4px',
            flexShrink: 0,
          }} />
          {/* Label*/}
          <span style={{
            color: '#ffffff',
            fontSize: '11px',   
            fontWeight: '400',
          }}>
            {label}
          </span>
        </div>
      ))}
    </div>
  ) : null
}

// Zoom Control & Severity Level Toggle Buttons 
export function CustomZoomControl() {
  const map = useMap()

  // Tracking Hover states --> Zoom In, Zoom Out, Severity Level Toggle Button
  const [hoveredIn, setHoveredIn] = useState(false)
  const [hoveredOut, setHoveredOut] = useState(false)
  const [hoveredToggle, setHoveredToggle] = useState(false)

  // Track Whether the Severity Legend is Open or Collapsed
  const [legendOpen, setLegendOpen] = useState(true)

  const buttonStyle = {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '36px',
    height: '36px',
    color: '#ffffff',
    border: '1px solid #444',
    cursor: 'pointer',
    fontSize: '20px',
    fontWeight: '300',
    userSelect: 'none',
    lineHeight: 1,
    transition: 'background-color 0.15s ease',
  }

  return (
    <>
      {/* Severity Legend Panel (controlled by legendOpen state) */}
      <SeverityLegend isOpen={legendOpen} />

      <div style={{
        position: 'absolute',
        bottom: '24px',
        right: '16px',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        gap: '2px',
        boxShadow: '0 2px 8px rgba(0,0,0,0.5)',
      }}>
        {/* Zoom In Button */}
        <button
          style={{
            ...buttonStyle,
            borderRadius: '6px 6px 0 0',
            backgroundColor: hoveredIn ? '#2a2a2a' : '#1e1e1e',
          }}
          onClick={() => map.zoomIn()}
          onMouseEnter={() => setHoveredIn(true)}
          onMouseLeave={() => setHoveredIn(false)}
          title="Zoom in"
        >
          +
        </button>

        {/* Zoom Out Button */}
        <button
          style={{
            ...buttonStyle,
            borderRadius: '0 0 6px 6px',
            marginBottom: '8px',  
            backgroundColor: hoveredOut ? '#2a2a2a' : '#1e1e1e',
          }}
          onClick={() => map.zoomOut()}
          onMouseEnter={() => setHoveredOut(true)}
          onMouseLeave={() => setHoveredOut(false)}
          title="Zoom out"
        >
          −
        </button>

        {/* Severity Legend Toggle Button */}
        <button
        style={{
            ...buttonStyle,
            borderRadius: '6px',
            fontSize: '24px',
            paddingBottom: '2px', 
            backgroundColor: hoveredToggle ? '#2a2a2a' : '#1e1e1e',
        }}
          onClick={() => setLegendOpen(!legendOpen)}
          onMouseEnter={() => setHoveredToggle(true)}
          onMouseLeave={() => setHoveredToggle(false)}
          title={legendOpen ? 'Hide legend' : 'Show legend'}
        >
          {/* Severity Legend Toggle Button: When Opened --> Faces (>) OR When Closed --> Faces (<) */}
          {legendOpen ? '›' : '‹'}
        </button>
      </div>
    </>
  )
}