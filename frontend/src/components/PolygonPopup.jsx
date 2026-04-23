import L from 'leaflet'

const SEVERITY_LABELS = {
  'no-damage':    'No Damage',
  'minor-damage': 'Minor Damage',
  'major-damage': 'Major Damage',
  'destroyed':    'Destroyed',
}

// --- LEAFLET POPUP OPTIONS ---
// Popup always stays open until closed or another polygon is pressed
export const popupOptions = {
  closeButton: false,         
  autoClose: false,          
  closeOnClick: false,       
  className: 'polygon-popup', 
  maxWidth: 320,
  offset: [0, -6],           
}

// --- HTML STRING FOR LEAFLET POPUP - Content inside popup itself ---
export function buildPopupHTML(feature) {
  const { damage_type, damage_cost } = feature.properties

  // Format damage cost as USD
  const formattedCost = damage_cost
    ? `$${Number(damage_cost).toLocaleString()}`
    : 'N/A'

  const severity    = SEVERITY_LABELS[damage_type] || 'Unknown'
  const description = feature.properties.description || 'N/A'

  return `
    <div style="
      position: relative;
      background-color: #1e1e1e;
      border-radius: 12px;
      padding: 18px 24px;
      min-width: 260px;
      color: #ffffff;
      font-family: sans-serif;
      box-shadow: 0 4px 16px rgba(0,0,0,0.5);
    ">
      <!-- X close button — identified by data-close-popup for event delegation in bindPopupHandlers -->
      <button
        data-close-popup="true"
        style="
          position: absolute;
          top: 10px;
          right: 12px;
          background: none;
          border: none;
          color: #ffffff;
          font-size: 16px;
          cursor: pointer;
          line-height: 1;
          padding: 2px 4px;
          opacity: 0.7;
        "
      >&times;</button>

      <div style="font-weight:700; font-size:16px; text-align:center; margin-bottom:16px;">
        More Information
      </div>
      ${[
        ['Damage Cost',   formattedCost],
        ['Severity Level', severity],
        ['Description',    description],
      ].map(([label, value]) => `
        <div style="display:flex; justify-content:space-between; gap:20px; margin-bottom:12px;">
          <span style="font-weight:700; font-size:13px; white-space:nowrap;">${label}</span>
          <span style="font-size:13px; color:#e2e8f0;">${value}</span>
        </div>
      `).join('')}
    </div>
  `
}

// --- BIND ALL POPUP INTERACTION HANDLERS TO A LAYER ---
// Call this from onEachFeature in Map.jsx
export function bindPopupHandlers(feature, layer, activeLayerRef, damageColor, onSelect, onDeselect) {

  // Binding Leaflet POPUP 
  layer.bindPopup(buildPopupHTML(feature), popupOptions)

  // --- HOVER — boost fill opacity on hover, border color stays as damage color ---
  layer.on('mouseover', () => {
    layer.setStyle({
      fillOpacity: 0.7,
      weight: 3,
      color: damageColor,
    })
  })

  // --- CLICK — close old popup + reset old style ---
  layer.on('click', () => {
    if (activeLayerRef.current && activeLayerRef.current !== layer) {
      activeLayerRef.current.closePopup()
      // Reset previous layer to default: colored border always visible
      activeLayerRef.current.setStyle({ fillOpacity: 0.4, weight: 2, color: damageColor })
      onDeselect?.()
    }

    // Open this layer's popup and mark it as active
    layer.openPopup()
    activeLayerRef.current = layer

    onSelect?.(feature)

    // --- X BUTTON CLOSE ---
    setTimeout(() => {
      const popupEl = layer.getPopup()?.getElement()
      if (!popupEl) return

      popupEl.addEventListener('click', (e) => {
        if (e.target.closest('[data-close-popup]')) {
          layer.closePopup()
          // Reset to default: colored border always visible
          layer.setStyle({ fillOpacity: 0.4, weight: 2, color: damageColor })
          activeLayerRef.current = null

          onDeselect?.()
        }
      })
    }, 0)
  })

  // --- MOUSEOUT — reset border only if layer isn't the current polygon that has pop up open---
  layer.on('mouseout', () => {
    if (activeLayerRef.current === layer) return
    // Restore default style: colored border always visible
    layer.setStyle({
      fillOpacity: 0.4,
      weight: 2,
      color: damageColor,
    })
  })
}