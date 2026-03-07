/**
 * AdvisorPanel — Session 5 advisor management.
 * Shows active advisors (max 3) and available hiring pool.
 * Supports hire, dismiss, and eliminate actions.
 *
 * Props:
 *   gs        : game_state object
 *   sessionId : string
 *   onGsUpdate: (newGs) => void
 */

import { useState, useEffect } from 'react'
import { api } from '../api'

export default function AdvisorPanel({ gs, sessionId, onGsUpdate }) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [successMsg, setSuccessMsg] = useState(null)
  const [confirmEliminate, setConfirmEliminate] = useState(null) // advisor_id or null

  const advisors = gs?.advisors || []
  const pool = gs?.advisor_pool || []
  const maxAdvisors = gs?.fourth_advisor_slot ? 4 : 3

  // Fetch pool on mount if empty
  useEffect(() => {
    if (pool.length === 0 && advisors.length < maxAdvisors) {
      fetchPool()
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  async function fetchPool() {
    try {
      const res = await api.getAdvisorPool(sessionId)
      if (res.game_state && onGsUpdate) {
        onGsUpdate(res.game_state)
      }
    } catch (e) {
      console.error('Failed to fetch advisor pool:', e)
    }
  }

  async function handleAction(action, advisorId) {
    setLoading(true)
    setError(null)
    setSuccessMsg(null)
    setConfirmEliminate(null)
    try {
      const res = await api.advisorAction(sessionId, action, advisorId)
      if (res.success) {
        setSuccessMsg(res.message)
      } else {
        setError(res.message)
      }
      if (res.game_state && onGsUpdate) {
        onGsUpdate(res.game_state)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  if (advisors.length === 0 && pool.length === 0) {
    return null // nothing to show
  }

  return (
    <div className="panel advisor-panel">
      <div className="panel-header">
        Advisors
        <span className="advisor-count">{advisors.length}/{maxAdvisors} active</span>
      </div>

      {successMsg && <div className="sc-success" style={{ margin: '0.3rem 0' }}>{successMsg}</div>}
      {error && <div className="sc-error" style={{ margin: '0.3rem 0' }}>{error}</div>}

      {/* Active advisors */}
      {advisors.length > 0 && (
        <div className="advisor-active-section">
          {advisors.map(a => (
            <div key={a.id} className={`advisor-card ${a.nefarious ? 'advisor-nefarious' : ''}`}>
              <div className="advisor-card-header">
                <span className="advisor-icon">{a.icon}</span>
                <div className="advisor-info">
                  <span className="advisor-name">{a.name}</span>
                  <span className="advisor-type">{a.label}</span>
                </div>
                <div className="advisor-stats">
                  <span className="advisor-stat" title="Competence">🎯 {a.competence}</span>
                  <span className={`advisor-stat ${a.loyalty < 30 ? 'advisor-stat-danger' : a.loyalty < 50 ? 'advisor-stat-warn' : ''}`} title="Loyalty">
                    ❤️ {a.loyalty}
                  </span>
                </div>
              </div>
              <div className="advisor-desc">{a.description}</div>
              {a.bias_stat && (
                <div className="advisor-bias">
                  Bias: {a.bias_stat} {a.bias_direction > 0 ? `+${a.bias_direction}` : a.bias_direction}
                </div>
              )}
              <div className="advisor-actions">
                <button
                  className="advisor-btn advisor-btn-dismiss"
                  onClick={() => handleAction('dismiss', a.id)}
                  disabled={loading}
                >
                  Dismiss
                </button>
                {confirmEliminate === a.id ? (
                  <div className="advisor-eliminate-confirm">
                    <span>Permanent?</span>
                    <button
                      className="advisor-btn advisor-btn-eliminate"
                      onClick={() => handleAction('eliminate', a.id)}
                      disabled={loading}
                    >
                      Confirm
                    </button>
                    <button
                      className="advisor-btn"
                      onClick={() => setConfirmEliminate(null)}
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <button
                    className="advisor-btn advisor-btn-eliminate-init"
                    onClick={() => setConfirmEliminate(a.id)}
                    disabled={loading}
                    title="Permanently remove — cannot be rehired. Costs $2.0B personal."
                    style={{ color: '#ff5252' }}
                  >
                    Eliminate ($2B)
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Hiring pool */}
      {advisors.length < maxAdvisors && pool.length > 0 && (
        <div className="advisor-pool-section">
          <div className="advisor-pool-header">Available for Hire</div>
          {pool.map(a => (
            <div key={a.id} className={`advisor-card advisor-card-pool ${a.nefarious ? 'advisor-nefarious' : ''}`}>
              <div className="advisor-card-header">
                <span className="advisor-icon">{a.icon}</span>
                <div className="advisor-info">
                  <span className="advisor-name">{a.name}</span>
                  <span className="advisor-type">{a.label}</span>
                  {/* fixes_12 Fix 6: Previously served badge */}
                  {a.previously_served && (
                    <span style={{ fontSize: '0.65rem', color: '#b0b040', fontWeight: 600, marginLeft: '0.3rem' }}>
                      Previously Served
                    </span>
                  )}
                </div>
                <div className="advisor-stats">
                  <span className="advisor-stat" title="Competence">🎯 {a.competence}</span>
                  <span className="advisor-stat" title="Loyalty">❤️ {a.loyalty}</span>
                </div>
              </div>
              <div className="advisor-desc">{a.description}</div>
              <button
                className="advisor-btn advisor-btn-hire"
                onClick={() => handleAction('hire', a.id)}
                disabled={loading}
              >
                Hire
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
