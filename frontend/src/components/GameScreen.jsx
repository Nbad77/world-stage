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
  async function handleBrigadeDeploy(deploy) {
    clearError()
    setBrigadeLoading(true)
    try {
      const res = await api.deployBrigades(sessionId, deploy)
      setGs(res.game_state)
      setBrigadeResult(res.messages?.[0] || (deploy ? 'Brigades deployed.' : 'Brigades stood down.'))
    } catch (e) {
      setError(e.message)
    } finally {
      setBrigadeLoading(false)
      // After brigade decision (either way), move to skim
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
      setEotMessages(res.eot_effects || [])
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
      setEotMessages(res.eot_effects || [])
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

  function handleHistoryChange(npcKey, newMessages) {
    setChatHistories(prev => ({ ...prev, [npcKey]: newMessages }))
  }

  // ── FEATURE 1: Shadow Cabinet upgrade purchased → sync gs ────────────────
  function handleUpgradePurchased(newGs) {
    setGs(newGs)
  }

  // ── Render: ENDED ────────────────────────────────────────────────────────
  if (phase === PHASE.ENDED) {
    return (
      <div className="app-container">
        <StatusBar gs={gs} />
        <EndingScreen ending={ending} gs={gs} onRestart={onRestart} />
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
                  initialMessages={chatHistories[negotiatingNpc] || []}
                  onHistoryChange={(msgs) => handleHistoryChange(negotiatingNpc, msgs)}
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

            {/* FEATURE 2: Brigade secondary prompt — shown before skim if available */}
            {brigadeAvailable && !brigadeResult && (
              <div className="brigade-prompt-panel">
                <div className="brigade-prompt-header">⚔️ LOYALTY BRIGADE DEPLOYMENT</div>
                <div className="brigade-prompt-desc">
                  Deploy Loyalty Brigades this turn?
                  Costs $2B personal, -5% approval, +10% stability, all relations -3.
                </div>
                {brigadeLoading ? (
                  <div className="brigade-loading">Mobilising forces…</div>
                ) : (
                  <div className="brigade-prompt-actions">
                    <button
                      className="brigade-btn brigade-btn-yes"
                      onClick={() => handleBrigadeDeploy(true)}
                      disabled={brigadeLoading}
                    >
                      Deploy — $2B · -5% approval · +10% stability
                    </button>
                    <button
                      className="brigade-btn brigade-btn-no"
                      onClick={() => handleBrigadeDeploy(false)}
                      disabled={brigadeLoading}
                    >
                      Stand Down
                    </button>
                  </div>
                )}
              </div>
            )}

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

      {/* FEATURE 1: Shadow Cabinet drawer */}
      {shadowCabinetOpen && (
        <ShadowCabinet
          gs={gs}
          sessionId={sessionId}
          onClose={() => setShadowCabinetOpen(false)}
          onUpgradePurchased={handleUpgradePurchased}
        />
      )}

    </div>
  )
}
