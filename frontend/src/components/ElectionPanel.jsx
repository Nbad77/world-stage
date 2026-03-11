/**
 * Election Panel — Session 4B
 * Replaces OffersPanel on election turn (turn 4).
 * Shows 4 election choices, confirmation modal, then result + NPC reactions.
 *
 * Props:
 *   gameState     : serialized game state object
 *   sessionId     : string
 *   onElectionDone: (resultData) => void — called after election completes
 *   disabled      : bool
 */
import { useState } from 'react'

const API = import.meta.env.VITE_API_URL || ''

const ELECTION_CHOICES = [
  {
    key: 'fair',
    label: 'Hold Fair Election',
    icon: '🗳️',
    desc: 'Let the people decide. Outcome depends on your approval rating.',
    color: 'var(--success)',
  },
  {
    key: 'rigged',
    label: 'Rig the Election',
    icon: '🎭',
    desc: 'Guarantee victory, but the world may notice. Heat +10%, costs $2B.',
    color: 'var(--warning)',
  },
  {
    key: 'canceled',
    label: 'Cancel the Election',
    icon: '🚫',
    desc: 'No vote at all. Maximum control, maximum backlash. Heat +20%.',
    color: 'var(--danger)',
  },
  {
    key: 'observers',
    label: 'Invite International Observers',
    icon: '🏛️',
    desc: 'Full transparency. Requires 60+ approval and no prior brigade deployments. Costs $1B.',
    color: 'var(--accent)',
    gated: true,
  },
]

const RESULT_LABELS = {
  fair_success: { title: 'Victory!', subtitle: 'The people have spoken — and they chose you.', icon: '✅' },
  fair_squeaker: { title: 'Narrow Win', subtitle: 'You scraped through. The opposition is energized.', icon: '😰' },
  fair_fail: { title: 'Defeated', subtitle: 'The electorate has rejected your leadership. Protests loom.', icon: '💔' },
  rigged: { title: 'Election Rigged', subtitle: 'You won on paper. The world has its suspicions.', icon: '🎭' },
  canceled: { title: 'Election Canceled', subtitle: 'No vote, no mandate. The streets are restless.', icon: '🚫' },
  observers: { title: 'Transparent Election', subtitle: 'The world witnessed a credible democratic process.', icon: '🏛️' },
}

export default function ElectionPanel({ gameState, sessionId, onElectionDone, disabled }) {
  const [phase, setPhase] = useState('choose')  // 'choose' | 'confirm' | 'loading' | 'result'
  const [selected, setSelected] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const approval = gameState?.public_approval ?? 50
  const hasBrigades = (gameState?.action_history || []).some(a => a.type === 'deploy_brigades')

  function isChoiceAvailable(choice) {
    if (choice.key === 'observers') {
      return approval >= 60 && !hasBrigades
    }
    return true
  }

  function getUnavailableReason(choice) {
    if (choice.key !== 'observers') return null
    if (approval < 60) return `Requires 60% approval (currently ${approval}%)`
    if (hasBrigades) return 'Unavailable: brigade deployments detected in history'
    return null
  }

  async function submitElection() {
    setPhase('loading')
    setError(null)
    try {
      const res = await fetch(`${API}/game/${sessionId}/election`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ choice: selected }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail || `HTTP ${res.status}`)
      }
      const data = await res.json()
      setResult(data)
      setPhase('result')
    } catch (e) {
      setError(e.message)
      setPhase('confirm')
    }
  }

  // ── Choose phase ──
  if (phase === 'choose' || phase === 'confirm') {
    return (
      <div className="panel election-panel">
        <div className="panel-header" style={{ color: 'var(--accent)' }}>
          🗳️ National Election
        </div>
        <p className="election-context">
          The scheduled election has arrived. Your approval is <strong>{approval}%</strong>.
          How will you handle this?
        </p>

        <div className="election-choices">
          {ELECTION_CHOICES.map(choice => {
            const available = isChoiceAvailable(choice)
            const reason = getUnavailableReason(choice)
            const isSelected = selected === choice.key

            return (
              <button
                key={choice.key}
                className={`election-choice-btn ${isSelected ? 'selected' : ''}`}
                style={{
                  borderColor: isSelected ? choice.color : undefined,
                  opacity: available ? 1 : 0.4,
                }}
                disabled={disabled || !available || phase === 'confirm'}
                onClick={() => { setSelected(choice.key); setPhase('confirm') }}
                title={reason || ''}
              >
                <span className="election-choice-icon">{choice.icon}</span>
                <span className="election-choice-body">
                  <span className="election-choice-label">{choice.label}</span>
                  <span className="election-choice-desc">{choice.desc}</span>
                  {reason && <span className="election-choice-gate">{reason}</span>}
                </span>
              </button>
            )
          })}
        </div>

        {/* Confirmation modal */}
        {phase === 'confirm' && selected && (
          <div className="election-confirm">
            <p>
              Confirm: <strong>{ELECTION_CHOICES.find(c => c.key === selected)?.label}</strong>?
              This cannot be undone.
            </p>
            {error && <p className="election-error">{error}</p>}
            <div className="election-confirm-btns">
              <button className="election-btn-yes" onClick={submitElection}>
                Confirm
              </button>
              <button className="election-btn-no" onClick={() => { setPhase('choose'); setSelected(null) }}>
                Go Back
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  // ── Loading phase ──
  if (phase === 'loading') {
    return (
      <div className="panel election-panel">
        <div className="panel-header" style={{ color: 'var(--accent)' }}>
          🗳️ National Election
        </div>
        <p className="election-loading">The votes are being counted...</p>
      </div>
    )
  }

  // ── Result phase ──
  if (phase === 'result' && result) {
    const info = RESULT_LABELS[result.result_key] || { title: 'Results', subtitle: '', icon: '🗳️' }
    const reactions = result.npc_reactions || {}

    return (
      <div className="panel election-panel">
        <div className="panel-header" style={{ color: 'var(--accent)' }}>
          🗳️ Election Results
        </div>

        <div className="election-result-banner">
          <span className="election-result-icon">{info.icon}</span>
          <div>
            <div className="election-result-title">{info.title}</div>
            <div className="election-result-subtitle">{info.subtitle}</div>
          </div>
        </div>

        {/* Consequences */}
        {result.consequences && result.consequences.length > 0 && (
          <div className="election-consequences">
            <div className="election-section-label">Consequences</div>
            {result.consequences.map((c, i) => (
              <div key={i} className="election-consequence-line">{c}</div>
            ))}
          </div>
        )}

        {/* NPC Reactions */}
        <div className="election-reactions">
          <div className="election-section-label">World Reactions</div>
          {['usa', 'arabia', 'eu', 'dprg', 'russia', 'china'].map(npc => (
            reactions[npc] ? (
              <div key={npc} className="election-reaction">
                <span className="election-npc-tag" style={{ color: `var(--${npc})` }}>
                  {npc === 'usa' ? 'Bill' : npc === 'arabia' ? 'Sadam' : npc === 'eu' ? 'Marsha' : npc === 'dprg' ? 'Ji-won' : npc === 'russia' ? 'Volkov' : 'Wei'}
                </span>
                <span className="election-reaction-text">{reactions[npc]}</span>
              </div>
            ) : null
          ))}
        </div>

        <button
          className="election-btn-continue"
          onClick={() => onElectionDone(result)}
        >
          Continue
        </button>
      </div>
    )
  }

  return null
}
