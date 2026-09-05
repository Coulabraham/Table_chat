"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { api, ensureCsrf } from "@/lib/api";
import type { User } from "@/lib/types";

type AuthValue = { user: User | null; loading: boolean; refresh: () => Promise<void>; logout: () => Promise<void> };
const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const refresh = async () => {
    try { setUser(await api<User>("/auth/me/")); } catch { setUser(null); } finally { setLoading(false); }
  };
  useEffect(() => { ensureCsrf().then(refresh).catch(() => setLoading(false)); }, []);
  const logout = async () => { await api("/auth/logout/", { method: "POST" }); setUser(null); };
  return <AuthContext.Provider value={{ user, loading, refresh, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider manquant");
  return value;
}
