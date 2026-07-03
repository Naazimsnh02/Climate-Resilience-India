import ChatPanel from "../components/ChatPanel";

export default function FarmerChat() {
  return (
    <div className="farmer-chat">
      <h1>Farmer Advisory</h1>
      <p className="farmer-chat__intro">
        Ask about sowing timing, crop switching, or your district's drought risk.
        Answers cite the underlying data and will tell you when to check with your
        local Krishi Vigyan Kendra instead.
      </p>
      <ChatPanel
        agent="farmer_advisory"
        placeholder='Try: "Should I sow paddy this week in Latur?"'
      />
    </div>
  );
}
