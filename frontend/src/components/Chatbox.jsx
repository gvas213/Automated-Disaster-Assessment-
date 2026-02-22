import { useEffect, useRef, useState } from "react";

//states for the chatbox
//messages track text of msg and isUser - whether msg sent by user or AI
//ai ready - returns bool and determines if user can initiate a chat. Prevents input before puter has loaded
//is loading - to handle input/output flow
export default function ChatBox({ onClose }) {
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState(""); //current input field value - default null
  const [aiReady, setAIReady] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

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

  //appends message based on if user or ai 
  //assigns a random chat 'id' for tracking
  const addMessage = (content, isUser) => {
    setMessages((prev) => [...prev, { content, isUser, id: Date.now() + Math.random() }]);
  };

  //handles senfing messages to puter
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

    //appends messsage to list
    addMessage(message, true);
    setInputValue("");
    setIsLoading(true);

    //TO BE REPLACED WITH BACKEND LOGIC
    //right now this is sending messages to puter and waiting on response
    //handels response validation
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
    <div className="fixed inset-0 z-[20000] pointer-events-none">
      {/* Overlay (keeps map visible) 
        full screen container
      */}
      <div
        className="absolute inset-0 bg-black/20 pointer-events-auto"
        onClick={onClose}
      />

      {/* chatbox window (slides from left) */}
      <aside
        className="
          absolute left-0 top-0 h-full
          w-2/3 md:w-2/5 lg:w-1/3 backdrop-blur
          border-r border-white/10 shadow-2xl
          pointer-events-auto
          animate-in slide-in-from-left duration-200
          flex flex-col
        "
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-white/10">
          <h2 className="text-sm font-semibold tracking-wide text-white/90">Chat</h2>
          <button
            onClick={onClose}
            className="text-white/60 hover:text-white transition"
            aria-label="Close chat"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 flex flex-col p-4 gap-4 overflow-hidden">
          {/* Status alert (ai ready or loading) */}
          <div
            className={`self-start px-4 py-2 rounded-full text-sm ${
              aiReady
                ? "bg-green-500/20 text-green-300 border border-green-500/30"
                : "bg-yellow-500/20 text-yellow-300 border border-yellow-500/30"
            }`}
          >
            {aiReady ? "Ask me questions about this disaster" : "Waiting for Chatbot"}
          </div>

          {/* message/conversation box area */}
          <div className="flex-1 overflow-y-auto rounded-3xl bg-white/5 border border-white/10 p-4">
            {messages.length === 0 && (
              <div className="text-center text-white/40 mt-10">Start the convo</div>
            )}

            {messages.map((msg) => (
              <div
                key={msg.id}
                className={`p-3 my-2 rounded-2xl max-w-[85%] break-words ${
                  msg.isUser
                    ? "bg-white/10 text-white ml-auto text-right"
                    : "bg-black/30 text-white"
                }`}
              >
                <div className="whitespace-pre-wrap">{msg.content}</div>
              </div>
            ))}

            {isLoading && (
              <div className="p-3 my-2 rounded-2xl max-w-[85%] bg-white/10 text-white">
                <div className="flex items-center gap-2">
                  <div className="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
                  Thinking…
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* input box - user input */}
          <div className="flex gap-3">
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={aiReady ? "Type your message" : "Waiting for AI"}
              disabled={!aiReady || isLoading}
              className="flex-1 px-4 py-3 bg-white/5 border border-white/10 rounded-2xl text-white placeholder-white/40 focus:outline-none focus:ring-2 focus:ring-white/20 transition disabled:opacity-50 disabled:cursor-not-allowed"
            />

            <button
              onClick={sendMessage}
              disabled={!aiReady || isLoading || !inputValue.trim()}
              className="px-6 py-3 bg-white/10 hover:bg-white/15 text-white font-semibold rounded-2xl transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="animate-spin w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
                  Sending…
                </span>
              ) : (
                "Send"
              )}
            </button>
          </div>
        </div>
      </aside>
    </div>
  );
}