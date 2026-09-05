export function ConnectionStatus({ connected }: { connected: boolean }) {
  return <span className={`status ${connected ? "" : "offline"}`}>{connected ? "En direct" : "Reconnexion…"}</span>;
}

