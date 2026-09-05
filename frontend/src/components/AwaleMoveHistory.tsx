import type { AwaleMove } from "@/lib/types";

export function AwaleMoveHistory({ moves, selectedMove, onSelect }: { moves: AwaleMove[]; selectedMove?: number | null; onSelect?: (move: AwaleMove) => void }) {
  if (!moves.length) return <div className="empty">Aucun semis pour le moment.</div>;
  return <ol className="awale-history">{moves.map((move) => <li key={move.move_number}><button className={selectedMove === move.move_number ? "active" : ""} onClick={() => onSelect?.(move)}><span>{move.move_number}. {move.author}</span><strong>Trou {move.pit + 1}</strong><small>{move.capture_cancelled ? "Capture annulée" : move.captures.length ? `${move.captures.length} trou(s) capturé(s)` : "Semis"}</small></button></li>)}</ol>;
}
