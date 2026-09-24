import { chromium } from '@playwright/test'
import { mkdir } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const output = resolve(frontend, '..', 'docs', 'screenshots')
await mkdir(output, {recursive:true})

const groupId = '11111111-1111-4111-8111-111111111111'
const now = new Date().toISOString()
const alice = {id:1,public_id:'alice',display_name:'Alice Martin',bio:'Disponible le soir'}
const bob = {id:2,public_id:'bob',display_name:'Bob Durand',bio:''}
const charlie = {id:3,public_id:'charlie',display_name:'Charlie Test',bio:''}
const message = (id, author, content, minutes=0) => ({id,server_sequence:id,conversation_id:groupId,author_id:author.id,author,client_id:`00000000-0000-4000-8000-${String(id).padStart(12,'0')}`,content,created_at:new Date(Date.now()-minutes*60000).toISOString()})
const messages = [message(8,bob,'Bienvenue dans le groupe !',12),message(9,charlie,'Je prépare le compte rendu.',5),message(10,bob,'Parfait, rendez-vous à 18 h.',0)]
const group = {id:groupId,kind:'group',name:'Équipe TableChat',description:'Organisation du lancement et suivi des essais.',owner:alice,other_user:null,last_message:messages[2],blocked_by_me:false,my_role:'owner',muted:false,member_count:3,unread_count:2,updated_at:now,created_at:now}
const privateConversation = {id:'22222222-2222-4222-8222-222222222222',kind:'private',name:'',description:'',owner:null,other_user:bob,last_message:message(7,bob,'À tout à l’heure',30),blocked_by_me:false,my_role:'member',muted:false,member_count:2,unread_count:0,updated_at:now,created_at:now}

const browser = await chromium.launch({headless:true})
for (const viewport of [{name:'desktop',width:1440,height:900},{name:'mobile-320',width:320,height:700}]) {
  const page = await browser.newPage({viewport:{width:viewport.width,height:viewport.height}})
  await page.addInitScript(() => {
    class DemoSocket {
      static OPEN=1; readyState=1; onopen=null; onmessage=null; onclose=null
      constructor(){setTimeout(()=>this.onopen?.({}),20)} send(){} close(){}
    }
    window.WebSocket=DemoSocket
  })
  await page.route('**/api/**', async route => {
    const request=route.request();const url=new URL(request.url());const path=url.pathname;const method=request.method()
    if(path==='/api/me/')return route.fulfill({json:{...alice,email:'alice@example.test',email_verified:true,email_verified_at:now}})
    if(path==='/api/conversations/'&&method==='GET')return route.fulfill({json:[group,privateConversation]})
    if(path===`/api/conversations/${groupId}/`)return route.fulfill({json:group})
    if(path===`/api/conversations/${groupId}/messages/`&&method==='GET')return route.fulfill({json:{results:messages,next_before:null}})
    if(path===`/api/conversations/${groupId}/members/`)return route.fulfill({json:[{id:1,user:alice,role:'owner',joined_at:now},{id:2,user:bob,role:'admin',joined_at:now},{id:3,user:charlie,role:'member',joined_at:now}]})
    if(path===`/api/conversations/${groupId}/invitations/`)return route.fulfill({json:[]})
    if(path==='/api/group-invitations/')return route.fulfill({json:[{id:'33333333-3333-4333-8333-333333333333',conversation:{id:groupId,name:'Club produit'},inviter:bob,invitee:alice,status:'pending',created_at:now,expires_at:now,responded_at:null}]})
    if(path==='/api/auth/csrf/')return route.fulfill({json:{csrfToken:'demo'}})
    if(method!=='GET')return route.fulfill({json:{}})
    return route.fulfill({status:404,json:{error:{details:'Introuvable'}}})
  })
  await page.goto('http://127.0.0.1:5173/chats')
  await page.getByText('Équipe TableChat').waitFor()
  await page.screenshot({path:resolve(output,`lot3-${viewport.name}-liste.png`),fullPage:true})
  await page.getByText('Équipe TableChat').click()
  await page.getByText('Parfait, rendez-vous à 18 h.').last().waitFor()
  await page.screenshot({path:resolve(output,`lot3-${viewport.name}-groupe.png`),fullPage:true})
  if(viewport.name==='desktop') {
    await page.getByRole('button',{name:'Infos'}).click()
    await page.getByText('Organisation du lancement').waitFor()
    await page.screenshot({path:resolve(output,'lot3-desktop-administration.png'),fullPage:true})
  }
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)
  if(overflow)throw new Error(`Débordement horizontal détecté pour ${viewport.name}`)
  await page.close()
}
await browser.close()
