import { AwalePit } from "./AwalePit";

type Props = { pits: number[]; legalMoves: number[]; orientation: 0 | 1; lastPit?: number; disabled?: boolean; onMove: (pit: number) => void };

export function AwaleBoard({ pits, legalMoves, orientation, lastPit, disabled = false, onMove }: Props) {
  const rows = orientation === 0
    ? [[11, 10, 9, 8, 7, 6], [0, 1, 2, 3, 4, 5]]
    : [[5, 4, 3, 2, 1, 0], [6, 7, 8, 9, 10, 11]];
  return <div className="awale-board" role="group" aria-label="Plateau d’Awalé">
    {rows.map((row, rowIndex) => <div className="awale-row" key={rowIndex}>{row.map((pit) => <AwalePit key={pit} index={pit} seeds={pits[pit]} legal={legalMoves.includes(pit)} last={lastPit === pit} disabled={disabled} onPlay={onMove} />)}</div>)}
  </div>;
}
