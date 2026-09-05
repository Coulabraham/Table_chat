import Link from "next/link";
import { AuthGuard } from "@/components/AuthGuard";

export default function GamesPage() {
  return <AuthGuard><main className="main"><div className="shell games-menu-shell">
    <div className="page-heading"><p className="eyebrow">La ludothèque</p><h1>Choisissez votre jeu</h1><p className="subtitle">Retrouvez un classique ou découvrez une nouvelle table.</p></div>
    <div className="games-menu">
      <article className="card game-menu-card chess-card">
        <div className="game-menu-symbol" aria-hidden>♞</div><div><span className="eyebrow">Stratégie</span><h2>Échecs</h2><p>Jouez une partie complète, affrontez l’IA ou progressez avec les cours guidés.</p></div>
        <div className="game-menu-actions"><Link className="btn primary" href="/play/ai">Contre l’IA</Link><Link className="btn" href="/friends?game=chess">Inviter un ami</Link><Link className="btn ghost" href="/lessons">Cours</Link></div>
      </article>
      <article className="card game-menu-card awale-card">
        <div className="game-menu-symbol seeds" aria-hidden><i /><i /><i /><i /></div><div><span className="eyebrow">Semer et capturer</span><h2>Awalé</h2><p>Découvrez l’Awalé Abapa, ses captures en chaîne et l’obligation de nourrir l’adversaire.</p></div>
        <div className="game-menu-actions"><Link className="btn primary" href="/play/awale">Contre l’IA</Link><Link className="btn" href="/friends?game=awale">Inviter un ami</Link><Link className="btn ghost" href="/awale/lessons">Initiation</Link></div>
      </article>
    </div>
  </div></main></AuthGuard>;
}
