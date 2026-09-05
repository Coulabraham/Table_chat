"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { Chess } from "chess.js";
import { AuthGuard } from "@/components/AuthGuard";
import { ChatPanel } from "@/components/ChatPanel";
import { ChessBoard } from "@/components/ChessBoard";
import { ConnectionStatus } from "@/components/ConnectionStatus";
import { UserAvatar } from "@/components/UserAvatar";
import { useAuth } from "@/context/AuthContext";
import { api, wsUrl } from "@/lib/api";
import type { ChessState, User } from "@/lib/types";

type Game = { id: string; mode: "human" | "ai"; status: string; configuration: { color?: "white" | "black"; level?: string; draw_offered_by?: number }; result: string; end_reason: string; conversation_id: string | null; participants: { user: User; role: "white" | "black" }[] };

function browserEngine(fen: string, timeMs: number): Promise<string> {
  return new Promise((resolve, reject) => {
    const worker = new Worker("/stockfish/stockfish.js");
    const timeout = window.setTimeout(() => { worker.terminate(); reject(new Error("Délai dépassé")); }, 3500);
    worker.onmessage = (event) => { const line = String(event.data); if (line.startsWith("bestmove")) { clearTimeout(timeout); worker.terminate(); resolve(line.split(" ")[1]); } };
    worker.onerror = () => { clearTimeout(timeout); worker.terminate(); reject(new Error("Moteur local indisponible")); };
    worker.postMessage(`position fen ${fen}`);
    worker.postMessage(`go movetime ${timeMs}`);
  });
}

function GameContent() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [game, setGame] = useState<Game | null>(null);
  const [state, setState] = useState<ChessState | null>(null);
  const [connected, setConnected] = useState(false);
  const [tab, setTab] = useState<"chat" | "moves">("chat");
  const [error, setError] = useState("");
  const [thinking, setThinking] = useState(false);
  const socket = useRef<WebSocket | null>(null);
  const aiRevision = useRef<number | null>(null);

  useEffect(() => { Promise.all([api<Game>(`/games/${id}/`), api<ChessState>(`/chess/games/${id}/state/`)]).then(([gameData, stateData]) => { setGame(gameData); setState(stateData); }).catch((err) => setError(err.message)); }, [id]);
  useEffect(() => {
    let retry: number | undefined;
    let active = true;
    const connect = () => {
      if (!active) return;
      const ws = new WebSocket(wsUrl(`/games/${id}/`)); socket.current = ws;
      ws.onopen = () => { setConnected(true); ws.send(JSON.stringify({ type: "game.sync" })); };
      ws.onclose = () => { setConnected(false); retry = window.setTimeout(connect, 1500); };
      ws.onmessage = (event) => { const data = JSON.parse(event.data); if (data.type === "game.state") { setState(data.state); setError(""); } else if (data.type === "game.error") setError(typeof data.message === "string" ? data.message : JSON.stringify(data.message)); };
    };
    connect(); return () => { active = false; if (retry) clearTimeout(retry); socket.current?.close(); };
  }, [id]);

  const participant = game?.participants.find((item) => item.user.id === user?.id);
  const opponent = game?.participants.find((item) => item.user.id !== user?.id)?.user;
  const turn = state?.fen.split(" ")[1] === "w" ? "white" : "black";

  const askAi = useCallback(async (current: ChessState, currentGame: Game) => {
    if (aiRevision.current === current.revision) return;
    aiRevision.current = current.revision; setThinking(true);
    try {
      let uci: string | undefined;
      if (["decouverte", "club"].includes(currentGame.configuration.level ?? "")) {
        try { uci = await browserEngine(current.fen, currentGame.configuration.level === "club" ? 500 : 180); } catch { /* Le serveur prend le relais si le WASM n’est pas installé. */ }
      }
      const next = await api<ChessState>(`/chess/games/${id}/ai-turn/`, { method: "POST", body: JSON.stringify(uci ? { uci } : {}) });
      setState(next);
    } catch (err) { setError(err instanceof Error ? err.message : "Le moteur ne répond pas."); aiRevision.current = null; }
    finally { setThinking(false); }
  }, [id]);

  useEffect(() => {
    if (game?.mode === "ai" && state?.status === "in_progress" && participant && turn !== participant.role) void askAi(state, game);
  }, [game, state, participant, turn, askAi]);

  const move = async (uci: string) => {
    if (!state || !participant || turn !== participant.role || state.status !== "in_progress") return false;
    if (game?.mode === "human") {
      if (socket.current?.readyState !== WebSocket.OPEN) { setError("Connexion perdue : le coup n’a pas été envoyé."); return false; }
      socket.current.send(JSON.stringify({ type: "game.move", uci, revision: state.revision, request_id: crypto.randomUUID() }));
    } else {
      try { setState(await api<ChessState>(`/chess/games/${id}/moves/`, { method: "POST", body: JSON.stringify({ uci, revision: state.revision, request_id: crypto.randomUUID() }) })); }
      catch (err) { setError(err instanceof Error ? err.message : "Coup refusé."); return false; }
    }
    return true;
  };
  const finish = async (action: "resign" | "draw") => { const updated = await api<Game>(`/games/${id}/${action}/`, { method: "POST" }); setGame(updated); setState((value) => value ? { ...value, status: updated.status, result: updated.result, end_reason: updated.end_reason } : value); };
  if (!game || !state || !participant || !user) return <main className="auth-wrap">{error ? <div className="form-error">{error}</div> : <div className="spinner" />}</main>;
  const chess = new Chess(state.fen);
  const reasonLabels: Record<string, string> = { checkmate: "Échec et mat", stalemate: "Pat", insufficient_material: "Matériel insuffisant", seventyfive_moves: "Règle des 75 coups", fivefold_repetition: "Répétition de position", abandon: "Abandon", "accord mutuel": "Nulle par accord" };
  const endReason = reasonLabels[state.end_reason] ?? state.end_reason;
  const resultLabel = state.result === "1-0" ? "Les Blancs gagnent" : state.result === "0-1" ? "Les Noirs gagnent" : state.result === "1/2-1/2" ? "Partie nulle" : state.result;
  const statusText = state.status === "finished" ? `${resultLabel} · ${endReason}` : thinking ? "L’IA réfléchit…" : turn === participant.role ? "À vous de jouer" : "À votre adversaire";
  return <main className="main"><div className="shell"><div className="breadcrumb">Jouer / {game.mode === "human" ? "Partie entre amis" : "Entraînement contre l’IA"}</div><div className="page-heading" style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}><h1>{game.mode === "human" ? `Votre partie avec ${opponent?.display_name ?? "un ami"}` : "Votre partie d’entraînement"}</h1><ConnectionStatus connected={connected} /></div>{error && <div className="connection-banner">{error}</div>}<div className="game-layout"><div className="board-column"><div className="player-strip"><div className="player"><UserAvatar name={opponent?.display_name ?? "TableChat IA"} /><div><strong>{opponent?.display_name ?? "TableChat IA"}</strong><br /><small>{participant.role === "white" ? "Noirs" : "Blancs"}</small></div></div></div><div className="board-wrap"><ChessBoard fen={state.fen} orientation={participant.role} onMove={move} disabled={thinking || state.status !== "in_progress"} lastMove={state.moves.at(-1)?.uci} />{state.status === "finished" && <div className="game-over-overlay" role="dialog" aria-label="Partie terminée"><div className="card game-over-card"><p className="eyebrow">Partie terminée</p><h2>{endReason || "Fin de la partie"}</h2><p>{resultLabel}</p><button className="btn primary" style={{ marginTop: 14 }} onClick={() => window.location.href = "/"}>Retour à l’accueil</button></div></div>}</div><div className="player-strip"><div className="player"><UserAvatar name={user.display_name} /><div><strong>Vous</strong><br /><small>{participant.role === "white" ? "Blancs" : "Noirs"}</small></div></div><span className="status">{statusText}</span></div><div className="game-actions"><button className="btn" disabled={state.status !== "in_progress"} onClick={() => finish("draw")}>Proposer la nulle</button><button className="btn danger" disabled={state.status !== "in_progress"} onClick={() => finish("resign")}>Abandonner</button></div></div><aside><div className="tabs"><button className={`tab ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")}>Discussion</button><button className={`tab ${tab === "moves" ? "active" : ""}`} onClick={() => setTab("moves")}>Coups</button></div>{tab === "chat" ? (game.conversation_id ? <ChatPanel conversationId={game.conversation_id} currentUserId={user.id} /> : <div className="card empty">Le chat est disponible dans les parties entre amis.</div>) : <section className="card side-panel"><h2>Historique</h2>{state.moves.length ? <ol className="moves-list">{state.moves.map((item) => <li key={item.ply}>{item.san}</li>)}</ol> : <div className="empty">Aucun coup joué.</div>}<button className="btn" onClick={() => navigator.clipboard.writeText(state.pgn)}>Copier le PGN</button>{chess.inCheck() && state.status !== "finished" && <div className="feedback wrong">Le roi est en échec.</div>}</section>}</aside></div></div></main>;
}

export default function GamePage() { return <AuthGuard><GameContent /></AuthGuard>; }
