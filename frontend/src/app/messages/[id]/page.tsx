"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { AuthGuard } from "@/components/AuthGuard";
import { ChatPanel } from "@/components/ChatPanel";
import { useAuth } from "@/context/AuthContext";
import { api } from "@/lib/api";

type Message = { id: string; author: { id: number; display_name: string; chess_level: string; created_at: string }; content: string; client_id: string; created_at: string };
function ConversationContent() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [messages, setMessages] = useState<Message[] | null>(null);
  useEffect(() => { api<{ results: Message[] }>(`/chat/conversations/${id}/messages/`).then((data) => setMessages(data.results.reverse())); void api(`/chat/conversations/${id}/read/`, { method: "POST" }); }, [id]);
  if (!user || !messages) return <main className="auth-wrap"><div className="spinner" /></main>;
  return <main className="main"><div className="shell" style={{ maxWidth: 800 }}><div className="breadcrumb">Messages / Conversation</div><div className="page-heading"><h1>Discussion</h1></div><ChatPanel conversationId={id} currentUserId={user.id} initialMessages={messages} /></div></main>;
}
export default function ConversationPage() { return <AuthGuard><ConversationContent /></AuthGuard>; }

