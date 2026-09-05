"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { UserAvatar } from "./UserAvatar";

const links = [["/", "Jouer"], ["/friends", "Amis"], ["/messages", "Messages"], ["/lessons", "Leçons"]] as const;

export function Header() {
  const pathname = usePathname();
  const { user } = useAuth();
  const isGame = pathname.startsWith("/games/");
  return <header className={`header ${isGame ? "game-header" : ""}`}><div className="shell header-inner">
    <Link className="brand" href="/"><span className="brand-mark" aria-hidden>♞</span>TableChat</Link>
    {user && <nav className="nav" aria-label="Navigation principale">{links.map(([href, label]) => <Link key={href} className={(href === "/" ? pathname === "/" || pathname.startsWith("/play") || pathname.startsWith("/games") : pathname.startsWith(href)) ? "active" : ""} href={href}>{label}</Link>)}</nav>}
    {user ? <Link className="profile-link" href="/profile"><UserAvatar name={user.display_name} /><span>{user.display_name}</span></Link> : <Link className="btn ghost" href="/login">Se connecter</Link>}
  </div></header>;
}
