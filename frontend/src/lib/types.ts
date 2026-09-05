export type User = { id: number; display_name: string; chess_level: string; created_at: string };
export type Move = { ply: number; uci: string; san: string };
export type ChessState = { game_id: string; fen: string; initial_fen: string; moves: Move[]; pgn: string; revision: number; status: string; result: string; end_reason: string };
export type LessonSession = { fen: string; current_ply: number; completed: boolean; attempts: number; hint_stage: number; coach_message: string; can_undo: boolean };
export type Lesson = { id: number; title: string; instruction: string; initial_fen: string; side_to_move: "white" | "black"; objective: string; difficulty: string; hints: string[]; explanation: string; coach_messages: Record<string, string>; order: number; progress: LessonSession | null; next_lesson_id: number | null };
