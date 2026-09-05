export function AwaleScore({ names, scores, currentPlayer }: { names: [string, string]; scores: [number, number]; currentPlayer: 0 | 1 }) {
  return <div className="awale-scores">{scores.map((score, player) => <div className={currentPlayer === player ? "active" : ""} key={player}><span>{names[player]}</span><strong>{score}</strong><small>graines capturées</small></div>)}</div>;
}
