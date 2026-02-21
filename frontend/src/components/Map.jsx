import { MapContainer, TileLayer, ZoomControl, Polygon } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

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
      zoomControl={false}
    >
      {/* Positioned at bottom-left to stay clear of your NavBar */}
      <ZoomControl position="bottomleft" />

      {/* Dark-themed map tiles */}
      <TileLayer
        url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/">CARTO</a>'
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
    </MapContainer>
  )
}