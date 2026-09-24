import type { Conversation } from './types'

export function conversationTitle(conversation:Conversation) {
  return conversation.kind === 'group'
    ? conversation.name
    : conversation.other_user?.display_name ?? 'Discussion'
}

export function conversationSubtitle(conversation:Conversation) {
  if (conversation.last_message) return conversation.last_message.content
  if (conversation.kind === 'group') {
    return `${conversation.member_count} membre${conversation.member_count > 1 ? 's' : ''}`
  }
  return conversation.other_user ? `@${conversation.other_user.public_id}` : 'Discussion privée'
}

export function totalUnread(conversations:Conversation[]|undefined) {
  return conversations?.reduce((sum, conversation) => sum + conversation.unread_count, 0) ?? 0
}
