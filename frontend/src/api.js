/**
 * API client for The World Stage backend.
 * Base URL comes from env var VITE_API_URL (set on Vercel),
 * or defaults to '' (same-origin in dev via Vite proxy).
 */

const BASE = import.meta.env.VITE_API_URL || ''

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body !== undefined) opts.body = JSON.stringify(body)

  const res = await fetch(`${BASE}${path}`, opts)

  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const j = await res.json()
      detail = j.detail || detail
    } catch (_) {}
    throw new Error(detail)
  }

  return res.json()
}

export const api = {
  /** POST /game/new */
  newGame: () => request('POST', '/game/new'),

  /** GET /game/{id} */
  getGame: (id) => request('GET', `/game/${id}`),

  /** POST /game/{id}/action — body: { choice: "A"-"G" } */
  postAction: (id, choice) => request('POST', `/game/${id}/action`, { choice }),

  /** POST /game/{id}/skim — body: { choice: 1-4 } */
  postSkim: (id, choice) => request('POST', `/game/${id}/skim`, { choice }),

  /** POST /game/{id}/inject — body: { choice: 0-3 } */
  postInject: (id, choice) => request('POST', `/game/${id}/inject`, { choice }),
}
