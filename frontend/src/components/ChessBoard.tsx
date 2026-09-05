"use client";

import { useMemo, useState } from "react";
import { Chess, Square } from "chess.js";
import { Chessboard } from "react-chessboard";

export function ChessBoard({ fen, orientation = "white", onMove, disabled = false, lastMove }: { fen: string; orientation?: "white" | "black"; onMove: (uci: string) => Promise<boolean> | boolean; disabled?: boolean; lastMove?: string }) {
  const [selected, setSelected] = useState<Square | null>(null);
  const [promotion, setPromotion] = useState<{ from: Square; to: Square } | null>(null);
  const game = useMemo(() => new Chess(fen), [fen]);
  const styles = useMemo(() => {
    const result: Record<string, React.CSSProperties> = {};
    if (lastMove) {
      result[lastMove.slice(0, 2)] = { backgroundColor: "rgba(214, 169, 63, .48)" };
      result[lastMove.slice(2, 4)] = { backgroundColor: "rgba(214, 169, 63, .62)" };
    }
    if (game.inCheck()) {
      const king = game.board().flat().find((piece) => piece?.type === "k" && piece.color === game.turn());
      if (king) result[king.square] = { boxShadow: "inset 0 0 0 5px rgba(159,61,53,.8)" };
    }
    if (!selected) return result;
    result[selected] = { boxShadow: "inset 0 0 0 4px rgba(49,92,73,.65)" };
    for (const move of game.moves({ square: selected, verbose: true })) result[move.to] = { background: "radial-gradient(circle, rgba(49,92,73,.55) 18%, transparent 20%)" };
    return result;
  }, [game, selected, lastMove]);

  const tryMove = (from: Square, to: Square, promotionPiece?: string) => {
    if (disabled) return false;
    const candidates = game.moves({ square: from, verbose: true }).filter((move) => move.to === to);
    if (!candidates.length) return false;
    if (candidates.some((move) => move.promotion) && !promotionPiece) { setPromotion({ from, to }); return false; }
    const suffix = promotionPiece ?? candidates[0].promotion ?? "";
    setSelected(null);
    void onMove(`${from}${to}${suffix}`);
    return true;
  };
  const click = (square: Square) => {
    if (selected) { const moved = tryMove(selected, square); if (!moved && game.get(square)?.color === game.turn()) setSelected(square); }
    else if (game.get(square)) setSelected(square);
  };
  return <div style={{ position: "relative" }}>
    <Chessboard id="tablechat-board" position={fen} boardOrientation={orientation} onPieceDrop={(from, to) => tryMove(from as Square, to as Square)} onSquareClick={(square) => click(square as Square)} customSquareStyles={styles} customLightSquareStyle={{ backgroundColor: "var(--light-square)" }} customDarkSquareStyle={{ backgroundColor: "var(--dark-square)" }} customBoardStyle={{ borderRadius: "7px", boxShadow: "0 12px 28px rgba(53,34,20,.18)" }} arePiecesDraggable={!disabled} />
    {promotion && <div className="card" role="dialog" aria-label="Choisir la promotion" style={{ position: "absolute", inset: "35% 15% auto", zIndex: 4, padding: 18, textAlign: "center" }}><strong>Promouvoir en</strong><div style={{ display: "flex", justifyContent: "center", gap: 8, marginTop: 12 }}>{["q", "r", "b", "n"].map((piece) => <button className="btn" key={piece} onClick={() => { void tryMove(promotion.from, promotion.to, piece); setPromotion(null); }}>{({ q: "Dame", r: "Tour", b: "Fou", n: "Cavalier" } as Record<string, string>)[piece]}</button>)}</div></div>}
  </div>;
}
