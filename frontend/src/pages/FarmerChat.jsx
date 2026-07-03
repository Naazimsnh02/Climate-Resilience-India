import { useState } from "react";
import ChatPanel from "../components/ChatPanel";

export default function FarmerChat() {
  const [chatKey, setChatKey] = useState(0);

  return (
    <div className="farmer-chat">
      <div className="farmer-chat__head">
        <div>
          <span className="farmer-chat__eyebrow">Farmer Advisory</span>
          <h1>Ask about this season's risk</h1>
          <p className="farmer-chat__intro">
            Ask about sowing timing, crop switching, or your district's drought risk.
            Answers cite the underlying data and will tell you when to check with your
            local Krishi Vigyan Kendra instead.
          </p>
        </div>
        <button className="copilot-panel__new-chat" onClick={() => setChatKey((k) => k + 1)}>
          + New Chat
        </button>
      </div>
      <ChatPanel
        key={chatKey}
        agent="farmer_advisory"
        placeholder='Try: "Should I sow paddy this week in Latur?"'
      />
    </div>
  );
}
