export function UserAvatar({ name, small = false }: { name: string; small?: boolean }) {
  const initials = name.split(/\s+/).map((part) => part[0]).slice(0, 2).join("").toUpperCase();
  return <span className={`avatar ${small ? "sm" : ""}`} aria-label={`Avatar de ${name}`}>{initials}</span>;
}

