import { expect, test } from '@playwright/test'

test('deux sessions échangent en direct et gardent leur historique', async ({browser,baseURL},testInfo) => {
  const aliceContext=await browser.newContext({ignoreHTTPSErrors:true});const bobContext=await browser.newContext({ignoreHTTPSErrors:true})
  const alice=await aliceContext.newPage();const bob=await bobContext.newPage();const nonce=`${testInfo.project.name}_${Date.now()}`;
  for(const [page,name] of [[alice,'alice'],[bob,'bob']] as const){await page.goto(`${baseURL}/register`);await page.getByLabel('Adresse email').fill(`${name}${nonce}@example.test`);await page.getByLabel('Identifiant public').fill(`${name}${nonce}`);await page.getByLabel('Nom affiché').fill(name==='alice'?'Alice':'Bob');await page.getByLabel('Mot de passe').fill('Correct horse battery staple 42');await page.getByRole('button',{name:'Créer mon compte'}).click();await expect(page).toHaveURL(/\/chats/)}
  await alice.getByRole('button',{name:'Rechercher un contact'}).click();await alice.getByLabel('Identifiant public exact').fill(`bob${nonce}`);await alice.getByRole('button',{name:/Bob/}).click();
  await alice.getByLabel('Votre message').fill('Bonjour Bob');await alice.getByRole('button',{name:'Envoyer'}).click();
  await bob.reload();await bob.getByText('Alice').click();await expect(bob.getByText('Bonjour Bob').last()).toBeVisible();
  await bob.getByLabel('Votre message').fill('Bonjour Alice');await bob.getByRole('button',{name:'Envoyer'}).click();await expect(alice.getByText('Bonjour Alice').last()).toBeVisible();
  await alice.reload();await expect(alice.getByText('Bonjour Bob').last()).toBeVisible();await expect(alice.getByText('Bonjour Alice').last()).toBeVisible();
  await aliceContext.close();await bobContext.close()
})
