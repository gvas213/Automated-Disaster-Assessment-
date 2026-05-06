import { useEffect, useRef, useState, useCallback } from "react";

const CHAT_STORAGE_KEY = "chat_messages";

const SEVERITY_LABELS = {
  'no-damage':    'No Damage',
  'minor-damage': 'Minor Damage',
  'major-damage': 'Major Damage',
  'destroyed':    'Destroyed',
}

export default function ChatBox({ onClose, selectedFeature }) {
  const [messages, setMessages] = useState(() => {
    try {
      const stored = sessionStorage.getItem(CHAT_STORAGE_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });
  const [inputValue, setInputValue] = useState("");
  const [aiReady, setAIReady] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [panelWidth, setPanelWidth] = useState(360);
  const isResizing = useRef(false);
  const startX = useRef(0);
  const startWidth = useRef(0);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { setAIReady(true); }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  useEffect(() => {
    try {
      sessionStorage.setItem(CHAT_STORAGE_KEY, JSON.stringify(messages));
    } catch {
      // sessionStorage unavailable (private mode, quota exceeded) — non-fatal
    }
  }, [messages]);

  const handleNewChat = () => {
    setMessages([]);
    try {
      sessionStorage.removeItem(CHAT_STORAGE_KEY);
    } catch {
      // sessionStorage unavailable — non-fatal
    }
  };

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

  const handleResizeMouseDown = (e) => {
    e.preventDefault();
    isResizing.current = true;
    startX.current = e.clientX;
    startWidth.current = panelWidth;
    document.body.style.cursor = "ew-resize";
    document.body.style.userSelect = "none";
  };

  const addMessage = (content, isUser, isFeatureSummary = false) => {
    setMessages((prev) => [...prev, { content, isUser, isFeatureSummary, id: Date.now() + Math.random() }]);
  };

  // build a context string from the selected feature to inject into every message
  const buildFeatureContext = (feature) => {
    if (!feature) return null
    const props = feature.properties
    const severity = SEVERITY_LABELS[props.damage_type] || props.damage_type || 'Unknown'
    const cost = props.cost_usd ? `$${Number(props.cost_usd).toLocaleString()}` : 'N/A'

    // extract coordinates from the polygon 
    let lat = null
    let lon = null
    if (feature.geometry?.coordinates?.[0]?.[0]) {
        const coord = feature.geometry.coordinates[0][0]
        lon = coord[0]
        lat = coord[1]
    }

    let descriptionText = 'N/A'
    if (props.description && typeof props.description === 'object') {
        descriptionText = props.description.reasoning || props.description.diff_description || 'N/A'
    } else if (props.description) {
        descriptionText = props.description
    }

    return `The user has selected a specific damage assessment tile on the map. Here are its details:
- Feature type: ${props.feature_type || 'Unknown'}
- Damage type: ${severity}
- Damage cost: ${cost}
- UID: ${props.uid || 'Unknown'}
- Coordinates: (${lat}, ${lon})
- Assessment reasoning: ${descriptionText}

Use this information to answer any follow-up questions about this specific tile. If the user asks for the address, use the get_address_from_coordinates tool with the coordinates above.`
}

  const sendMessage = async () => {
    const message = inputValue.trim();
    if (!message) return;

    if (!aiReady) {
      addMessage("AI service still loading, please wait…", false);
      return;
    }

    addMessage(message, true);
    setInputValue("");
    if (inputRef.current) inputRef.current.style.height = "auto";
    setIsLoading(true);
    setTimeout(() => inputRef.current?.focus(), 0);

    //add selected feature to context
    const featureContext = buildFeatureContext(selectedFeature)
    const messageWithContext = featureContext
      ? `${message}\n\n[Selected tile context: ${featureContext}]`
      : message

    try {
      const response = await fetch(`/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: messageWithContext,
          chat_history: messages.map((m) => ({
            role: m.isUser ? "user" : "assistant",
            content: m.content
          }))
        })
      });
      const data = await response.json();
      addMessage(data.reply, false);
    } catch (err) {
      addMessage(`Error: ${err?.message || "Something went wrong"}`, false);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  // build summary from selected feature
  const renderFeatureSummary = () => {
    if (!selectedFeature) return null
    const props = selectedFeature.properties
    const severity = SEVERITY_LABELS[props.damage_type] || props.damage_type || 'Unknown'
    const cost = props.cost_usd ? `$${Number(props.cost_usd).toLocaleString()}` : 'N/A'

    let reasoning = null
    if (props.description && typeof props.description === 'object') {
      reasoning = props.description.reasoning
    }

    return (
      <div className="mx-4 mb-3 p-3 rounded-xl border border-white/10 bg-white/5">
        <p className="text-white/60 text-xs font-semibold uppercase tracking-wide mb-2">
          Selected Tile
        </p>
        <ul className="text-white/90 text-sm space-y-1">
          <li>• <span className="text-white/50">Feature:</span> {props.feature_type || 'Unknown'}</li>
          <li>• <span className="text-white/50">Damage:</span> {severity}</li>
          <li>• <span className="text-white/50">Cost:</span> {cost}</li>
          {reasoning && (
            <li>• <span className="text-white/50">Assessment:</span> {reasoning}</li>
          )}
        </ul>
        <p className="text-white/30 text-xs mt-2">Ask me anything about this tile</p>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 z-20000 pointer-events-none">
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
          <div className="flex items-center gap-3">
            <button
              onClick={handleNewChat}
              className="text-white/50 hover:text-white transition text-sm"
              aria-label="Start a new chat"
            >
              New Chat
            </button>
            <button
              onClick={onClose}
              className="text-white/50 hover:text-white transition text-lg leading-none"
              aria-label="Close chat"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Divider */}
        <div className="h-px bg-white/10 shrink-0 mx-4" />

        {/* Selected feature card*/}
        {selectedFeature && renderFeatureSummary()}

        <div className="flex-1 overflow-y-auto min-h-0 px-4 py-4" style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}>

          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center h-full gap-3 text-center px-6">
              <p className="text-white text-xl font-semibold leading-snug">
                What can I help with?
              </p>
              <p className="text-white/40 text-sm leading-relaxed">
                {selectedFeature
                  ? "Ask me anything about the selected tile."
                  : "Ask me any questions about the disaster."}
              </p>
            </div>
          )}

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

        {/* Input area */}
        <div className="shrink-0 px-4 pb-5 pt-3">
          <div
            className="flex items-end gap-2 rounded-2xl border border-white/10 bg-white/5 px-4 pr-2 py-2"
            style={{ minHeight: "52px" }}
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={inputValue}
              onChange={(e) => {
                setInputValue(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = `${e.target.scrollHeight}px`;
              }}
              onKeyDown={handleKeyDown}
              placeholder={
                selectedFeature
                  ? "Ask about this tile…"
                  : aiReady ? "Ask anything" : "Connecting…"
              }
              disabled={!aiReady || isLoading}
              className="flex-1 min-w-0 bg-transparent text-white text-sm placeholder-white/30 focus:outline-none disabled:opacity-40 disabled:cursor-not-allowed resize-none overflow-hidden"
              style={{ lineHeight: "1.5", maxHeight: "160px", overflowY: "auto" }}
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
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
                  <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Resize handle */}
        <div
          onMouseDown={handleResizeMouseDown}
          className="absolute top-0 right-0 h-full w-2 cursor-ew-resize flex items-center justify-center group"
          title="Drag to resize"
        >
          <div className="w-1 h-12 rounded-full bg-white/20 group-hover:bg-white/60 transition-colors duration-150" />
        </div>
      </aside>
    </div>
  );
}