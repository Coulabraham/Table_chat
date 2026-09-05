"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

type CreatedGame = { id: string };
const levels = [{ value: "decouverte", label: "Découverte" }, { value: "club", label: "Club" }, { value: "confirme", label: "Confirmé" }, { value: "expert", label: "Expert" }];

export function GameLobby() {
  const router = useRouter();
  const [color, setColor] = useState("white");
  const [level, setLevel] = useState("decouverte");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const start = async () => {
    setPending(true); setError("");
    try {
      const game = await api<CreatedGame>("/games/", { method: "POST", body: JSON.stringify({ mode: "ai", game_type: "chess", configuration: { color, level } }) });
      router.push(`/games/${game.id}`);
    } catch (err) { setError(err instanceof Error ? err.message : "Impossible de créer la partie."); setPending(false); }
  };
  return <div className="card list-card">
    <h2>Préparer la table</h2>
    <p className="subtitle">Les niveaux sont des réglages de moteur, pas des classements Elo.</p>
    <div style={{ display: "grid", gap: 18, marginTop: 24 }}>
      <label className="label">Votre camp<select className="input" value={color} onChange={(e) => setColor(e.target.value)}><option value="white">Blancs</option><option value="black">Noirs</option><option value="random">Au hasard</option></select></label>
      <label className="label">Difficulté<select className="input" value={level} onChange={(e) => setLevel(e.target.value)}>{levels.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
      {error && <div className="form-error">{error}</div>}
      <button className="btn primary" disabled={pending} onClick={start}>{pending ? "Installation des pièces…" : "Commencer la partie"}</button>
    </div>
  </div>;
}

