import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { LoadingState } from "@/components/ui/spinner";

export function ProtectedRoute() {
  const { user, loading } = useAuth();
  if (loading) return <LoadingState message="Loading Sage..." />;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}
