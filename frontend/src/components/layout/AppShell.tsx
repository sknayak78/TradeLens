import { Outlet } from "react-router-dom";
import Header from "@/components/layout/Header";
import Sidebar from "@/components/layout/Sidebar";
import EducationalDisclaimer from "@/components/common/EducationalDisclaimer";
import { Toaster } from "@/components/ui/toaster";
import { useState } from "react";

export default function AppShell() {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  return (
    <div
      className="h-screen w-screen flex flex-col overflow-hidden bg-[#F6F7F5] text-[#1F2933]"
      data-testid="app-shell"
    >
      <Header onOpenMobileNav={() => setMobileNavOpen(true)} />
      <div className="flex flex-1 min-h-0">
        <Sidebar
          mobileOpen={mobileNavOpen}
          onCloseMobile={() => setMobileNavOpen(false)}
        />
        <div className="flex flex-1 min-w-0 flex-col min-h-0">
          <main
            className="flex-1 min-w-0 overflow-y-auto"
            data-testid="main-content"
          >
            <Outlet />
          </main>
          <footer
            className="shrink-0 border-t border-[#D9DDE2] bg-white px-4 py-2"
            data-testid="app-footer"
          >
            <EducationalDisclaimer />
          </footer>
        </div>
      </div>
      <Toaster />
    </div>
  );
}
