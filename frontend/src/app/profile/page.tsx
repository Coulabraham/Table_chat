"use client";

import { useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { UserAvatar } from "@/components/UserAvatar";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

function ProfileContent() {
  const { user, logout, refresh } = useAuth();
  const [name, setName] = useState(user?.display_name ?? "");
  const [level, setLevel] = useState(user?.chess_level ?? "beginner");
  const [notice, setNotice] = useState("");
  if (!user) return null;
  const save = async () => { await api("/auth/me/", { method: "PATCH", body: JSON.stringify({ display_name: name, chess_level: level }) }); await refresh(); setNotice("Profil mis à jour."); };
  return <main className="main"><div className="shell" style={{ maxWidth: 680 }}><div className="page-heading"><h1>Votre profil</h1></div><section className="card list-card"><div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 24 }}><UserAvatar name={user.display_name} /><div><strong>{user.display_name}</strong><br /><small>Membre depuis {new Date(user.created_at).toLocaleDateString("fr-FR")}</small></div></div><div style={{ display: "grid", gap: 18 }}><label className="label">Pseudo public<input className="input" value={name} onChange={(e) => setName(e.target.value)} /></label><label className="label">Niveau déclaré<select className="input" value={level} onChange={(e) => setLevel(e.target.value)}><option value="beginner">Débutant</option><option value="casual">Loisir</option><option value="intermediate">Intermédiaire</option><option value="advanced">Avancé</option></select></label>{notice && <div className="feedback">{notice}</div>}<button className="btn primary" onClick={save}>Enregistrer</button><button className="btn danger" onClick={logout}>Se déconnecter</button></div></section></div></main>;
}
export default function ProfilePage() { return <AuthGuard><ProfileContent /></AuthGuard>; }
