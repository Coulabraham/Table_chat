import { describe, expect, it } from 'vitest'

import { mergeMessages } from './messageMerge'
import type { Message } from './types'

const saved:Message={
  id:42,
  server_sequence:42,
  conversation_id:'conversation',
  author_id:1,
  client_id:'client-message-id',
  content:'Bonjour',
  created_at:'2026-09-23T12:00:00Z',
  status:'saved',
}

describe('message merge',()=>{
  it('replaces an optimistic row and ignores a repeated WebSocket event',()=>{
    const pending={...saved,id:-1,server_sequence:0,status:'pending' as const}
    const once=mergeMessages([pending],saved)
    const twice=mergeMessages(once,saved)

    expect(once).toEqual([saved])
    expect(twice).toEqual([saved])
  })
})
