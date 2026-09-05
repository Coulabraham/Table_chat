import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { Header } from "@/components/Header";
import { GameInvitationWatcher } from "@/components/GameInvitationWatcher";

export const metadata: Metadata = { title: "TableChat", description: "Les jeux de société, entre amis." };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="fr"><body><AuthProvider><GameInvitationWatcher /><Header />{children}</AuthProvider></body></html>;
}
