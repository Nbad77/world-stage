import { useState, useRef, useEffect } from 'react'
import { api } from '../api'
import StatusBar from './StatusBar'
import RelationBadges from './RelationBadges'
import DialoguePanel from './DialoguePanel'
import OffersPanel from './OffersPanel'
import ConsequencesPanel from './ConsequencesPanel'
import SkimPanel from './SkimPanel'
import InjectPanel from './InjectPanel'
import InterceptPanel from './InterceptPanel'
import EotPanel from './EotPanel'
import EndingScreen from './EndingScreen'
import EventBanner from './EventBanner'
import NegotiationPanel from './NegotiationPanel'
import ShadowCabinet from './ShadowCabinet'

/**
 * GameScreen manages the full turn lifecycle:
 *
 * PHASE 0 — dialogue      : show NPC messages + offers panel
 * PHASE 1 — consequences  : show choice result + skim panel
 *                           (or inject panel if Option G)
 *                         : FEATURE 2 — brigade secondary prompt (if available)
 * PHASE 2 — eot           : show skim/inject result + EOT effects + intercepts
 *                           → then auto-advance to next turn (PHASE 0)
 *                         : FEATURE 3 — brigade aftermath banner (if flag set)
 */

const PHASE = {
  DIALOGUE: 'dialogue',
  CONSEQUENCES: 'consequences',
  BRIGADE_PROMPT: 'brigade_prompt',   // FEATURE 2: secondary brigade prompt
  INJECT_PROMPT: 'inject_prompt',
  EOT: 'eot',
  ENDED: 'ended',
}

const NPC_INFO = {
  usa:    { label: 'Bill Washington', flag: '🇺🇸', letter: 'A' },
  arabia: { label: 'Sadam',          flag: '🛢️',  letter: 'B' },
  eu:     { label: 'Marsha',         flag: '🇪🇺', letter: 'C' },
  dprg:   { label: 'Ji-won Ryang',   flag: '⚡',  letter: 'D' },
}

export default function GameScreen({ sessionId, initialData, onGameEnd, onRestart }) {
  const [gs, setGs] = useState(initialData.game_state)
  const [dialogue, setDialogue] = useState(initialData.dialogue)
  const [offers, setOffers] = useState(initialData.offers)
  const [skimOptions, setSkimOptions] = useState(initialData.skim_options || [])
  const [blackmailActive, setBlackmailActive] = useState(initialData.blackmail_active || false)
  const [phase, setPhase] = useState(PHASE.DIALOGUE)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // FEATURE 1: Shadow Cabinet state
  const [shadowCabinetOpen, setShadowCabinetOpen] = useState(false)

  // FEATURE 2: Brigade secondary prompt
  const [brigadeAvailable, setBrigadeAvailable] = useState(false)
  const [brigadeLoading, setBrigadeLoading] = useState(false)
  const [brigadeResult, setBrigadeResult] = useState(null)

  // Addition 2: Pre-skim EOT drain projection
  const [drainProjection, setDrainProjection] = useState(null)

  // FEATURE 3: Brigade aftermath
  const [aftermathLoading, setAftermathLoading] = useState(false)
  const [aftermathResult, setAftermathResult] = useState(null)

  // Phase 1 data
  const [consequences, setConsequences] = useState([])
  const [blackmailResult, setBlackmailResult] = useState(null)

  // Phase 2 data
  const [skimMessages, setSkimMessages] = useState([])
  const [corruptionAlert, setCorruptionAlert] = useState(null)
  const [patriotMessage, setPatriotMessage] = useState(null)
  const [intercepts, setIntercepts] = useState([])
  const [eotMessages, setEotMessages] = useState([])

  // Inject sub-choice
  const [injectOptions, setInjectOptions] = useState([])

  // Ending
  const [ending, setEnding] = useState(null)

  // Session 2 Item 6: Diplomatic crisis modal — broken deal messages
  const [dipCrisisMessages, setDipCrisisMessages] = useState([])

  // FEATURE 1: Confirmation dialog — intercepts choice + skim before committing
  // { type: 'choice'|'skim', value: letter|choiceNum, text: string } | null
  const [pendingConfirm, setPendingConfirm] = useState(null)

  // Stage 4: World events
  const [currentEvent, setCurrentEvent] = useState(initialData.current_event || null)

  // Stage 4: Negotiation
  const [negotiatingNpc, setNegotiatingNpc] = useState(null)   // 'usa'|'arabia'|'eu'|'dprg'|null
  // counterOffers: { [letter]: counterOffer } — displayed in OffersPanel
  const [counterOffers, setCounterOffers] = useState({})
  // per-NPC chat history, keyed by npcKey — survives panel close/reopen within same turn
  // shape: { [npcKey]: { messages: [], pendingOffers: [] } }
  const [chatHistories, setChatHistories] = useState({})

  const scrollRef = useRef(null)

  // Scroll to top of game area whenever phase changes
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0
  }, [phase])

  const clearError = () => setError(null)

  // ── FEATURE 1: Confirmation dialog helpers ────────────────────────────────
  function requestConfirmChoice(letter) {
    const allOffers = offers || []
    const counter = counterOffers[letter]
    const base = allOffers.find(o => o.letter === letter)
    const text = counter
      ? `[NEGOTIATED] ${counter.text}`
      : base?.text || `Option ${letter}`
    setPendingConfirm({ type: 'choice', value: letter, text })
  }

  function requestConfirmSkim(choice) {
    const opt = (skimOptions || []).find(o => o.choice === choice)
    const text = opt?.label || `Option ${choice}`
    setPendingConfirm({ type: 'skim', value: choice, text })
  }

  function handleConfirmExecute() {
    if (!pendingConfirm) return
    const { type, value } = pendingConfirm
    setPendingConfirm(null)
    if (type === 'choice') _executeChoice(value)
    else if (type === 'skim') _executeSkim(value)
  }

  function handleConfirmCancel() {
    setPendingConfirm(null)
  }

  // ── PHASE 0 → 1: player picks A-G ───────────────────────────────────────
  async function handleChoice(letter) {
    requestConfirmChoice(letter)
  }

  async function _executeChoice(letter) {
    clearError()
    setLoading(true)
    try {
      const res = await api.postAction(sessionId, letter)

      // Option F — escape
      if (res.action === 'escape') {
        setGs(res.game_state)
        setEnding(res.ending)
        setPhase(PHASE.ENDED)
        onGameEnd && onGameEnd(res.ending)
        return
      }

      // Option G — inject sub-prompt
      if (res.action === 'inject_prompt') {
        setGs(res.game_state)
        setInjectOptions(res.inject_options || [])
        setPhase(PHASE.INJECT_PROMPT)
        return
      }

      // Normal A-E choice
      setGs(res.game_state)
      setConsequences(res.consequences || [])
      setBlackmailResult(res.blackmail_result)
      setSkimOptions(res.skim_options || [])
      setBlackmailActive(false)
      setBrigadeAvailable(res.brigade_available || false)
      setBrigadeResult(null)
      setDrainProjection(res.drain_projection || null)
      setPhase(PHASE.CONSEQUENCES)

    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── FEATURE 2: Brigade secondary prompt ───────────────────────────────────
  const [brigadeTargetNpc, setBrigadeTargetNpc] = useState('usa')   // for op 3

  async function handleBrigadeDeploy(operation, targetNpc = '') {
    clearError()
    setBrigadeLoading(true)
    try {
      const res = await api.deployBrigades(sessionId, operation > 0, operation, targetNpc)
      setGs(res.game_state)
      setBrigadeResult(res.messages?.join(' · ') || (operation > 0 ? 'Brigades deployed.' : 'Brigades stood down.'))
    } catch (e) {
      setError(e.message)
    } finally {
      setBrigadeLoading(false)
      // After brigade decision (either way), hide the prompt
      setBrigadeAvailable(false)
    }
  }

  // ── PHASE 1 → 2: player picks skim option ────────────────────────────────
  async function handleSkim(choice) {
    requestConfirmSkim(choice)
  }

  async function _executeSkim(choice) {
    clearError()
    setLoading(true)
    try {
      const res = await api.postSkim(sessionId, choice)

      setGs(res.game_state)
      setSkimMessages(res.skim_messages || [])
      setCorruptionAlert(res.corruption_alert || null)
      setIntercepts(res.intercepts || [])
      const eotMsgs = res.eot_effects || []
      setEotMessages(eotMsgs)
      // Session 2 Item 6: surface broken deal messages as diplomatic crisis modal
      const brokenDeals = eotMsgs.filter(m => m.startsWith('💔'))
      if (brokenDeals.length > 0) setDipCrisisMessages(brokenDeals)
      setPatriotMessage(null)
      setAftermathResult(null)

      if (res.status !== 'active') {
        setEnding(res.ending)
        setPhase(PHASE.EOT)
        return
      }

      setPhase(PHASE.EOT)

      _nextTurnRef.current = {
        dialogue: res.next_dialogue,
        offers: res.next_offers,
        skimOptions: res.next_skim_options,
        blackmailActive: res.next_blackmail,
        status: res.status,
        ending: res.ending,
        event: res.next_event || null,
      }

    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── PHASE inject → 2: player picks inject option ──────────────────────────
  async function handleInject(choice) {
    clearError()
    setLoading(true)
    try {
      const res = await api.postInject(sessionId, choice)

      setGs(res.game_state)
      setSkimMessages(res.inject_messages || [])
      setCorruptionAlert(null)
      setIntercepts([])
      const eotMsgsInject = res.eot_effects || []
      setEotMessages(eotMsgsInject)
      const brokenDealsInject = eotMsgsInject.filter(m => m.startsWith('💔'))
      if (brokenDealsInject.length > 0) setDipCrisisMessages(brokenDealsInject)
      setPatriotMessage(res.patriot_message || null)
      setAftermathResult(null)

      if (res.status !== 'active') {
        setEnding(res.ending)
        setPhase(PHASE.EOT)
        return
      }

      setPhase(PHASE.EOT)

      _nextTurnRef.current = {
        dialogue: res.next_dialogue,
        offers: res.next_offers,
        skimOptions: res.next_skim_options,
        blackmailActive: res.next_blackmail,
        status: res.status,
        ending: res.ending,
        event: res.next_event || null,
      }

    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── FEATURE 3: Brigade aftermath handler ──────────────────────────────────
  async function handleAftermath(choice) {
    clearError()
    setAftermathLoading(true)
    try {
      const res = await api.brigadeAftermath(sessionId, choice)
      setGs(res.game_state)
      setAftermathResult(res.messages?.[0] || 'Crisis managed.')
    } catch (e) {
      setError(e.message)
    } finally {
      setAftermathLoading(false)
    }
  }

  // Stash next-turn data between phases
  const _nextTurnRef = useRef(null)

  // ── PHASE 2 → 0 (or ENDED): player hits "Next Turn" ─────────────────────
  function handleContinue() {
    const next = _nextTurnRef.current

    if (ending) {
      setPhase(PHASE.ENDED)
      onGameEnd && onGameEnd(ending)
      return
    }

    if (!next || next.status !== 'active') {
      if (next?.ending) {
        setEnding(next.ending)
        setPhase(PHASE.ENDED)
        onGameEnd && onGameEnd(next.ending)
      }
      return
    }

    // Advance to next turn
    setDialogue(next.dialogue)
    setOffers(next.offers)
    setSkimOptions(next.skimOptions || [])
    setBlackmailActive(next.blackmailActive || false)
    setConsequences([])
    setBlackmailResult(null)
    setSkimMessages([])
    setCorruptionAlert(null)
    setPatriotMessage(null)
    setIntercepts([])
    setEotMessages([])
    setBrigadeAvailable(false)
    setBrigadeResult(null)
    setAftermathResult(null)
    setDrainProjection(null)
    // Stage 4
    setCurrentEvent(next.event || null)
    setNegotiatingNpc(null)
    setCounterOffers({})
    setChatHistories({})
    setPhase(PHASE.DIALOGUE)
    _nextTurnRef.current = null
  }

  // ── Stage 4: counter-offer handler ────────────────────────────────────────
  async function handleCounterOffer(letter, counterOffer) {
    setCounterOffers(prev => ({ ...prev, [letter]: counterOffer }))
    try {
      await api.acceptCounter(sessionId, letter, counterOffer)
    } catch (e) {
      console.warn('acceptCounter failed:', e.message)
    }
  }

  function handleHistoryChange(npcKey, newMessages, newPendingOffers) {
    setChatHistories(prev => ({
      ...prev,
      [npcKey]: { messages: newMessages, pendingOffers: newPendingOffers || [] },
    }))
  }

  // ── FEATURE 1: Shadow Cabinet upgrade purchased → sync gs ────────────────
  function handleUpgradePurchased(newGs) {
    setGs(newGs)
  }

  // # DEV FEATURE — remove before public launch
  // ── Addition 1: Export Debug Log ─────────────────────────────────────────
  function handleExportDebugLog() {
    if (!gs) return
    const now = new Date()
    const ts = now.toISOString().replace('T', ' ').slice(0, 19)
    const tsFile = now.toISOString().replace(/[:.]/g, '-').slice(0, 19)

    const lines = []
    lines.push('=== WORLD STAGE — SESSION EXPORT ===')
    lines.push(`Generated: ${ts}`)
    lines.push('')

    // ── CURRENT STATE ─────────────────────────────────────────────────────
    lines.push('CURRENT STATE')
    lines.push('─────────────')
    lines.push(`Turn: ${gs.current_turn}/${gs.max_turns}`)
    lines.push(`Budget: $${gs.budget?.toFixed(1)}B`)
    lines.push(`Personal Wealth: $${gs.personal_wealth?.toFixed(1)}B`)
    lines.push(`Stability: ${gs.stability}%`)
    lines.push(`Approval: ${gs.public_approval}%`)
    lines.push(`Oil: $${gs.oil_price}/bbl`)
    const regime = gs.state_identity
    lines.push(`Regime: ${regime?.regime_type || '—'} · ${regime?.power_base || '—'}`)
    const rel = gs.relations || {}
    const rr = (v) => typeof v === 'number' ? Math.round(v) : (v ?? '—')
    lines.push(`Relations: USA ${rr(rel.usa)} | Arabia ${rr(rel.arabia)} | EU ${rr(rel.eu)} | DPRG ${rr(rel.dprg)}`)

    // Active deals
    const activeDeals = (gs.deal_history || []).filter(
      d => !d.broken && (d.expires_turn ?? 0) >= gs.current_turn
    )
    if (activeDeals.length > 0) {
      lines.push('Active Deals:')
      activeDeals.forEach(d => lines.push(`  · [${d.npc?.toUpperCase()}] ${d.summary} (expires turn ${d.expires_turn})`))
    } else {
      lines.push('Active Deals: none')
    }

    // Active world events
    const worldEvents = gs.active_world_events || gs.world_events || []
    if (worldEvents.length > 0) {
      lines.push('Active World Events:')
      worldEvents.forEach(e => lines.push(`  · ${e.name || e.description || JSON.stringify(e)}`))
    } else {
      lines.push('Active World Events: none')
    }

    // Active upgrades (Shadow Cabinet)
    const upgrades = gs.corruption_upgrades || {}
    const activeUpgrades = Object.entries(upgrades).filter(([, v]) => v).map(([k]) => k.replace(/_/g, ' '))
    lines.push(`Active Upgrades: ${activeUpgrades.length > 0 ? activeUpgrades.join(', ') : 'none'}`)

    // Active embargoes / sanctions
    const penalties = []
    if (gs.usa_sanctions_active) penalties.push(`USA Sanctions (tier ${gs.usa_sanctions_tier})`)
    if (gs.arabia_embargo_active) penalties.push(`Arabia Embargo (tier ${gs.arabia_embargo_tier})`)
    lines.push(`Active Embargoes: ${penalties.length > 0 ? penalties.join(', ') : 'none'}`)
    lines.push('')

    // ── TURN HISTORY ──────────────────────────────────────────────────────
    lines.push('TURN HISTORY')
    lines.push('─────────────')
    const history = gs.action_history || []
    if (history.length === 0) {
      lines.push('(no turns completed yet)')
    } else {
      history.forEach((action, idx) => {
        lines.push(`Turn ${idx + 1}:`)
        lines.push(`  Choice: ${action.choice || action.type || '—'}`)
        if (action.consequences?.length > 0) {
          lines.push('  Consequences:')
          action.consequences.forEach(c => lines.push(`    - ${c}`))
        }
        if (action.skim) lines.push(`  Skim: ${action.skim}`)
        if (action.eot_effects?.length > 0) {
          lines.push('  EOT Effects:')
          action.eot_effects.forEach(e => lines.push(`    - ${e}`))
        }
        if (action.epitaph) lines.push(`  Epitaph: "${action.epitaph}"`)
      })
    }
    lines.push('')

    // ── NEGOTIATION LOG ───────────────────────────────────────────────────
    lines.push('NEGOTIATION LOG')
    lines.push('─────────────')
    const negLog = gs.negotiation_log || []
    if (negLog.length === 0) {
      lines.push('(no negotiations recorded)')
    } else {
      negLog.forEach(entry => {
        const npcLabel = NPC_INFO[entry.npc]?.label || entry.npc
        lines.push(`Turn ${entry.turn} — ${npcLabel}:`)
        if (entry.player_message) lines.push(`  Player: "${entry.player_message}"`)
        if (entry.npc_response)   lines.push(`  NPC: "${entry.npc_response}"`)
        if (entry.counter_offer)  lines.push(`  Counter-offer: ${JSON.stringify(entry.counter_offer)}`)
        else                       lines.push('  Counter-offer: none')
        lines.push(`  Outcome: ${entry.outcome || '—'}`)
      })
    }
    lines.push('')

    // ── DEAL HISTORY ──────────────────────────────────────────────────────
    lines.push('DEAL HISTORY')
    lines.push('─────────────')
    const allDeals = gs.deal_history || []
    if (allDeals.length === 0) {
      lines.push('(no deals recorded)')
    } else {
      allDeals.forEach(d => {
        const npcLabel = NPC_INFO[d.npc]?.label || d.npc
        const status = d.broken
          ? 'BROKEN'
          : (d.expires_turn ?? 0) >= gs.current_turn
            ? 'ACTIVE'
            : 'EXPIRED'
        lines.push(`Turn ${d.turn_accepted} — ${npcLabel} [${status}]:`)
        lines.push(`  Terms: ${d.summary}`)
        if (d.expires_turn) lines.push(`  Expires: turn ${d.expires_turn}`)
      })
    }
    lines.push('')
    lines.push('=== END OF EXPORT ===')

    const blob = new Blob([lines.join('\n')], { type: 'text/plain;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `worldstage-turn${gs.current_turn}-${tsFile}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  // ── Render: ENDED ────────────────────────────────────────────────────────
  if (phase === PHASE.ENDED) {
    return (
      <div className="app-container">
        <StatusBar gs={gs} />
        <EndingScreen ending={ending} gs={gs} onRestart={onRestart} onExportLog={handleExportDebugLog} />
      </div>
    )
  }

  // ── Render: GAME ─────────────────────────────────────────────────────────
  return (
    <div className="app-container">
      <StatusBar
        gs={gs}
        onShadowCabinet={() => setShadowCabinetOpen(true)}
      />

      <div className="game-scroll" ref={scrollRef}>

        {error && (
          <div className="error-banner">⚠️ {error}</div>
        )}

        {/* Crisis banners */}
        {gs?.usa_sanctions_active && (
          <div className="crisis-banner">
            ⚠️ USA SANCTIONS ACTIVE — Budget penalty each turn
          </div>
        )}
        {gs?.arabia_embargo_active && (
          <div className="crisis-banner">
            ⚠️ ARABIA OIL EMBARGO ACTIVE — Oil price surcharges apply
          </div>
        )}

        {/* Blackmail warning (shows during DIALOGUE phase only) */}
        {blackmailActive && phase === PHASE.DIALOGUE && (
          <div className="blackmail-banner">
            🔴 CIA BLACKMAIL THREAT ACTIVE<br />
            Your ${gs?.personal_wealth?.toFixed(1)}B account has been flagged.<br />
            Cooperate with USA this turn to pay the &quot;fee&quot;. Refuse and face exposure.
          </div>
        )}

        {/* ── PHASE: DIALOGUE ── */}
        {phase === PHASE.DIALOGUE && (
          <>
            <div className="turn-divider">— TURN {gs?.current_turn}/{gs?.max_turns} —</div>

            {gs?.current_epitaph && (
              <div className="epitaph-line">
                <em>{gs.current_epitaph}</em>
              </div>
            )}

            {/* FEATURE 3: Brigade aftermath banner — fires at start of next turn */}
            {gs?.brigades_deployed_last_turn && !aftermathResult && (
              <div className="brigade-aftermath-banner">
                <div className="aftermath-header">
                  ⚔️ LOYALTY BRIGADE DEPLOYMENT — AFTERMATH
                </div>
                <div className="aftermath-desc">
                  The deployment has made headlines. Street protests have erupted in three districts.
                  Your press office is demanding a response. How do you proceed?
                </div>
                {aftermathLoading ? (
                  <div className="aftermath-loading">Consulting advisors…</div>
                ) : (
                  <div className="aftermath-choices">
                    <button
                      className="aftermath-btn aftermath-btn-suppress"
                      onClick={() => handleAftermath(1)}
                      disabled={aftermathLoading}
                    >
                      <span className="aftermath-btn-label">Suppress Coverage</span>
                      <span className="aftermath-btn-cost">-$3B personal · +5% stability</span>
                    </button>
                    <button
                      className="aftermath-btn aftermath-btn-aid"
                      onClick={() => handleAftermath(2)}
                      disabled={aftermathLoading}
                    >
                      <span className="aftermath-btn-label">Launch Aid Programs</span>
                      <span className="aftermath-btn-cost">-$5B budget · +8% approval · +3% stability</span>
                    </button>
                    <button
                      className="aftermath-btn aftermath-btn-favor"
                      onClick={() => handleAftermath(3)}
                      disabled={aftermathLoading}
                    >
                      <span className="aftermath-btn-label">Call in a Favor</span>
                      <span className="aftermath-btn-cost">Highest-relation NPC -10 · +8% stability · +5% approval</span>
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Aftermath resolved message */}
            {aftermathResult && (
              <div className="alert alert-success">{aftermathResult}</div>
            )}

            {/* World event banner */}
            <EventBanner event={currentEvent} />

            <DialoguePanel
              dialogue={dialogue}
              onNegotiate={!loading ? setNegotiatingNpc : null}
              negotiatingNpc={negotiatingNpc}
              intelActive={!!gs?.corruption_upgrades?.intelligence_apparatus}
              sessionId={sessionId}
              gs={gs}
            />

            {/* Negotiation slide-up panel */}
            {negotiatingNpc && (() => {
              const info = NPC_INFO[negotiatingNpc]

              let activeDealSummary = null
              if (gs) {
                const summaries = []
                if (
                  negotiatingNpc === 'arabia' &&
                  gs.oil_price_locked &&
                  gs.oil_price_lock_turns_remaining > 0
                ) {
                  summaries.push(
                    `🔒 Oil locked at $${gs.oil_price_lock_value}/bbl — ${gs.oil_price_lock_turns_remaining} turn(s) remaining`
                  )
                }
                if (Array.isArray(gs.active_trade_commitments)) {
                  for (const c of gs.active_trade_commitments) {
                    if (!c.npc || c.npc === negotiatingNpc) {
                      summaries.push(
                        `🤝 ${c.description} — ${c.turns_remaining} turn(s) remaining`
                      )
                    }
                  }
                }
                if (summaries.length > 0) {
                  activeDealSummary = summaries.join(' · ')
                }
              }

              const savedHistory = chatHistories[negotiatingNpc] || {}
              return (
                <NegotiationPanel
                  key={negotiatingNpc}
                  npcKey={negotiatingNpc}
                  npcLabel={info.label}
                  npcFlag={info.flag}
                  sessionId={sessionId}
                  offerLetter={info.letter}
                  onClose={() => setNegotiatingNpc(null)}
                  onCounterOffer={handleCounterOffer}
                  initialMessages={savedHistory.messages || []}
                  initialPendingOffers={savedHistory.pendingOffers || []}
                  onHistoryChange={(msgs, offers) => handleHistoryChange(negotiatingNpc, msgs, offers)}
                  activeDealSummary={activeDealSummary}
                />
              )
            })()}

            <div className="panel" style={{ paddingBottom: '0.5rem' }}>
              <div className="panel-header">Relations</div>
              <RelationBadges
                relations={gs?.relations}
                sanctions={gs?.usa_sanctions_active}
                embargo={gs?.arabia_embargo_active}
              />
            </div>

            <OffersPanel
              offers={offers}
              onChoice={handleChoice}
              disabled={loading}
              counterOffers={counterOffers}
            />

            {/* Restart game link — always accessible during dialogue phase */}
            <div style={{ textAlign: 'center', paddingBottom: '1.5rem' }}>
              <button
                className="btn-ghost"
                style={{ fontSize: '0.75rem', opacity: 0.5 }}
                onClick={onRestart}
                disabled={loading}
              >
                Abandon &amp; Start New Game
              </button>
            </div>
          </>
        )}

        {/* ── PHASE: CONSEQUENCES ── */}
        {phase === PHASE.CONSEQUENCES && (
          <>
            <div className="turn-divider">— TURN {gs?.current_turn}/{gs?.max_turns} — CHOICE MADE —</div>

            <ConsequencesPanel
              consequences={consequences}
              blackmailResult={blackmailResult}
            />

            {/* FEATURE 2: Brigade tiered deployment — shown before skim if available */}
            {brigadeAvailable && !brigadeResult && (() => {
              const pw = gs?.personal_wealth ?? 0
              const brigadeOps = [
                {
                  op: 1, cost: 2, label: 'Domestic Suppression',
                  desc: '+10% stability · -5% approval · All relations -3',
                  canAfford: pw >= 2,
                },
                {
                  op: 2, cost: 3, label: 'Propaganda Campaign',
                  desc: '+8% approval · -3% stability · -$2B national',
                  canAfford: pw >= 3,
                },
                {
                  op: 3, cost: 4, label: 'Foreign Influence Ops',
                  desc: 'Target NPC relations -8 · +5% stability',
                  canAfford: pw >= 4,
                  hasTarget: true,
                },
                {
                  op: 4, cost: 6, label: 'Covert Security Apparatus',
                  desc: '+15% stability · -10% approval · All relations -5 · Regime shifts right',
                  canAfford: pw >= 6,
                },
              ]
              return (
                <div className="brigade-prompt-panel">
                  <div className="brigade-prompt-header">⚔️ LOYALTY BRIGADE DEPLOYMENT</div>
                  <div className="brigade-prompt-desc">
                    Choose an operation or stand down. Cost deducted from personal funds.
                  </div>
                  {brigadeLoading ? (
                    <div className="brigade-loading">Mobilising forces…</div>
                  ) : (
                    <div className="brigade-tiered-ops">
                      {brigadeOps.map(({ op, cost, label, desc, canAfford, hasTarget }) => (
                        <div key={op} className={`brigade-op-row${canAfford ? '' : ' brigade-op-disabled'}`}>
                          <div className="brigade-op-info">
                            <span className="brigade-op-label">{label}</span>
                            <span className="brigade-op-desc">{desc}</span>
                          </div>
                          {hasTarget && canAfford && (
                            <select
                              className="brigade-target-select"
                              value={brigadeTargetNpc}
                              onChange={e => setBrigadeTargetNpc(e.target.value)}
                            >
                              <option value="usa">🇺🇸 USA</option>
                              <option value="arabia">🛢️ Arabia</option>
                              <option value="eu">🇪🇺 EU</option>
                              <option value="dprg">⚡ DPRG</option>
                            </select>
                          )}
                          <button
                            className="brigade-btn brigade-btn-yes"
                            onClick={() => handleBrigadeDeploy(op, hasTarget ? brigadeTargetNpc : '')}
                            disabled={!canAfford || brigadeLoading}
                          >
                            {canAfford ? `$${cost}B` : `Need $${cost}B`}
                          </button>
                        </div>
                      ))}
                      <button
                        className="brigade-btn brigade-btn-no"
                        style={{ marginTop: '0.4rem', width: '100%' }}
                        onClick={() => handleBrigadeDeploy(0)}
                        disabled={brigadeLoading}
                      >
                        Stand Down — no deployment
                      </button>
                    </div>
                  )}
                </div>
              )
            })()}

            {/* Brigade result message */}
            {brigadeResult && (
              <div className="alert alert-warn">{brigadeResult}</div>
            )}

            <SkimPanel
              skimOptions={skimOptions}
              onSkim={handleSkim}
              disabled={loading || brigadeLoading || (brigadeAvailable && !brigadeResult)}
              drainProjection={drainProjection}
            />
          </>
        )}

        {/* ── PHASE: INJECT PROMPT ── */}
        {phase === PHASE.INJECT_PROMPT && (
          <>
            <div className="turn-divider">— TURN {gs?.current_turn}/{gs?.max_turns} — EMERGENCY FUNDS —</div>

            <div className="alert alert-warn">
              National treasury is critically low (${gs?.budget?.toFixed(1)}B).
            </div>

            <InjectPanel
              injectOptions={injectOptions}
              onInject={handleInject}
              disabled={loading}
            />
          </>
        )}

        {/* ── PHASE: EOT ── */}
        {phase === PHASE.EOT && (
          <>
            <div className="turn-divider">— END OF TURN {(gs?.current_turn || 1) - 1}/{gs?.max_turns} —</div>

            {skimMessages.length > 0 && (
              <div className="panel">
                <div className="panel-header">Allocation Result</div>
                <ul className="msg-list">
                  {skimMessages.map((m, i) => <li key={i}>{m}</li>)}
                </ul>
              </div>
            )}

            {corruptionAlert && (
              <div className="alert alert-warn">{corruptionAlert}</div>
            )}

            {patriotMessage && (
              <div className="alert alert-success">{patriotMessage}</div>
            )}

            <InterceptPanel intercepts={intercepts} />

            <EotPanel messages={eotMessages} />

            <div className="continue-row">
              <button
                className="btn-primary"
                onClick={handleContinue}
                disabled={loading}
              >
                {ending ? 'See Results' : `Turn ${gs?.current_turn || 1} →`}
              </button>
            </div>
          </>
        )}

        {loading && (
          <div style={{
            textAlign: 'center',
            padding: '1rem',
            fontFamily: 'var(--mono)',
            fontSize: '0.82rem',
            color: 'var(--muted)'
          }}>
            Consulting advisors…
          </div>
        )}

      </div>

      {/* FEATURE 1: Confirmation modal */}
      {pendingConfirm && (
        <div className="confirm-overlay">
          <div className="confirm-dialog">
            <div className="confirm-header">
              {pendingConfirm.type === 'choice' ? 'Confirm Diplomatic Choice' : 'Confirm Allocation'}
            </div>
            <div className="confirm-body">
              {pendingConfirm.text}
            </div>
            <div className="confirm-actions">
              <button
                className="btn-ghost confirm-back-btn"
                onClick={handleConfirmCancel}
              >
                ← Go Back
              </button>
              <button
                className="btn-primary confirm-commit-btn"
                onClick={handleConfirmExecute}
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Session 2 Item 6: Diplomatic Crisis modal — broken deals */}
      {dipCrisisMessages.length > 0 && (
        <div className="confirm-overlay" style={{ zIndex: 350 }}>
          <div className="confirm-dialog" style={{ borderColor: 'var(--danger)', borderWidth: 2 }}>
            <div className="confirm-header" style={{ color: 'var(--danger)', background: 'rgba(229,74,74,0.08)' }}>
              ⚠️ DIPLOMATIC CRISIS
            </div>
            <div className="confirm-body">
              {dipCrisisMessages.map((msg, i) => (
                <p key={i} style={{ marginBottom: i < dipCrisisMessages.length - 1 ? '0.5rem' : 0, color: 'var(--danger)', fontFamily: 'var(--mono)', fontSize: '0.86rem' }}>
                  {msg.replace(/^💔\s*Deal broken:\s*/i, '')}
                </p>
              ))}
              <p style={{ marginTop: '0.75rem', fontSize: '0.84rem', color: 'var(--muted)' }}>
                Expect consequences in upcoming turns.
              </p>
            </div>
            <div className="confirm-actions">
              <button className="btn-primary" onClick={() => setDipCrisisMessages([])}>
                Dismiss
              </button>
            </div>
          </div>
        </div>
      )}

      {/* FEATURE 1: Shadow Cabinet drawer */}
      {shadowCabinetOpen && (
        <ShadowCabinet
          gs={gs}
          sessionId={sessionId}
          onClose={() => setShadowCabinetOpen(false)}
          onUpgradePurchased={handleUpgradePurchased}
        />
      )}

      {/* # DEV FEATURE — remove before public launch */}
      {/* Addition 1: Export Debug Log — desktop only (hidden on mobile via CSS) */}
      <div className="dev-export-footer">
        <button
          className="dev-export-btn"
          onClick={handleExportDebugLog}
          title="Export full game state as .txt debug log"
        >
          ⬇ Export Debug Log
        </button>
      </div>

    </div>
  )
}
