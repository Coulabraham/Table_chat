import type { Message } from './types'

export function mergeMessages(current:Message[],incoming:Message):Message[] {
  const filtered=current.filter(message=>
    message.id!==incoming.id&&message.client_id!==incoming.client_id
  )
  return [...filtered,{...incoming,status:'saved' as const}]
    .sort((left,right)=>(left.server_sequence||Number.MAX_SAFE_INTEGER)-(right.server_sequence||Number.MAX_SAFE_INTEGER))
}

export function mergeBatch(current:Message[],incoming:Message[]):Message[] {
  return incoming.reduce(mergeMessages,current)
}
