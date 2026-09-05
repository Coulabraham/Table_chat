"use client";

import { UserAvatar } from "./UserAvatar";
import type { User } from "@/lib/types";

export function FriendsList({ friends, onInvite, onMessage }: { friends: User[]; onInvite?: (user: User) => void; onMessage?: (user: User) => void }) {
  if (!friends.length) return <div className="empty">Aucun ami pour le moment.</div>;
  return <div>{friends.map((friend) => <div className="friend-row" key={friend.id}>
    <UserAvatar name={friend.display_name} />
    <div className="meta"><strong>{friend.display_name}</strong><br /><small>Disponible</small></div>
    {onMessage && <button className="btn ghost" onClick={() => onMessage(friend)}>Écrire</button>}
    {onInvite && <button className="btn" onClick={() => onInvite(friend)}>Inviter</button>}
  </div>)}</div>;
}
