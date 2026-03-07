/**
 * PromiseTracker — Session 7D Step 3+4: Persistent covert promise display
 * with expandable backchannel history log.
 * Compact card shown in center panel during DIALOGUE phase.
 * Shows active promises grouped by NPC, detection risk, and full history toggle.
 * Renders when there are active promises OR backchannel history entries.
 */

import { useState } from 'react'

// Client-side detection risk — mirrors npc_engine.calculate_detection_risk
const BASE_RISK = { usa: 0.25, arabia: 0.20, eu: 0.15, dprg: 0.10 }
const OPSEC_MULT = { 0: 1.0, 1: 0.7, 2: 0.45 }

function calcDetectionRisk(npcKey, gs) {
  const base = BASE_RISK[npcKey] ?? 0.20
  const opsec = gs?.opsec_level ?? 0
  const mult = OPSEC_MULT[opsec] ?? 1.0
  let risk = base * mult

  const rel = gs?.relations || {}
  if (npcKey === 'usa' && (rel.usa ?? 50) < 30) risk *= 1.3
  if (npcKey === 'eu' && (rel.eu ?? 50) < 30) risk *= 1.2
  if (npcKey === 'dprg') risk *= 0.8

  return Math.min(1.0, risk)
}

function riskTier(risk) {
  if (risk < 0.15) return { label: 'LOW',      color: '#4db6ac' }
  if (risk < 0.30) return { label: 'MODERATE', color: '#ffb74d' }
  if (risk < 0.50) return { label: 'HIGH',     color: '#ff8a65' }
  return              { label: 'CRITICAL', color: '#ef5350' }
}

const NPC_NAMES = {
  usa:    'Bill Hartwell',
  arabia: 'Sadam',
  eu:     'Marsha',
  dprg:   'Ji-won Ryang',
}

const NPC_FLAGS = {
  usa: '🇺🇸', arabia: '🛢️', eu: '🇪🇺', dprg: '⚡',
}

export default function PromiseTracker({ gs }) {
  const [historyOpen, setHistoryOpen] = useState(false)

  const promises = (gs?.active_backchannel_promises || []).filter(p => p.promise_text && !p.resolved)
  const history = gs?.backchannel_history || []

  // Don't render if no promises and no history
  if (promises.length === 0 && history.length === 0) return null

  // Group promises by NPC
  const byNpc = {}
  promises.forEach(p => {
    const npc = p.npc_id
    if (!byNpc[npc]) byNpc[npc] = []
    byNpc[npc].push(p)
  })

  const npcKeys = Object.keys(byNpc)

  // Highest risk across all active promises
  let maxRisk = 0
  npcKeys.forEach(k => {
    const r = calcDetectionRisk(k, gs)
    if (r > maxRisk) maxRisk = r
  })
  const overallTier = riskTier(maxRisk)

  return (
    <div className="promise-tracker">
      <div className="promise-tracker-header">
        <span className="promise-tracker-title">🔒 COVERT COMMITMENTS</span>
        <span className="promise-tracker-risk" style={{ color: overallTier.color }}>
          {promises.length > 0 ? `${overallTier.label} EXPOSURE` : 'NO ACTIVE'}
        </span>
      </div>

      {/* Active promises grouped by NPC */}
      {npcKeys.map(npcKey => {
        const npcPromises = byNpc[npcKey]
        const risk = calcDetectionRisk(npcKey, gs)
        const tier = riskTier(risk)
        const name = NPC_NAMES[npcKey] || npcKey
        const flag = NPC_FLAGS[npcKey] || ''

        return (
          <div key={npcKey} className="promise-tracker-npc">
            <div className="promise-tracker-npc-header">
              <span>{flag} {name}</span>
              <span className="promise-tracker-npc-risk" style={{ color: tier.color }}>
                {Math.round(risk * 100)}% RISK
              </span>
            </div>
            {npcPromises.map((p, i) => (
              <div key={i} className="promise-tracker-item">
                <span className="promise-tracker-bullet" style={{ color: tier.color }}>▸</span>
                <span className="promise-tracker-text">{p.promise_text}</span>
                {p.turn && (
                  <span className="promise-tracker-turn">T{p.turn}</span>
                )}
              </div>
            ))}
          </div>
        )
      })}

      {/* Risk bar (only when promises exist) */}
      {promises.length > 0 && (
        <div className="promise-tracker-bar">
          <div
            className="promise-tracker-bar-fill"
            style={{
              width: `${Math.min(100, maxRisk * 100)}%`,
              background: overallTier.color,
            }}
          />
        </div>
      )}

      {/* Session 7D Step 4: Backchannel History Log toggle */}
      {history.length > 0 && (
        <>
          <button
            className="promise-tracker-history-toggle"
            onClick={() => setHistoryOpen(prev => !prev)}
          >
            {historyOpen ? '▾' : '▸'} BACKCHANNEL LOG ({history.length})
          </button>

          {historyOpen && (
            <div className="backchannel-history-log">
              {[...history].reverse().map((entry, i) => {
                const name = NPC_NAMES[entry.npc_id] || entry.npc_id
                const flag = NPC_FLAGS[entry.npc_id] || ''
                const detected = entry.detected_by
                  ? `DETECTED by ${entry.detected_by}`
                  : null

                return (
                  <div
                    key={i}
                    className={`bclog-entry ${detected ? 'bclog-detected' : ''}`}
                  >
                    <div className="bclog-entry-header">
                      <span>{flag} {name}</span>
                      <span className="bclog-turn">Turn {entry.turn || '?'}</span>
                    </div>
                    <div className="bclog-exchange">
                      <div className="bclog-player">
                        <span className="bclog-role">YOU:</span> {entry.player_message}
                      </div>
                      <div className="bclog-npc">
                        <span className="bclog-role">{name.toUpperCase()}:</span> {entry.response_text}
                      </div>
                    </div>
                    {entry.promise_made && entry.promise_text && (
                      <div className="bclog-promise">
                        📋 {entry.promise_text}
                      </div>
                    )}
                    {detected && (
                      <div className="bclog-detected-badge">
                        ⚠ {detected}
                      </div>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}
    </div>
  )
}
