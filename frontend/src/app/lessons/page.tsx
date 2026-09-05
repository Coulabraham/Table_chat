"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { api } from "@/lib/api";
import type { Lesson } from "@/lib/types";

function LessonsContent() {
  const [lessons, setLessons] = useState<Lesson[]>([]);
  useEffect(() => { api<{ results: Lesson[] }>("/chess/lessons/").then((data) => setLessons(data.results)); }, []);
  const recommended = lessons.findIndex((lesson, index) => !lesson.progress?.completed && (index === 0 || lessons[index - 1].progress?.completed));
  return <main className="main"><div className="shell" style={{ maxWidth: 950 }}><div className="page-heading"><p className="eyebrow">Parcours du club</p><h1>Progressez, un coup à la fois.</h1><p className="subtitle">Votre maître du club vous guide après chaque coup et reprend là où vous vous êtes arrêté.</p></div><div className="game-choice-inline card" style={{ marginBottom: 20 }}><span className="active" style={{ display: "grid", placeItems: "center", borderRadius: 9 }}>♞ Échecs</span><Link className="btn ghost" href="/awale/lessons">● Initiation Awalé</Link></div><section className="card list-card">{lessons.map((lesson, index) => {
    const unlocked = index === 0 || Boolean(lessons[index - 1].progress?.completed) || Boolean(lesson.progress?.completed);
    const content = <><span className="avatar">{lesson.progress?.completed ? "✓" : unlocked ? lesson.order : "🔒"}</span><div className="grow"><strong>{lesson.title}</strong><br /><small>{lesson.difficulty} · {lesson.objective}</small></div><span style={{ color: unlocked ? "var(--green)" : "var(--muted)" }}>{lesson.progress?.completed ? "Terminée" : index === recommended ? "Recommandée →" : unlocked ? lesson.progress ? "Continuer →" : "Commencer →" : "À débloquer"}</span></>;
    return unlocked ? <Link className="list-row" href={`/lessons/${lesson.id}`} key={lesson.id}>{content}</Link> : <div className="list-row" aria-disabled="true" key={lesson.id} style={{ opacity: .6 }}>{content}</div>;
  })}</section></div></main>;
}
export default function LessonsPage() { return <AuthGuard><LessonsContent /></AuthGuard>; }
