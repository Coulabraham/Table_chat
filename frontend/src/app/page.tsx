"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { FriendsList } from "@/components/FriendsList";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import type { Lesson, User } from "@/lib/types";

type Friendship = { id: number; requester: User; addressee: User; status: string };
type Page<T> = { results: T[] };

function Dashboard() {
  const { user } = useAuth();
  const [relations, setRelations] = useState<Friendship[]>([]);
  const [lessons, setLessons] = useState<Lesson[]>([]);
  useEffect(() => { Promise.all([api<Page<Friendship>>("/friends/"), api<Page<Lesson>>("/chess/lessons/")]).then(([friends, availableLessons]) => { setRelations(friends.results); setLessons(availableLessons.results); }).catch(() => undefined); }, []);
  const friends = useMemo(() => relations.filter((item) => item.status === "accepted").map((item) => item.requester.id === user?.id ? item.addressee : item.requester), [relations, user]);
  return <main className="main"><div className="shell"><div className="page-heading"><h1>Une partie, entre amis.</h1><p className="subtitle">Échecs ou Awalé : choisissez votre table.</p></div><div className="dashboard-grid"><div><section className="card hero"><p className="eyebrow">À vous de jouer</p><h2>À quel jeu jouons-nous ?</h2><div className="hero-actions"><Link className="btn primary" href="/games">Choisir un jeu</Link><Link className="btn" href="/friends">Inviter un ami</Link></div><span className="hero-piece" aria-hidden>♞</span></section><h2 className="section-title">Continuer à apprendre</h2><div className="lesson-cards">{lessons.slice(0, 2).map((lesson) => <article className="card lesson-card" key={lesson.id}><span className="eyebrow">{lesson.difficulty}</span><h3>{lesson.title}</h3><p>{lesson.objective}</p><Link className="btn" href={`/lessons/${lesson.id}`}>{lesson.progress?.completed ? "Revoir" : "Commencer"}</Link></article>)}</div></div><aside className="card friends-panel"><h2>Vos amis</h2><FriendsList friends={friends} /><div className="message-preview"><span className="eyebrow">Messages</span><p>{friends.length ? `Écrivez à ${friends[0].display_name}` : "Ajoutez un ami pour discuter."}</p><Link href="/messages" style={{ color: "var(--green)", fontWeight: 600 }}>Voir les messages →</Link></div></aside></div></div></main>;
}

export default function Home() { return <AuthGuard><Dashboard /></AuthGuard>; }
