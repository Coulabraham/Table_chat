import { expect, test } from '@playwright/test'

const mailpit = process.env.TABLECHAT_MAILPIT_URL || 'http://127.0.0.1:8025'

async function verificationTokenFor(email:string) {
  for (let attempt=0; attempt<40; attempt++) {
    const response=await fetch(`${mailpit}/api/v1/search?query=${encodeURIComponent(`to:${email}`)}`)
    if(response.ok) {
      const data=await response.json() as {messages?:Array<{ID:string}>}
      const id=data.messages?.[0]?.ID
      if(id) {
        const body=await (await fetch(`${mailpit}/view/${id}.txt`)).text()
        const token=body.match(/#token=([A-Za-z0-9._-]+)/)?.[1]
        if(token)return token
      }
    }
    await new Promise(resolve=>setTimeout(resolve,250))
  }
  throw new Error(`Email de vérification introuvable pour ${email}`)
}

test('deux sessions vérifiées échangent en direct et gardent leur historique', async ({browser,baseURL},testInfo) => {
  const aliceContext=await browser.newContext({ignoreHTTPSErrors:true});const bobContext=await browser.newContext({ignoreHTTPSErrors:true})
  const alice=await aliceContext.newPage();const bob=await bobContext.newPage();const nonce=`${testInfo.project.name}_${Date.now()}`
  for(const [page,name] of [[alice,'alice'],[bob,'bob']] as const){const email=`${name}${nonce}@example.test`;await page.goto(`${baseURL}/register`);await page.getByLabel('Adresse email').fill(email);await page.getByLabel('Identifiant public').fill(`${name}${nonce}`);await page.getByLabel('Nom affiché').fill(name==='alice'?'Alice':'Bob');await page.getByLabel('Mot de passe').fill('Correct horse battery staple 42');await page.getByRole('button',{name:'Créer mon compte'}).click();await expect(page).toHaveURL(/\/verify-email/);const token=await verificationTokenFor(email);await page.goto(`${baseURL}/verify-email#token=${token}`);await page.getByRole('button',{name:'Continuer vers les discussions'}).click();await expect(page).toHaveURL(/\/chats/)}
  await alice.getByRole('button',{name:'Rechercher un contact'}).click();await alice.getByLabel('Identifiant public exact').fill(`bob${nonce}`);await alice.getByRole('button',{name:/Bob/}).click();await expect(alice.getByText('Connecté')).toBeVisible()
  await alice.getByLabel('Votre message').fill('Bonjour Bob');await alice.getByRole('button',{name:'Envoyer'}).click()
  await bob.reload();await bob.getByText('Alice').click();await expect(bob.getByText('Bonjour Bob').last()).toBeVisible();await expect(bob.getByText('Connecté')).toBeVisible()
  await bob.getByLabel('Votre message').fill('Bonjour Alice');await bob.getByRole('button',{name:'Envoyer'}).click();await expect(alice.getByText('Bonjour Alice').last()).toBeVisible()
  await alice.reload();await expect(alice.getByText('Bonjour Bob').last()).toBeVisible();await expect(alice.getByText('Bonjour Alice').last()).toBeVisible()
  await aliceContext.close();await bobContext.close()
})
