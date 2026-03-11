/**
 * AdvisorPanel — v2 full 9-archetype system with trust mechanics.
 * Shows staff roster advisors with archetype, character name, competence/loyalty,
 * background one-liner, trust bar, distortion indicator, assign/dismiss/eliminate.
 *
 * Analyses are persisted in gs.advisor_analyses (backend) — both the main game
 * screen and Cabinet drawer read from the same source.
 * Slot usage tracks unique advisors: gs.advisor_assigned_today is a Set (as array).
 * Dismissing does NOT free slots. Reassigning the same advisor does NOT consume a new slot.
 *
 * Props:
 *   gs        : game_state object (advisors dict keyed by archetype)
 *   sessionId : string
 *   onGsUpdate: (newGs) => void
 */

import { useState } from 'react'
import { api } from '../api'

const ARCHETYPE_COLORS = {
  finance_minister:   '#4caf50',
  technocrat:         '#00bcd4',
  diplomat:           '#42a5f5',
  general:            '#ff9800',
  propagandist:       '#9c27b0',
  militia_commander:  '#d32f2f',
  spy_chief:          '#607d8b',
  oligarch:           '#ffc107',
  fixer:              '#795548',
}

function trustTier(trust) {
  if (trust >= 70) return { label: 'High',     cls: 'trust-high' }
  if (trust >= 40) return { label: 'Medium',   cls: 'trust-med' }
  if (trust >= 20) return { label: 'Low',      cls: 'trust-low' }
  return              { label: 'Critical', cls: 'trust-critical' }
}

// Archetypes that have stat distortion
const DISTORTION_ARCHETYPES = new Set([
  'general', 'propagandist', 'militia_commander', 'spy_chief', 'oligarch', 'fixer'
])

export default function AdvisorPanel({ gs, sessionId, onGsUpdate }) {
  const [loading, setLoading] = useState(null)
  const [error, setError] = useState(null)
  const [confirmAction, setConfirmAction] = useState(null) // {key, action}
  const [minimizedAnalyses, setMinimizedAnalyses] = useState({}) // {key: true} for minimized

  const advisors = gs?.advisors
  if (!advisors || typeof advisors !== 'object' || Array.isArray(advisors)) {
    return (
      <div className="advisor-panel-7c">
        <div className="advisor-panel-header">
          <span className="advisor-panel-title">YOUR ADVISORS</span>
          <span className="advisor-slot-indicator" style={{ opacity: 0.5 }}>
            No advisors hired — hire from pool below
          </span>
        </div>
      </div>
    )
  }

  const entries = Object.entries(advisors).filter(([, v]) => v && typeof v === 'object' && v.archetype)
  if (entries.length === 0) {
    return (
      <div className="advisor-panel-7c">
        <div className="advisor-panel-header">
          <span className="advisor-panel-title">YOUR ADVISORS</span>
          <span className="advisor-slot-indicator" style={{ opacity: 0.5 }}>
            No advisors hired — hire from pool below
          </span>
        </div>
      </div>
    )
  }

  const slots = gs?.advisor_slots_available ?? 2
  // Unique advisors assigned this turn (Set semantics via array)
  const assignedToday = gs?.advisor_assigned_today ?? []
  const slotsUsed = new Set(assignedToday).size
  const assignedCount = entries.filter(([, a]) => a.assigned_this_turn).length
  const distortions = gs?.advisor_distortions || {}
  const hasDistortion = Object.keys(distortions).length > 0

  // Analyses from backend (persisted per-turn, shared across all AdvisorPanel instances)
  const analyses = gs?.advisor_analyses || {}

  async function handleToggle(key) {
    const adv = advisors[key]
    if (!adv) return
    const action = adv.assigned_this_turn ? 'unassign' : 'assign'
    // Reassigning same advisor doesn't consume a new slot
    const isReassign = assignedToday.includes(key)
    if (action === 'assign' && !isReassign && slotsUsed >= slots) return

    setLoading(key)
    setError(null)
    try {
      const res = action === 'assign'
        ? await api.assignAdvisor(sessionId, key)
        : await api.unassignAdvisor(sessionId, key)

      const advName = adv.name || key
      const newAssigned = action === 'assign'
      console.log(`[advisor] ASSIGN TOGGLED: ${advName} (${adv.archetype}) — now assigned=${newAssigned}`)

      // Log slot usage from response
      const newAssignedToday = res.game_state?.advisor_assigned_today ?? assignedToday
      const newSlotsUsed = new Set(newAssignedToday).size
      console.log(`[advisor] SLOT CHECK: assigned_today=${JSON.stringify(newAssignedToday)} slots_used=${newSlotsUsed}`)

      if (res.game_state && onGsUpdate) onGsUpdate(res.game_state)
    } catch (e) {
      console.error(`[ADVISOR] ${action} failed:`, e)
      setError(e.message)
      setTimeout(() => setError(null), 3000)
    } finally {
      setLoading(null)
    }
  }

  async function handleDismiss(key) {
    setLoading(key)
    setError(null)
    try {
      const res = await api.dismissAdvisor(sessionId, key)
      console.log('[ADVISOR] Dismissed:', key, res.message)
      if (res.game_state && onGsUpdate) onGsUpdate(res.game_state)
    } catch (e) {
      setError(e.message)
      setTimeout(() => setError(null), 3000)
    } finally {
      setLoading(null)
      setConfirmAction(null)
    }
  }

  async function handleEliminate(key) {
    setLoading(key)
    setError(null)
    try {
      const res = await api.eliminateAdvisor(sessionId, key)
      console.log('[ADVISOR] Eliminated:', key, res.message)
      if (res.game_state && onGsUpdate) onGsUpdate(res.game_state)
    } catch (e) {
      setError(e.message)
      setTimeout(() => setError(null), 3000)
    } finally {
      setLoading(null)
      setConfirmAction(null)
    }
  }

  // Show analysis cards for all advisors that have cached analyses (even if unassigned)
  // Only show if the advisor is still on staff
  const activeAnalyses = Object.entries(analyses).filter(
    ([key]) => advisors[key] && !minimizedAnalyses[key]
  )

  return (
    <div className="advisor-panel-7c">
      <div className="advisor-panel-header">
        <span className="advisor-panel-title">YOUR ADVISORS</span>
        <span className="advisor-slot-indicator">
          {slotsUsed}/{slots} slots used today
          {hasDistortion && <span title="Active advisor is distorting displayed stats" style={{ marginLeft: 6, color: '#ff9800' }}>⚠</span>}
        </span>
      </div>

      {error && <div className="advisor-error">{error}</div>}

      <div className="advisor-card-row">
        {entries.map(([key, adv]) => {
          const color = ARCHETYPE_COLORS[adv.archetype] || '#888'
          const tier = trustTier(adv.trust ?? 75)
          const isAssigned = adv.assigned_this_turn
          const isLoading = loading === key
          // Can assign if: not currently assigned AND (slots available OR this is a reassign)
          const isReassignCandidate = assignedToday.includes(key)
          const canAssign = !isAssigned && (slotsUsed < slots || isReassignCandidate)
          const hasDistort = DISTORTION_ARCHETYPES.has(adv.archetype) && isAssigned
          const isConfirming = confirmAction?.key === key
          const hasAnalysis = !!analyses[key]

          return (
            <div
              key={key}
              className={`advisor-card-7c ${isAssigned ? 'advisor-assigned' : ''}`}
              style={{ '--advisor-accent': color }}
            >
              <div className="advisor-card-top">
                <span className="advisor-card-icon">{adv.icon || '👤'}</span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="advisor-card-name">{adv.name}</div>
                  <div className="advisor-archetype-label">{adv.label}</div>
                </div>
                {hasDistort && <span className="advisor-distortion-icon" title="This advisor distorts displayed stats">⚠</span>}
              </div>

              {/* Competence / Loyalty stats */}
              <div className="advisor-stats-row">
                <span className="advisor-stat">C: {adv.competence ?? '—'}</span>
                <span className="advisor-stat">L: {adv.loyalty ?? '—'}</span>
              </div>

              {/* Background one-liner */}
              {adv.background && (
                <div className="advisor-background">{adv.background}</div>
              )}

              {/* Trust tier bar */}
              <div className="advisor-trust-row">
                <span className={`advisor-trust-label ${tier.cls}`}>{tier.label}</span>
                <div className="advisor-trust-bar">
                  <div
                    className={`advisor-trust-fill ${tier.cls}`}
                    style={{ width: `${Math.max(5, Math.min(100, adv.trust ?? 75))}%` }}
                  />
                </div>
              </div>

              {/* Betrayal warning */}
              {adv.has_betrayed && (
                <div className="advisor-defection-badge">⚠️ BETRAYED</div>
              )}

              {/* Actions */}
              {isConfirming ? (
                <div className="advisor-confirm-row">
                  <span style={{ fontSize: '0.65rem', color: confirmAction.action === 'eliminate' ? '#ff1744' : '#ff9800' }}>
                    {confirmAction.action === 'dismiss'
                      ? `Dismiss ${adv.name}?`
                      : `Eliminate ${adv.name}? $2B — cannot be undone.`}
                  </span>
                  <button className="advisor-confirm-btn" onClick={() => confirmAction.action === 'dismiss' ? handleDismiss(key) : handleEliminate(key)}>Yes</button>
                  <button className="advisor-confirm-btn" onClick={() => setConfirmAction(null)}>No</button>
                </div>
              ) : (
                <div className="advisor-action-row">
                  <button
                    className={`advisor-assign-btn ${isAssigned ? 'btn-assigned' : canAssign ? 'btn-available' : 'btn-disabled'}`}
                    onClick={() => handleToggle(key)}
                    disabled={isLoading || (!isAssigned && !canAssign)}
                    title={!isAssigned && !canAssign && slotsUsed >= slots ? 'All slots used this turn — dismissing does not free slots' : ''}
                  >
                    {isLoading ? '...' : isAssigned ? 'ASSIGNED ✓' : 'Assign'}
                  </button>
                  <button className="advisor-action-small" title="Dismiss" onClick={() => setConfirmAction({ key, action: 'dismiss' })} disabled={isLoading}>✕</button>
                  <button className="advisor-action-small advisor-elim-btn" title="Eliminate ($2B personal)" onClick={() => setConfirmAction({ key, action: 'eliminate' })} disabled={isLoading}>☠</button>
                </div>
              )}

              {/* Minimized analysis indicator — click to expand */}
              {hasAnalysis && minimizedAnalyses[key] && (
                <button
                  className="advisor-analysis-minimized"
                  onClick={() => setMinimizedAnalyses(prev => { const next = { ...prev }; delete next[key]; return next })}
                  title="Show assessment"
                >
                  📋 Assessment available
                </button>
              )}
            </div>
          )
        })}
      </div>

      {/* Analysis cards below advisor row — from gs.advisor_analyses (persisted backend) */}
      {activeAnalyses.length > 0 && (
        <div className="advisor-analyses">
          {activeAnalyses.map(([key, text]) => {
            const adv = advisors[key]
            const color = ARCHETYPE_COLORS[adv?.archetype] || '#888'
            return (
              <div key={key} className="advisor-analysis-card" style={{ borderLeftColor: color }}>
                <div className="analysis-card-header">
                  <span>{adv?.icon || '👤'} {adv?.name}</span>
                  <div style={{ display: 'flex', gap: '0.4rem', alignItems: 'center' }}>
                    <span className="analysis-label">ASSESSMENT</span>
                    <button
                      className="advisor-analysis-minimize-btn"
                      onClick={() => setMinimizedAnalyses(prev => ({ ...prev, [key]: true }))}
                      title="Minimize"
                    >
                      −
                    </button>
                  </div>
                </div>
                <div className="analysis-card-body">{text}</div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
