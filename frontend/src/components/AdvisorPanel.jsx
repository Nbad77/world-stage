/**
 * AdvisorPanel — Session 7C Step 2+3: Advisor Assignment + Analysis UI.
 * Shows 3 fixed advisor cards in a compact row.
 * Each card: name + icon, trust tier bar, assign/unassign button.
 * When assigned, generates Claude analysis displayed below.
 *
 * Props:
 *   gs        : game_state object (advisors dict)
 *   sessionId : string
 *   onGsUpdate: (newGs) => void
 */

import { useState } from 'react'
import { api } from '../api'

const ADVISOR_META = {
  finance_minister: { icon: '💰', color: '#4caf50', tint: 'analysis-green' },
  security_chief:   { icon: '🛡️', color: '#f44336', tint: 'analysis-red' },
  diplomatic_aide:  { icon: '🕊️', color: '#42a5f5', tint: 'analysis-blue' },
}

function trustTier(trust) {
  if (trust >= 70) return { label: 'High',     cls: 'trust-high' }
  if (trust >= 40) return { label: 'Medium',   cls: 'trust-med' }
  if (trust >= 20) return { label: 'Low',      cls: 'trust-low' }
  return              { label: 'Critical', cls: 'trust-critical' }
}

export default function AdvisorPanel({ gs, sessionId, onGsUpdate }) {
  const [loading, setLoading] = useState(null) // advisor key being acted on
  const [error, setError] = useState(null)
  // Step 3: Store analysis results keyed by advisor key
  const [analyses, setAnalyses] = useState({})

  const advisors = gs?.advisors
  if (!advisors || typeof advisors !== 'object' || Array.isArray(advisors)) {
    return null
  }

  const slots = gs?.advisor_slots_available ?? 2
  const assignedCount = Object.values(advisors).filter(a => a.assigned_this_turn).length

  async function handleToggle(key) {
    const adv = advisors[key]
    if (!adv) return
    const action = adv.assigned_this_turn ? 'unassign' : 'assign'

    // Check slot limit before assigning
    if (action === 'assign' && assignedCount >= slots) return

    setLoading(key)
    setError(null)
    try {
      const res = action === 'assign'
        ? await api.assignAdvisor(sessionId, key)
        : await api.unassignAdvisor(sessionId, key)

      console.log(`[ADVISOR] ${action === 'assign' ? 'Assigned' : 'Unassigned'}:`, key)

      // Step 3: Store analysis if returned from assign call
      if (action === 'assign' && res.advisor_analysis) {
        console.log('[ADVISOR] Analysis received:', key)
        setAnalyses(prev => ({ ...prev, [key]: res.advisor_analysis }))
      }

      // Clear analysis on unassign
      if (action === 'unassign') {
        setAnalyses(prev => {
          const next = { ...prev }
          delete next[key]
          return next
        })
      }

      if (res.game_state && onGsUpdate) {
        onGsUpdate(res.game_state)
      }
    } catch (e) {
      console.error(`[ADVISOR] ${action} failed:`, e)
      setError(e.message)
      setTimeout(() => setError(null), 3000)
    } finally {
      setLoading(null)
    }
  }

  // Collect active analyses for display
  const activeAnalyses = Object.entries(analyses).filter(
    ([key]) => advisors[key]?.assigned_this_turn
  )

  return (
    <div className="advisor-panel-7c">
      <div className="advisor-panel-header">
        <span className="advisor-panel-title">ADVISORS</span>
        <span className="advisor-slot-indicator">
          {assignedCount}/{slots} assigned today
        </span>
      </div>

      {error && (
        <div className="advisor-error">{error}</div>
      )}

      <div className="advisor-card-row">
        {Object.entries(advisors).map(([key, adv]) => {
          const meta = ADVISOR_META[key] || { icon: '👤', color: '#888', tint: '' }
          const tier = trustTier(adv.trust ?? 75)
          const isAssigned = adv.assigned_this_turn
          const isLoading = loading === key
          const canAssign = !isAssigned && assignedCount < slots

          return (
            <div
              key={key}
              className={`advisor-card-7c ${isAssigned ? 'advisor-assigned' : ''}`}
              style={{ '--advisor-accent': meta.color }}
            >
              <div className="advisor-card-top">
                <span className="advisor-card-icon">{meta.icon}</span>
                <span className="advisor-card-name">{adv.name}</span>
              </div>

              {/* Trust tier bar — hides exact number */}
              <div className="advisor-trust-row">
                <span className={`advisor-trust-label ${tier.cls}`}>
                  {tier.label}
                </span>
                <div className="advisor-trust-bar">
                  <div
                    className={`advisor-trust-fill ${tier.cls}`}
                    style={{ width: `${Math.max(5, Math.min(100, adv.trust ?? 75))}%` }}
                  />
                </div>
              </div>

              {/* Defection warning */}
              {adv.defection_triggered && (
                <div className="advisor-defection-badge">⚠️ DEFECTED</div>
              )}

              {/* Assign/Unassign button */}
              <button
                className={`advisor-assign-btn ${isAssigned ? 'btn-assigned' : canAssign ? 'btn-available' : 'btn-disabled'}`}
                onClick={() => handleToggle(key)}
                disabled={isLoading || (!isAssigned && !canAssign)}
              >
                {isLoading ? 'Consulting...' : isAssigned ? 'ASSIGNED ✓' : 'Assign'}
              </button>
            </div>
          )
        })}
      </div>

      {/* Step 3: Analysis cards below advisor row */}
      {activeAnalyses.length > 0 && (
        <div className="advisor-analyses">
          {activeAnalyses.map(([key, text]) => {
            const meta = ADVISOR_META[key] || { icon: '👤', tint: '' }
            const adv = advisors[key]
            return (
              <div key={key} className={`advisor-analysis-card ${meta.tint}`}>
                <div className="analysis-card-header">
                  <span>{meta.icon} {adv?.name}</span>
                  <span className="analysis-label">ASSESSMENT</span>
                </div>
                <div className="analysis-card-body">
                  {text}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
