"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { ChessBoard } from "@/components/ChessBoard";
import { api } from "@/lib/api";
import type { Lesson, LessonSession } from "@/lib/types";

type Attempt = LessonSession & { correct: boolean; opponent_move: string | null };

function LessonContent() {
  const { id } = useParams<{ id: string }>();
  const [lesson, setLesson] = useState<Lesson | null>(null);
  const [fen, setFen] = useState("");
  const [session, setSession] = useState<LessonSession | null>(null);
  const [hints, setHints] = useState<string[]>([]);
  const [feedback, setFeedback] = useState<{ correct: boolean; completed: boolean } | null>(null);
  const [pending, setPending] = useState(false);
  useEffect(() => {
    Promise.all([api<Lesson>(`/chess/lessons/${id}/`), api<LessonSession>(`/chess/lessons/${id}/start/`, { method: "POST", body: "{}" })]).then(([lessonData, sessionData]) => { setLesson(lessonData); setSession(sessionData); setFen(sessionData.fen); });
  }, [id]);
  if (!lesson) return <main className="auth-wrap"><div className="spinner" /></main>;
  const move = async (uci: string) => {
    setPending(true);
    try {
      const response = await api<Attempt>(`/chess/lessons/${lesson.id}/attempt/`, { method: "POST", body: JSON.stringify({ uci }) });
      setSession(response); setFen(response.fen); setFeedback({ correct: response.correct, completed: response.completed });
      return response.correct;
    } finally { setPending(false); }
  };
  const restart = async () => { const next = await api<LessonSession>(`/chess/lessons/${lesson.id}/start/`, { method: "POST", body: JSON.stringify({ reset: true }) }); setSession(next); setFen(next.fen); setHints([]); setFeedback(null); };
  const hint = async () => { const response = await api<{ hint: string; has_more: boolean }>(`/chess/lessons/${lesson.id}/hint/`, { method: "POST" }); setHints((items) => items.includes(response.hint) ? items : [...items, response.hint]); };
  const undo = async () => { const next = await api<LessonSession>(`/chess/lessons/${lesson.id}/undo/`, { method: "POST" }); setSession(next); setFen(next.fen); setFeedback(null); };
  return <main className="main"><div className="shell"><div className="breadcrumb">Leçons / Parcours guidé</div><div className="page-heading"><h1>{lesson.title}</h1><p className="subtitle">{lesson.difficulty} · Leçon {lesson.order} sur 5</p></div><div className="lesson-layout"><div className="board-column"><div className="board-wrap"><ChessBoard fen={fen} orientation={lesson.side_to_move} onMove={move} disabled={pending || session?.completed} /></div><div className="player-strip"><strong>{pending ? "Le maître analyse votre coup…" : session?.completed ? "Leçon terminée" : `Les ${lesson.side_to_move === "white" ? "blancs" : "noirs"} jouent`}</strong></div></div><aside className="card lesson-panel"><div className="coach-header"><span className="coach-avatar" aria-hidden>♞</span><div><p className="eyebrow">Votre maître du club</p><strong>Conseil pas à pas</strong></div></div><div className="coach-bubble" aria-live="polite">{session?.coach_message ?? lesson.instruction}</div><h2>{lesson.instruction}</h2><div className="objective">Objectif : {lesson.objective}</div>{feedback && <div className={`feedback ${feedback.correct ? "" : "wrong"}`} role="status"><strong>{feedback.completed ? "Leçon réussie !" : feedback.correct ? "Bon coup." : "Essayons autrement."}</strong></div>}<div className="lesson-actions"><button className="btn primary" onClick={hint}>💡 {hints.length ? "Un autre indice" : "Demander un indice"}</button><button className="btn" disabled={!session?.can_undo} onClick={undo}>↶ Reprendre le coup</button><button className="btn ghost" onClick={restart}>↻ Recommencer la leçon</button></div>{hints.length > 0 && <div className="club-tip"><h3>Indices du maître</h3>{hints.map((text, index) => <p key={text}><strong>{index + 1}.</strong> {text}</p>)}</div>}<div className="progress-dots">{[1,2,3,4,5].map((step) => <span className={step <= lesson.order ? "done" : ""} key={step}>{step}</span>)}</div>{session?.completed && lesson.next_lesson_id ? <Link className="btn primary" href={`/lessons/${lesson.next_lesson_id}`} style={{ marginTop: 20 }}>Leçon suivante →</Link> : <Link href="/lessons" style={{ display: "inline-block", marginTop: 22, color: "var(--green)", textDecoration: "underline" }}>Toutes les leçons</Link>}</aside></div></div></main>;
}
export default function LessonPage() { return <AuthGuard><LessonContent /></AuthGuard>; }
