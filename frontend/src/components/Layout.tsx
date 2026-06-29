import { Link, Outlet } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { LogOut, Sparkles, Cpu } from "lucide-react";
import { api } from "@/api/client";
import { useAuth } from "@/hooks/useAuth";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function Layout() {
  const { user, logout } = useAuth();
  const { data: aiInfo } = useQuery({ queryKey: ["ai-info"], queryFn: api.aiInfo });

  return (
    <div className="min-h-screen page-gradient">
      <header className="sticky top-0 z-40 border-b bg-white/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6">
          <Link to="/" className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground shadow-sm">
              <Sparkles className="h-5 w-5" />
            </div>
            <span className="text-xl font-bold tracking-tight">Sage</span>
          </Link>

          <div className="flex items-center gap-3">
            {aiInfo && (
              <Badge variant="secondary" className="hidden sm:inline-flex gap-1.5 py-1">
                <Cpu className="h-3.5 w-3.5" />
                {aiInfo.chat_provider}:{aiInfo.chat_model}
              </Badge>
            )}
            <span className="hidden text-sm text-muted-foreground sm:inline">{user?.name}</span>
            <Button variant="outline" size="sm" onClick={logout} className="gap-2">
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Log out</span>
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <Outlet />
      </main>
    </div>
  );
}
