import { useEffect, useState } from "react";
import { useAppState } from "../context/AppState";
import { getHealth } from "../api";

export default function TopBar() {
  const { activeAgent, openChat } = useAppState();
  const [query, setQuery] = useState("");
  const [health, setHealth] = useState(null);
  const [healthError, setHealthError] = useState(false);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealthError(true));
  }, []);

  function handleSearchSubmit(e) {
    e.preventDefault();
    const text = query.trim();
    if (!text) return;
    openChat("triage", text);
    setQuery("");
  }

  return (
    <header className="topbar">
      <div className="topbar__brand">
        <img src="/logo_transparent.png" className="topbar__logo" alt="Climate Resilience India Logo" />
        <div className="topbar__titles">
          <span className="topbar__title">El Niño 2026 Decision Copilot</span>
          <span className="topbar__subtitle">Climate Resilience India</span>
        </div>
      </div>
      <form className="topbar__search" onSubmit={handleSearchSubmit}>
        <span className="topbar__search-icon" aria-hidden="true">⌕</span>
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Ask anything… e.g. Which districts need immediate attention?"
        />
      </form>
      <div className="topbar__agents">
        <button
          type="button"
          className={activeAgent === "triage" ? "topbar__agent-btn topbar__agent-btn--active" : "topbar__agent-btn"}
          onClick={() => openChat("triage")}
        >
          Triage Agent
        </button>
        <button
          type="button"
          className={activeAgent === "allocation" ? "topbar__agent-btn topbar__agent-btn--active" : "topbar__agent-btn"}
          onClick={() => openChat("allocation")}
        >
          Allocation Agent
        </button>
      </div>
      <div className="topbar__status">
        <div className="topbar__status-col">
          <span className="topbar__status-label">System Status</span>
          <span className="topbar__status-val">
            <span className={healthError ? "status-dot-red" : "status-dot-green"} />
            {healthError ? "Offline" : health ? "Nominal" : "Checking…"}
          </span>
        </div>
        {health?.model && (
          <div className="topbar__status-col">
            <span className="topbar__status-label">Model</span>
            <span className="topbar__status-val topbar__status-val--cyan">✦ {health.model}</span>
          </div>
        )}
      </div>
    </header>
  );
}
