export type SocketCloseAction = 'login' | 'forbidden' | 'verify-email' | 'retry'

export function socketCloseAction(code:number):SocketCloseAction {
  if(code===4401)return 'login'
  if(code===4403)return 'forbidden'
  if(code===4404)return 'verify-email'
  return 'retry'
}

export function reconnectDelayMs(attempt:number,random=Math.random()):number {
  return Math.min(30000,1000*2**attempt)+random*500
}
