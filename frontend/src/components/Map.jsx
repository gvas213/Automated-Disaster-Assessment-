import { useState, useEffect } from 'react'
import { MapContainer, TileLayer, ImageOverlay, GeoJSON, ZoomControl } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

const DEFAULT_CENTER = [29.7597, -95.4568]
const DEFAULT_ZOOM = 15

export default function Map({ currentIndex, onTotalChange, showPolygon }) {

  // --- STATE ---
  const [maps, setMaps] = useState([])         // all maps from the API
  const [showAfter, setShowAfter] = useState(false)  // toggle: false = before, true = after
  const [geoData, setGeoData] = useState(null) // the GeoJSON damage polygon

  // --- FETCH ALL MAPS ON LOAD ---
  useEffect(() => {
    fetch('https://automated-disaster-assessment-backend.onrender.com/api/maps')
      .then(res => res.json())
      .then(data => {
        setMaps(data.maps)
        onTotalChange(data.maps.length) // tell navbar how many maps there are
      })
      .catch(err => console.error('Failed to fetch maps:', err))
  }, [])

  // --- FETCH GEOJSON WHENEVER CURRENT MAP CHANGES ---
  const currentMap = maps[currentIndex]
  useEffect(() => {
    if (!currentMap) return
    fetch('/harvey-geojson-3.geojson')
      .then(res => res.json())
      .then(data => setGeoData(data))
      .catch(err => console.error('Failed to fetch GeoJSON:', err))
  }, [currentMap])

  // --- GEOJSON POLYGON STYLE ---
  // Color the polygon based on the damage property in the GeoJSON
  const getStyle = (feature) => {
    const damage = feature?.properties?.damage_type
  
    const colors = {
      'no-damage':    '#22c55e',  // green
      'minor-damage': '#eab308',  // yellow
      'major-damage': '#ef4444',  // red
      'destroyed':    '#ef4444',  // red
    }
  
    const color = colors[damage] || '#94a3b8' // gray if unknown
  
    return {
      color,
      fillColor: color,
      fillOpacity: 0.4,
      weight: 2
    }
  }

  return (
    <div style={{ width: '100vw', height: '100vh' }}>

      {/* PRE/POST TOGGLE BUTTON */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[10000]">
        <button
          onClick={() => setShowAfter(prev => !prev)}
          className="border border-zinc-600 bg-black/30 backdrop-blur-md text-white text-sm px-6 py-2 rounded-full hover:bg-white hover:text-black hover:border-transparent transition-all duration-300"
        >
          {showAfter ? 'Viewing: Post-Harvey' : 'Viewing: Pre-Harvey'}
        </button>
      </div>

      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ width: '100%', height: '100%' }}
        zoomControl={false}
      >
        <ZoomControl position="bottomleft" />

        {/* Dark base map */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
          subdomains="abcd"
          maxZoom={20}
        />

        {/* Aerial image overlay — swaps between before/after */}
        {currentMap && (
          <ImageOverlay
            url={showAfter ? currentMap.images.after : currentMap.images.before}
            bounds={currentMap.map_bounds}
            opacity={1}
          />
        )}

        {/* Damage polygon from GeoJSON */}
{/* Only show polygons if showPolygon is true */}
{geoData && showPolygon && <GeoJSON key={currentMap?.map_id} data={geoData} style={getStyle} />}
      </MapContainer>
    </div>
  )
}