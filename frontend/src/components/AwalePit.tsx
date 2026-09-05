type Props = { index: number; seeds: number; legal: boolean; last: boolean; disabled: boolean; onPlay: (pit: number) => void };

export function AwalePit({ index, seeds, legal, last, disabled, onPlay }: Props) {
  const dots = Array.from({ length: Math.min(seeds, 8) });
  return <button className={`awale-pit ${legal ? "legal" : ""} ${last ? "last" : ""}`} disabled={disabled || !legal} onClick={() => onPlay(index)} aria-label={`Trou ${index + 1}, ${seeds} graine${seeds > 1 ? "s" : ""}`}>
    <span className="seed-dots" aria-hidden>{dots.map((_, dot) => <i key={dot} />)}</span>
    <strong>{seeds}</strong><small>{index + 1}</small>
  </button>;
}
