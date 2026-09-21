let csrfToken = ''

export class ApiError extends Error {
  constructor(public status:number, public details:unknown) { super(typeof details === 'string' ? details : 'Une erreur est survenue.') }
}

async function refreshCsrf() {
  const response = await fetch('/api/auth/csrf/', {credentials:'include'})
  if (!response.ok) throw new ApiError(response.status, 'Impossible d’initialiser la protection de session.')
  csrfToken = (await response.json()).csrfToken
}

export async function api<T>(path:string, options:RequestInit = {}):Promise<T> {
  const method = (options.method ?? 'GET').toUpperCase()
  if (!['GET','HEAD','OPTIONS'].includes(method)) await refreshCsrf()
  const headers = new Headers(options.headers)
  if (options.body) headers.set('Content-Type','application/json')
  if (csrfToken && !['GET','HEAD','OPTIONS'].includes(method)) headers.set('X-CSRFToken',csrfToken)
  const response = await fetch(`/api${path}`, {...options, headers, credentials:'include'})
  if (response.status === 204) return undefined as T
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new ApiError(response.status, data?.error?.details ?? 'La requête a échoué.')
  return data as T
}

export function errorText(error:unknown):string {
  if (error instanceof ApiError) {
    const d = error.details as Record<string, unknown>
    if (typeof error.details === 'string') return error.details
    if (d && typeof d === 'object') return Object.values(d).flat().join(' ')
  }
  return error instanceof Error ? error.message : 'Une erreur est survenue.'
}
