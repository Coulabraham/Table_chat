"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function LoginPage() {
  const [email, setEmail] = useState("alice@tablechat.local");
  const [password, setPassword] = useState("TableChat123!");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const { refresh } = useAuth();
  const router = useRouter();
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setPending(true); setError("");
    try { await api("/auth/login/", { method: "POST", body: JSON.stringify({ email, password }) }); await refresh(); router.push("/"); }
    catch (err) { setError(err instanceof Error ? err.message : "Connexion impossible."); setPending(false); }
  };
  return <main className="auth-wrap"><section className="card auth-card"><p className="eyebrow">Bienvenue au club</p><h1>Retrouvez votre table</h1><p className="subtitle">Connectez-vous pour jouer avec vos amis.</p><form onSubmit={submit}><label className="label">Adresse email<input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label><label className="label">Mot de passe<input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required /></label>{error && <div className="form-error">{error}</div>}<button className="btn primary" disabled={pending}>{pending ? "Connexion…" : "Se connecter"}</button></form><p>Pas encore de compte ? <Link href="/register" style={{ color: "var(--green)", textDecoration: "underline" }}>S’inscrire</Link></p></section></main>;
}

