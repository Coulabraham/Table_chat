import { chromium } from '@playwright/test'

const baseURL=(process.env.TABLECHAT_URL||'https://table-chat-blush.vercel.app').replace(/\/$/,'')
const password=process.env.TABLECHAT_TEST_PASSWORD
if(!password)throw new Error('TABLECHAT_TEST_PASSWORD est requis.')

const assert=(condition,message)=>{if(!condition)throw new Error(message)}
const marker=`prod-${Date.now()}`

async function login(context,email){
  const page=await context.newPage()
  await page.goto(`${baseURL}/login`)
  await page.getByLabel('Adresse email').fill(email)
  await page.getByLabel('Mot de passe').fill(password)
  await page.getByRole('button',{name:'Se connecter'}).click()
  await page.waitForURL(/\/chats(?:\/|$)/)
  return page
}

async function api(page,path,{method='GET',body}={}){
  return page.evaluate(async ({path,method,body})=>{
    let csrf=''
    if(!['GET','HEAD','OPTIONS'].includes(method)){
      const csrfResponse=await fetch('/api/auth/csrf/',{credentials:'include'})
      csrf=(await csrfResponse.json()).csrfToken
    }
    const response=await fetch(`/api${path}`,{
      method,
      credentials:'include',
      headers:{...(body?{'Content-Type':'application/json'}:{}),...(csrf?{'X-CSRFToken':csrf}:{})},
      body:body?JSON.stringify(body):undefined,
    })
    return {status:response.status,data:response.status===204?null:await response.json().catch(()=>null)}
  },{path,method,body})
}

function recordWebSockets(page){
  const frames=[]
  let opened=0
  let closed=0
  page.on('websocket',socket=>{
    opened++
    socket.on('framereceived',event=>{
      try{
        const raw=Buffer.isBuffer(event.payload)?event.payload.toString('utf8'):event.payload
        frames.push(JSON.parse(raw))
      }catch{/* Les pongs ou trames non JSON ne font pas échouer la recette. */}
    })
    socket.on('close',()=>{closed++})
  })
  return {frames,get opened(){return opened},get closed(){return closed}}
}

async function expectMessage(page,content){
  await page.locator('div.chat-pattern').getByText(content,{exact:true}).last().waitFor({state:'visible',timeout:20000})
}

async function waitFor(check,message,timeout=20000){
  const deadline=Date.now()+timeout
  while(Date.now()<deadline){
    if(check())return
    await new Promise(resolve=>setTimeout(resolve,100))
  }
  throw new Error(message)
}

const browser=await chromium.launch({headless:true})
const aliceContext=await browser.newContext()
const bobContext=await browser.newContext()
const results={baseURL,marker,checks:[]}
let alice

try{
  alice=await login(aliceContext,'test1@example.test')
  const bob=await login(bobContext,'test2@example.test')
  await api(alice,'/blocks/test_user_2/',{method:'DELETE'})
  const conversationResponse=await api(alice,'/conversations/',{
    method:'POST',body:{contact_public_id:'test_user_2'},
  })
  assert(conversationResponse.status===200,'Création/récupération de conversation refusée.')
  const conversationId=conversationResponse.data.id

  const aliceSockets=recordWebSockets(alice)
  const bobSockets=recordWebSockets(bob)
  await Promise.all([
    alice.goto(`${baseURL}/chats/${conversationId}`),
    bob.goto(`${baseURL}/chats/${conversationId}`),
  ])
  await Promise.all([
    alice.getByText('Connecté',{exact:true}).waitFor({timeout:20000}),
    bob.getByText('Connecté',{exact:true}).waitFor({timeout:20000}),
  ])
  assert(aliceSockets.opened>0&&bobSockets.opened>0,'Les deux WebSockets ne se sont pas ouverts.')
  await Promise.all([
    waitFor(()=>aliceSockets.frames.some(event=>event.type==='ready'),'Alice n’a pas reçu la trame WebSocket ready.'),
    waitFor(()=>bobSockets.frames.some(event=>event.type==='ready'),'Bob n’a pas reçu la trame WebSocket ready.'),
  ])
  await alice.waitForTimeout(1000)
  results.checks.push('deux WebSockets authentifiés ouverts')

  const aliceMessage=`Alice ${marker}`
  await alice.getByLabel('Votre message').fill(aliceMessage)
  await alice.getByRole('button',{name:'Envoyer'}).click()
  await expectMessage(bob,aliceMessage)
  await waitFor(
    ()=>bobSockets.frames.some(event=>event.type==='message.created'&&event.message?.content===aliceMessage),
    'Bob n’a pas reçu la vraie trame WebSocket Alice.',
  )

  const bobMessage=`Bob ${marker}`
  await bob.getByLabel('Votre message').fill(bobMessage)
  await bob.getByRole('button',{name:'Envoyer'}).click()
  await expectMessage(alice,bobMessage)
  await waitFor(
    ()=>aliceSockets.frames.some(event=>event.type==='message.created'&&event.message?.content===bobMessage),
    `Alice n’a pas reçu la vraie trame WebSocket Bob. Diagnostic: ${JSON.stringify({aliceOpened:aliceSockets.opened,aliceClosed:aliceSockets.closed,aliceFrames:aliceSockets.frames.map(event=>({type:event.type,content:event.message?.content}))})}`,
  )
  results.checks.push('échange bidirectionnel par trames message.created')

  const clientId=crypto.randomUUID()
  const dedupeMessage=`Dédoublonnage ${marker}`
  const first=await api(alice,`/conversations/${conversationId}/messages/`,{method:'POST',body:{client_id:clientId,content:dedupeMessage}})
  const second=await api(alice,`/conversations/${conversationId}/messages/`,{method:'POST',body:{client_id:clientId,content:dedupeMessage}})
  assert(first.status===201&&second.status===200&&first.data.id===second.data.id,'La clé client_id n’est pas idempotente.')
  const history=await api(bob,`/conversations/${conversationId}/messages/`)
  assert(history.data.results.filter(message=>message.client_id===clientId).length===1,'Le message idempotent est dupliqué en base.')
  results.checks.push('persistance et idempotence client_id')

  const closedBeforeInterruption=bobSockets.closed
  await bob.goto(`${baseURL}/settings`)
  await waitFor(
    ()=>bobSockets.closed>closedBeforeInterruption,
    'La fermeture contrôlée du WebSocket Bob n’a pas été observée.',
  )
  const catchupMessage=`Rattrapage ${marker}`
  await alice.getByLabel('Votre message').fill(catchupMessage)
  await alice.getByRole('button',{name:'Envoyer'}).click()
  await bob.goto(`${baseURL}/chats/${conversationId}`)
  await expectMessage(bob,catchupMessage)
  await bob.getByText('Connecté',{exact:true}).waitFor({timeout:20000})
  assert(bobSockets.opened>=2,'Le WebSocket Bob ne s’est pas rouvert après la coupure simulée.')
  results.checks.push('fermeture contrôlée, reconnexion authentifiée et rattrapage')

  await Promise.all([alice.reload(),bob.reload()])
  await Promise.all([expectMessage(alice,bobMessage),expectMessage(bob,aliceMessage),expectMessage(bob,catchupMessage)])
  results.checks.push('historique persistant après rechargement')

  const blockResponse=await api(alice,'/blocks/',{method:'POST',body:{public_id:'test_user_2'}})
  assert(blockResponse.status===201,'Le blocage de contrôle a échoué.')
  await Promise.all([
    alice.getByText('Messagerie indisponible',{exact:true}).waitFor({timeout:10000}),
    bob.getByText('Messagerie indisponible',{exact:true}).waitFor({timeout:10000}),
  ])
  assert((await api(alice,'/blocks/test_user_2/',{method:'DELETE'})).status===204,'Le déblocage de nettoyage a échoué.')
  results.checks.push('blocage ferme les connexions ouvertes dans les deux sens')

  const socketContext=await browser.newContext()
  const controllerContext=await browser.newContext()
  try{
    const socketPage=await login(socketContext,'test5@example.test')
    const sessionConversation=await api(socketPage,'/conversations/',{method:'POST',body:{contact_public_id:'test_user_4'}})
    await socketPage.goto(`${baseURL}/chats/${sessionConversation.data.id}`)
    await socketPage.getByText('Connecté',{exact:true}).waitFor({timeout:20000})
    const controllerPage=await login(controllerContext,'test5@example.test')
    const revoked=await api(controllerPage,'/sessions/others/',{method:'DELETE'})
    assert(revoked.status===200&&revoked.data.revoked>=1,'Aucune autre session n’a été révoquée.')
    await socketPage.waitForURL(/\/login$/, {timeout:10000})
    results.checks.push('révocation ferme une connexion ouverte et renvoie vers la connexion')
  }finally{
    await socketContext.close()
    await controllerContext.close()
  }

  process.stdout.write(`${JSON.stringify(results,null,2)}\n`)
}finally{
  if(alice)await api(alice,'/blocks/test_user_2/',{method:'DELETE'}).catch(()=>{})
  await aliceContext.close()
  await bobContext.close()
  await browser.close()
}
