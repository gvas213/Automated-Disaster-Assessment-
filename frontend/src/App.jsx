import { useState } from "react"
import Map from './components/Map'
import NavBar from './components/NavBar'
import ChatBox from './components/Chatbox'

function App() {
  const [chatOpen, setChatOpen] = useState(false)
  const [currentIndex, setCurrentIndex] = useState(0) // which map we're on
  const [total, setTotal] = useState(0)               // total maps from API
  const [showPolygon, setShowPolygon] = useState(true)

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
/>
<Map
  currentIndex={currentIndex}
  onTotalChange={setTotal}
  showPolygon={showPolygon}
/>
      {chatOpen && <ChatBox onClose={() => setChatOpen(false)} />}
    </div>
  )
}

export default App