import { useEffect, useState } from "react";
import DistrictMap from "../components/DistrictMap";
import DistrictDrilldown from "../components/DistrictDrilldown";
import CopilotPanel from "../components/CopilotPanel";
import StatStrip from "../components/StatStrip";
import { useAppState } from "../context/AppState";

export default function OverviewPage() {
  const [rightView, setRightView] = useState("chat");
  const { districts, districtsError: error, selectedDistrictId, districtFocusToken, chatFocusToken, selectDistrict } =
    useAppState();

  useEffect(() => {
    if (districtFocusToken > 0) setRightView("district");
  }, [districtFocusToken]);

  useEffect(() => {
    if (chatFocusToken > 0) setRightView("chat");
  }, [chatFocusToken]);

  return (
    <div className="overview">
      <div className="overview__left">
        <StatStrip districts={districts} />
        {error && <div className="map-load-error">Failed to load districts: {error}</div>}
        <div className="map-card">
          <DistrictMap districts={districts} selectedId={selectedDistrictId} onSelect={selectDistrict} />
        </div>
      </div>
      <div className="overview__right">
        {rightView === "district" && selectedDistrictId ? (
          <DistrictDrilldown districtId={selectedDistrictId} onOpenChat={() => setRightView("chat")} />
        ) : (
          <CopilotPanel onShowDistrict={selectedDistrictId ? () => setRightView("district") : null} />
        )}
      </div>
    </div>
  );
}
