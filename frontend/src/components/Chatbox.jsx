import { useEffect, useRef, useState, useCallback } from "react";

//states for the chatbox
//messages track text of msg and isUser - whether msg sent by user or AI
//ai ready - returns bool and determines if user can initiate a chat. Prevents input before puter has loaded
//is loading - to handle input/output flow
export default function ChatBox({ onClose }) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState(""); //current input field value - default null
  const [aiReady, setAIReady] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  // width state for resizable panel - default 360px, min 260px, max 720px
  const [panelWidth, setPanelWidth] = useState(360);
  const isResizing = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);

  const messagesEndRef = useRef(null);  //used for autoscroll on new messages

  //testing puter readiness this will be replaces with out backend logic
  useEffect(() => {
    const checkReady = setInterval(() => {
      if (window.puter && window.puter.ai && typeof window.puter.ai.chat === "function") {
        setAIReady(true);
        clearInterval(checkReady);
      }
    }, 300);

    return () => clearInterval(checkReady);
  }, []);

  //set scrolling behavior for when the chat extends beyond the chatbox height
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // mouse move/up listeners for drag-to-resize
  // attached to window so dragging outside the handle still works
  const handleMouseMove = useCallback((e) => {
    if (!isResizing.current) return;
    const delta = e.clientX - startX.current;
    const newWidth = Math.min(720, Math.max(260, startWidth.current + delta));
    setPanelWidth(newWidth);
  }, []);

  const handleMouseUp = useCallback(() => {
    isResizing.current = false;
    document.body.style.cursor = "";
    document.body.style.userSelect = "";
  }, []);

  useEffect(() => {
    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  // called when user presses down on the resize handle lip
  const handleResizeMouseDown = (e) => {
    e.preventDefault();
    isResizing.current = true;
    startX.current = e.clientX;
    startWidth.current = panelWidth;
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none"; //prevents text selection while dragging
  };

  //appends message based on if user or ai 
  //assigns a random chat 'id' for tracking
  const addMessage = (content, isUser) => {
    setMessages((prev) => [...prev, { content, isUser, id: Date.now() + Math.random() }]);
  };

  //handles sending messages to puter
  //will be replaced with out backend logic
  const sendMessage = async () => {
    //input validation
    const message = inputValue.trim();
    if (!message) return;

    //blocks if ai isn't ready
    if (!aiReady) {
      addMessage("AI service still loading, please wait…", false);
      return;
    }

    //appends message to list
    addMessage(message, true);
    setInputValue("");
    setIsLoading(true);

    //TO BE REPLACED WITH BACKEND LOGIC
    //right now this is sending messages to puter and waiting on response
    //handles response validation
    try {
      const response = await window.puter.ai.chat(message);
      const reply =
        typeof response === "string"
          ? response
          : response?.message?.content || "No reply received.";
      addMessage(reply, false);
    } catch (err) {
      addMessage(`Error: ${err?.message || "Something went wrong"}`, false);
    } finally {
      setIsLoading(false);
    }
  };

  //handle shift+enter - newline
  //allows enter to send msg
  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="fixed inset-0 z-20000 pointer-events-none">

      {/* Chatbox panel window width (width controlled by panelWidth state)*/} 
      <aside
        style={{ width: panelWidth, backgroundColor: "#1e1e1e" }}
        className="
          absolute left-0 top-0 h-full
          border-r border-white/10 shadow-2xl
          pointer-events-auto
          animate-in slide-in-from-left duration-200
          flex flex-col
          overflow-hidden
        "
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 shrink-0">
          <h2 className="text-base font-semibold text-white">Chat</h2>
          <button
            onClick={onClose}
            className="text-white/50 hover:text-white transition text-lg leading-none"
            aria-label="Close chat"
          >
            ✕
          </button>
        </div>

        {/* Line Divider under header */}
        <div className="h-px bg-white/10 shrink-0 mx-4" />

        <div className="flex-1 overflow-y-auto min-h-0 px-4 py-4" style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}>

          {/* Hide starting AI text after first message sent */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-6">
              <p className="text-white text-xl font-semibold leading-snug">
                What can I help with?
              </p>
              <p className="text-white/40 text-sm leading-relaxed">
                Ask me any questions about the disaster.
              </p>
            </div>
          )}

        
          {messages.length === 0 && !aiReady && (
            <div className="flex justify-center mt-4">
              <span className="px-3 py-1 rounded-full text-xs bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
                Connecting to AI…
              </span>
            </div>
          )}

          {/* Render chat messages */}
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex mb-3 ${msg.isUser ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`px-4 py-3 rounded-2xl max-w-[80%] wrap-break-word text-sm leading-relaxed ${
                  msg.isUser
                    ? "bg-white/15 text-white rounded-br-sm"
                    : "bg-white/5 text-white/90 rounded-bl-sm border border-white/10"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            </div>
          ))}

          {/* Loading indicator on AI response */}
          {isLoading && (
            <div className="flex justify-start mb-3">
              <div className="px-4 py-3 rounded-2xl rounded-bl-sm bg-white/5 border border-white/10 text-white/60 text-sm flex items-center gap-2">
                <div className="animate-spin w-3.5 h-3.5 border-2 border-white/20 border-t-white/60 rounded-full" />
                Thinking…
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

       
        <div className="shrink-0 px-4 pb-5 pt-3">
          <div
            className="flex items-center gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 pr-2 py-2"
            style={{ minHeight: "52px" }}
          >
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={aiReady ? "Ask anything" : "Connecting…"}
              disabled={!aiReady || isLoading}
              className="flex-1 min-w-0 bg-transparent text-white text-sm placeholder-white/30 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed"
            />

            <button
              onClick={sendMessage}
              disabled={!aiReady || isLoading || !inputValue.trim()}
              className="shrink-0 w-8 h-8 flex items-center justify-center rounded-xl bg-white/10 hover:bg-white/20 text-white transition disabled:opacity-30 disabled:cursor-not-allowed"
              aria-label="Send message"
            >
              {isLoading ? (
                <span className="animate-spin w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full" />
              ) : (
                /* Send Icon Arrow */
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                  <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Resize handle lip */}
        <div
          onMouseDown={handleResizeMouseDown}
          className="absolute top-0 right-0 h-full w-2 cursor-ew-resize flex items-center justify-center group"
          title="Drag to resize"
        >
          {/* Visible grip pill appearing on hover */}
          <div className="w-1 h-12 rounded-full bg-white/20 group-hover:bg-white/60 transition-colors duration-150" />
        </div>
      </aside>
    </div>
  );
}