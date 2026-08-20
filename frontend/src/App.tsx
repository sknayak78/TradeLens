import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import AppShell from "@/components/layout/AppShell";
import Dashboard from "@/pages/Dashboard";
import WatchlistPage from "@/pages/WatchlistPage";
import TradingJournal from "@/pages/TradingJournal";
import SettingsPage from "@/pages/SettingsPage";
import HowToUseHubPage from "@/pages/HowToUseHubPage";
import HowToUsePage from "@/pages/HowToUsePage";
import FoundersVisionHubPage from "@/pages/FoundersVisionHubPage";
import CommunityPage from "@/pages/CommunityPage";
import "@/App.css";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/how-to-use" element={<HowToUseHubPage />}>
            <Route index element={<HowToUsePage />} />
          </Route>
          <Route path="/founders-vision" element={<FoundersVisionHubPage />} />
          {/* Legacy learn routes */}
          <Route path="/learn" element={<Navigate to="/how-to-use" replace />} />
          <Route path="/learn/vision" element={<Navigate to="/founders-vision" replace />} />
          <Route path="/community" element={<CommunityPage />} />
          <Route path="/watchlist" element={<WatchlistPage />} />
          <Route path="/journal" element={<TradingJournal />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
