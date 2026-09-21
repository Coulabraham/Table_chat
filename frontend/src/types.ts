export type User = {id:number; email?:string; public_id:string; display_name:string; bio:string; email_verified?:boolean; email_verified_at?:string|null}
export type Message = {id:number; server_sequence:number; conversation_id:string; author_id:number; client_id:string; content:string; created_at:string; status?:'pending'|'saved'|'failed'}
export type Conversation = {id:string; other_user:User; last_message:Message|null; blocked_by_me:boolean; updated_at:string; created_at:string}
export type MessagePage = {results:Message[]; next_before:number|null}
export type AccountSession = {id:string; description:string; ip_address:string|null; created_at:string; last_activity_at:string; current:boolean}
export type UserBlock = {id:number; user:User; created_at:string}
