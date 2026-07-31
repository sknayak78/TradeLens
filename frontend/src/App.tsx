import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import Dashboard from "@/pages/Dashboard";
import WatchlistPage from "@/pages/WatchlistPage";
import TradingJournal from "@/pages/TradingJournal";
import SettingsPage from "@/pages/SettingsPage";
import "@/App.css";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/journal" element={<TradingJournal />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
