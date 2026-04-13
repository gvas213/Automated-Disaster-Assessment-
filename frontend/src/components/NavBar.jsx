import { useState } from 'react'

const useFlash = () => {
  const [active, setActive] = useState(false)
  const flash = () => {
    setActive(true)
    setTimeout(() => setActive(false), 250)
  }
  return [active, flash]
}

// --- PROPS ---
// current, total, onPrev, onNext come from App.jsx
// onChatToggle also comes from App.jsx
export default function NavBar({ onChatToggle, current, total, onPrev, onNext, showPolygon, onPolygonToggle, currentZoom, showHurricanePath, onHurricanePathToggle, polygonMinZoom, onPolygonMinZoomChange }) {
  const [prevClicked, flashPrev] = useFlash()
  const [nextClicked, flashNext] = useFlash()
  const [chatClicked, flashChat] = useFlash()
  const [userClicked, flashUser] = useFlash()
  const [hideClicked, flashHide] = useFlash()
  const [showClicked, flashShow] = useFlash()
  const [layersClicked, flashLayers] = useFlash()
  const [pathClicked, flashPath] = useFlash()
  const [settingsClicked, flashSettings] = useFlash()

  const [isVisible, setIsVisible] = useState(true)
  const [settingsOpen, setSettingsOpen] = useState(false)

  // --- BUTTON HANDLERS ---
  const handlePrev = () => { flashPrev(); onPrev() }   // flash + tell App to go back
  const handleNext = () => { flashNext(); onNext() }   // flash + tell App to go forward
  const handleHide = () => { flashHide(); setTimeout(() => setIsVisible(false), 250) }
  const handleShow = () => { flashShow(); setTimeout(() => setIsVisible(true), 250) }
  const handleChat = () => { flashChat(); if (typeof onChatToggle === 'function') onChatToggle() }
  const handleLayers = () => { flashLayers(); onPolygonToggle() }
  const handlePath = () => { flashPath(); onHurricanePathToggle() }
  const handleSettings = () => { flashSettings(); setSettingsOpen(v => !v) }
  const iconBtn = (clicked) =>
    `transition-colors duration-200 ${clicked ? 'text-blue-500' : 'text-zinc-400 hover:text-black'}`

  return (
    <div className="fixed top-6 left-1/2 -translate-x-1/2 z-[10000] flex flex-col items-center gap-1">

      {isVisible && (
        <nav className="border border-zinc-600 h-11 w-80 rounded-full bg-black/30 backdrop-blur-md hover:bg-white hover:border-transparent transition-all duration-300 flex items-center justify-between px-4 group">

          {/* LEFT ARROW — disabled on first image */}
          <button onClick={handlePrev} disabled={current === 1} className={`${iconBtn(prevClicked)} disabled:opacity-20`}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-6">
              <path fillRule="evenodd" d="M7.72 12.53a.75.75 0 0 1 0-1.06l7.5-7.5a.75.75 0 1 1 1.06 1.06L9.31 12l6.97 6.97a.75.75 0 1 1-1.06 1.06l-7.5-7.5Z" clipRule="evenodd" />
            </svg>
          </button>

          <div className="flex items-center gap-4">

            {/* Chat icon */}
            <button onClick={handleChat} className={iconBtn(chatClicked)}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-7">
                <path fillRule="evenodd" d="M4.804 21.644A6.707 6.707 0 0 0 6 21.75a6.721 6.721 0 0 0 3.583-1.029c.774.182 1.584.279 2.417.279 5.322 0 9.75-3.97 9.75-9 0-5.03-4.428-9-9.75-9s-9.75 3.97-9.75 9c0 2.409 1.025 4.587 2.674 6.192.232.226.277.428.254.543a3.73 3.73 0 0 1-.814 1.686.75.75 0 0 0 .44 1.223ZM8.25 10.875a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25ZM10.875 12a1.125 1.125 0 1 1 2.25 0 1.125 1.125 0 0 1-2.25 0Zm4.875-1.125a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25Z" clipRule="evenodd" />
              </svg>
            </button>

            {/* User icon */}
            <button onClick={flashUser} className={iconBtn(userClicked)}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-7">
                <path fillRule="evenodd" d="M7.5 6a4.5 4.5 0 1 1 9 0 4.5 4.5 0 0 1-9 0ZM3.751 20.105a8.25 8.25 0 0 1 16.498 0 .75.75 0 0 1-.437.695A18.683 18.683 0 0 1 12 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 0 1-.437-.695Z" clipRule="evenodd" />
              </svg>
            </button>

            {/* Polygon/layers toggle */}
<button onClick={handleLayers} className={`transition-colors duration-200 ${layersClicked ? 'text-blue-500' : showPolygon ? 'text-green-400 hover:text-green-300' : 'text-red-400 hover:text-red-300'}`} title={showPolygon ? 'Property lines on' : 'Property lines off'}>
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-6">
    <path d="M11.644 1.59a.75.75 0 0 1 .712 0l9.75 5.25a.75.75 0 0 1 0 1.32l-9.75 5.25a.75.75 0 0 1-.712 0l-9.75-5.25a.75.75 0 0 1 0-1.32l9.75-5.25Z" />
    <path d="m3.265 10.602 7.668 4.129a2.25 2.25 0 0 0 2.134 0l7.668-4.13 1.37.739a.75.75 0 0 1 0 1.32l-9.75 5.25a.75.75 0 0 1-.712 0l-9.75-5.25a.75.75 0 0 1 0-1.32l1.372-.738Z" />
    <path d="m10.933 19.231-7.668-4.13-1.37.739a.75.75 0 0 0 0 1.32l9.75 5.25c.221.12.491.12.712 0l9.75-5.25a.75.75 0 0 0 0-1.32l-1.37-.738-7.668 4.13a2.25 2.25 0 0 1-2.136-.001Z" />
  </svg>
</button>

            {/* Hurricane path toggle */}
            <button onClick={handlePath} className={`${iconBtn(pathClicked)} ${showHurricanePath ? '!text-cyan-400' : ''}`} title="Toggle hurricane path">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="size-6">
                <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2" />
              </svg>
            </button>

            {/* Settings */}
            <button onClick={handleSettings} className={`${iconBtn(settingsClicked)} ${settingsOpen ? '!text-blue-400' : ''}`} title="Settings">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-5">
                <path fillRule="evenodd" d="M11.078 2.25c-.917 0-1.699.663-1.85 1.567L9.05 4.889c-.02.12-.115.26-.297.348a7.493 7.493 0 0 0-.986.57c-.166.115-.334.126-.45.083L6.3 5.508a1.875 1.875 0 0 0-2.282.819l-.922 1.597a1.875 1.875 0 0 0 .432 2.385l.84.692c.095.078.17.229.154.43a7.598 7.598 0 0 0 0 1.139c.015.2-.059.352-.153.43l-.841.692a1.875 1.875 0 0 0-.432 2.385l.922 1.597a1.875 1.875 0 0 0 2.282.818l1.019-.382c.115-.043.283-.031.45.082.312.214.641.405.985.57.182.088.277.228.297.35l.178 1.071c.151.904.933 1.567 1.85 1.567h1.844c.916 0 1.699-.663 1.85-1.567l.178-1.072c.02-.12.114-.26.297-.349.344-.165.673-.356.985-.57.167-.114.335-.125.45-.082l1.02.382a1.875 1.875 0 0 0 2.28-.819l.923-1.597a1.875 1.875 0 0 0-.432-2.385l-.84-.692c-.095-.078-.17-.229-.154-.43a7.614 7.614 0 0 0 0-1.139c-.016-.2.059-.352.153-.43l.84-.692c.708-.582.891-1.59.433-2.385l-.922-1.597a1.875 1.875 0 0 0-2.282-.818l-1.02.382c-.114.043-.282.031-.449-.083a7.49 7.49 0 0 0-.985-.57c-.183-.087-.277-.227-.297-.348l-.179-1.072a1.875 1.875 0 0 0-1.85-1.567h-1.843ZM12 15.75a3.75 3.75 0 1 0 0-7.5 3.75 3.75 0 0 0 0 7.5Z" clipRule="evenodd" />
              </svg>
            </button>

            {/* Hide navbar — eye with slash */}
            <button onClick={handleHide} className={iconBtn(hideClicked)}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-5">
                <path d="M3.53 2.47a.75.75 0 0 0-1.06 1.06l18 18a.75.75 0 1 0 1.06-1.06l-18-18ZM22.676 12.553a11.249 11.249 0 0 1-2.631 4.31l-3.099-3.099a5.25 5.25 0 0 0-6.71-6.71L7.759 4.577a11.217 11.217 0 0 1 4.242-.827c4.97 0 9.185 3.223 10.675 7.69.12.362.12.752 0 1.113Z" />
                <path d="M15.75 12c0 .18-.013.357-.037.53l-4.244-4.243A3.75 3.75 0 0 1 15.75 12ZM12.53 15.713l-4.243-4.244a3.75 3.75 0 0 0 4.244 4.243Z" />
                <path d="M6.75 12c0-.619.107-1.213.304-1.764l-3.1-3.1a11.25 11.25 0 0 0-2.63 4.31c-.12.362-.12.752 0 1.114 1.489 4.467 5.704 7.69 10.675 7.69 1.5 0 2.933-.294 4.242-.827l-2.477-2.477A5.25 5.25 0 0 1 6.75 12Z" />
              </svg>
            </button>

          </div>

          {/* RIGHT ARROW — disabled on last image */}
          <button onClick={handleNext} disabled={current === total} className={`${iconBtn(nextClicked)} disabled:opacity-20`}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-6">
              <path fillRule="evenodd" d="M16.28 11.47a.75.75 0 0 1 0 1.06l-7.5 7.5a.75.75 0 0 1-1.06-1.06L14.69 12 7.72 5.03a.75.75 0 0 1 1.06-1.06l7.5 7.5Z" clipRule="evenodd" />
            </svg>
          </button>

        </nav>
      )}

      {/* Counter — now uses real current/total from App */}
      {isVisible && <span className="text-zinc-400 text-xs">{current} / {total}</span>}

      {/* Zoom hint — only when polygons are on but zoom is too low */}
      {isVisible && showPolygon && currentZoom < polygonMinZoom && (
        <span className="text-yellow-300 text-xs bg-black/50 backdrop-blur-sm px-3 py-1 rounded-full border border-yellow-500/30">
          Zoom in to see property lines
        </span>
      )}

      {/* Settings popup */}
      {settingsOpen && isVisible && (
        <div className="border border-zinc-600 bg-black/80 backdrop-blur-md rounded-xl p-4 mt-1" style={{ minWidth: '230px' }}>
          <div className="text-white text-sm font-semibold mb-3">Settings</div>
          <div className="flex items-center justify-between mb-2">
            <span className="text-white/70 text-xs">Property Lines Min Zoom</span>
            <span className="text-white text-sm font-mono">{polygonMinZoom}</span>
          </div>
          <input
            type="range"
            min={10}
            max={17}
            value={polygonMinZoom}
            onChange={(e) => onPolygonMinZoomChange(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
          <div className="flex justify-between text-white/30 text-[10px] mt-1">
            <span>10 (far)</span>
            <span>17 (close)</span>
          </div>
        </div>
      )}

      {/* Restore button when navbar is hidden */}
      {!isVisible && (
        <button onClick={handleShow} className={`border border-zinc-600 bg-black/30 backdrop-blur-md hover:bg-white hover:border-transparent transition-all duration-300 rounded-full p-2 ${iconBtn(showClicked)}`}>
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-5">
            <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6Z" />
            <path fillRule="evenodd" d="M1.323 11.447C2.811 6.976 7.028 3.75 12.001 3.75c4.97 0 9.185 3.223 10.675 7.69.12.362.12.752 0 1.113-1.487 4.471-5.705 7.697-10.677 7.697-4.97 0-9.186-3.223-10.675-7.69a1.762 1.762 0 0 1 0-1.113ZM17.25 12a5.25 5.25 0 1 1-10.5 0 5.25 5.25 0 0 1 10.5 0Z" clipRule="evenodd" />
          </svg>
        </button>
      )}

    </div>
  )
}