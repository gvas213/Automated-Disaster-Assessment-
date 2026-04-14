import { useState, useEffect, useRef} from 'react'
import { MapContainer, TileLayer, ImageOverlay, GeoJSON } from 'react-leaflet'
import { CustomZoomControl } from './MapControls'
import { bindPopupHandlers } from './PolygonPopup'
import 'leaflet/dist/leaflet.css'

const DEFAULT_CENTER = [29.7597, -95.4568]
const DEFAULT_ZOOM = 15

const DAMAGE_COLORS = {
  'no-damage':    '#22c55e',
  'minor-damage': '#eab308',
  'major-damage': '#fbb363',
  'destroyed':    '#ef4444',
}

// Normalize shape map_bounds
const normalizeBounds = (bounds) => {
  if (!bounds) return null

  // Already [[lat,lng],[lat,lng]]
  if (Array.isArray(bounds) && Array.isArray(bounds[0])) {
    const [[lat1, lng1], [lat2, lng2]] = bounds
    if (lat1 == null || lng1 == null || lat2 == null || lng2 == null) return null
    return bounds
  }

  // Object format: { sw: [lat, lng], ne: [lat, lng] }
  if (bounds.sw && bounds.ne) {
    return [bounds.sw, bounds.ne]
  }

  // Flat array: [minLat, minLng, maxLat, maxLng]
  if (Array.isArray(bounds) && bounds.length === 4) {
    return [[bounds[0], bounds[1]], [bounds[2], bounds[3]]]
  }

  return null
}

// -- COMPUTING MAP IMAGE BOUNDS --
const getBoundsFromGeoJSON = (geoData) => {
  if (!geoData || !geoData.features || geoData.features.length === 0) return null

  let minLat = Infinity, maxLat = -Infinity
  let minLng = Infinity, maxLng = -Infinity

  geoData.features.forEach(feature => {
    const coords = feature.geometry?.coordinates
    if (!coords) return

    // Flatten GeoJSON coordinates, nultiPolygon one extra level deeper than a regular Polygon since we only care abt [lng, lat] 
    // Polygon: [ [ [lng,lat], [lng,lat], ... ] ] → flat(1) gives [[lng,lat], ...]
    // MultiPolygon: [ [ [ [lng,lat], ... ] ] ]   → flat(2) gives [[lng,lat], ...]
    const flatCoords = feature.geometry.type === 'MultiPolygon'
      ? coords.flat(2)
      : coords.flat(1)

    // For each corner point of a polygon we update the bounding box if it's a new extreme
    // if any point is further in the direction then the previous --> update, & record outermost points
    flatCoords.forEach(([lng, lat]) => {
      if (lat < minLat) minLat = lat // tracking southernmost point
      if (lat > maxLat) maxLat = lat // tracking northernmost point
      if (lng < minLng) minLng = lng // tracking westernmost point
      if (lng > maxLng) maxLng = lng // tracking easternmost point
    })
  })

  const PAD = 0.001 // padding for polygons no clipping @ edge 
   
  // Stretch the image overlay on map based on SW/NE corner for leaflet
  return [
    [minLat - PAD, minLng - PAD], //Return SW corner  = (southernmost lat, westernmost lng)
    [maxLat + PAD, maxLng + PAD], //Return NE corner = (northernmost lat, easternmost lng) 
  ]
}

export default function Map({ currentIndex, onTotalChange, showPolygon }) {

  // --- STATE ---
  const [maps, setMaps] = useState([])       // all maps fetched from the API
  const [showAfter, setShowAfter] = useState(false) // toggle: false = before, true = after
  const [mapData, setMapData] = useState({}) // the GeoJSON damage polygon

  // Ref tracking whichever polygon tooltip is currently open
  const activeLayerRef = useRef(null)

  // --- FETCH ALL MAPS ON LOAD ---
  useEffect(() => {
    fetch('/api/maps')
      .then(res => res.json())
      .then(data => {
        const allMaps = data.maps
        setMaps(allMaps)
        onTotalChange(allMaps.length) // giving no. maps to navbar

        // Fetching all GeoJson at once, instead of one at a time 
        allMaps.forEach(map => {
          fetch(map.overlay_url) // fetch GeoJSON from API overlay_url
            .then(res => res.json())
            .then(geoData => {
              
              let bounds = null
              if (map.map_bounds) {
                bounds = normalizeBounds(map.map_bounds)
              } else {
                bounds = getBoundsFromGeoJSON(geoData) //Compute geojson cords
              }

              // Storing images that gave valid bounds, does not compute images with no coords 
              if (bounds) {
                setMapData(prev => ({
                  ...prev,
                  [map.map_id]: { bounds, geoData }
                }))
              }
            })
            .catch(err => console.error(`Failed to fetch GeoJSON for map ${map.map_id}:`, err))
        })
      })
      .catch(err => console.error('Failed to fetch maps:', err))
  }, [])

  // --- FETCH GEOJSON WHENEVER CURRENT MAP CHANGES ---
  const currentMap = maps[currentIndex]
  useEffect(() => {
    if (!currentMap) return
    fetch(currentMap.overlay_url) //fetch GeoJSON from API overlay_url instead of local file
      .then(res => res.json())
      .then(data => setGeoData(data))
      .catch(err => console.error('Failed to fetch GeoJSON:', err))
  }, [currentMap])

  // --- GEOJSON POLYGON STYLE ---
  // Color each polygon based on its damage_type property
  const getStyle = (feature) => {
    const damage = feature?.properties?.damage_type
    const fillColor = DAMAGE_COLORS[damage] || '#94a3b8' // gray if unknown
    return {
      color:       fillColor,
      fillColor,
      fillOpacity: 0.4,
      weight:      2,
    }
  }

  // --- BIND HOVER + CLICK + POPUP EVENTS FOR EACH POLYGON ---
  // Interaction logic is in bindPopupHandlers (PolygonPopup.jsx)
  const onEachFeature = (feature, layer) => {
    const damage = feature?.properties?.damage_type
    const damageColor = DAMAGE_COLORS[damage] || '#94a3b8' // gray if unknown
    bindPopupHandlers(feature, layer, activeLayerRef, damageColor)
  }

  return (
    <div style={{ width: '100vw', height: '100vh' }}>
      <style>{`
        .polygon-popup .leaflet-popup-content-wrapper {
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
          border-radius: 0 !important;
        }
        .polygon-popup .leaflet-popup-content {
          margin: 0 !important;
        }
        .polygon-popup .leaflet-popup-tip-container {
          display: none !important;
        }
        .leaflet-interactive:focus {
          outline: none !important;
        }
      `}</style>

      {/* PRE/POST TOGGLE BUTTON */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10000">
        <button
          onClick={() => setShowAfter(prev => !prev)}
          className="border border-zinc-600 bg-black/30 backdrop-blur-md text-white text-sm px-6 py-2 rounded-full hover:bg-white hover:text-black hover:border-transparent transition-all duration-300"
        >
          {showAfter ? 'Viewing: Post-Harvey' : 'Viewing: Pre-Harvey'}
        </button>
      </div>

      {/* -- DEBUG OVERLAY —- */}
      <div className="absolute top-20 left-4 z-10000 text-white text-xs bg-black/50 p-2 rounded space-y-1">
        <div>Total maps: {maps.length}</div>
        <div>Loaded tiles: {Object.keys(mapData).length}</div>
        <div>With polygons: {Object.values(mapData).filter(d => d.geoData?.features?.length > 0).length}</div>
        <div>No polygons (bounds only): {Object.values(mapData).filter(d => !d.geoData?.features?.length).length}</div>
        <div>Missing/failed: {maps.length - Object.keys(mapData).length}</div>
      </div>
      
      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ width: '100%', height: '100%' }}
        zoomControl={false}
      >
        <CustomZoomControl />

        {/* Dark base map */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
          subdomains="abcd"
          maxZoom={20}
        />

        {/* Render ALL image overlays at once */}
        {maps.map(map => {
          const data = mapData[map.map_id]
          if (!data?.bounds) return null
          return (
            <ImageOverlay
              key={`img-${map.map_id}`}
              url={showAfter ? map.images.after : map.images.before} // swap before/after on toggle
              bounds={data.bounds}
              opacity={1}
            />
          )
        })}

        {/* Render ALL damage polygons at once */}
        {showPolygon && maps.map(map => {
          const data = mapData[map.map_id]
          if (!data?.geoData) return null
          return (
            <GeoJSON
              key={`geo-${map.map_id}-${showAfter}`} 
              data={data.geoData}
              style={getStyle}
              onEachFeature={onEachFeature}
            />
          )
        })}
      </MapContainer>
    </div>
  )
}