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

/**
 * GameScreen manages the full turn lifecycle:
 *
 * PHASE 0 — dialogue      : show NPC messages + offers panel
 * PHASE 1 — consequences  : show choice result + skim panel
 *                           (or inject panel if Option G)
 * PHASE 2 — eot           : show skim/inject result + EOT effects + intercepts
 *                           → then auto-advance to next turn (PHASE 0)
 */

const PHASE = {
  DIALOGUE: 'dialogue',
  CONSEQUENCES: 'consequences',
  INJECT_PROMPT: 'inject_prompt',
  EOT: 'eot',
  ENDED: 'ended',
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

  const scrollRef = useRef(null)

  // Scroll to top of game area whenever phase changes
  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = 0
  }, [phase])

  const clearError = () => setError(null)

  // ── PHASE 0 → 1: player picks A-G ───────────────────────────────────────
  async function handleChoice(letter) {
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
      setBlackmailActive(false) // consumed or not fired
      setPhase(PHASE.CONSEQUENCES)

    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // ── PHASE 1 → 2: player picks skim option ────────────────────────────────
  async function handleSkim(choice) {
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

      if (res.status !== 'active') {
        setEnding(res.ending)
        setPhase(PHASE.EOT) // show effects first, then ending on continue
        return
      }

      setPhase(PHASE.EOT)

      // Stash next-turn data for when player hits continue
      _nextTurnRef.current = {
        dialogue: res.next_dialogue,
        offers: res.next_offers,
        skimOptions: res.next_skim_options,
        blackmailActive: res.next_blackmail,
        status: res.status,
        ending: res.ending,
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
      }

    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  // Stash next-turn data between phases (not in state to avoid re-renders)
  const _nextTurnRef = useRef(null)

  // ── PHASE 2 → 0 (or ENDED): player hits "Next Turn" ─────────────────────
  function handleContinue() {
    const next = _nextTurnRef.current

    // Game already ended during EOT
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
    setPhase(PHASE.DIALOGUE)
    _nextTurnRef.current = null
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
      <StatusBar gs={gs} />

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

            <DialoguePanel dialogue={dialogue} />

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

            <SkimPanel
              skimOptions={skimOptions}
              onSkim={handleSkim}
              disabled={loading}
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

            {/* Skim / inject result */}
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
    </div>
  )
}
