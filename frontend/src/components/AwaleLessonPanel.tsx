"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { AwaleBoard } from "./AwaleBoard";

type AwaleLesson = { id?: number; title: string; instruction: string; objective: string; content: { pits: number[]; legal: number[]; answer: number }; success?: string };

const defaultLessons: AwaleLesson[] = [
  { title: "Semer les graines", instruction: "Jouez le premier trou pour distribuer ses quatre graines.", objective: "Comprendre le sens du semis", content: { pits: [4,4,4,4,4,4,4,4,4,4,4,4], legal: [0], answer: 0 }, success: "Très bien. Les graines avancent une à une dans le sens du jeu." },
  { title: "Capturer", instruction: "Terminez votre semis dans le trou adverse qui contiendra deux graines.", objective: "Créer une capture simple", content: { pits: [0,0,0,0,0,1,1,4,4,4,4,4], legal: [5], answer: 5 }, success: "Exact : le trou 7 contient maintenant deux graines et peut être capturé." },
  { title: "Nourrir l’adversaire", instruction: "Le camp du haut est vide. Choisissez le seul trou qui peut le nourrir.", objective: "Respecter l’obligation de nourrir", content: { pits: [0,0,0,0,1,11,0,0,0,0,0,0], legal: [5], answer: 5 }, success: "Bien joué. Votre semis dépose une graine dans le camp adverse." },
  { title: "Éviter la famine", instruction: "Observez cette capture : elle serait annulée car elle viderait entièrement le camp adverse.", objective: "Anticiper une capture annulée", content: { pits: [9,9,9,9,9,1,1,0,0,0,0,0], legal: [5], answer: 5 }, success: "Exact. Le semis reste joué, mais les deux graines demeurent chez l’adversaire." },
];

export function AwaleLessonPanel() {
  const [index, setIndex] = useState(0);
  const [complete, setComplete] = useState(false);
  const [lessons, setLessons] = useState(defaultLessons);
  useEffect(() => {
    api<{ results: AwaleLesson[] }>("/awale/lessons/").then((response) => {
      if (response.results.length) setLessons(response.results);
    }).catch(() => undefined);
  }, []);
  const lesson = lessons[index];
  const play = (pit: number) => { if (pit === lesson.content.answer) setComplete(true); };
  const next = () => { setIndex((value) => (value + 1) % lessons.length); setComplete(false); };
  return <div className="awale-lesson-layout">
    <div className="card awale-lesson-board"><AwaleBoard pits={lesson.content.pits} legalMoves={complete ? [] : lesson.content.legal} orientation={0} onMove={play} disabled={complete} /></div>
    <aside className="card lesson-panel"><p className="eyebrow">Initiation · {index + 1}/{lessons.length}</p><h2>{lesson.title}</h2><div className="coach-bubble">{complete ? lesson.success ?? "Très bien. Vous avez trouvé le bon semis." : lesson.instruction}</div><div className="objective">Objectif : {lesson.objective}</div>{complete && <button className="btn primary" onClick={next}>{index === lessons.length - 1 ? "Recommencer" : "Leçon suivante"}</button>}<div className="club-tip"><strong>Règle TableChat</strong><p>La troisième occurrence d’une même position termine la partie et déclenche le décompte des graines restantes.</p></div></aside>
  </div>;
}
