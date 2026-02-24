import { useState } from 'react'

// --- CUSTOM HOOK ---
// A "hook" is just a reusable piece of logic in React.
// This one handles the blue flash animation when a button is clicked.
// It returns two things: whether the flash is currently active, and a function to trigger it.
const useFlash = () => {
  const [active, setActive] = useState(false)
  const flash = () => {
    setActive(true)                          // turn blue
    setTimeout(() => setActive(false), 250)  // go back to normal after 250ms
  }
  return [active, flash]
}

export default function NavBar({onChatToggle}) {

  // --- BUTTON FLASH STATES ---
  // Each button gets its own flash. "clicked" = is it blue right now? "flash" = trigger the blue
  const [prevClicked, flashPrev] = useFlash()  // left arrow
  const [nextClicked, flashNext] = useFlash()  // right arrow
  const [chatClicked, flashChat] = useFlash()  // chat icon
  const [userClicked, flashUser] = useFlash()  // user icon
  const [hideClicked, flashHide] = useFlash()  // hide navbar (eye with slash)
  const [showClicked, flashShow] = useFlash()  // show navbar (open eye)

  // --- NAVIGATION STATE ---
  const [current, setCurrent] = useState(1)   // which image we're on (starts at 1)
  const [isVisible, setIsVisible] = useState(true) // is the navbar showing?
  const total = 47 // total number of disaster images (swap with real data later)

  // --- BUTTON HANDLERS ---
  // These run when buttons are clicked. They flash blue AND do their action.
  const handlePrev = () => {
    flashPrev()
    setCurrent(c => Math.max(1, c - 1))       // go back one, but never below 1
  }
  const handleNext = () => {
    flashNext()
    setCurrent(c => Math.min(total, c + 1))   // go forward one, but never past total
  }
  const handleHide = () => {
    flashHide()
    setTimeout(() => setIsVisible(false), 250) // wait for blue flash, then hide
  }
  const handleShow = () => {
    flashShow()
    setTimeout(() => setIsVisible(true), 250)  // wait for blue flash, then show
  }
  const handleChat = () => {
    flashChat()
    if (typeof onChatToggle === 'function') onChatToggle()
  }

  // --- HELPER: BUTTON COLOR ---
  // Returns the right text color class depending on whether the button was just clicked.
  // If clicked → blue. If not → gray, turns black on hover.
  const iconBtn = (clicked) =>
    `transition-colors duration-200 ${clicked ? 'text-blue-500' : 'text-zinc-400 hover:text-black'}`

  return (
    <div className="fixed top-6 left-1/2 -translate-x-1/2 z-[10000] flex flex-col items-center gap-1">

      {/* Only render the navbar pill if isVisible is true */}
      {isVisible && (
        <nav className="border border-zinc-600 h-11 w-72 rounded-full bg-black/30 backdrop-blur-md hover:bg-white hover:border-transparent transition-all duration-300 flex items-center justify-between px-4 group">

          {/* LEFT ARROW — goes to previous image, disabled on first image */}
          <button onClick={handlePrev} disabled={current === 1} className={`${iconBtn(prevClicked)} disabled:opacity-20`}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-6">
              <path fillRule="evenodd" d="M7.72 12.53a.75.75 0 0 1 0-1.06l7.5-7.5a.75.75 0 1 1 1.06 1.06L9.31 12l6.97 6.97a.75.75 0 1 1-1.06 1.06l-7.5-7.5Z" clipRule="evenodd" />
            </svg>
          </button>

          {/* CENTER ICONS */}
          <div className="flex items-center gap-4">

            {/* Chat icon — will open a chat panel later */}

            <button onClick={handleChat} className={iconBtn(chatClicked)}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-7">
                <path fillRule="evenodd" d="M4.804 21.644A6.707 6.707 0 0 0 6 21.75a6.721 6.721 0 0 0 3.583-1.029c.774.182 1.584.279 2.417.279 5.322 0 9.75-3.97 9.75-9 0-5.03-4.428-9-9.75-9s-9.75 3.97-9.75 9c0 2.409 1.025 4.587 2.674 6.192.232.226.277.428.254.543a3.73 3.73 0 0 1-.814 1.686.75.75 0 0 0 .44 1.223ZM8.25 10.875a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25ZM10.875 12a1.125 1.125 0 1 1 2.25 0 1.125 1.125 0 0 1-2.25 0Zm4.875-1.125a1.125 1.125 0 1 0 0 2.25 1.125 1.125 0 0 0 0-2.25Z" clipRule="evenodd" />
              </svg>
            </button>

            {/* User icon — will open account/profile later */}
            <button onClick={flashUser} className={iconBtn(userClicked)}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-7">
                <path fillRule="evenodd" d="M7.5 6a4.5 4.5 0 1 1 9 0 4.5 4.5 0 0 1-9 0ZM3.751 20.105a8.25 8.25 0 0 1 16.498 0 .75.75 0 0 1-.437.695A18.683 18.683 0 0 1 12 22.5c-2.786 0-5.433-.608-7.812-1.7a.75.75 0 0 1-.437-.695Z" clipRule="evenodd" />
              </svg>
            </button>

            {/* Hide button — eye with slash, hides the navbar */}
            <button onClick={handleHide} className={iconBtn(hideClicked)}>
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-5">
                <path d="M3.53 2.47a.75.75 0 0 0-1.06 1.06l18 18a.75.75 0 1 0 1.06-1.06l-18-18ZM22.676 12.553a11.249 11.249 0 0 1-2.631 4.31l-3.099-3.099a5.25 5.25 0 0 0-6.71-6.71L7.759 4.577a11.217 11.217 0 0 1 4.242-.827c4.97 0 9.185 3.223 10.675 7.69.12.362.12.752 0 1.113Z" />
                <path d="M15.75 12c0 .18-.013.357-.037.53l-4.244-4.243A3.75 3.75 0 0 1 15.75 12ZM12.53 15.713l-4.243-4.244a3.75 3.75 0 0 0 4.244 4.243Z" />
                <path d="M6.75 12c0-.619.107-1.213.304-1.764l-3.1-3.1a11.25 11.25 0 0 0-2.63 4.31c-.12.362-.12.752 0 1.114 1.489 4.467 5.704 7.69 10.675 7.69 1.5 0 2.933-.294 4.242-.827l-2.477-2.477A5.25 5.25 0 0 1 6.75 12Z" />
              </svg>
            </button>

          </div>

          {/* RIGHT ARROW — goes to next image, disabled on last image */}
          <button onClick={handleNext} disabled={current === total} className={`${iconBtn(nextClicked)} disabled:opacity-20`}>
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="size-6">
              <path fillRule="evenodd" d="M16.28 11.47a.75.75 0 0 1 0 1.06l-7.5 7.5a.75.75 0 0 1-1.06-1.06L14.69 12 7.72 5.03a.75.75 0 0 1 1.06-1.06l7.5 7.5Z" clipRule="evenodd" />
            </svg>
          </button>

        </nav>
      )}

      {/* Image counter shown below the pill e.g. "3 / 47" */}
      {isVisible && <span className="text-zinc-400 text-xs">{current} / {total}</span>}

      {/* When navbar is hidden, show a small floating eye button to bring it back */}
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