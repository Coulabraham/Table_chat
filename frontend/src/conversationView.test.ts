import { describe, expect, it } from 'vitest'
import { conversationSubtitle, conversationTitle, totalUnread } from './conversationView'
import type { Conversation } from './types'

const base:Conversation = {id:'1',kind:'group',name:'Équipe',description:'',owner:null,other_user:null,last_message:null,blocked_by_me:false,my_role:'member',muted:false,member_count:3,unread_count:2,updated_at:'',created_at:''}

describe('présentation des conversations du lot 3', () => {
  it('présente un groupe sans dépendre d’un contact privé', () => {
    expect(conversationTitle(base)).toBe('Équipe')
    expect(conversationSubtitle(base)).toBe('3 membres')
  })

  it('conserve la présentation d’une conversation privée', () => {
    const privateConversation:Conversation={...base,kind:'private',name:'',member_count:2,unread_count:4,other_user:{id:2,public_id:'bob',display_name:'Bob',bio:''}}
    expect(conversationTitle(privateConversation)).toBe('Bob')
    expect(conversationSubtitle(privateConversation)).toBe('@bob')
    expect(totalUnread([base,privateConversation])).toBe(6)
  })
})
