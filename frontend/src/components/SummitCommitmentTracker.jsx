/**
 * SummitCommitmentTracker — Session 7E Step 3: Public commitment display.
 * Compact card shown in center panel during DIALOGUE phase.
 * Shows active and broken summit commitments with credibility bar.
 * Renders only when there are commitments OR credibility < 100.
 */

import { useState } from 'react'

export default function SummitCommitmentTracker({ gs }) {
  const [expanded, setExpanded] = useState(false)

  const commitments = gs?.active_summit_commitments || []
  const credibility = gs?.summit_credibility ?? 100
  const summitHistory = gs?.summit_history || []

  // Don't render if no commitments and credibility is full and no summit history
  if (commitments.length === 0 && credibility >= 100 && summitHistory.length === 0) return null

  const active = commitments.filter(c => !c.broken)
  const broken = commitments.filter(c => c.broken)

  const credClass = credibility >= 80 ? 'cred-high'
    : credibility >= 50 ? 'cred-mid'
    : 'cred-low'

  return (
    <div className="summit-commitment-tracker">
      <div className="sct-header">
        <span className="sct-title">🌐 PUBLIC COMMITMENTS</span>
        <span className={`sct-credibility ${credClass}`}>
          CREDIBILITY {Math.round(credibility)}
        </span>
      </div>

      {/* Credibility bar */}
      <div className="sct-bar">
        <div
          className={`sct-bar-fill ${credClass}`}
          style={{ width: `${Math.max(0, Math.min(100, credibility))}%` }}
        />
      </div>

      {/* Active commitments */}
      {active.length > 0 && (
        <div className="sct-section">
          {active.map((c, i) => (
            <div key={i} className="sct-item sct-item-active">
              <span className="sct-bullet">📋</span>
              <span className="sct-text">{c.commitment_text}</span>
              {c.day_made && (
                <span className="sct-day">D{c.day_made}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Broken commitments */}
      {broken.length > 0 && (
        <div className="sct-section">
          {broken.map((c, i) => (
            <div key={i} className="sct-item sct-item-broken">
              <span className="sct-bullet">❌</span>
              <span className="sct-text sct-text-broken">{c.commitment_text}</span>
              {c.day_made && (
                <span className="sct-day">D{c.day_made}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* No commitments yet but summit has occurred */}
      {commitments.length === 0 && summitHistory.length > 0 && (
        <div className="sct-empty">No active public commitments</div>
      )}

      {/* Summit history toggle */}
      {summitHistory.length > 0 && (
        <>
          <button
            className="sct-history-toggle"
            onClick={() => setExpanded(prev => !prev)}
          >
            {expanded ? '▾' : '▸'} SUMMIT LOG ({summitHistory.length})
          </button>

          {expanded && (
            <div className="sct-history-log">
              {[...summitHistory].reverse().map((entry, i) => (
                <div key={i} className="sct-history-entry">
                  <div className="sct-history-header">
                    <span>Era {entry.era ?? '?'} · Day {entry.day ?? '?'}</span>
                    {entry.commitments_made?.length > 0 && (
                      <span className="sct-history-commitments">
                        📋 {entry.commitments_made.length}
                      </span>
                    )}
                  </div>
                  <div className="sct-history-declaration">
                    {entry.player_declaration
                      ? `"${entry.player_declaration.length > 120
                          ? entry.player_declaration.slice(0, 120) + '…'
                          : entry.player_declaration}"`
                      : '(no declaration)'}
                  </div>
                  {entry.npc_reactions && entry.npc_reactions.length > 0 && (
                    <div className="sct-history-reactions">
                      {entry.npc_reactions.map((r, j) => {
                        const badge = r.reaction_type === 'endorse' ? '✅'
                          : r.reaction_type === 'challenge' ? '🔴'
                          : r.reaction_type === 'silence' ? '—'
                          : '○'
                        return (
                          <span key={j} className={`sct-history-reaction sct-rx-${r.reaction_type || 'neutral'}`}>
                            {badge} {r.npc_name || r.npc_id}
                          </span>
                        )
                      })}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
