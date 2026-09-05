"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

const levels = [
  { value: "beginner", label: "Débutant" },
  { value: "intermediate", label: "Intermédiaire" },
  { value: "advanced", label: "Avancé" },
];

export function AwaleGameLobby() {
  const router = useRouter();
  const [side, setSide] = useState("player0");
  const [level, setLevel] = useState("beginner");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const start = async () => {
    setPending(true);
    setError("");
    try {
      const game = await api<{ id: string }>("/games/", {
        method: "POST",
        body: JSON.stringify({ mode: "ai", game_type: "awale", configuration: { side, level } }),
      });
      router.push(`/awale/games/${game.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Impossible de créer la partie.");
      setPending(false);
    }
  };
  return <div className="card list-card">
    <h2>Préparer le plateau</h2><p className="subtitle">Chaque trou commence avec quatre graines. Le joueur 0 ouvre la partie.</p>
    <div style={{ display: "grid", gap: 18, marginTop: 24 }}>
      <label className="label">Votre camp<select className="input" value={side} onChange={(event) => setSide(event.target.value)}><option value="player0">Joueur 0 · commence</option><option value="player1">Joueur 1 · joue en second</option><option value="random">Au hasard</option></select></label>
      <label className="label">Difficulté<select className="input" value={level} onChange={(event) => setLevel(event.target.value)}>{levels.map((item) => <option value={item.value} key={item.value}>{item.label}</option>)}</select></label>
      {error && <div className="form-error">{error}</div>}
      <button className="btn primary" disabled={pending} onClick={start}>{pending ? "Les graines sont distribuées…" : "Commencer la partie"}</button>
    </div>
  </div>;
}
