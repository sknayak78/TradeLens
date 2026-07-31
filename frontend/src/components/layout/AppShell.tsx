import { Outlet } from "react-router-dom";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import { useState } from "react";

export default function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div
      className="h-screen w-screen flex flex-col overflow-hidden bg-[#131722] text-[#d1d4dc]"
      data-testid="app-shell"
    >
      <Header onOpenMobileNav={() => setMobileNavOpen(true)} />
      <div className="flex flex-1 min-h-0">
        <Sidebar
          mobileOpen={mobileNavOpen}
          onCloseMobile={() => setMobileNavOpen(false)}
        />
        <main
          className="flex-1 min-w-0 overflow-y-auto"
          data-testid="main-content"
        >
          <Outlet />
        </main>
      </div>
    </div>
  );
}
