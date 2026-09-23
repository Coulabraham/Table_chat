import { describe, expect, it } from 'vitest'

import { reconnectDelayMs, socketCloseAction } from './socketPolicy'

describe('socket close policy',()=>{
  it.each([
    [4401,'login'],
    [4403,'forbidden'],
    [4404,'verify-email'],
  ] as const)('does not retry authorization close %i',(code,action)=>{
    expect(socketCloseAction(code)).toBe(action)
  })

  it('retries transient closures with bounded exponential backoff',()=>{
    expect(socketCloseAction(1006)).toBe('retry')
    expect(reconnectDelayMs(0,0)).toBe(1000)
    expect(reconnectDelayMs(4,0)).toBe(16000)
    expect(reconnectDelayMs(20,0)).toBe(30000)
    expect(reconnectDelayMs(20,1)).toBe(30500)
  })
})
