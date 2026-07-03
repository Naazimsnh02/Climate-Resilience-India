import { useEffect, useState } from "react";
import { listDistricts } from "../api";
import DistrictMap from "../components/DistrictMap";
import DistrictDrilldown from "../components/DistrictDrilldown";
import ChatPanel from "../components/ChatPanel";

export default function AdminConsole() {
  const [districts, setDistricts] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [error, setError] = useState(null);
  const [activeAgent, setActiveAgent] = useState("triage");

  useEffect(() => {
    listDistricts()
      .then((data) => setDistricts(data.districts))
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="admin-console">
      <div className="admin-console__map-col">
        {error && <div className="chat-error">Failed to load districts: {error}</div>}
        <DistrictMap districts={districts} selectedId={selectedId} onSelect={setSelectedId} />
        <DistrictDrilldown districtId={selectedId} />
      </div>
      <div className="admin-console__chat-col">
        <div className="agent-tabs">
          <button
            className={activeAgent === "triage" ? "agent-tab agent-tab--active" : "agent-tab"}
            onClick={() => setActiveAgent("triage")}
          >
            Triage Agent
          </button>
          <button
            className={activeAgent === "allocation" ? "agent-tab agent-tab--active" : "agent-tab"}
            onClick={() => setActiveAgent("allocation")}
          >
            Allocation Agent
          </button>
        </div>
        {activeAgent === "triage" ? (
          <ChatPanel
            key="triage"
            agent="triage"
            placeholder='Ask e.g. "Show me the top 10 riskiest districts"'
            showToolCalls
          />
        ) : (
          <ChatPanel
            key="allocation"
            agent="allocation"
            placeholder='Ask e.g. "I have 50 water tankers, allocate across Marathwada"'
            showToolCalls
          />
        )}
      </div>
    </div>
  );
}
