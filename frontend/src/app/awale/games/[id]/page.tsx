"use client";

import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { MessageCircle, X } from "lucide-react";

import { AuthGuard } from "@/components/AuthGuard";
import { AwaleBoard } from "@/components/AwaleBoard";
import { AwaleMoveHistory } from "@/components/AwaleMoveHistory";
import { AwaleScore } from "@/components/AwaleScore";
import { ChatPanel } from "@/components/ChatPanel";
import { ConnectionStatus } from "@/components/ConnectionStatus";
import { useAuth } from "@/context/AuthContext";
import { api, wsUrl } from "@/lib/api";
import { createClientId } from "@/lib/clientId";
import type { AwaleState, User } from "@/lib/types";

type Game = { id: string; game_type: "awale"; mode: "human" | "ai"; status: string; configuration: { level?: string; side?: string }; result: string; end_reason: string; conversation_id: string | null; participants: { user: User; role: "player0" | "player1" }[] };

function AwaleGameContent() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [game, setGame] = useState<Game | null>(null);
  const [state, setState] = useState<AwaleState | null>(null);
  const [connected, setConnected] = useState(false);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState("");
  const [tab, setTab] = useState<"chat" | "moves">("chat");
  const [mobileChatOpen, setMobileChatOpen] = useState(false);
  const [animations, setAnimations] = useState(true);
  const [reviewMove, setReviewMove] = useState<number | null>(null);
  const socket = useRef<WebSocket | null>(null);
  const aiRevision = useRef<number | null>(null);

  useEffect(() => {
    Promise.all([api<Game>(`/games/${id}/`), api<AwaleState>(`/awale/games/${id}/state/`)]).then(([gameData, stateData]) => {
      if (gameData.game_type !== "awale") throw new Error("Cette partie n’est pas une partie d’Awalé.");
      setGame(gameData);
      setState(stateData);
      if (gameData.mode === "ai") setTab("moves");
    }).catch((reason) => setError(reason instanceof Error ? reason.message : "Partie introuvable."));
  }, [id]);

  useEffect(() => {
    let active = true;
    let retry: number | undefined;
    const connect = () => {
      if (!active) return;
      const ws = new WebSocket(wsUrl(`/awale/games/${id}/`));
      socket.current = ws;
      ws.onopen = () => { setConnected(true); ws.send(JSON.stringify({ type: "awale.sync" })); };
      ws.onclose = () => { setConnected(false); if (active) retry = window.setTimeout(connect, 1500); };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "awale.state") { setState(data.state); setReviewMove(null); setError(""); }
        if (data.type === "awale.error") setError(typeof data.message === "string" ? data.message : JSON.stringify(data.message));
      };
    };
    connect();
    return () => { active = false; if (retry) window.clearTimeout(retry); socket.current?.close(); };
  }, [id]);

  useEffect(() => {
    document.body.classList.toggle("chat-drawer-open", mobileChatOpen);
    return () => document.body.classList.remove("chat-drawer-open");
  }, [mobileChatOpen]);

  const participant = game?.participants.find((item) => item.user.id === user?.id);
  const playerIndex = participant?.role === "player1" ? 1 : 0;
  const opponent = game?.participants.find((item) => item.user.id !== user?.id)?.user;

  const askAi = useCallback(async (current: AwaleState) => {
    if (aiRevision.current === current.revision) return;
    aiRevision.current = current.revision;
    setThinking(true);
    try {
      setState(await api<AwaleState>(`/awale/games/${id}/ai-turn/`, { method: "POST" }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "L’IA ne répond pas.");
      aiRevision.current = null;
    } finally {
      setThinking(false);
    }
  }, [id]);

  useEffect(() => {
    if (game?.mode === "ai" && state?.status === "in_progress" && participant && state.current_player !== playerIndex) void askAi(state);
  }, [game, state, participant, playerIndex, askAi]);

  const play = async (pit: number) => {
    if (!state || !participant || state.current_player !== playerIndex || state.status !== "in_progress" || thinking) return;
    const request = { type: "awale.move", pit, revision: state.revision, request_id: createClientId() };
    if (game?.mode === "human") {
      if (socket.current?.readyState !== WebSocket.OPEN) { setError("Connexion perdue : le coup n’a pas été envoyé."); return; }
      socket.current.send(JSON.stringify(request));
    } else {
      try {
        setState(await api<AwaleState>(`/awale/games/${id}/moves/`, { method: "POST", body: JSON.stringify(request) }));
      } catch (reason) { setError(reason instanceof Error ? reason.message : "Coup refusé."); }
    }
  };

  const finish = async (action: "resign" | "draw") => {
    const updated = await api<Game>(`/games/${id}/${action}/`, { method: "POST" });
    setGame(updated);
    setState((current) => current ? { ...current, status: updated.status, result: updated.result, end_reason: updated.end_reason } : current);
  };

  if (!game || !state || !participant || !user) return <main className="auth-wrap">{error ? <div className="form-error">{error}</div> : <div className="spinner" />}</main>;

  const names: [string, string] = participant.role === "player0"
    ? [user.display_name, opponent?.display_name ?? "TableChat IA"]
    : [opponent?.display_name ?? "TableChat IA", user.display_name];
  const reasonLabels: Record<string, string> = { majority: "Majorité atteinte", "24-24": "Égalité 24–24", no_legal_move: "Aucun coup légal", threefold_repetition: "Troisième répétition", abandon: "Abandon", "accord mutuel": "Nulle par accord" };
  const resultLabel = state.result === "1-0" ? `${names[0]} gagne` : state.result === "0-1" ? `${names[1]} gagne` : "Partie nulle";
  const feedback = state.last_move.capture_cancelled
    ? "Capture annulée : elle viderait le camp adverse."
    : state.last_move.captured_seeds
      ? `${state.last_move.captured_seeds} graines capturées.`
      : state.current_player === playerIndex ? "Choisissez un trou de votre camp." : "Votre adversaire réfléchit.";
  const reviewed = state.history.find((move) => move.move_number === reviewMove);
  const visiblePits = reviewed?.state_after.pits ?? state.pits;
  const visibleScores = reviewed?.state_after.scores ?? state.scores;
  const visiblePlayer = reviewed?.state_after.current_player ?? state.current_player;

  return <main className="main game-main awale-game-main"><div className="shell game-shell">
    <div className="game-heading"><div><div className="breadcrumb">Jeux / Awalé</div><h1>Awalé avec {opponent?.display_name ?? "TableChat IA"}</h1></div><ConnectionStatus connected={game.mode === "ai" || connected} /></div>
    {error && <div className="connection-banner">{error}</div>}
    <div className="game-layout awale-game-layout">
      <div className="board-column awale-board-column">
        <AwaleScore names={names} scores={visibleScores} currentPlayer={visiblePlayer} />
        <div className={`awale-board-wrap ${animations ? "animated" : ""}`}><AwaleBoard pits={visiblePits} legalMoves={!reviewed && state.current_player === playerIndex ? state.legal_moves : []} orientation={playerIndex} lastPit={reviewed?.pit ?? state.last_move.pit} disabled={Boolean(reviewed) || thinking || state.status !== "in_progress"} onMove={play} />{state.status === "finished" && !reviewed && <div className="game-over-overlay" role="dialog"><div className="card game-over-card"><p className="eyebrow">Partie terminée</p><h2>{resultLabel}</h2><p>{reasonLabels[state.end_reason] ?? state.end_reason}</p><button className="btn primary" onClick={() => window.location.href = "/games"}>Retour aux jeux</button></div></div>}</div>
        <div className="awale-feedback" role="status"><span>{reviewed ? `Relecture du coup ${reviewed.move_number} de ${reviewed.author}.` : thinking ? "L’IA cherche son meilleur semis…" : feedback}</span>{reviewed ? <button className="btn ghost" onClick={() => setReviewMove(null)}>Retour au direct</button> : <button className="btn ghost" onClick={() => setAnimations((value) => !value)}>{animations ? "Animations actives" : "Animations coupées"}</button>}</div>
        <div className="game-actions"><button className="btn" disabled={state.status !== "in_progress"} onClick={() => finish("draw")}>Proposer la nulle</button><button className="btn danger" disabled={state.status !== "in_progress"} onClick={() => finish("resign")}>Abandonner</button></div>
      </div>
      <aside className={`card game-sidebar ${mobileChatOpen ? "open" : ""}`} aria-label="Panneau de partie">
        <div className="game-sidebar-mobile-header"><strong>Conversation</strong><button className="icon-button" onClick={() => setMobileChatOpen(false)} aria-label="Fermer"><X size={22} /></button></div>
        <div className="tabs"><button className={`tab ${tab === "chat" ? "active" : ""}`} onClick={() => setTab("chat")}>Discussion</button><button className={`tab ${tab === "moves" ? "active" : ""}`} onClick={() => setTab("moves")}>Coups</button></div>
        {tab === "chat" ? (game.conversation_id ? <ChatPanel conversationId={game.conversation_id} currentUserId={user.id} embedded /> : <div className="empty">Le chat est disponible entre amis.</div>) : <section className="side-panel embedded-panel"><AwaleMoveHistory moves={state.history} selectedMove={reviewMove} onSelect={(move) => setReviewMove(move.move_number)} /></section>}
      </aside>
    </div>
    {mobileChatOpen && <button className="game-chat-backdrop" onClick={() => setMobileChatOpen(false)} aria-label="Fermer le chat" />}
    {game.mode === "human" && game.conversation_id && <button className="mobile-chat-button" onClick={() => { setTab("chat"); setMobileChatOpen(true); }} aria-label="Ouvrir la conversation"><MessageCircle size={26} /></button>}
  </div></main>;
}

export default function AwaleGamePage() { return <AuthGuard><AwaleGameContent /></AuthGuard>; }
