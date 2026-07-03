import { createContext, useContext, useEffect, useState, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { listDistricts } from "../api";

const AppStateContext = createContext(null);

export function AppStateProvider({ children }) {
  const navigate = useNavigate();
  const [activeAgent, setActiveAgent] = useState("triage");
  const [chatFocusToken, setChatFocusToken] = useState(0);
  const [seedMessage, setSeedMessage] = useState(null);
  const [selectedDistrictId, setSelectedDistrictId] = useState(null);
  const [districtFocusToken, setDistrictFocusToken] = useState(0);
  const [districts, setDistricts] = useState([]);
  const [districtsError, setDistrictsError] = useState(null);
  const [districtsLoaded, setDistrictsLoaded] = useState(false);

  const refreshDistricts = useCallback(() => {
    return listDistricts()
      .then((data) => {
        setDistricts(data.districts);
        setDistrictsError(null);
      })
      .catch((err) => setDistrictsError(err.message))
      .finally(() => setDistrictsLoaded(true));
  }, []);

  useEffect(() => {
    refreshDistricts();
  }, [refreshDistricts]);

  function openChat(agent, message) {
    setActiveAgent(agent);
    if (message) setSeedMessage({ agent, text: message, token: Date.now() });
    setChatFocusToken((t) => t + 1);
    navigate("/overview");
  }

  function selectDistrict(id) {
    setSelectedDistrictId(id);
    setDistrictFocusToken((t) => t + 1);
    navigate("/overview");
  }

  const value = {
    activeAgent,
    setActiveAgent,
    chatFocusToken,
    seedMessage,
    clearSeedMessage: () => setSeedMessage(null),
    openChat,
    selectedDistrictId,
    districtFocusToken,
    selectDistrict,
    districts,
    districtsError,
    districtsLoaded,
    refreshDistricts,
  };

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState() {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}
