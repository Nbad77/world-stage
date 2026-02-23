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

  /** POST /game/{id}/negotiate — body: { npc_id, message, history, last_counter_offer? } */
  negotiate: (id, npc_id, message, history = [], last_counter_offer = null) =>
    request('POST', `/game/${id}/negotiate`, { npc_id, message, history, last_counter_offer }),

  /** POST /game/{id}/accept_counter — body: { letter, counter_offer } */
  acceptCounter: (id, letter, counter_offer) =>
    request('POST', `/game/${id}/accept_counter`, { letter, counter_offer }),

  /** POST /game/{id}/purchase_upgrade — body: { upgrade_id } */
  purchaseUpgrade: (id, upgrade_id) =>
    request('POST', `/game/${id}/purchase_upgrade`, { upgrade_id }),

  /** POST /game/{id}/deploy_brigades — body: { deploy: bool } */
  deployBrigades: (id, deploy) =>
    request('POST', `/game/${id}/deploy_brigades`, { deploy }),

  /** POST /game/{id}/brigade_aftermath — body: { choice: 1|2|3 } */
  brigadeAftermath: (id, choice) =>
    request('POST', `/game/${id}/brigade_aftermath`, { choice }),

  /** POST /game/{id}/get_intel — body: { npc_id } */
  getIntel: (id, npc_id) =>
    request('POST', `/game/${id}/get_intel`, { npc_id }),
}
