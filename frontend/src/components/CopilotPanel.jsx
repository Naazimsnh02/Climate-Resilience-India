import { useEffect, useState } from "react";
import ChatPanel from "./ChatPanel";
import { useAppState } from "../context/AppState";

const AGENTS = {
  triage: {
    label: "Triage Agent",
    placeholder: '',
    suggestions: [
      { icon: "🧭", text: "What should I prioritize today?" },
      { icon: "🚨", text: "Show me top 10 riskiest districts" },
      { icon: "🚚", text: "Which districts need tankers?" },
      { icon: "❓", text: "Explain why the top district is high risk" },
    ],
  },
  allocation: {
    label: "Allocation Agent",
    placeholder: '',
    suggestions: [
      { icon: "🚚", text: "I have 50 water tankers, allocate across Marathwada" },
      { icon: "📦", text: "Suggest MGNREGA works for high-risk districts" },
      { icon: "⚖️", text: "Compare Maharashtra vs Madhya Pradesh needs" },
      { icon: "📋", text: "Summarize today's allocation priorities" },
    ],
  },
};

export default function CopilotPanel({ onShowDistrict }) {
  const { activeAgent, setActiveAgent, seedMessage, clearSeedMessage, selectDistrict } = useAppState();
  const [pendingMessage, setPendingMessage] = useState(null);
  const [chatKey, setChatKey] = useState(0);
  const [hasStarted, setHasStarted] = useState(false);

  const agent = AGENTS[activeAgent];

  useEffect(() => {
    if (seedMessage && seedMessage.agent === activeAgent) {
      setHasStarted(true);
      setPendingMessage(seedMessage.text);
      clearSeedMessage();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seedMessage, activeAgent]);

  function handleSuggestion(text) {
    setHasStarted(true);
    setPendingMessage(text);
  }

  function handleNewChat() {
    setChatKey((k) => k + 1);
    setHasStarted(false);
    selectDistrict(null);
  }

  return (
    <div className="copilot-panel">
      <div className="copilot-panel__header">
        <div className="copilot-panel__title">
          <span className="copilot-panel__badge">✨</span>
          AI Copilot
        </div>
        <button className="copilot-panel__new-chat" onClick={handleNewChat}>+ New Chat</button>
      </div>
      {onShowDistrict && (
        <button className="copilot-panel__back" onClick={onShowDistrict}>
          ← Back to district profile
        </button>
      )}
      {!hasStarted && (
        <div className="try-asking">
          <span className="try-asking__label">Try asking</span>
          <div className="try-asking__grid">
            {agent.suggestions.map((s) => (
              <button key={s.text} className="try-asking__chip" onClick={() => handleSuggestion(s.text)}>
                <span className="try-asking__chip-icon">{s.icon}</span>
                {s.text}
              </button>
            ))}
          </div>
        </div>
      )}
      <ChatPanel
        key={`${activeAgent}-${chatKey}`}
        agent={activeAgent}
        placeholder={agent.placeholder}
        showToolCalls
        pendingMessage={pendingMessage}
        onPendingSent={() => setPendingMessage(null)}
        onFirstMessage={() => setHasStarted(true)}
      />
    </div>
  );
}
