import { MapContainer, TileLayer, Polygon } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { CustomZoomControl } from './MapControls'

// Coordinates for Houston, TX
const DEFAULT_CENTER = [29.7604, -95.3698] 
const DEFAULT_ZOOM = 11

// A sample disaster zone polygon over the Houston area
const hazardZoneCoordinates = [
  [29.85, -95.45],
  [29.85, -95.25],
  [29.65, -95.25],
  [29.65, -95.45]
];

export default function Map() {
  return (
    <MapContainer
      center={DEFAULT_CENTER}
      zoom={DEFAULT_ZOOM}
      style={{ width: '100vw', height: '100vh' }}
      zoomControl={false}       // Disable default zoom control so we can use our custom one
      attributionControl={false}
    >
      {/* Dark-themed map tiles */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        subdomains="abcd"
        maxZoom={20}
      />

      {/* The Red Disaster Zone Polygon */}
      <Polygon 
        positions={hazardZoneCoordinates} 
        pathOptions={{ 
          color: '#ef4444', 
          fillColor: '#ef4444', 
          fillOpacity: 0.4,
          weight: 2 
        }} 
      />

      {/* Custom zoom control + severity legend toggle — positioned at bottom-right */}
      <CustomZoomControl />
    </MapContainer>
  )
}