export type User = {id:number; email?:string; public_id:string; display_name:string; bio:string; email_verified?:boolean; email_verified_at?:string|null}
export type Message = {id:number; server_sequence:number; conversation_id:string; author_id:number; author?:User; client_id:string; content:string; created_at:string; status?:'pending'|'saved'|'failed'}
export type Conversation = {
  id:string
  kind:'private'|'group'
  name:string
  description:string
  owner:User|null
  other_user:User|null
  last_message:Message|null
  blocked_by_me:boolean
  my_role:'owner'|'admin'|'member'
  muted:boolean
  member_count:number
  unread_count:number
  updated_at:string
  created_at:string
}
export type Membership = {id:number; user:User; role:'owner'|'admin'|'member'; joined_at:string}
export type GroupInvitation = {id:string; conversation:{id:string;name:string}; inviter:User; invitee:User; status:'pending'|'accepted'|'declined'|'cancelled'|'expired'; created_at:string; expires_at:string; responded_at:string|null}
export type MessagePage = {results:Message[]; next_before:number|null}
export type AccountSession = {id:string; description:string; ip_address:string|null; created_at:string; last_activity_at:string; current:boolean}
export type UserBlock = {id:number; user:User; created_at:string}
