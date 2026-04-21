
import { useState, useEffect, useRef, useCallback, useMemo} from 'react'
import { MapContainer, TileLayer, ImageOverlay, GeoJSON, useMap, useMapEvents} from 'react-leaflet' // added useMap for FlyToLocation
import L from 'leaflet'
import { CustomZoomControl } from './MapControls'
import { bindPopupHandlers } from './PolygonPopup'
import { useMapNavigation } from './useMapNavigation'
import HurricanePath, { HurricanePathLegend } from './HurricanePath'
import 'leaflet/dist/leaflet.css'

const DEFAULT_CENTER = [29.7597, -95.4568]
const DEFAULT_ZOOM = 15

const DAMAGE_COLORS = {
  'no-damage':    '#22c55e',
  'minor-damage': '#eab308',
  'major-damage': '#fbb363',
  'destroyed':    '#ef4444',
}

const normalizeBounds = (bounds) => {
  if (!bounds) return null
  if (Array.isArray(bounds) && Array.isArray(bounds[0])) {
    const [[lat1, lng1], [lat2, lng2]] = bounds
    if (lat1 == null || lng1 == null || lat2 == null || lng2 == null) return null
    return bounds
  }
  if (bounds.sw && bounds.ne) {
    return [bounds.sw, bounds.ne]
  }
  if (Array.isArray(bounds) && bounds.length === 4) {
    return [[bounds[0], bounds[1]], [bounds[2], bounds[3]]]
  }
  return null
}

const getBoundsFromGeoJSON = (geoData) => {
  if (!geoData || !geoData.features || geoData.features.length === 0) return null

  let minLat = Infinity, maxLat = -Infinity
  let minLng = Infinity, maxLng = -Infinity

  geoData.features.forEach(feature => {
    const coords = feature.geometry?.coordinates
    if (!coords) return
    const flatCoords = feature.geometry.type === 'MultiPolygon'
      ? coords.flat(2)
      : coords.flat(1)
    flatCoords.forEach(([lng, lat]) => {
      if (lat < minLat) minLat = lat
      if (lat > maxLat) maxLat = lat
      if (lng < minLng) minLng = lng
      if (lng > maxLng) maxLng = lng
    })
  })

  const PAD = 0.001 // padding for polygons no clipping @ edge
  // Stretch the image overlay on map based on SW/NE corner for leaflet
  return [
    [minLat - PAD, minLng - PAD], //Return SW corner  = (southernmost lat, westernmost lng)
    [maxLat + PAD, maxLng + PAD], //Return NE corner = (northernmost lat, easternmost lng)
  ]
}
function FlyToLocation({ target }) {
  const map = useMap()
  useEffect(() => {
    if (target) {
      map.flyTo(target.center, 17, { duration: 1.2 }) // zoom 17, 1.2s animation
    }
  }, [target, map]) // re-runs when a new tile is clicked or arrow is pressed
  return null
}
// Only renders overlays whose bounds intersect the current map viewport
function ViewportOverlays({ maps, mapData, showAfter, showPolygon, polygonMinZoom, getStyle, onEachFeature, onZoomChange }) {
  const map = useMap()
  const [visibleBounds, setVisibleBounds] = useState(() => map.getBounds())
  const [zoom, setZoom] = useState(() => map.getZoom())

  useMapEvents({
    moveend: () => {
      setVisibleBounds(map.getBounds())
      const newZoom = map.getZoom()
      setZoom(newZoom)
      onZoomChange?.(newZoom)
    },
  })

  const visibleMaps = useMemo(() => {
    if (!visibleBounds) return []
    const padded = visibleBounds.pad(0.2)
    return maps.filter(m => {
      const data = mapData[m.map_id]
      if (!data?.bounds) return false
      const overlayBounds = L.latLngBounds(data.bounds[0], data.bounds[1])
      return padded.intersects(overlayBounds)
    })
  }, [visibleBounds, maps, mapData])

  return (
    <>
      {visibleMaps.map(map => {
        const data = mapData[map.map_id]
        return (
          <ImageOverlay
            key={`img-${map.map_id}`}
            url={showAfter ? map.images.after : map.images.before}
            bounds={data.bounds}
            opacity={1}
          />
        )
      })}

      {showPolygon && zoom >= polygonMinZoom && visibleMaps.map(map => {
        const data = mapData[map.map_id]
        if (!data?.geoData) return null
        return (
          <GeoJSON
            key={`geo-${map.map_id}`}
            data={data.geoData}
            style={getStyle}
            onEachFeature={onEachFeature}
          />
        )
      })}
    </>
  )
}

export default function Map({ currentIndex, onTotalChange, showPolygon, showHurricanePath, polygonMinZoom, onZoomChange }) {
  const [maps, setMaps] = useState([])
  const [showAfter, setShowAfter] = useState(false)
  const [mapData, setMapData] = useState({})
  const [showGrid, setShowGrid] = useState(false)  // toggles grid overlay open/closed
  const [flyTarget, setFlyTarget] = useState(null) // stores center coords to fly to on tile click or arrow press

  const activeLayerRef = useRef(null)
  const stableOnTotalChange = useCallback((count) => onTotalChange(count), [onTotalChange])

  useEffect(() => {
    fetch('/api/maps')
      .then(res => res.json())
      .then(async data => {
        const allMaps = data.maps
        setMaps(allMaps)
        stableOnTotalChange(allMaps.length)

        // Fetch all GeoJSON in parallel, then batch into a single state update
        const results = await Promise.allSettled(
          allMaps.map(async (map) => {
            const res = await fetch(map.overlay_url)
            const geoData = await res.json()
            // skip tiles we can't place on the map
            const bounds = map.map_bounds
              ? normalizeBounds(map.map_bounds)
              : getBoundsFromGeoJSON(geoData)

            if (!bounds) return null
            return { mapId: map.map_id, bounds, geoData }
          })
        )

        const batch = {}
        for (const result of results) {
          if (result.status === 'fulfilled' && result.value) {
            const { mapId, bounds, geoData } = result.value
            batch[mapId] = { bounds, geoData }
          }
        }
        setMapData(batch)
      })
      .catch(err => console.error('Failed to fetch maps:', err))
  }, [stableOnTotalChange])

  // arrow navigation: whenever currentIndex changes, fly to that tile's center
  useMapNavigation(currentIndex, maps, mapData, setFlyTarget)

  // --- GEOJSON POLYGON STYLE ---
  // Color each polygon based on its damage_type property
  const getStyle = (feature) => {
    const damage = feature?.properties?.damage_type
    const fillColor = DAMAGE_COLORS[damage] || '#94a3b8'
    return {
      color:       fillColor,
      fillColor,
      fillOpacity: 0.4,
      weight:      2,
    }
  }

  const onEachFeature = (feature, layer) => {
    const damage = feature?.properties?.damage_type
    const damageColor = DAMAGE_COLORS[damage] || '#94a3b8'
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

      {/* PRE/POST TOGGLE + GRID VIEW BUTTON -- wrapped in flex so they sit side by side */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-10000 flex gap-3">
        <button
          onClick={() => setShowAfter(prev => !prev)}
          className="border border-zinc-600 bg-black/30 backdrop-blur-md text-white text-sm px-6 py-2 rounded-full hover:bg-white hover:text-black hover:border-transparent transition-all duration-300"
        >
          {showAfter ? 'Viewing: Post-Harvey' : 'Viewing: Pre-Harvey'}
        </button>

        {/* opens/closes the grid overlay */}
        <button
          onClick={() => setShowGrid(prev => !prev)}
          className="border border-zinc-600 bg-black/30 backdrop-blur-md text-white text-sm px-6 py-2 rounded-full hover:bg-white hover:text-black hover:border-transparent transition-all duration-300"
        >
          {showGrid ? 'Close Grid' : 'Grid View'}
        </button>
      </div>

      {/* -- DEBUG OVERLAY -- */}
      <div className="absolute top-20 left-4 z-10000 text-white text-xs bg-black/50 p-2 rounded space-y-1">
        <div>Total maps: {maps.length}</div>
        <div>Loaded tiles: {Object.keys(mapData).length}</div>
        <div>With polygons: {Object.values(mapData).filter(d => d.geoData?.features?.length > 0).length}</div>
        <div>No polygons (bounds only): {Object.values(mapData).filter(d => !d.geoData?.features?.length).length}</div>
        <div>Missing/failed: {maps.length - Object.keys(mapData).length}</div>
      </div>

      {/* -- GRID VIEW OVERLAY -- */}
      {/* full screen dark overlay on top of map, only renders when showGrid is true */}
      {showGrid && (
        <div className="absolute inset-0 z-10001 bg-black/80 backdrop-blur-sm overflow-auto p-6">
          <div className="flex justify-between items-center mb-4">
            {/* only count tiles that actually have valid bounds */}
            <h2 className="text-white text-lg font-semibold">
              All Image Tiles ({maps.filter(m => mapData[m.map_id]?.bounds).length})
            </h2>
            <button
              onClick={() => setShowGrid(false)}
              className="text-white border border-zinc-600 px-4 py-1 rounded-full hover:bg-white hover:text-black transition-all"
            >
              Close
            </button>
          </div>

          <div className="grid grid-cols-4 gap-4">
            {maps.map(map => {
              const data = mapData[map.map_id]
              if (!data?.bounds) return null // skip tiles that failed to load
              return (
                <div
                  key={map.map_id}
                  className="rounded overflow-hidden border border-zinc-700 bg-zinc-900 cursor-pointer hover:border-white transition-all"
                  onClick={() => {
                    // avg the SW + NE corners to get the center of this tile
                    const center = [
                      (data.bounds[0][0] + data.bounds[1][0]) / 2,
                      (data.bounds[0][1] + data.bounds[1][1]) / 2,
                    ]
                    setFlyTarget({ center, id: map.map_id }) // triggers FlyToLocation
                    setShowGrid(false) // close grid so map is visible
                  }}
                >
                  {/* respects the current pre/post toggle */}
                  <img
                    src={showAfter ? map.images.after : map.images.before}
                    alt={`Map ${map.map_id}`}
                    className="w-full h-40 object-cover"
                  />
                  <div className="text-white text-xs p-2 truncate">ID: {map.map_id}</div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      <MapContainer
        center={DEFAULT_CENTER}
        zoom={DEFAULT_ZOOM}
        style={{ width: '100%', height: '100%' }}
        zoomControl={false}
      >
        <CustomZoomControl />
        <FlyToLocation target={flyTarget} /> {/* inside MapContainer so it can access map instance */}

        {/* Dark base map */}
        <TileLayer
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
          subdomains="abcd"
          maxZoom={20}
        />

        {/* Render only overlays visible in the current viewport */}
        <ViewportOverlays
          maps={maps}
          mapData={mapData}
          showAfter={showAfter}
          showPolygon={showPolygon}
          polygonMinZoom={polygonMinZoom}
          getStyle={getStyle}
          onEachFeature={onEachFeature}
          onZoomChange={onZoomChange}
        />

        {/* Hurricane Harvey track path */}
        {showHurricanePath && <HurricanePath />}
      </MapContainer>

      {/* Hurricane path legend (outside MapContainer so it's not a map layer) */}
      {showHurricanePath && <HurricanePathLegend isOpen={showHurricanePath} />}
    </div>
  )
}