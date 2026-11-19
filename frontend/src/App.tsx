import { Routes, Route, Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import DashboardLayout from "@/components/layout/DashboardLayout";
import AuthLayout from "@/components/layout/AuthLayout";
import LoginPage from "@/pages/LoginPage";
import RegisterPage from "@/pages/RegisterPage";
import DashboardPage from "@/pages/DashboardPage";
import DecisionsPage from "@/pages/DecisionsPage";
import DocumentsPage from "@/pages/DocumentsPage";
import MemoryPage from "@/pages/MemoryPage";
import NewsPage from "@/pages/NewsPage";
import InsightsPage from "@/pages/InsightsPage";
import SettingsPage from "@/pages/SettingsPage";

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = useAuthStore((s) => s.token);
  return token ? <>{children}</> : <Navigate to="/login" replace />;
}

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route element={<AuthLayout />}>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Route>

      {/* Protected */}
      <Route
        element={
          <PrivateRoute>
            <DashboardLayout />
          </PrivateRoute>
        }
      >
        <Route path="/" element={<DashboardPage />} />
        <Route path="/decisions" element={<DecisionsPage />} />
        <Route path="/documents" element={<DocumentsPage />} />
        <Route path="/memory" element={<MemoryPage />} />
        <Route path="/news" element={<NewsPage />} />
        <Route path="/insights" element={<InsightsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
