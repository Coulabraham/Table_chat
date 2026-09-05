"use client";

import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { ConversationList, type Conversation } from "@/components/ConversationList";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

function MessagesContent() {
  const { user } = useAuth();
  const [items, setItems] = useState<Conversation[]>([]);
  useEffect(() => { api<{ results: Conversation[] }>("/chat/conversations/").then((data) => setItems(data.results)); }, []);
  if (!user) return null;
  return <main className="main"><div className="shell" style={{ maxWidth: 850 }}><div className="page-heading"><h1>Messages</h1><p className="subtitle">Vos conversations restent disponibles après les parties.</p></div><section className="card list-card"><ConversationList conversations={items} currentUserId={user.id} /></section></div></main>;
}
export default function MessagesPage() { return <AuthGuard><MessagesContent /></AuthGuard>; }

