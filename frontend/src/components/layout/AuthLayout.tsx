// Centered card layout for login / register pages
import { Outlet } from "react-router-dom";

export default function AuthLayout() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <Outlet />
    </div>
  );
}
