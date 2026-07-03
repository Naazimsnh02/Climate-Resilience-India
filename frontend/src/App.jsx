import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import { AppStateProvider } from "./context/AppState";
import LandingPage from "./pages/LandingPage";
import OverviewPage from "./pages/OverviewPage";
import DistrictsPage from "./pages/DistrictsPage";
import FarmerChat from "./pages/FarmerChat";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <AppStateProvider>
        <Routes>
          <Route path="/" element={<LandingPage />} />
          <Route element={<Layout />}>
            <Route path="/overview" element={<OverviewPage />} />
            <Route path="/districts" element={<DistrictsPage />} />
            <Route path="/farmer" element={<FarmerChat />} />
            <Route path="*" element={<Navigate to="/overview" replace />} />
          </Route>
        </Routes>
      </AppStateProvider>
    </BrowserRouter>
  );
}
