export type User = {id:number; email?:string; public_id:string; display_name:string; bio:string}
export type Message = {id:number; server_sequence:number; conversation_id:string; author_id:number; client_id:string; content:string; created_at:string; status?:'pending'|'saved'|'failed'}
export type Conversation = {id:string; other_user:User; last_message:Message|null; updated_at:string; created_at:string}
export type MessagePage = {results:Message[]; next_before:number|null}

