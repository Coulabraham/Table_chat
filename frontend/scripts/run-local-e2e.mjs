import { spawn } from 'node:child_process'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const frontend = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const root = resolve(frontend, '..')
const backend = resolve(root, 'backend')
const python = resolve(root, '.venv', 'Scripts', 'python.exe')
const node = process.execPath
const vite = resolve(frontend, 'node_modules', 'vite', 'bin', 'vite.js')
const playwright = resolve(frontend, 'node_modules', '@playwright', 'test', 'cli.js')
const children = []

function start(command, args, options) {
  const child = spawn(command, args, {...options, stdio:'inherit'})
  children.push(child)
  return child
}

async function waitFor(url) {
  for (let attempt=0; attempt<60; attempt++) {
    try { if ((await fetch(url)).ok) return } catch { /* Le processus ASGI démarre encore. */ }
    await new Promise(resolve => setTimeout(resolve, 500))
  }
  throw new Error(`Le serveur local n’a pas répondu : ${url}`)
}

let exitCode = 1
try {
  start(python, ['-m','daphne','-b','127.0.0.1','-p','8001','tablechat.asgi:application'], {cwd:backend, env:{...process.env,DJANGO_SETTINGS_MODULE:'tablechat.settings.test'}})
  start(node, [vite,'--host','127.0.0.1','--port','5174'], {cwd:frontend, env:{...process.env,VITE_BACKEND_TARGET:'http://127.0.0.1:8001'}})
  await waitFor('http://127.0.0.1:5174/api/health/')
  const tests = spawn(node, [playwright,'test',...process.argv.slice(2)], {cwd:frontend, env:{...process.env,TABLECHAT_URL:'http://127.0.0.1:5174'}, stdio:'inherit'})
  exitCode = await new Promise(resolve => tests.on('exit', code => resolve(code ?? 1)))
} finally {
  for (const child of children.reverse()) if (!child.killed) child.kill()
}
process.exit(exitCode)
