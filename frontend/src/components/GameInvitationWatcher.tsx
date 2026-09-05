"use client";

import { useEffect, useRef } from "react";
import { usePathname, useRouter } from "next/navigation";

import { useAuth } from "@/context/AuthContext";
import { api, wsUrl } from "@/lib/api";

type Invitation = {
  id: string;
  sender: { id: number };
  status: string;
  game_id: string | null;
};

export function GameInvitationWatcher() {
  const { user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const pendingSent = useRef(new Set<string>());
  const initialized = useRef(false);

  useEffect(() => {
    if (!user) {
      initialized.current = false;
      pendingSent.current.clear();
      return;
    }
    let active = true;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | undefined;

    const openGame = (gameId: string) => {
      if (!window.location.pathname.startsWith(`/games/${gameId}`)) router.push(`/games/${gameId}`);
    };

    const poll = async () => {
      try {
        const response = await api<{ results: Invitation[] }>("/games/invitations/");
        if (!active) return;
        const sent = response.results.filter((item) => item.sender.id === user.id);
        if (initialized.current) {
          const accepted = sent.find((item) => item.status === "accepted" && item.game_id && pendingSent.current.has(item.id));
          if (accepted?.game_id) openGame(accepted.game_id);
        }
        pendingSent.current = new Set(sent.filter((item) => item.status === "pending").map((item) => item.id));
        initialized.current = true;
      } catch {
        // Le prochain passage ou le WebSocket réessaiera sans gêner la navigation.
      }
    };

    const connect = () => {
      if (!active) return;
      socket = new WebSocket(wsUrl("/notifications/"));
      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "game.ready" && data.game_id) openGame(data.game_id);
      };
      socket.onclose = () => {
        if (active) reconnectTimer = window.setTimeout(connect, 1500);
      };
    };

    void poll();
    const pollTimer = window.setInterval(poll, 3000);
    connect();
    return () => {
      active = false;
      window.clearInterval(pollTimer);
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      socket?.close();
    };
  }, [user, router, pathname]);

  return null;
}
