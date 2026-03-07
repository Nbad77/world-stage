/**
 * API client for The World Stage backend.
 * Base URL comes from env var VITE_API_URL (set on Vercel),
 * or defaults to '' (same-origin in dev via Vite proxy).
 *
 * Auth: call setTokenGetter() once with Clerk's getToken function.
 * All subsequent requests will include Authorization: Bearer <token>.
 */

const BASE = import.meta.env.VITE_API_URL || ''

// Module-level token getter — set by App on mount via setTokenGetter()
let _getToken = null

/**
 * Register Clerk's getToken function so all API requests include the JWT.
 * Call once from the authenticated app shell.
 */
export function setTokenGetter(fn) {
  _getToken = fn
}

async function request(method, path, body) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  }
  if (body !== undefined) opts.body = JSON.stringify(body)

  // Attach Clerk JWT if token getter is registered
  if (_getToken) {
    try {
      const token = await _getToken()
      if (token) {
        opts.headers['Authorization'] = `Bearer ${token}`
        console.log('[AUTH] Clerk token attached to request')
      }
    } catch (e) {
      console.warn('[AUTH] Failed to get Clerk token:', e)
    }
  }

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

  /** POST /game/{id}/negotiate — body: { npc_id, message, history, last_counter_offer?, player_initiated? } */
  negotiate: (id, npc_id, message, history = [], last_counter_offer = null, player_initiated = false) =>
    request('POST', `/game/${id}/negotiate`, { npc_id, message, history, last_counter_offer, player_initiated }),

  /** POST /game/{id}/accept_counter — body: { letter, counter_offer, covert? } */
  acceptCounter: (id, letter, counter_offer, covert = false) =>
    request('POST', `/game/${id}/accept_counter`, { letter, counter_offer, covert }),

  /** POST /game/{id}/purchase_upgrade — body: { upgrade_id } */
  purchaseUpgrade: (id, upgrade_id) =>
    request('POST', `/game/${id}/purchase_upgrade`, { upgrade_id }),

  /** POST /game/{id}/deploy_brigades — body: { deploy, operation, target_npc } */
  deployBrigades: (id, deploy, operation = 0, target_npc = '') =>
    request('POST', `/game/${id}/deploy_brigades`, { deploy, operation, target_npc }),

  /** POST /game/{id}/brigade_aftermath — body: { choice: 1|2|3 } */
  brigadeAftermath: (id, choice) =>
    request('POST', `/game/${id}/brigade_aftermath`, { choice }),

  /** POST /game/{id}/get_intel — body: { npc_id } */
  getIntel: (id, npc_id) =>
    request('POST', `/game/${id}/get_intel`, { npc_id }),

  /** POST /game/{id}/domestic_action — body: { action } */
  domesticAction: (id, action) =>
    request('POST', `/game/${id}/domestic_action`, { action }),

  intelAllocation: (id, allocation) =>
    request('POST', `/game/${id}/intel_allocation`, { allocation }),

  /** POST /game/{id}/budget_allocation — Domestic Affairs persistent allocation */
  budgetAllocation: (id, allocation) =>
    request('POST', `/game/${id}/budget_allocation`, allocation),

  /** POST /game/{id}/debug/set_state — body: { overrides } — fixes_10 Fix 7 */
  debugSetState: (id, overrides) =>
    request('POST', `/game/${id}/debug/set_state`, { overrides }),

  // ── Session 5 endpoints ─────────────────────────────────────────────────

  /** POST /game/{id}/cabinet_invest — body: { axis, direction } */
  cabinetInvest: (id, axis, direction) =>
    request('POST', `/game/${id}/cabinet_invest`, { axis, direction }),

  /** POST /game/{id}/advisor_action — body: { action, advisor_id } (legacy) */
  advisorAction: (id, action, advisor_id) =>
    request('POST', `/game/${id}/advisor_action`, { action, advisor_id }),

  /** GET /game/{id}/advisor_pool (legacy) */
  getAdvisorPool: (id) =>
    request('GET', `/game/${id}/advisor_pool`),

  /** POST /game/{id}/advisor/assign — Session 7C: assign advisor for this turn */
  assignAdvisor: (id, advisorKey) =>
    request('POST', `/game/${id}/advisor/assign`, { advisor_key: advisorKey }),

  /** POST /game/{id}/advisor/unassign — Session 7C: unassign advisor */
  unassignAdvisor: (id, advisorKey) =>
    request('POST', `/game/${id}/advisor/unassign`, { advisor_key: advisorKey }),

  /** POST /game/{id}/backchannel — Session 7D: send covert message */
  backchannel: (id, npcId, message) =>
    request('POST', `/game/${id}/backchannel`, { npc_id: npcId, message }),

  /** GET /game/{id}/backchannel/history — Session 7D: get backchannel logs */
  backchannelHistory: (id) =>
    request('GET', `/game/${id}/backchannel/history`),

  /** POST /game/{id}/summit/declare — Session 7E: submit declaration, get NPC reactions */
  summitDeclare: (id, declaration) =>
    request('POST', `/game/${id}/summit/declare`, { declaration }),

  /** POST /game/{id}/summit/auto_position — Session 7E: generate holding statement */
  summitAutoPosition: (id) =>
    request('POST', `/game/${id}/summit/auto_position`),

  /** POST /game/{id}/summit/close — Session 7E: close summit, unblock End Day */
  summitClose: (id) =>
    request('POST', `/game/${id}/summit/close`),

  /** POST /game/{id}/set_tax_rates — body: { income_tax?, corporate_tax?, resource_tax? } */
  setTaxRates: (id, rates) =>
    request('POST', `/game/${id}/set_tax_rates`, rates),

  /** POST /game/{id}/brigade_operation — body: { deploy, operation, target_npc } */
  brigadeOperation: (id, operation, target_npc = '') =>
    request('POST', `/game/${id}/brigade_operation`, { deploy: true, operation, target_npc }),

  /** fixes_13 Fix 21: POST /game/{id}/issue_bonds — body: { amount: 5|10 } */
  issueBonds: (id, amount) =>
    request('POST', `/game/${id}/issue_bonds`, { amount }),

  /** fixes_13 Fix 26: POST /game/{id}/black_operation — body: { operation, target_npc } */
  blackOperation: (id, operation, target_npc) =>
    request('POST', `/game/${id}/black_operation`, { operation, target_npc }),

  // ── Session 6 endpoints ─────────────────────────────────────────────────

  /** POST /game/{id}/military_action — body: { action, target_npc? } */
  militaryAction: (id, action, target_npc = '') =>
    request('POST', `/game/${id}/military_action`, { action, target_npc }),

  /** POST /game/{id}/intelligence_action — body: { action, target_npc? } */
  intelligenceAction: (id, action, target_npc = '') =>
    request('POST', `/game/${id}/intelligence_action`, { action, target_npc }),

  /** POST /game/{id}/media_action — body: { action, target_npc? } */
  mediaAction: (id, action, target_npc = '') =>
    request('POST', `/game/${id}/media_action`, { action, target_npc }),

  /** POST /game/{id}/judicial_action — body: { action, target_npc? } */
  judicialAction: (id, action, target_npc = '') =>
    request('POST', `/game/${id}/judicial_action`, { action, target_npc }),

  /** POST /game/{id}/political_action — body: { action } */
  politicalAction: (id, action) =>
    request('POST', `/game/${id}/political_action`, { action }),

  /** POST /game/{id}/extraction_action — body: { action, amount?, target_npc? } */
  extractionAction: (id, action, amount = 0, target_npc = '') =>
    request('POST', `/game/${id}/extraction_action`, { action, amount, target_npc }),

  /** POST /game/{id}/resource_dev_action — body: { action, target_npc? } */
  resourceDevAction: (id, action, target_npc = '') =>
    request('POST', `/game/${id}/resource_dev_action`, { action, target_npc }),

  /** POST /game/{id}/leverage_response — body: { leverage_type, accept } */
  leverageResponse: (id, leverage_type, accept) =>
    request('POST', `/game/${id}/leverage_response`, { leverage_type, accept }),

  // ── Session 7A Step 5: Era + Historian endpoints ───────────────────────

  /** POST /game/{id}/close_era — close current era, get historian summary */
  closeEra: (id) => request('POST', `/game/${id}/close_era`),

  /** POST /game/{id}/historian_summary — on-demand historian assessment */
  historianSummary: (id) => request('POST', `/game/${id}/historian_summary`),

  // ── Test Account endpoints ──────────────────────────────────────────────

  /** POST /test/reset — delete all game states for test user */
  testReset: () => {
    console.log('[TEST] calling POST', `${BASE}/test/reset`)
    return request('POST', '/test/reset')
  },

  /** POST /test/set_state — inject a full game state blob */
  testSetState: (state_data) => request('POST', '/test/set_state', { state_data }),

  /** GET /test/snapshots — list available snapshots */
  testListSnapshots: () => request('GET', '/test/snapshots'),

  /** GET /test/snapshot/{name} — get snapshot state_data by name */
  testGetSnapshot: (name) => request('GET', `/test/snapshot/${name}`),
}
