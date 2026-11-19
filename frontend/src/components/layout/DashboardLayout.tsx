// Persistent sidebar + topbar shell for authenticated pages
import { Outlet } from "react-router-dom";

export default function DashboardLayout() {
  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      {/* Topbar */}
      <main className="flex-1 overflow-y-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
