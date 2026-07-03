import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout";
import AdminConsole from "./pages/AdminConsole";
import FarmerChat from "./pages/FarmerChat";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route index element={<Navigate to="/admin" replace />} />
          <Route path="/admin" element={<AdminConsole />} />
          <Route path="/farmer" element={<FarmerChat />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
