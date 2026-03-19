/**
 * LeakCrisisModal — 8D: The Leak scripted branching crisis.
 * Full-screen modal. Player must choose one of four options. No escape.
 */
import { useState } from 'react'
import { api } from '../api'

const CHOICES = [
  {
    key: 'deny',
    label: 'DENY PUBLICLY',
    description: 'Issue a statement dismissing the documents as fabricated.',
    consequences: 'USA \u22125 \u00b7 DPRG +5 \u00b7 Stability \u22128 \u00b7 Scandal risk 40%',
  },
  {
    key: 'admit',
    label: 'ADMIT AND APOLOGIZE',
    description: 'Acknowledge the communications and frame them as routine diplomacy.',
    consequences: 'USA +10 \u00b7 DPRG \u221215 \u00b7 Approval \u221210%',
  },
  {
    key: 'blame',
    label: 'BLAME A MINISTER',
    description: 'Attribute the leak to a rogue official. Name someone.',
    consequences: 'Stability \u22125',
    warning: 'ONE-TIME \u2014 Scapegoat mechanic permanently consumed',
  },
  {
    key: 'jiwon',
    label: 'LET JI-WON HANDLE IT',
    description: "Contact Ji-won's office and arrange for the story to disappear.",
    consequences: '\u2212$3B personal \u00b7 DPRG +3 \u00b7 Story suppressed',
  },
]

export default function LeakCrisisModal({ gs, sessionId, onResolve }) {
  const [selected, setSelected] = useState(null)
  const [confirming, setConfirming] = useState(false)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  const scapegoatUsed = gs?.scapegoat_used || false
  const personalWealth = gs?.personal_wealth || 0
  const insufficientFunds = personalWealth < 3.0

  function isDisabled(key) {
    if (key === 'blame' && scapegoatUsed) return true
    if (key === 'jiwon' && insufficientFunds) return true
    return false
  }

  function getDisabledReason(key) {
    if (key === 'blame' && scapegoatUsed) return 'UNAVAILABLE \u2014 scapegoat already used'
    if (key === 'jiwon' && insufficientFunds) return `Insufficient funds ($3B required, you have $${personalWealth.toFixed(1)}B)`
    return null
  }

  async function handleConfirm() {
    if (!selected || loading) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.resolveTheLeakCrisis(sessionId, selected)
      console.log(`[leak] Resolved: choice=${selected}`)
      setResult(res)
    } catch (e) {
      setError(e.message)
      setLoading(false)
    }
  }

  function handleContinue() {
    if (result?.game_state) {
      onResolve(result.game_state)
    } else {
      onResolve(null)
    }
  }

  // Resolution screen
  if (result) {
    return (
      <div className="leak-overlay">
        <div className="leak-modal">
          <div className="leak-header">
            <div className="leak-title">
              <span className="leak-crisis-badge">{'\uD83D\uDD34'} CRISIS RESOLVED</span>
            </div>
            <div className="leak-subtitle">THE LEAK</div>
          </div>
          <div className="leak-body leak-result-body">
            <div className="leak-narrative">
              {result.result}
            </div>
            <div className="leak-consequence-summary">
              <div className="leak-summary-header">Consequences</div>
              {result.consequences && Object.entries(result.consequences).map(([key, val]) => {
                if (key === 'note') return null
                const label = key === 'personal_wealth' ? 'Personal Wealth'
                  : key === 'stability' ? 'Stability'
                  : key === 'approval' ? 'Approval'
                  : key.toUpperCase()
                const valStr = typeof val === 'number'
                  ? (val > 0 ? `+${val}` : `${val}`)
                  : String(val)
                return (
                  <div key={key} className="leak-summary-row">
                    <span className="leak-summary-label">{label}</span>
                    <span className={`leak-summary-val ${val > 0 ? 'leak-val-pos' : 'leak-val-neg'}`}>{valStr}</span>
                  </div>
                )
              })}
              {result.consequences?.note && (
                <div className="leak-summary-note">{result.consequences.note}</div>
              )}
            </div>
            <button className="leak-continue-btn" onClick={handleContinue}>
              Continue
            </button>
          </div>
        </div>
      </div>
    )
  }

  // Choice screen
  return (
    <div className="leak-overlay">
      <div className="leak-modal">
        <div className="leak-header">
          <div className="leak-title">
            <span className="leak-crisis-badge">{'\uD83D\uDD34'} CRISIS — THE LEAK</span>
          </div>
          <div className="leak-subtitle">
            Classified documents reveal your back-channel with Ji-won Ryang
          </div>
        </div>

        <div className="leak-body">
          <div className="leak-situation">
            International media is reporting on classified communications between
            your office and DPRG leadership. The documents appear authentic.
            Bill Hartwell has requested an urgent explanation. Ji-won has gone silent.
            You have hours to decide how to respond.
          </div>

          <div className="leak-choices">
            {CHOICES.map(c => {
              const disabled = isDisabled(c.key)
              const disabledReason = getDisabledReason(c.key)
              const isSelected = selected === c.key

              return (
                <div
                  key={c.key}
                  className={`leak-choice-card ${isSelected ? 'leak-choice-selected' : ''} ${disabled ? 'leak-choice-disabled' : ''}`}
                  onClick={() => {
                    if (disabled || loading) return
                    setSelected(c.key)
                    setConfirming(false)
                    setError(null)
                  }}
                >
                  <div className="leak-choice-label">{c.label}</div>
                  <div className="leak-choice-desc">{c.description}</div>
                  <div className="leak-choice-consequences">{c.consequences}</div>
                  {c.warning && !disabled && (
                    <div className="leak-choice-warning">{c.warning}</div>
                  )}
                  {disabled && disabledReason && (
                    <div className="leak-choice-unavailable">{disabledReason}</div>
                  )}

                  {isSelected && !confirming && !disabled && (
                    <button
                      className="leak-confirm-step-btn"
                      onClick={e => { e.stopPropagation(); setConfirming(true) }}
                    >
                      Confirm this choice?
                    </button>
                  )}
                  {isSelected && confirming && !disabled && (
                    <div className="leak-confirm-row" onClick={e => e.stopPropagation()}>
                      <button
                        className="leak-confirm-btn"
                        onClick={handleConfirm}
                        disabled={loading}
                      >
                        {loading ? 'Resolving...' : 'Confirm'}
                      </button>
                      <button
                        className="leak-back-btn"
                        onClick={() => { setConfirming(false); setError(null) }}
                        disabled={loading}
                      >
                        Back
                      </button>
                    </div>
                  )}
                </div>
              )
            })}
          </div>

          {error && (
            <div className="leak-error">{error}</div>
          )}

          <div className="leak-footer">
            This decision will be recorded in your political biography.
          </div>
        </div>
      </div>
    </div>
  )
}
