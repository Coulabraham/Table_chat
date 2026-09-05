"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useAuth } from "@/context/AuthContext";

export default function RegisterPage() {
  const [form, setForm] = useState({ email: "", display_name: "", password: "", chess_level: "beginner" });
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const { refresh } = useAuth();
  const router = useRouter();
  const submit = async (event: FormEvent) => { event.preventDefault(); setPending(true); setError(""); try { await api("/auth/register/", { method: "POST", body: JSON.stringify(form) }); await refresh(); router.push("/"); } catch (err) { setError(err instanceof Error ? err.message : "Inscription impossible."); setPending(false); } };
  const field = (name: keyof typeof form) => ({ value: form[name], onChange: (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => setForm({ ...form, [name]: e.target.value }) });
  return <main className="auth-wrap"><section className="card auth-card"><p className="eyebrow">Une place vous attend</p><h1>Rejoindre TableChat</h1><form onSubmit={submit}><label className="label">Pseudo public<input className="input" {...field("display_name")} maxLength={40} required /></label><label className="label">Adresse email<input className="input" type="email" {...field("email")} required /></label><label className="label">Mot de passe<input className="input" type="password" {...field("password")} minLength={8} required /></label><label className="label">Votre niveau déclaré<select className="input" {...field("chess_level")}><option value="beginner">Débutant</option><option value="casual">Loisir</option><option value="intermediate">Intermédiaire</option><option value="advanced">Avancé</option></select></label>{error && <div className="form-error">{error}</div>}<button className="btn primary" disabled={pending}>{pending ? "Création…" : "Créer mon compte"}</button></form><p>Déjà membre ? <Link href="/login" style={{ color: "var(--green)", textDecoration: "underline" }}>Se connecter</Link></p></section></main>;
}

