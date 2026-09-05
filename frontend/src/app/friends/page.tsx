"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { FriendsList } from "@/components/FriendsList";
import { UserAvatar } from "@/components/UserAvatar";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";
import type { User } from "@/lib/types";

type Friendship = { id: number; requester: User; addressee: User; status: string };
type Page<T> = { results: T[] };
type Invitation = { id: string; sender: User; recipient: User; status: string; game_id: string | null };

function FriendsPageContent() {
  const { user } = useAuth();
  const [relations, setRelations] = useState<Friendship[]>([]);
  const [results, setResults] = useState<User[]>([]);
  const [query, setQuery] = useState("");
  const [notice, setNotice] = useState("");
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const load = () => Promise.all([api<Page<Friendship>>("/friends/"), api<Page<Invitation>>("/games/invitations/")]).then(([friendsData, invitationsData]) => { setRelations(friendsData.results); setInvitations(invitationsData.results); });
  useEffect(() => { void load(); }, []);
  const friends = useMemo(() => relations.filter((item) => item.status === "accepted").map((item) => item.requester.id === user?.id ? item.addressee : item.requester), [relations, user]);
  const incoming = relations.filter((item) => item.status === "pending" && item.addressee.id === user?.id);
  const search = async (event: FormEvent) => { event.preventDefault(); const data = await api<Page<User>>(`/auth/users/?q=${encodeURIComponent(query)}`); setResults(data.results); };
  const send = async (target: User) => { await api("/friends/", { method: "POST", body: JSON.stringify({ addressee_id: target.id }) }); setNotice(`Demande envoyée à ${target.display_name}.`); setResults([]); await load(); };
  const action = async (id: number, name: string) => { await api(`/friends/${id}/${name}/`, { method: "POST" }); await load(); };
  const invite = async (target: User) => { await api("/games/invitations/", { method: "POST", body: JSON.stringify({ recipient_id: target.id, configuration: { sender_color: "white" } }) }); setNotice(`Invitation envoyée à ${target.display_name}.`); };
  const message = async (target: User) => { const conversation = await api<{ id: string }>("/chat/conversations/", { method: "POST", body: JSON.stringify({ user_id: target.id }) }); window.location.href = `/messages/${conversation.id}`; };
  const gameAction = async (id: string, name: string) => { const result = await api<Invitation>(`/games/invitations/${id}/${name}/`, { method: "POST" }); await load(); if (result.game_id) window.location.href = `/games/${result.game_id}`; };
  const pendingGames = invitations.filter((item) => item.status === "pending" && item.recipient.id === user?.id);
  return <main className="main"><div className="shell" style={{ maxWidth: 900 }}><div className="page-heading"><h1>Vos amis</h1><p className="subtitle">Retrouvez une personne par son pseudo, sans exposer son email.</p></div>{notice && <div className="feedback">{notice}</div>}<section className="card list-card" style={{ marginTop: 20 }}><h2>Rechercher un joueur</h2><form className="search-form" onSubmit={search} style={{ marginTop: 18 }}><input className="input" minLength={2} value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Pseudo, au moins 2 caractères" /><button className="btn primary">Rechercher</button></form>{results.map((person) => <div className="list-row" key={person.id}><UserAvatar name={person.display_name} /><div className="grow"><strong>{person.display_name}</strong></div><button className="btn" onClick={() => send(person)}>Ajouter</button></div>)}</section>{pendingGames.length > 0 && <section className="card list-card" style={{ marginTop: 22 }}><h2>Invitations à jouer</h2>{pendingGames.map((item) => <div className="list-row" key={item.id}><UserAvatar name={item.sender.display_name} /><div className="grow"><strong>{item.sender.display_name}</strong><br /><small>Vous propose une partie d’échecs</small></div><button className="btn primary" onClick={() => gameAction(item.id, "accept")}>Jouer</button><button className="btn" onClick={() => gameAction(item.id, "decline")}>Refuser</button></div>)}</section>}{incoming.length > 0 && <section className="card list-card" style={{ marginTop: 22 }}><h2>Demandes reçues</h2>{incoming.map((item) => <div className="list-row" key={item.id}><UserAvatar name={item.requester.display_name} /><div className="grow"><strong>{item.requester.display_name}</strong></div><button className="btn primary" onClick={() => action(item.id, "accept")}>Accepter</button><button className="btn" onClick={() => action(item.id, "decline")}>Refuser</button></div>)}</section>}<section className="card list-card" style={{ marginTop: 22 }}><h2>Amis</h2><FriendsList friends={friends} onInvite={invite} onMessage={message} /></section></div></main>;
}

export default function FriendsPage() { return <AuthGuard><FriendsPageContent /></AuthGuard>; }
