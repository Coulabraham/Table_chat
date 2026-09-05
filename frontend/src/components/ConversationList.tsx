"use client";

import Link from "next/link";
import { UserAvatar } from "./UserAvatar";
import type { User } from "@/lib/types";

export type Conversation = { id: string; kind: string; game_id: string | null; participants: User[]; unread_count: number; created_at: string };

export function ConversationList({ conversations, currentUserId }: { conversations: Conversation[]; currentUserId: number }) {
  if (!conversations.length) return <div className="empty">Vos conversations apparaîtront ici.</div>;
  return <div>{conversations.map((conversation) => {
    const other = conversation.participants.find((person) => person.id !== currentUserId);
    return <Link className="list-row" href={`/messages/${conversation.id}`} key={conversation.id}>
      <UserAvatar name={other?.display_name ?? "Partie"} />
      <div className="grow"><strong>{other?.display_name ?? "Discussion de partie"}</strong><br /><small>{conversation.kind === "game" ? "Conversation de partie" : "Conversation privée"}</small></div>
      {conversation.unread_count > 0 && <span className="avatar sm" aria-label={`${conversation.unread_count} messages non lus`}>{conversation.unread_count}</span>}
    </Link>;
  })}</div>;
}

