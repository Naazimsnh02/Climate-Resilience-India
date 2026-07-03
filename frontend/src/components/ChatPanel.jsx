import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import { sendChat } from "../api";

export default function ChatPanel({ agent, placeholder, showToolCalls = false }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [error, setError] = useState(null);
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setSending(true);
    setError(null);

    try {
      const result = await sendChat(agent, { message: text, sessionId });
      setSessionId(result.session_id);
      setMessages((m) => [
        ...m,
        { role: "assistant", text: result.reply, toolCalls: result.tool_calls },
      ]);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-messages">
        {messages.length === 0 && (
          <p className="chat-empty">{placeholder}</p>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-message chat-message--${m.role}`}>
            <div className="chat-message__text">
              {m.role === "assistant" ? (
                <ReactMarkdown>{m.text}</ReactMarkdown>
              ) : (
                m.text
              )}
            </div>
            {showToolCalls && m.toolCalls?.length > 0 && (
              <details className="chat-message__tools">
                <summary>{m.toolCalls.length} tool call(s)</summary>
                <pre>{JSON.stringify(m.toolCalls, null, 2)}</pre>
              </details>
            )}
          </div>
        ))}
        {sending && <div className="chat-message chat-message--assistant chat-message--pending">Thinking…</div>}
        {error && <div className="chat-error">Error: {error}</div>}
        <div ref={bottomRef} />
      </div>
      <form className="chat-input" onSubmit={handleSend}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message…"
          disabled={sending}
        />
        <button type="submit" disabled={sending || !input.trim()}>Send</button>
      </form>
    </div>
  );
}
