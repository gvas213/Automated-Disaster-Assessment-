import { useState } from "react"
import Map from './components/Map'
import NavBar from './components/NavBar'
import ChatBox from './components/Chatbox'
import VLMUploadModal from "./components/VLMUploadModal"

function App() {
  const [chatOpen, setChatOpen] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0) // which map we're on
  const [total, setTotal] = useState(0)               // total maps from API
  const [showPolygon, setShowPolygon] = useState(true)
  const [showHurricanePath, setShowHurricanePath] = useState(false)
  const [polygonMinZoom, setPolygonMinZoom] = useState(15)
  const [currentZoom, setCurrentZoom] = useState(15)
  const [selectedFeature, setSelectedFeature] = useState(null) //which polygon is clicked
  const [showAssessModal, setShowAssessModal] = useState(false)
  return (
    <div className="h-screen w-screen overflow-hidden">
    <NavBar
  onChatToggle={() => setChatOpen((v) => !v)}
  current={currentIndex + 1}
  total={total}
  onPrev={() => setCurrentIndex(i => Math.max(0, i - 1))}
  onNext={() => setCurrentIndex(i => Math.min(total - 1, i + 1))}
  showPolygon={showPolygon}
  onPolygonToggle={() => setShowPolygon(v => !v)}
  currentZoom={currentZoom}
  showHurricanePath={showHurricanePath}
  onHurricanePathToggle={() => setShowHurricanePath(v => !v)}
  polygonMinZoom={polygonMinZoom}
  onPolygonMinZoomChange={setPolygonMinZoom}
  
/>
{showAssessModal && (
        <VLMUploadModal onClose={() => setShowAssessModal(false)} />
      )}

<Map
  currentIndex={currentIndex}
  onTotalChange={setTotal}
  showPolygon={showPolygon}
  showHurricanePath={showHurricanePath}
  polygonMinZoom={polygonMinZoom}
  onZoomChange={setCurrentZoom}
  onFeatureSelect={setSelectedFeature}
  onAssessClick={() => setShowAssessModal(true)}
/>
      {chatOpen && <ChatBox onClose={() => setChatOpen(false)} 
      selectedFeature={selectedFeature}
      />}
      
    </div>
  )
}

export default App