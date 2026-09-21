import { chromium } from '@playwright/test'

const browser = await chromium.launch({headless:true})
const results = []
const conversationId = '11111111-1111-4111-8111-111111111111'

for (const viewport of [{name:'desktop',width:1440,height:900},{name:'mobile-320',width:320,height:700}]) {
  const page = await browser.newPage({viewport:{width:viewport.width,height:viewport.height}})
  await page.goto('http://127.0.0.1:5173/login')
  await page.screenshot({path:`visual-${viewport.name}-login.png`,fullPage:true})
  const loginOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)

  await page.route('**/api/me/', route => route.fulfill({json:{id:1,email:'alice@example.test',public_id:'alice',display_name:'Alice Martin',bio:''}}))
  await page.route('**/api/conversations/', route => route.fulfill({json:[{id:conversationId,other_user:{id:2,public_id:'bob',display_name:'Bob Durand',bio:''},last_message:{id:2,server_sequence:2,conversation_id:conversationId,author_id:2,client_id:'22222222-2222-4222-8222-222222222222',content:'On se retrouve à 18 h ?',created_at:new Date().toISOString()},updated_at:new Date().toISOString(),created_at:new Date().toISOString()}]}))
  await page.route(`**/api/conversations/${conversationId}/`, route => route.fulfill({json:{id:conversationId,other_user:{id:2,public_id:'bob',display_name:'Bob Durand',bio:''},last_message:null,updated_at:new Date().toISOString(),created_at:new Date().toISOString()}}))
  await page.route(`**/api/conversations/${conversationId}/messages/**`, route => route.fulfill({json:{results:[{id:1,server_sequence:1,conversation_id:conversationId,author_id:1,client_id:'11111111-1111-4111-8111-111111111112',content:'Bonjour Bob !',created_at:new Date(Date.now()-60000).toISOString()},{id:2,server_sequence:2,conversation_id:conversationId,author_id:2,client_id:'22222222-2222-4222-8222-222222222222',content:'On se retrouve à 18 h ?',created_at:new Date().toISOString()}],next_before:null}}))
  await page.goto(`http://127.0.0.1:5173/chats/${conversationId}`)
  await page.getByText('On se retrouve à 18 h ?').last().waitFor()
  await page.screenshot({path:`visual-${viewport.name}-chat.png`,fullPage:true})
  const chatOverflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)
  const composerVisible = await page.getByLabel('Votre message').isVisible()
  results.push({viewport:viewport.name,loginOverflow,chatOverflow,composerVisible})
  await page.close()
}

await browser.close()
console.log(JSON.stringify(results,null,2))
