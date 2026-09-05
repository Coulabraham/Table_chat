"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { api, wsUrl } from "@/lib/api";
import { createClientId } from "@/lib/clientId";
import type { User } from "@/lib/types";
import { ConnectionStatus } from "./ConnectionStatus";

type Message = { id: string; author: User; content: string; client_id: string; created_at: string };

export function ChatPanel({ conversationId, currentUserId, initialMessages = [], embedded = false }: { conversationId: string; currentUserId: number; initialMessages?: Message[]; embedded?: boolean }) {
  const [messages, setMessages] = useState(initialMessages);
  const [content, setContent] = useState("");
  const [connected, setConnected] = useState(false);
  const [sound, setSound] = useState(false);
  const socket = useRef<WebSocket | null>(null);
  const reconnect = useRef<number | null>(null);

  useEffect(() => {
    if (!initialMessages.length) api<{ results: Message[] }>(`/chat/conversations/${conversationId}/messages/`).then((data) => setMessages(data.results.reverse())).catch(() => undefined);
    void api(`/chat/conversations/${conversationId}/read/`, { method: "POST" });
  }, [conversationId, initialMessages.length]);

  useEffect(() => {
    let active = true;
    const connect = () => {
      if (!active) return;
      const ws = new WebSocket(wsUrl(`/conversations/${conversationId}/`));
      socket.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onclose = () => { setConnected(false); if (active) reconnect.current = window.setTimeout(connect, 1500); };
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type !== "chat.message") return;
        setMessages((items) => items.some((item) => item.id === data.message.id) ? items : [...items, data.message]);
        if (sound && data.message.author.id !== currentUserId) new Audio("data:audio/wav;base64,UklGRjIAAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQ4AAACAgICAgICAgICAgIA=").play().catch(() => undefined);
      };
    };
    connect();
    return () => { active = false; if (reconnect.current) clearTimeout(reconnect.current); socket.current?.close(); };
  }, [conversationId, currentUserId, sound]);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const text = content.trim();
    if (!text || socket.current?.readyState !== WebSocket.OPEN) return;
    socket.current.send(JSON.stringify({ type: "chat.message", content: text, client_id: createClientId() }));
    setContent("");
  };
  return <section className={`side-panel ${embedded ? "embedded-panel" : "card"}`} aria-label="Discussion">
    <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 18 }}><ConnectionStatus connected={connected} /><button className="btn ghost" onClick={() => setSound((value) => !value)} aria-pressed={sound}>{sound ? "🔊 Son actif" : "🔇 Son coupé"}</button></div>
    <div className="messages" aria-live="polite">{messages.map((message) => <div className={`bubble ${message.author.id === currentUserId ? "mine" : ""}`} key={message.id}><small>{message.author.display_name}</small>{message.content}</div>)}</div>
    <form className="message-form" onSubmit={submit}><input className="input" maxLength={1000} value={content} onChange={(e) => setContent(e.target.value)} placeholder="Écrire un message…" aria-label="Message" /><button className="btn primary" disabled={!connected || !content.trim()}>Envoyer</button></form>
  </section>;
}
