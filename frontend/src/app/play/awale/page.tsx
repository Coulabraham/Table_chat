import { AuthGuard } from "@/components/AuthGuard";
import { AwaleGameLobby } from "@/components/AwaleGameLobby";

export default function AwaleLobbyPage() {
  return <AuthGuard><main className="main"><div className="shell" style={{ maxWidth: 720 }}><div className="breadcrumb">Jeux / Awalé / Contre l’IA</div><div className="page-heading"><h1>Jouer à l’Awalé</h1><p className="subtitle">Semez, nourrissez et capturez les graines de votre adversaire.</p></div><AwaleGameLobby /></div></main></AuthGuard>;
}
