import { AuthGuard } from "@/components/AuthGuard";
import { GameLobby } from "@/components/GameLobby";

export default function AiLobbyPage() {
  return <AuthGuard><main className="main"><div className="shell" style={{ maxWidth: 720 }}><div className="breadcrumb">Jouer / Contre l’IA</div><div className="page-heading"><h1>Jouer contre l’IA</h1><p className="subtitle">Une partie d’entraînement, à votre rythme.</p></div><GameLobby /></div></main></AuthGuard>;
}
