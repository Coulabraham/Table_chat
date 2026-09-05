import { AuthGuard } from "@/components/AuthGuard";
import { AwaleLessonPanel } from "@/components/AwaleLessonPanel";

export default function AwaleLessonsPage() {
  return <AuthGuard><main className="main"><div className="shell"><div className="breadcrumb">Jeux / Awalé / Initiation</div><div className="page-heading"><h1>Apprendre l’Awalé</h1><p className="subtitle">Quatre exercices courts pour semer, capturer et nourrir correctement.</p></div><AwaleLessonPanel /></div></main></AuthGuard>;
}
