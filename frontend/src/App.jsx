import {useState} from "react";
import Map from './components/Map'
import NavBar from './components/NavBar'
import ChatBox from './components/Chatbox'


function App() {
  const [chatOpen, setChatOpen] = useState(false);

  return (
    <div className="h-screen w-screen overflow-hidden">
      <NavBar onChatToggle={() => setChatOpen((v) => !v)} />
      <Map />
      {chatOpen && <ChatBox onClose={() => setChatOpen(false)} />}
    </div>
  )
}

export default App